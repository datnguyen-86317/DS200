import socket
import json
from datetime import datetime

HOST = "localhost"
PORT = 6300
OUTPUT_FILE = "results.jsonl"


def handle_client(connection, address):
    print(f"[STORAGE] Connected from {address}")
    buffer = b""

    while True:
        data = connection.recv(65536)

        if not data:
            print("[STORAGE] Client disconnected")
            break

        buffer += data

        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)

            if not line.strip():
                continue

            try:
                result = json.loads(line.decode("utf-8"))
                result["stored_at"] = datetime.now().isoformat()

                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")

                print(
                    f"[STORAGE] Saved frame_id={result.get('frame_id')} "
                    f"person_count={result.get('person_count')}"
                )

            except Exception as e:
                print(f"[STORAGE] Error parsing result: {e}")


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    print(f"[STORAGE] Listening on {HOST}:{PORT}")

    while True:
        connection, address = server_socket.accept()
        handle_client(connection, address)


if __name__ == "__main__":
    main()