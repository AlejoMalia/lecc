# -*- coding: utf-8 -*-
import json
import socket
import requests
import threading
import time
import queue
import serial
from flask import Flask, request
import io
import paho.mqtt.client as mqtt
import smbus2 as smbus
from werkzeug.serving import make_server

print()  # Espacio antes de LECC Universal System Complete
print("\033[1mLECC Universal System Complete\033[0m")

class GenericModule:
    def __init__(self, protocol, config):
        self.protocol = protocol
        self.config = config
        self.message_queue = queue.Queue()
        self.failed_message_queue = queue.Queue()
        self.running = True
        self.available = False
        self.core = None
        self.failed_once = False
        self.retry_attempts = 3
        self.retry_delay = 2
        self.emulated = False
        self.socket = None
        self.server_socket = None
        self.emulated_messages = None
        self.client = None
        self.connected = False
        self.serial = None
        self.bus = None
        self.app = None
        self.http_server = None

    def init(self):
        if self.protocol == "http":
            self.app = Flask(__name__)
            threading.Thread(target=self._run_http_server, daemon=True).start()
            time.sleep(2)
        elif self.protocol == "tcp":
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.config["host"], self.config["port"]))
            self.server_socket.listen(5)
            threading.Thread(target=self._listen_tcp, daemon=True).start()
            time.sleep(1)
        elif self.protocol == "udp":
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.config["host"], self.config["port"]))
            threading.Thread(target=self._listen_udp, daemon=True).start()
            time.sleep(1)
        elif self.protocol == "mqtt" and not self.emulated:
            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
            self.client.on_message = self.on_message
            try:
                self.client.connect(self.config["host"], self.config["port"])
                self.client.subscribe(self.config["topic"])
                self.client.loop_start()
                self.connected = True
            except Exception as e:
                print(f"MQTT initialization error: {e}")
        elif self.protocol == "i2c":
            try:
                self.bus = smbus.SMBus(1)
                print("I2C initialized on bus 1")
            except Exception:
                print("I2C simulated (no hardware)")
                self.bus = None
        elif self.protocol == "uart":
            try:
                self.serial = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)
                print("UART initialized on /dev/ttyUSB0")
            except Exception:
                print("UART simulated (no hardware)")
                self.serial = None

    def send(self, message, silent=False):
        if self.failed_once and self.retry_attempts <= 0 and not self.emulated:
            if not silent:
                print(f"{self.protocol}: Failed to send, module permanently unavailable [UNAVAILABLE]")
            self.failed_message_queue.put(self.core.normalize_message(message))
            return
        try:
            combined_output = ""
            if self.protocol == "uart":
                if self.serial:
                    self.serial.write(json.dumps(message).encode())
                else:
                    combined_output += f"UART/I2C simulated: {message['data']}"
            elif self.protocol == "http":
                response = requests.post(self.config["url"], json=message, timeout=5)
                if response.status_code != 200:
                    raise Exception(f"HTTP failure: {response.status_code}")
                elif not self.core.http_printed:
                    combined_output += " 200 OK"
                    self.core.http_printed = True
            elif self.protocol in ["tcp", "websocket", "ftp", "bluetooth", "zigbee"]:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                    client.connect((self.config["host"], self.config["port"]))
                    client.send(json.dumps(message).encode())
            elif self.protocol == "udp":
                if not self.socket:
                    raise Exception("UDP not initialized")
                self.socket.sendto(json.dumps(message).encode(), (self.config["host"], self.config["port"]))
            elif self.protocol == "mqtt":
                if self.emulated:
                    self.emulated_messages.put(json.dumps(message))
                    if not silent:
                        print(f"MQTT simulated: {message['data']}")
                else:
                    if not self.connected:
                        raise Exception("MQTT not connected")
                    self.client.publish(self.config["topic"], json.dumps(message))
            elif self.protocol == "i2c":
                if self.bus:
                    data = json.dumps(message).encode()
                    self.bus.write_i2c_block_data(self.config["address"], 0, list(data))
                else:
                    combined_output += f"UART/I2C simulated: {message['data']}"
            elif self.protocol == "ethernet":
                if not self.socket:
                    raise Exception("Ethernet not initialized")
                self.socket.sendto(json.dumps(message).encode(), (self.config["host"], self.config["port"]))
            self.available = True
            self.failed_once = False
            self.retry_attempts = 3
            if combined_output and not silent:
                print(combined_output)
        except Exception as e:
            self.available = False
            if not self.failed_once and not silent:
                print(f"{self.protocol}: Failure '{e}' [UNAVAILABLE]")
            self.failed_once = True
            self.retry_attempts -= 1
            self.failed_message_queue.put(self.core.normalize_message(message))

    def receive(self):
        try:
            return self.message_queue.get_nowait()
        except queue.Empty:
            return None

    def test_availability(self):
        attempt = 0
        while attempt < self.retry_attempts:
            try:
                self.send({"data": f"test_{self.protocol}", "destination_protocol": self.protocol}, silent=True)
                self.available = True
                self.emulated = False
                break
            except Exception as e:
                attempt += 1
                if attempt == self.retry_attempts:
                    print(f"[✗] {self.protocol} unavailable after {self.retry_attempts} attempts - {e}, activating emulator")
                    self.emulated = True
                    self.core.emulate_module(self)
                else:
                    print(f"{self.protocol}: Attempt {attempt}/{self.retry_attempts} failed - {e}, retrying in {self.retry_delay}s")
                    time.sleep(self.retry_delay)

    def start_emulator(self):
        if self.protocol in ["tcp", "websocket", "ftp", "bluetooth", "zigbee"]:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.config["host"], self.config["port"]))
            self.server_socket.listen(5)
            print(f"[✓] {self.protocol} emulated at {self.config['host']}:{self.config['port']}")
            threading.Thread(target=self._emulator_server, daemon=True).start()
        elif self.protocol == "udp":
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.config["host"], self.config["port"]))
            print(f"[✓] {self.protocol} emulated at {self.config['host']}:{self.config['port']}")
            threading.Thread(target=self._listen_udp, daemon=True).start()
        elif self.protocol == "mqtt":
            self.connected = True
            self.emulated_messages = queue.Queue()
            print(f"[✓] {self.protocol} emulated at {self.config['host']}:{self.config['port']}")
            threading.Thread(target=self._mqtt_emulator, daemon=True).start()
        elif self.protocol == "ethernet":
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.config["host"], self.config["port"]))
            print(f"[✓] {self.protocol} emulated at {self.config['host']}:{self.config['port']}")
            threading.Thread(target=self._listen_ethernet, daemon=True).start()
        self.emulated = True
        self.available = True
        self.failed_once = False
        self.retry_attempts = 3

    def _emulator_server(self):
        while self.running:
            conn, addr = self.server_socket.accept()
            data = conn.recv(1024).decode()
            if data:
                self.message_queue.put(json.loads(data))
            conn.close()

    def _mqtt_emulator(self):
        while self.running:
            if not self.emulated_messages.empty():
                msg = self.emulated_messages.get()
                self.message_queue.put(json.loads(msg))
            time.sleep(0.1)

    def _run_http_server(self):
        @self.app.route("/api/data", methods=["POST"])
        def receive_data():
            data = request.json
            self.message_queue.put(data)
            return {"status": "success"}
        print(f"Starting HTTP server: Running on all addresses (0.0.0.0) ||| http://127.0.0.1:{self.config['port']} ||| http://192.168.1.14:{self.config['port']}")
        self.http_server = make_server("0.0.0.0", self.config["port"], self.app, threaded=True)
        self.http_server.serve_forever()

    def _listen_tcp(self):
        while self.running:
            conn, addr = self.server_socket.accept()
            data = conn.recv(1024).decode()
            if data:
                self.message_queue.put(json.loads(data))
            conn.close()

    def _listen_udp(self):
        while self.running:
            data, _ = self.socket.recvfrom(1024)
            self.message_queue.put(json.loads(data.decode()))

    def _listen_ethernet(self):
        while self.running:
            data, _ = self.socket.recvfrom(1024)
            self.message_queue.put(json.loads(data.decode()))

    def on_message(self, client, userdata, msg):
        self.message_queue.put(json.loads(msg.payload.decode()))

    def _listen(self):
        while self.running and self.available:
            msg = self.receive()
            if msg:
                print(f"{self.protocol}: Received '{msg['data']}'")
                self.core.route_message(msg, self.protocol)
            time.sleep(0.01)

class LECCCore:
    def __init__(self):
        self.modules = {}
        self.running = True
        self.maskpert_protocols = ["http", "tcp"]
        self.http_printed = False

    def register_module(self, protocol, module):
        self.modules[protocol] = module
        module.core = self
        threading.Thread(target=module._listen, daemon=True).start()
        module.init()
        module.test_availability()

    def emulate_module(self, module):
        module.start_emulator()

    def normalize_message(self, message):
        msg = message.copy() if isinstance(message, dict) else {"data": str(message)}
        msg.setdefault("protocol", "unknown")
        msg.setdefault("destination_protocol", "broadcast")
        msg.setdefault("masked_history", [])
        return msg

    def route_message(self, message, source_protocol=None):
        msg = self.normalize_message(message)
        if source_protocol:
            msg["protocol"] = source_protocol
        print(f"Sending from {msg['protocol']}: {msg['data']}")
        self.http_printed = False
        self.maskpert_send(msg)

    def maskpert_send(self, message):
        available_modules = {p: m for p, m in self.modules.items() if m.available}
        sent_protocols = []
        for protocol in available_modules:
            try:
                adapted_msg = message.copy()
                adapted_msg["masked_history"].append(f"via_{protocol}")
                available_modules[protocol].send(adapted_msg, silent=True)
                sent_protocols.append(protocol)
            except Exception as e:
                print(f"Failed to send via {protocol}: {e}")
                available_modules[protocol].available = False
                available_modules[protocol].failed_once = True
        for maskpert_protocol in self.maskpert_protocols:
            if maskpert_protocol in available_modules and available_modules[maskpert_protocol].available:
                try:
                    adapted_msg = message.copy()
                    adapted_msg["masked_history"].append(f"maskpert_{maskpert_protocol}")
                    available_modules[maskpert_protocol].send(adapted_msg, silent=True)
                    print(f"\nSent with maskpert via {', '.join(sent_protocols)}, success with {maskpert_protocol}")
                    return
                except Exception as e:
                    print(f"Failed to send with maskpert via {maskpert_protocol}: {e}")
                    available_modules[maskpert_protocol].available = False
                    available_modules[maskpert_protocol].failed_once = True

    def _maskpert_rescue(self):
        while self.running:
            for protocol, module in self.modules.items():
                if not module.available and not module.failed_message_queue.empty():
                    while not module.failed_message_queue.empty():
                        failed_msg = module.failed_message_queue.get()
                        print(f"Rescuing message from {protocol} with maskpert: {failed_msg['data']}")
                        available_maskpert = {p: m for p, m in self.modules.items() if m.available and p in self.maskpert_protocols}
                        sent_protocols = []
                        for maskpert_protocol in available_maskpert:
                            try:
                                adapted_msg = failed_msg.copy()
                                adapted_msg["masked_history"].append(f"maskpert_{maskpert_protocol}")
                                available_maskpert[maskpert_protocol].send(adapted_msg, silent=True)
                                sent_protocols.append(maskpert_protocol)
                                print(f"Sent with maskpert via {', '.join(sent_protocols)}, success with {maskpert_protocol}")
                                break
                            except Exception as e:
                                print(f"Failed to send with maskpert via {maskpert_protocol}: {e}")
                                available_maskpert[maskpert_protocol].available = False
                                available_maskpert[maskpert_protocol].failed_once = True
            time.sleep(5)

# Configuration of protocols
protocol_configs = {
    "uart": {"port": None, "host": None},
    "http": {"port": 5000, "host": "localhost", "url": "http://localhost:5000/api/data"},
    "tcp": {"port": 65433, "host": "127.0.0.1"},
    "udp": {"port": 65434, "host": "127.0.0.1"},
    "websocket": {"port": 8765, "host": "localhost"},
    "ftp": {"port": 2121, "host": "localhost"},
    "mqtt": {"port": 1883, "host": "localhost", "topic": "lecc/data"},
    "i2c": {"port": None, "host": None, "address": 0x48},
    "ethernet": {"port": 65435, "host": "127.0.0.1"},
    "bluetooth": {"port": 9999, "host": "localhost"},
    "zigbee": {"port": 8888, "host": "localhost"}
}

def main():
    global core
    core = LECCCore()
    for protocol, config in protocol_configs.items():
        core.register_module(protocol, GenericModule(protocol, config))

    print("\033[1mInitializing...\033[0m")
    print()  # Espacio antes de Initializing...
    time.sleep(15)

    available_protocols = [p for p, m in core.modules.items() if m.available]
    print(f"\033[1mAvailable ({len(available_protocols)}): {available_protocols}\033[0m")
    if available_protocols:
        test_message = "Automatic test message"
        core.route_message(test_message, "tcp")

    print("\033[1mLECC System Running...\033[0m")
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping system...")
        core.running = False
        for module in core.modules.values():
            module.running = False

if __name__ == "__main__":
    main()