import zmq
import argparse
import pickle
import json
import socket
import numpy as np
import threading
from nitrogen.inference_session import InferenceSession

# Lock to ensure thread safety for the stateful InferenceSession
session_lock = threading.Lock()

def handle_request(session, request, raw_image=None):
    """Universal request handler for ZeroMQ+Pickle and TCP+JSON+RawBytes protocols."""
    with session_lock:
        if request["type"] == "reset":
            session.reset()
            return {"status": "ok"}
        elif request["type"] == "info":
            return {"status": "ok", "info": session.info()}
        elif request["type"] == "predict":
            # If this is a Pickle request, the image is already inside the object
            image = raw_image if raw_image is not None else request.get("image")
            result = session.predict(image)
            return {"status": "ok", "pred": result}
        return {"status": "error", "message": "Unknown type"}

def run_zmq_server(session, port):
    """Runs the ZeroMQ server (original protocol)."""
    context = zmq.Context()
    socket_zmq = context.socket(zmq.REP)
    socket_zmq.bind(f"tcp://*:{port}")
    print(f"ZMQ Server running on port {port}")
    
    while True:
        try:
            msg = socket_zmq.recv()
            req = pickle.loads(msg)
            res = handle_request(session, req)
            socket_zmq.send(pickle.dumps(res))
        except Exception as e:
            print(f"ZMQ Error: {e}")

def run_tcp_server(session, port):
    """Runs the simple TCP server (for BizHawk/Lua)."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(('0.0.0.0', port))
    except OSError as e:
        print(f"Error binding TCP port {port}: {e}")
        return

    server.listen(1)
    print(f"Simple TCP Server (JSON+Bytes) running on port {port}")
    
    while True:
        conn, addr = server.accept()
        # print(f"TCP Client connected from {addr}")
        try:
            while True:
                # 1. Read request header (JSON string until \n)
                # Read byte by byte until newline to avoid over-reading the pixel data
                line_bytes = b""
                while True:
                    char = conn.recv(1)
                    if not char: 
                        break # Connection closed or empty
                    if char == b'\n':
                        break
                    line_bytes += char
                
                if not line_bytes: 
                    break

                try:
                    req = json.loads(line_bytes.decode('utf-8'))
                except json.JSONDecodeError:
                    print("Invalid JSON received")
                    break

                img = None
                if req.get("type") == "predict":
                    # 2. Read exactly 196608 pixel bytes (256x256x3)
                    expected_bytes = 256 * 256 * 3
                    raw_data = b""
                    while len(raw_data) < expected_bytes:
                        chunk = conn.recv(expected_bytes - len(raw_data))
                        if not chunk: break
                        raw_data += chunk
                    
                    if len(raw_data) == expected_bytes:
                        # Convert bytes to numpy array for the model
                        img = np.frombuffer(raw_data, dtype=np.uint8).reshape(256, 256, 3)
                    else:
                        print("Incomplete image data received")
                        break

                # 3. Process and send JSON response
                res = handle_request(session, req, raw_image=img)
                
                # Convert numpy to lists for JSON
                if "pred" in res:
                    res["pred"] = {k: v.tolist() for k, v in res["pred"].items()}
                
                response_json = json.dumps(res)
                conn.sendall((response_json + "\n").encode('utf-8'))
        except Exception as e:
            print(f"TCP Connection error: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ckpt", type=str)
    parser.add_argument("--zmq-port", type=int, default=5555, help="Port for ZeroMQ server")
    parser.add_argument("--tcp-port", type=int, default=5556, help="Port for Simple TCP server")
    
    args = parser.parse_args()

    session = InferenceSession.from_ckpt(args.ckpt)

    # Start TCP server in a daemon thread
    tcp_thread = threading.Thread(target=run_tcp_server, args=(session, args.tcp_port), daemon=True)
    tcp_thread.start()

    # Run ZMQ server in the main thread
    try:
        run_zmq_server(session, args.zmq_port)
    except KeyboardInterrupt:
        print("\nShutting down server...")
