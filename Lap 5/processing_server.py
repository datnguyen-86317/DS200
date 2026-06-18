import socket
import json
import base64
import cv2
import numpy as np
from datetime import datetime

PROCESSING_HOST = "localhost"
PROCESSING_PORT = 6200

STORAGE_HOST = "localhost"
STORAGE_PORT = 6300


def send_json(connection, payload):
    message = json.dumps(payload, ensure_ascii=False) + "\n"
    connection.sendall(message.encode("utf-8"))


def connect_to_storage():
    storage_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    storage_socket.connect((STORAGE_HOST, STORAGE_PORT))
    print(f"[PROCESSING] Connected to storage server {STORAGE_HOST}:{STORAGE_PORT}")
    return storage_socket


def decode_image(image_b64):
    image_bytes = base64.b64decode(image_b64)
    np_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return frame


def create_people_detector():
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    return hog


def detect_people(frame, detector):
    boxes, weights = detector.detectMultiScale(
        frame,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.05
    )

    results = []

    for index, (x, y, w, h) in enumerate(boxes):
        score = float(weights[index]) if len(weights) > index else 0.0

        results.append({
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
            "score": score
        })

    return results


def handle_camera_connection(camera_connection, camera_address, storage_connection):
    print(f"[PROCESSING] Camera connected from {camera_address}")

    detector = create_people_detector()
    buffer = b""

    while True:
        data = camera_connection.recv(65536)

        if not data:
            print("[PROCESSING] Camera disconnected")
            break

        buffer += data

        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)

            if not line.strip():
                continue

            try:
                payload = json.loads(line.decode("utf-8"))

                frame_id = payload.get("frame_id")
                camera_id = payload.get("camera_id", "camera_01")
                image_b64 = payload.get("image_b64")

                if not image_b64:
                    print("[PROCESSING] Missing image_b64")
                    continue

                frame = decode_image(image_b64)

                if frame is None:
                    print(f"[PROCESSING] Cannot decode frame_id={frame_id}")
                    continue

                boxes = detect_people(frame, detector)

                result = {
                    "type": "detection_result",
                    "camera_id": camera_id,
                    "frame_id": frame_id,
                    "timestamp": payload.get("timestamp"),
                    "processed_at": datetime.now().isoformat(),
                    "person_count": len(boxes),
                    "boxes": boxes
                }

                send_json(storage_connection, result)

                ack = {
                    "type": "ack",
                    "frame_id": frame_id,
                    "status": "processed",
                    "person_count": len(boxes)
                }

                send_json(camera_connection, ack)

                print(
                    f"[PROCESSING] frame_id={frame_id}, "
                    f"person_count={len(boxes)}"
                )

            except Exception as e:
                print(f"[PROCESSING] Error: {e}")


def main():
    storage_connection = connect_to_storage()

    processing_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    processing_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    processing_socket.bind((PROCESSING_HOST, PROCESSING_PORT))
    processing_socket.listen(1)

    print(f"[PROCESSING] Listening on {PROCESSING_HOST}:{PROCESSING_PORT}")

    while True:
        camera_connection, camera_address = processing_socket.accept()
        handle_camera_connection(
            camera_connection,
            camera_address,
            storage_connection
        )


if __name__ == "__main__":
    main()