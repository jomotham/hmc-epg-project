# EPG System Firmware

This folder contains the firmware for the EPG System developed for the **nRF5340-DK** board.  
The firmware integrates various components like ADC (Analog-to-Digital Converter), SPI (Serial Peripheral Interface) communication, GPIO (General Purpose Input/Output) control, and UART (Universal Asynchronous Receiver/Transmitter) communication into a single package.  
The goal is to ensure seamless interaction and control over these components, enabling efficient data collection and control via Bluetooth and UART commands.

---

## Main File: `main.c`

The `main.c` file serves as the central entry point for the firmware. It orchestrates the operation of multiple hardware interfaces, including ADC, SPI, GPIO, and UART.  
The primary operations performed by this firmware are:

- **UART Communication**: Handles the reception of commands (e.g., `START`, `ON`) via UART, which control the state of the system.
- **ADC Data Acquisition**: Samples ADC values at a specified rate (100 Hz by default), which are sent to the connected host over UART.
- **DDS Configuration**: Configures the Direct Digital Synthesizer (DDS) for signal generation with a predefined offset and amplification.
- **System Control**: The firmware listens for specific commands and powers up the system, configures hardware components, and initiates data collection based on those commands.

---

## System Components

1. **ADC (Analog-to-Digital Converter)**  
   Converts analog signals from sensors into digital values for processing and transmission.

2. **SPI (Serial Peripheral Interface)**  
   A communication protocol for interacting with peripherals (currently not utilized in the provided code, but can be extended).

3. **GPIO (General Purpose Input/Output)**  
   Controls and monitors pins for interacting with external devices or sensors.

4. **UART (Universal Asynchronous Receiver/Transmitter)**  
   Communication interface for receiving commands and sending data to/from a host system.

---

## How to Build & Flash

1. **Prerequisites**:
   - Install the Zephyr SDK and toolchain.
   - Set up the development environment for the **nRF5340-DK** board.
   - Plug in the **nRF5340-DK** board to your computer.

2. **Build the firmware**:  
   Navigate to the firmware directory and build the project using the Zephyr nRF Connect "Build" button.

3. **Flash the firmware**:  
   After building the firmware, flash it to the **nRF5340-DK** board by pressing the "Flash" button.