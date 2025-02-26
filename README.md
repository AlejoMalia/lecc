LECC · Linked Electronic Communication Core
========================
![HEADER](docs/banner01.png)
**Linked Electronic Communication Core (LECC)** is a modular Python framework for communication across multiple protocols, drawing inspiration from Ray Kurzweil's vision in *The Age of Spiritual Machines*. In the book, Kurzweil imagines a future with a shared electronic communication language, a concept that sparked the idea for this system. LECC enables sending and receiving messages via protocols like HTTP, TCP, UDP, MQTT, UART, I2C, and more, with built-in emulation and failure recovery through the unique Maskpert mechanism.

    👁 The creator has tested this successfully, but functionality may vary depending on your system.
![Python](https://img.shields.io/badge/Python-3.7+-blue) ![License](https://img.shields.io/badge/License-MIT-yellow)

Features
--------

- 🌐 **Multi-Protocol Support**: Compatible with UART, HTTP, TCP, UDP, WebSocket, FTP, MQTT, I2C, Ethernet, Bluetooth, and Zigbee.
- 🔄 **Automatic Emulation**: Activates an emulator if a protocol fails due to missing hardware or connectivity issues.
- 👺 **Maskpert**: A smart routing and rescue system ensuring message delivery using alternative protocols when the primary one fails.
- 🧩 **Modular and Extensible**: Easy to add new protocols or customize existing ones.
- ⚡ **Concurrency**: Uses threading to handle simultaneous communications without blocking.
- 💪 **Resilience**: Automatic retries and failed message queues to guarantee delivery.

#### What Does It Achieve?

LECC provides a unified system for connecting heterogeneous devices and services. It's perfect for IoT projects, automation, network testing, or any application requiring protocol interoperability.

What is Maskpert?
-----------------

**Maskpert** 👺 (Masked Expert) is LECC's intelligent failure management system:

- 🎯 **Dynamic Routing**: Sends messages across all available protocols and confirms success with a priority protocol (HTTP or TCP by default).
- 🧰 **Message Rescue**: Retrieves failed messages from a queue and resends them via available alternative protocols.

This ensures messages reach their destination even under network or hardware failures.

Installation
------------

#### Requirements

*   Python 3.7 or higher
*   Operating System: Tested on Linux (may require adjustments for Windows/macOS)

#### Dependencies

Install the required libraries with:

    pip install -r requirements.txt

See `requirements.txt` for the full list.

#### Steps

1.  Clone the repository:
    
        git clone https://github.com/[your-username]/lecc-universal-system.gitcd lecc-universal-system
    
2.  Install dependencies:
    
        pip install -r requirements.txt
    
3.  Run the system:
    
        python3 lecc.py
    

Usage
-----

1.  **Configuration**: Edit `protocol_configs` in `lecc.py` to adjust ports, hosts, or URLs for your environment:
    
        protocol_configs = {    "http": {"port": 5000, "host": "localhost", "url": "http://localhost:5000/api/data"},    "tcp": {"port": 65433, "host": "127.0.0.1"},    # ...}
    
2.  **Execution**: Running the script initializes all modules, tests availability, and sends a test message.
3.  **Expected Output**:
    
        LECC Universal System CompleteStarting HTTP server: Running on all addresses (0.0.0.0) ||| http://127.0.0.1:5000Available (11): ['uart', 'http', 'tcp', ...]Sending from tcp: Automatic test messageSent with maskpert via uart, http, tcp, ..., success with httpLECC System Running...
    
4.  **Customization**: Add your own logic in `LECCCore.route_message()` to process received messages.

Example
-------

Send a custom message by modifying `main()`:

    core.route_message({"data": "Hello world", "destination_protocol": "http"})

Output:

    Sending from http: Hello worldSent with maskpert via ..., success with http

Important Notes
---------------

*   **MQTT**: Requires a broker (e.g., Mosquitto) on `localhost:1883`. If unavailable, it switches to emulation.
*   **UART/I2C**: Needs connected hardware (e.g., `/dev/ttyUSB0`). Without hardware, it simulates.
*   **Ports**: Ensure configured ports are free.

Contributing
------------

Contributions are welcome! Please:

1.  Fork the repository.
2.  Create a branch (`git checkout -b feature/new-feature`).
3.  Submit a pull request.

License
-------

Distributed under the MIT License. See `LICENSE` for details.

Credits
-------

|                                                                                    | Name        | Role         | GitHub                                         |
| ---------------------------------------------------------------------------------- | ----------- | ------------ | ---------------------------------------------- |
| ![Alejo](https://github.com/alejomalia.png?size=72) | Alejo |   Author & Development   | [@alejomalia](https://github.com/alejomalia) |

[![Twitter](https://img.shields.io/badge/Twitter-black?style=for-the-badge&logo=twitter&logoColor=white)](https://twitter.com/alejomalia_) [![Instagram](https://img.shields.io/badge/Instagram-black?style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/alejomalia/)

<small>*Inspired by _The Age of Spiritual Machines_ by Ray Kurzweil.*</small>
<small>*Developed with assistance from Grok3, created by xAI.*</small>
