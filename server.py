"""
Multiplayer Server for BindGame
Handles 2-player connection and position synchronization
"""
import socket
import threading
import json
import time
from typing import Dict, List

# ===== CONFIGURATION =====
MAX_PLAYERS = 2
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5555

# Global shared state
connected_players: Dict[str, dict] = {}  # {player_id: {socket, addr, position}}
lock = threading.Lock()

def get_local_ip():
	"""Get local IP address."""
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.connect(("8.8.8.8", 80))
		ip = s.getsockname()[0]
	except Exception:
		ip = "127.0.0.1"
	finally:
		s.close()
	return ip

def handle_client(client_socket, addr, player_id):
	"""
	Handle individual client connection.
	Receives position updates and broadcasts to other players.
	"""
	global connected_players
	
	print(f"[SERVER] Player {player_id} ({addr}) connected")
	
	try:
		while True:
			data = client_socket.recv(1024)
			if not data:
				print(f"[SERVER] Player {player_id} disconnected (no data)")
				break
			
			try:
				message = data.decode('utf-8').strip()
				
				# Check for quit command
				if message.lower() == "quit" or message == "":
					print(f"[SERVER] Player {player_id} requested disconnect")
					break
				
				# Parse JSON message
				msg_data = json.loads(message)
				msg_type = msg_data.get('type')
				
				# Handle position update
				if msg_type == 'position' or 'x' in msg_data:
					pos_data = {'x': msg_data.get('x', 0), 'y': msg_data.get('y', 0)}
					
					# Update player position in shared state
					with lock:
						if player_id in connected_players:
							connected_players[player_id]['position'] = pos_data
					
					# Broadcast to all other players
					broadcast_position(player_id, pos_data)
				
				# Handle key event (only from host/player 1)
				elif msg_type == 'key_event' and player_id == 1:
					event_data = msg_data.get('event', {})
					# Forward key event to join player (player 2)
					broadcast_key_event(event_data)
				
				# Handle dialogue state (only from host/player 1)
				elif msg_type == 'dialogue_state' and player_id == 1:
					dialog_state = msg_data.get('state', {})
					# Forward dialogue state to join player (player 2)
					broadcast_dialogue_state(dialog_state)
				
				# Note: Input keys (w/a/s/d) are no longer sent
				# Join player uses position from host directly
				
			except json.JSONDecodeError as e:
				print(f"[SERVER] Invalid JSON from player {player_id}: {e}")
			except Exception as e:
				print(f"[SERVER] Error handling message from player {player_id}: {e}")
	
	except Exception as e:
		print(f"[SERVER] Error in player {player_id} thread: {e}")
	
	finally:
		# Remove player from shared state
		with lock:
			if player_id in connected_players:
				del connected_players[player_id]
		
		client_socket.close()
		print(f"[SERVER] Player {player_id} thread closed")

def broadcast_position(sender_id: int, position: dict):
	"""
	Broadcast sender's position to all other connected players.
	"""
	with lock:
		for pid, player_data in connected_players.items():
			if pid != sender_id:
				try:
					# Send update with sender_id so clients know which player
					message = json.dumps({
						'player_id': sender_id,
						'position': position
					})
					player_data['socket'].sendall(message.encode('utf-8'))
				except Exception as e:
					print(f"[SERVER] Failed to send to player {pid}: {e}")

def broadcast_key_event(event_data: dict):
	"""
	Broadcast key event from host to join player (for synchronized input).
	"""
	with lock:
		# Only send to player 2 (join player)
		if 2 in connected_players:
			try:
				message = json.dumps({
					'type': 'key_event',
					'event': event_data
				})
				connected_players[2]['socket'].sendall(message.encode('utf-8'))
			except Exception as e:
				print(f"[SERVER] Failed to send key event to player 2: {e}")

def broadcast_dialogue_state(dialog_state: dict):
	"""
	Broadcast dialogue state from host to join player.
	"""
	with lock:
		# Only send to player 2 (join player)
		if 2 in connected_players:
			try:
				message = json.dumps({
					'type': 'dialogue_state',
					'state': dialog_state
				})
				connected_players[2]['socket'].sendall(message.encode('utf-8'))
			except Exception as e:
				print(f"[SERVER] Failed to send dialogue state to player 2: {e}")

# broadcast_input removed - join player now uses position from host directly
# No need to send input keys (w/a/s/d) anymore

def get_all_positions() -> dict:
	"""Get all player positions for initial sync."""
	with lock:
		return {
			pid: player_data['position']
			for pid, player_data in connected_players.items()
		}

def start_server():
	"""
	Main server function.
	Listens for connections and waits until MAX_PLAYERS connected.
	"""
	global connected_players
	
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	
	try:
		server.bind((HOST, PORT))
		server.listen(MAX_PLAYERS)
		
		local_ip = get_local_ip()
		print("=" * 60)
		print(f"[SERVER] Server started on {local_ip}:{PORT}")
		print(f"[SERVER] Waiting for {MAX_PLAYERS} players to connect...")
		print("=" * 60)
		
		# Accept connections until we have MAX_PLAYERS
		while len(connected_players) < MAX_PLAYERS:
			client_socket, addr = server.accept()
			player_id = len(connected_players) + 1  # Assign ID (1 or 2)
			
			# Initialize player data
			with lock:
				connected_players[player_id] = {
					'socket': client_socket,
					'addr': addr,
					'position': {'x': 0, 'y': 0}  # Default position
				}
			
			# Send player ID to client
			client_socket.sendall(json.dumps({
				'player_id': player_id,
				'message': 'connected'
			}).encode('utf-8'))
			
			# Start thread to handle this player
			client_thread = threading.Thread(
				target=handle_client,
				args=(client_socket, addr, player_id),
				daemon=True
			)
			client_thread.start()
			
			print(f"[SERVER] Player {player_id} joined. Total: {len(connected_players)}/{MAX_PLAYERS}")
		
		print("=" * 60)
		print(f"[SERVER] All {MAX_PLAYERS} players connected!")
		print("[SERVER] Sending 'ready' signal to all players...")
		print("=" * 60)
		
		# Send "ready" signal to all players
		ready_message = json.dumps({'message': 'ready'})
		with lock:
			for pid, player_data in connected_players.items():
				try:
					player_data['socket'].sendall(ready_message.encode('utf-8'))
					print(f"[SERVER] Sent ready signal to Player {pid}")
				except Exception as e:
					print(f"[SERVER] Failed to send ready to Player {pid}: {e}")
		
		# Keep server running
		try:
			while True:
				time.sleep(1)
				
				# Check if we still have players
				with lock:
					if len(connected_players) == 0:
						print("[SERVER] No players remaining, shutting down")
						break
		except KeyboardInterrupt:
			print("\n[SERVER] Shutdown requested")
		
	except Exception as e:
		print(f"[SERVER] Error: {e}")
	
	finally:
		server.close()
		print("[SERVER] Server closed")

if __name__ == "__main__":
	start_server()
