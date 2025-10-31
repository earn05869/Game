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
		
		# Flag to track ready state
		self.server_ready = False
	
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
	
	def send_position(self, x: float, y: float):
		"""
		Send current position to server.
		"""
		if not self.connected or not self.socket:
			return
		
		try:
			message = json.dumps({'x': x, 'y': y})
			self.socket.sendall(message.encode('utf-8'))
		except Exception as e:
			print(f"[NETWORK] Failed to send position: {e}")
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
				# Otherwise it's a position update
				elif self.on_position_update:
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
	
	def is_connected(self) -> bool:
		"""Check if still connected to server."""
		return self.connected

