"""
Network Client for BindGame
Handles connection to server and position synchronization
"""
import socket
import json
import threading
from typing import Optional, Callable

class NetworkClient:
	"""
	Client for connecting to multiplayer server.
	Handles sending position updates and receiving other players' positions.
	"""
	
	def __init__(self, host: str = "localhost", port: int = 5555):
		self.host = host
		self.port = port
		self.socket: Optional[socket.socket] = None
		self.player_id: Optional[int] = None
		self.connected = False
		self.listening = False
		self.receive_thread: Optional[threading.Thread] = None
		
		# Callback for when we receive position updates
		self.on_position_update: Optional[Callable] = None
		
		# Callback for when server is ready
		self.on_ready: Optional[Callable] = None
		
		# Callback for when we receive input updates (for join player)
		self.on_input_update: Optional[Callable] = None
		
		# Callback for when we receive key events (for join player)
		self.on_key_event: Optional[Callable] = None
		
		# Flag to track ready state
		self.server_ready = False
		
		# Received input keys (for join player)
		self.received_input_keys = {}
		
		# Queue for received key events
		self.received_key_events = []
		
		# Received dialogue state (for join player)
		self.received_dialogue_state = None
		
		# Received teleport data (for join player)
		self.received_teleport_data = None
	
	def connect(self) -> bool:
		"""
		Connect to the server.
		Returns True if successful, False otherwise.
		"""
		try:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect((self.host, self.port))
			self.connected = True
			
			# Receive player ID from server
			data = self.socket.recv(1024)
			message = json.loads(data.decode('utf-8'))
			
			self.player_id = message.get('player_id')
			print(f"[NETWORK] Connected as Player {self.player_id}")
			
			# Start receiving thread
			self.listening = True
			self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
			self.receive_thread.start()
			
			return True
			
		except Exception as e:
			print(f"[NETWORK] Connection failed: {e}")
			self.connected = False
			return False
	
	def set_ready_callback(self, callback: Callable):
		"""
		Set callback function to be called when server sends ready signal.
		"""
		self.on_ready = callback
	
	def is_ready(self) -> bool:
		"""Check if server has sent ready signal."""
		return self.server_ready
	
	def disconnect(self):
		"""Disconnect from the server."""
		self.listening = False
		self.connected = False
		
		if self.socket:
			try:
				self.socket.sendall("quit".encode('utf-8'))
				self.socket.close()
			except:
				pass
		
		print("[NETWORK] Disconnected from server")
	
	def send_position(self, x: float, y: float, direction: Optional[str] = None):
		"""
		Send current position (and optional facing direction) to server.
		"""
		if not self.connected or not self.socket:
			return
		
		try:
			payload = {'type': 'position', 'x': x, 'y': y}
			if direction:
				payload['dir'] = direction
			message = json.dumps(payload)
			self.socket.sendall(message.encode('utf-8'))
		except Exception as e:
			print(f"[NETWORK] Failed to send position: {e}")
			self.connected = False
	
	def send_input(self, keys: dict):
		"""
		Send input keys to server (host only).
		keys: dict with keys like {'w': bool, 'a': bool, 's': bool, 'd': bool, 'e': bool}
		"""
		if not self.connected or not self.socket:
			return
		
		try:
			message = json.dumps({'type': 'input', 'keys': keys})
			self.socket.sendall(message.encode('utf-8'))
		except Exception as e:
			print(f"[NETWORK] Failed to send input: {e}")
			self.connected = False
	
	def send_input_event(self, event: dict):
		"""
		Send key event to server (host only).
		event: dict like {'type': 'KEYDOWN', 'key': 'e'}
		"""
		if not self.connected or not self.socket:
			return
		
		try:
			message = json.dumps({'type': 'key_event', 'event': event})
			self.socket.sendall(message.encode('utf-8'))
		except Exception as e:
			print(f"[NETWORK] Failed to send key event: {e}")
			self.connected = False
	
	def _receive_loop(self):
		"""
		Background thread to receive messages from server.
		"""
		while self.listening and self.connected:
			try:
				if not self.socket:
					break
				
				data = self.socket.recv(1024)
				if not data:
					print("[NETWORK] Server disconnected")
					self.connected = False
					break
				
				message = json.loads(data.decode('utf-8'))
				
				# Check if it's a ready message
				if message.get('message') == 'ready':
					self.server_ready = True
					if self.on_ready:
						self.on_ready()
				# Check if it's a key event (for synchronized input)
				elif message.get('type') == 'key_event':
					event_data = message.get('event', {})
					self.received_key_events.append(event_data)
					if self.on_key_event:
						self.on_key_event(event_data)
				# Check if it's a dialogue state update
				elif message.get('type') == 'dialogue_state':
					self.received_dialogue_state = message.get('state', {})
				# Check if it's a teleport update
				elif message.get('type') == 'teleport':
					self.received_teleport_data = {
						'target_map': message.get('target_map'),
						'target_spawn': message.get('target_spawn')
					}
				# Check if it's an input update
				elif message.get('type') == 'input':
					self.received_input_keys = message.get('keys', {})
					if self.on_input_update:
						self.on_input_update(self.received_input_keys)
				# Otherwise it's a position update
				elif message.get('type') == 'position' or 'position' in message:
					if self.on_position_update:
						self.on_position_update(message)
					
			except json.JSONDecodeError:
				continue
			except Exception as e:
				print(f"[NETWORK] Receive error: {e}")
				self.connected = False
				break
	
	def set_position_callback(self, callback: Callable):
		"""
		Set callback function to be called when receiving position updates.
		Callback will receive: {'player_id': int, 'position': {'x': float, 'y': float}}
		"""
		self.on_position_update = callback
	
	def set_input_callback(self, callback: Callable):
		"""
		Set callback function to be called when receiving input updates.
		Callback will receive: dict of input keys
		"""
		self.on_input_update = callback
	
	def set_key_event_callback(self, callback: Callable):
		"""
		Set callback function to be called when receiving key events.
		Callback will receive: dict of event like {'type': 'KEYDOWN', 'key': 'e'}
		"""
		self.on_key_event = callback
	
	def get_received_input_keys(self) -> dict:
		"""
		Get the latest received input keys (for join player).
		After reading, input is cleared to prevent persistence.
		"""
		keys = self.received_input_keys.copy()
		# Clear input after reading to prevent persistence
		# This ensures input doesn't carry over to next frame
		self.received_input_keys = {
			'w': False,
			'a': False,
			's': False,
			'd': False,
			'e': False
		}
		return keys
	
	def pop_received_key_events(self) -> list:
		"""Get and clear received key events queue."""
		events = self.received_key_events.copy()
		self.received_key_events.clear()
		return events
	
	def send_dialogue_state(self, state: dict):
		"""Send dialogue state to server (host only)."""
		if not self.connected or not self.socket:
			return
		
		try:
			message = json.dumps({'type': 'dialogue_state', 'state': state})
			self.socket.sendall(message.encode('utf-8'))
		except Exception as e:
			print(f"[NETWORK] Failed to send dialogue state: {e}")
			self.connected = False
	
	def get_received_dialogue_state(self) -> dict:
		"""Get the latest received dialogue state (for join player)."""
		return self.received_dialogue_state
	
	def send_teleport(self, target_map: str, target_spawn: str):
		"""Send teleport data to server (host only)."""
		if not self.connected or not self.socket:
			return
		
		try:
			message = json.dumps({
				'type': 'teleport',
				'target_map': target_map,
				'target_spawn': target_spawn
			})
			self.socket.sendall(message.encode('utf-8'))
		except Exception as e:
			print(f"[NETWORK] Failed to send teleport: {e}")
			self.connected = False
	
	def get_received_teleport_data(self) -> dict:
		"""Get the latest received teleport data (for join player)."""
		data = self.received_teleport_data
		# Clear after reading to prevent retriggering
		self.received_teleport_data = None
		return data
	
	def is_connected(self) -> bool:
		"""Check if still connected to server."""
		return self.connected

