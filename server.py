from hmac import new
import socket
from GameConfig import MAX_PLAYER
from _thread import start_new_thread
from Script.ShareMemory import ShareMemory, shared_data

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

server_ip = get_local_ip()
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((server_ip, port))
s.listen(MAX_PLAYER)
print(f"Server started on {server_ip}:{port}, waiting for {MAX_PLAYER} players...")

share_mem: ShareMemory = ShareMemory()

def threaded_client(conn, addr):
    try:
        while True:
            data = conn.recv(2048)
            if not data:  # <-- disconnect เงียบๆ หรือปิด socket จาก client
                print(f"Player {addr} disconnected (recv empty)")
                break

            message = data.decode('utf-8').strip()
            if message.lower() == "quit":
                print(f"Player {player} requested to quit.")
                break

            print(f"From Player {player}: {message}")
            # send data back to client (echo)
            conn.sendall(str.encode(f"Echo: {message}"))
    except Exception as e:
        print(f"Exception: player {player} disconnected: {e}")
    finally:
        # cleanup: เช่น ลบออกจาก shared_data
        conn.close()
        print(f"Thread for player {player} closed.")

while shared_data["connected_players"] < MAX_PLAYER:
    conn, addr = s.accept()
    print(f"Connected to: {addr}")
    start_new_thread(threaded_client, (conn, addr))
    shared_data["connected_players"] += 1

print("Max player reached, server no longer accepts new connections.")
s.close()