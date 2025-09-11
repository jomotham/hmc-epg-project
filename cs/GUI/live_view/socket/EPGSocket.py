import socket
import threading
import json
import queue
import time
import sys
import logging

from PyQt6.QtCore import QObject, pyqtSignal

# Log output to console even if running in background thread
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="[%H:%M:%S]",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)

class SocketServer:
    """
    A bidirectional socket to connect the CS and ENGR UIs.
    Forwards EPG data and slider control events beteween the clients. 
    """
    def __init__(self, host = "localhost", port=16671):
        self.host: str = host                                                   # use "localhost" for interal socket
        self.port: int = port                                                   # arbitrary port
        self.clients: dict[str, socket.socket] = {"CS": None, "ENGR": None}     # map of client IDs to their connection objects
        self.running = False                                                    # whether the server is running
        self.ready_event = threading.Event()                                    # event to signal that the server is ready to receive connections
        self._server_socket: socket.socket = None                               # the socket connection
        self._current_time:float = time.perf_counter()                          # time tracker used in logging

        self.control_state: dict = {}                                           # the dictionary containing the current state of the controls

    def start(self):
        """
        Starts the server in a background thread, listening for incoming client connections.
        """
        if self.running:
            return
        self.running = True
        threading.Thread(target = self._listen, daemon = True).start()
        self.ready_event.wait()  # wait for server to fully initialize

    def stop(self):
        """
        Stops the server, closes all sockets, and disconnects any clients.
        """
        self.running = False
        logging.info("[SOCKET] Shutting down socket...")

        # Close client connections
        for client_id, client_sock in list(self.clients.items()):
            if client_sock:
                try:
                    client_sock.sendall('SERVER SHUTDOWN'.encode('utf-8'))
                    logging.info(f"[SOCKET] Disconnected {client_id}")
                except Exception as e:
                    logging.warning(f"[SOCKET] Error closing {client_id}: {e}")


        self.clients = {"CS": None, "ENGR": None}

        # Close server socket
        if self._server_socket:
            try:
                self._server_socket.close()
                logging.info("[SOCKET] Socket closed")
            except Exception as e:
                logging.warning(f"[SOCKET] Error closing socket: {e}")

        logging.info("[SOCKET] Shutdown complete")

    def _listen(self):
        """
        Internal loop that binds the server socket and accepts new connections.
        Spawns a new thread for each connected client.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            self._server_socket = server_sock
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.host, self.port))
            server_sock.listen(2)
            self.ready_event.set()
            logging.info(f"[SOCKET] Listening on {self.host}:{self.port}")

            while self.running:
                try:
                    conn, addr = self._server_socket.accept()
                    threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
                except OSError:
                    break  # socket closed
       
    def _handle_client(self, sock: socket.socket, addr):
        """
        Processes new client connections and begins reading messages from it.
        """
        client_id = None
        try:
            client_id = sock.recv(1024).decode().strip().split("=")[1]
            sock.sendall(b"ack\n")  # client acknowledged 
            if self.clients.get(client_id) is not None:  # duplicate connection
                sock.close()
                logging.info(f"[SOCKET] Ignoring duplicate client connection request from \"{client_id}\"")
                return

            self.clients[client_id] = sock

            # Get status of already-connected clients
            for peer_id, peer_sock in self.clients.items():
                if peer_id != client_id and peer_sock:
                    self.broadcast_peer_status(peer_id, "connected", target=client_id)

            # Notify other cilents of succesful connection
            self.broadcast_peer_status(client_id, "connected")
            logging.info(f"[SOCKET] Client \"{client_id}\" connected from {addr}")
            self._receive_loop(sock, client_id)
        except Exception as e:
            logging.warning(f"[SOCKET] Error in _handle_client: {e}")
        finally:
            if client_id:
                self.clients[client_id] = None         
                self.broadcast_peer_status(client_id, "disconnected")   
            try:
                sock.close()
            except:
                pass

    def broadcast_peer_status(self, changed_id: str, status: str, target: str = None):
        """
        Broadcasts a peer's status to all other clients or to a specific target client.
        - `changed_id`: ID of the client whose status changed.
        - `status`: "connected" or "disconnected"
        - `target`: if given, only send to this client (used when a new client joins).
        """
        message = json.dumps({
            "source": "socket",
            "type": "status",
            "peer_id": changed_id,
            "status": status
        }) + "\n"

        for client_id, client_sock in self.clients.items():
            if client_sock is None:
                continue
            if target is not None:
                if client_id == target:
                    try:
                        client_sock.sendall(message.encode('utf-8'))
                    except:
                        pass
            else:
                if client_id != changed_id:
                    try:
                        client_sock.sendall(message.encode('utf-8'))
                    except:
                        pass
    
    def _receive_loop(self, sock: socket.socket, client_id: str):
        """
        Backgroung loop to read newline-delimited JSON messages from the given client connection
        and dispatch them to the appropriate handler.
        """
        buffer = ""
        try:
            while True:
                if not self.clients.get(client_id):  # already removed externally
                    break

                chunk = sock.recv(1024)
                if not chunk:
                    logging.info(f"[SOCKET] Client \"{client_id}\" disconnected")
                    break

                buffer += chunk.decode('utf-8')
                
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self._process_message(line.strip(), client_id)
        except ConnectionResetError:
            logging.info(f"[SOCKET] Client \"{client_id}\" disconnected abruptly (reset)")
        except Exception as e:
            logging.warning(f"[SOCKET] Error in _receive_loop for \"{client_id}\": {e}")



    def _process_message(self, message: str, client_id: str):
        """
        Processes a single JSON-formatted message from a client.
        Delegates to control or data handlers based on message type.
        """
        try:
            message_dict = json.loads(message)
        except json.JSONDecodeError:
            logging.warning(f"[SOCKET] Invalid JSON from {client_id}: {message}")
            return
        
        message_type = message_dict["type"] 
        if message_type == "data": # time-voltage data
            self._forward_data(message_dict)

        elif message_type  == "control": # control value        
            if message_dict.get("source") == client_id:
                logging.info(f"[{client_id}] Control: {message_dict['name']} = {message_dict['value']}")        
                self.control_state[message_dict["name"]] = message_dict["value"]
                self._broadcast(message_dict, exclude=client_id)

        elif message_type == "state_sync":
            incoming_state = message_dict.get("value")
            logging.info(f"[{client_id}] Full state sync received with {len(incoming_state)} controls")

            # Update full state
            self.control_state.update(incoming_state)

            # Broadcast to CS
            self._broadcast(message_dict, exclude=client_id)

        else:
            logging.warning(f"[{client_id}] Unknown message type: {message_dict['type']}")
    
    def _forward_data(self, data: dict):
        """
        Forwards a simplified (timestamp, voltage) message from ENGR to CS.
        If CS is not connected, logs a warning.
        """
        cs_sock = self.clients.get("CS")
        if not cs_sock:
            if (time.perf_counter() - self._current_time) > 1: # only send every 1s
                logging.warning("[SOCKET] CS not connected, can't forward data.")
                self._current_time = time.perf_counter()
            return
        
        msg = {
            "source": "ENGR",
            "type": "data",
            "value": (data["value"][0], data["value"][1]),  # (unix timestamp, voltage)
        }
        cs_sock.sendall((json.dumps(msg) + "\n").encode("utf-8"))


    def _broadcast(self, message: dict, exclude: str = None):
        """
        Sends a JSON message to all connected clients, optionally excluding one.
        """
        serialized = json.dumps(message) + "\n"
        for client_id, sock in self.clients.items():
            if sock and client_id != exclude:
                try:
                    print(f"Sending to [{client_id}]")
                    sock.sendall(serialized.encode("utf-8"))
                except Exception as e:
                    logging.warning(f"[SOCKET] Failed to send to {client_id}: {e}")

  
class SocketClient(QObject):
    """
    A client class to connect to the socket and handle sending/receiving data it.
    Incoming messages are pulled from the recieve queue, and outgoing messages are placed in the send queue.
    """
    connectionChanged = pyqtSignal(bool)        # emitted when this client's connection changes
    peerConnectionChanged = pyqtSignal(bool)    # emitted when the other client's connection changes

    def __init__(self, client_id, host="localhost", port=16671, parent: QObject = None):
        """
        Initializes a new SocketClient instance.

        Parameters:
            client_id (str): A unique identifier for this client (e.g., "CS" or "ENGR").
            host (str): The server hostname or IP address to connect to.
            port (int): The server port to connect to.
            parent (QObject, optional): The parent QObject in the Qt hierarchy.
        """
        super().__init__()
        self.client_id: str = client_id         # identifying string for this client (e.g., CS, ENGR) 
        self.host: str = host                   # use "localhost" for interal socket
        self.port: int = port                   # arbitrary port
        self.parent = parent                    # the parent Qt object
        self.send_queue: queue = queue.Queue()  # queue to send data to other client
        self.recv_queue: queue = queue.Queue()  # queue to receive data from other client
        self.connected: bool = False            # whether the client is connected to the socket
        self._sock: socket.socket = None        # the socket connection
    def connect(self):
        """
        Attempts to connect to the server and begin communication.
        Starts background threads for sending and receiving data.
        Sends the client ID immediately upon connection.
        Emits `connectionChanged(True)` on success or `connectionChanged(False)` on failure.
        """
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect((self.host, self.port))

            # send initial message with client ID to socket
            self._sock.sendall(f"client_id={self.client_id}\n".encode('utf-8'))
            self.connected = True
            self.connectionChanged.emit(True)
    
            threading.Thread(target=self._send_loop, daemon=True).start()
            threading.Thread(target=self._recv_loop, daemon=True).start()
        except Exception as e:
            self.connected = False
            self.connectionChanged.emit(False)
            logging.warning(f"[SocketClient] Connection failed: {e}")



    def disconnect(self):
        """
        Gracefully disconnects from the server and closes the socket.
        Stops background communication threads.
        Emits `connectionChanged(False)` upon completion.
        """
        self.connected = False
        self.connectionChanged.emit(False)

        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # already closed or not a socket

            try:
                self._sock.close()
            except OSError:
                pass  # already closed

            self._sock = None

        
    def send(self, data: dict):
        """
        Queues a dictionary for sending to the server as a JSON-formatted message.

        Parameters:
            data (dict): The data to send.
        """
        self.send_queue.put_nowait(data)

    def receive(self):
        """
        Attempts to retrieve a received message from the receive queue.

        Returns:
            (str or dict or None): The next message if available, or None if the queue is empty.
        """
        try:
            return self.recv_queue.get_nowait()
        except queue.Empty:
            return None


    def _send_loop(self):
        """
        Internal method: runs in a background thread.
        Continuously reads from the send queue and transmits messages to the server.
        Terminates if the socket is closed or an error occurs.
        """
        while self.connected:
            try:
                msg = self.send_queue.get(timeout=0.1)
                json_str = json.dumps(msg) + "\n"
                self._sock.sendall(json_str.encode("utf-8"))
            except queue.Empty:
                continue
            except Exception as e:
                logging.info("[SocketClient SEND ERROR]", e)
                self.connected = False
                break

    def _recv_loop(self):
        """
        Internal method: runs in a background thread.
        Continuously reads from the socket and places incoming messages into the receive queue.
        Also handles peer connection status updates and filters self-originating messages.
        Terminates if the socket is closed or an error occurs.
        """
        buffer = ""
        while self.connected:
            try:
                message = self._sock.recv(1024).decode('utf-8')
                
                buffer += message
                while '\n' in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    if "SERVER SHUTDOWN" in line:
                        self.disconnect()
                        break
                    elif line.strip() == "ack": # server acknowledgement
                        self.recv_queue.put_nowait(line)
                        continue

                    

                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        # Fallback: non-JSON line, treat as plain message
                        print(f"JSON Decode Error: placing raw message in to queue: {line}")
                        self.recv_queue.put_nowait(line)
                        continue
                    if msg.get("source") == self.client_id:
                        continue  # don't process message from this client
                    if msg.get("type") == "status":
                        peer_id = msg.get("peer_id")
                        status = msg.get("status")
                        is_connected = (status == "connected")
                        if peer_id != self.client_id:  # only care about the *other* client
                            self.peerConnectionChanged.emit(is_connected)
                    else:
                        self.recv_queue.put_nowait(msg)

            except ConnectionResetError:
                if self.connected:
                    logging.info(f"[SOCKET] Socket remotely closed")
                break
            except Exception as e:
                if self.connected:
                    logging.info(f"[SocketClient RECV ERROR] {e}")
                break

        self.connected = False
        self.connectionChanged.emit(False)