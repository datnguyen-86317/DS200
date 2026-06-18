import socket
import json
import base64
import cv2
import sys
import time
from datetime import datetime

PROCESSING_HOST = "localhost"
PROCESSING_PORT = 6200

CAMERA_ID = "camera_01"
JPEG_QUALITY = 70

# Gửi mỗi N frame để giảm tải xử lý
FRAME_SKIP = 5


def send_json(connection, payload):
    message = json.dumps(payload, ensure_ascii=False) + "\n"
    connection.sendall(message.encode("utf-8"))


def receive_one_json(connection):
    buffer = b""

    while True:
        data = connection.recv(65536)

        if not data:
            return None

        buffer += data

        if b"\n" in buffer:
            line, _ = buffer.split(b"\n", 1)
            return json.loads(line.decode("utf-8"))


def encode_frame_to_base64(frame):
    encode_params = [
        int(cv2.IMWRITE_JPEG_QUALITY),
        JPEG_QUALITY
    ]

    success, encoded_image = cv2.imencode(".jpg", frame, encode_params)

    if not success:
        return None

    image_bytes = encoded_image.tobytes()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    return image_b64


def get_video_source():
    if len(sys.argv) < 2:
        return 0

    source = sys.argv[1]

    if source.isdigit():
        return int(source)

    return source


def main():
    source = get_video_source()

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print("[CAMERA] Cannot open camera/video source")
        return

    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.connect((PROCESSING_HOST, PROCESSING_PORT))

    print(f"[CAMERA] Connected to processing server {PROCESSING_HOST}:{PROCESSING_PORT}")

    frame_id = 0
    raw_frame_index = 0

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("[CAMERA] No more frames")
                break

            raw_frame_index += 1

            if raw_frame_index % FRAME_SKIP != 0:
                continue

            frame_id += 1

            image_b64 = encode_frame_to_base64(frame)

            if image_b64 is None:
                print(f"[CAMERA] Cannot encode frame_id={frame_id}")
                continue

            payload = {
                "type": "frame",
                "camera_id": CAMERA_ID,
                "frame_id": frame_id,
                "timestamp": datetime.now().isoformat(),
                "encoding": "jpg",
                "image_b64": image_b64
            }

            send_json(connection, payload)

            ack = receive_one_json(connection)

            if ack:
                print(
                    f"[CAMERA] frame_id={ack.get('frame_id')} "
                    f"person_count={ack.get('person_count')}"
                )

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("[CAMERA] Stopped by user")

    finally:
        cap.release()
        connection.close()


if __name__ == "__main__":
    main()