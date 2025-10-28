import socket
from _thread import *
import pickle

# หา IP ของเครื่องเองอัตโนมัติ
def get_local_ip():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		# ต่อกับ IP ภายนอกเพื่อหา IP ภายใน (ไม่ต้องจริงจังเชื่อมต่อ)
		s.connect(("8.8.8.8", 80))
		ip = s.getsockname()[0]
	except:
		ip = "127.0.0.1"
	finally:
		s.close()
	return ip

server_ip = get_local_ip()
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((server_ip, port))
s.listen(4)
print(f"Server started on {server_ip}:{port}, waiting for connections...")

players = []

def threaded_client(conn, player):
	conn.send(pickle.dumps(players[player]))
	while True:
		try:
			data = pickle.loads(conn.recv(2048))
			players[player] = data
			if not data:
				break

			other_players = [p for i,p in enumerate(players) if i != player]
			conn.sendall(pickle.dumps(other_players))
		except:
			break
	conn.close()

currentPlayer = 0
while currentPlayer < 2:
	conn, addr = s.accept()
	print(f"Connected to: {addr}")
	start_new_thread(threaded_client, (conn, currentPlayer))
	currentPlayer += 1
s.close()