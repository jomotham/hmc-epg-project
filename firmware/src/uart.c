/*
 * NAME: Dimitri Avila
 * EMAIL: davila@g.hmc.edu
 * DATA: February 18th, 2025
 * PURPOSE: This file contains the functions for UART control
 *          of the EPG system (perfomed via the callback function).
 */

 #include <zephyr/kernel.h>
 #include <zephyr/device.h>
 #include <zephyr/devicetree.h>
 #include <zephyr/drivers/gpio.h>
 #include <zephyr/sys/printk.h>
 /* STEP 3 - Include the header file of the UART driver in main.c */
 #include "../include/uart.h"  // Include the UART header file
 
 #include "../include/spi.h" // Include the SPI header file
 #include "../include/gpio.h" // Include the GPIO header file
 #include "../include/signal_chain_amp.h" // Include the signal chain amplification header file
 #include "../include/dds.h" // Include the DDS header file
 
 #include <stdlib.h> // For atoi()
 
 // Define the size of the receive buffer
 #define RECEIVE_BUFF_SIZE 20
 
 // Define the receiving timeout period
 #define RECEIVE_TIMEOUT 100
 
 // Get the device pointer of the UART hardware
 const struct device *uart= DEVICE_DT_GET(DT_NODELABEL(uart0));
 
 // Define the receive buffer
 static uint8_t rx_buf[RECEIVE_BUFF_SIZE] = {0};
 
 static uint8_t rx_index = 0;
 
 // Workqueue Things
 static int digipot_channel = 0;
 static int digipot_setting = 0;
 
 static int pga_number = 0;
 static int pga_setting = 0;
 
 // Create work_info structure and offload function 
 struct work_info {
     struct k_work work;
     char command[RECEIVE_BUFF_SIZE]; // Local copy of rx_buf
 } my_work;
 
 
 // Offload function for workqueue to decode incoming instructions via UART
 void offload_function(struct k_work *work_term)
 {
     printk("Processing command: %s\n", rx_buf);
 
     // Example: "D1:50" -> Set Digipot 1 to wiper value 50
     if (rx_buf[0] == 'D' && rx_buf[2] == ':') {
         int channel = rx_buf[1] - '0'; // Convert char to int
         int value = atoi(&rx_buf[3]);  // Convert string to int
 
         if (channel >= 0 && channel <= 3 && value >= 0 && value <= 255) {
             digipot_channel = channel;
             digipot_setting = value;
 
             printk("Setting Digipot %d to value %d\n", digipot_channel, digipot_setting);
             digipot_wiper_set(digipot_channel, digipot_setting);
         } else {
             printk("Invalid digipot command!\n");
         }
         
     // Example: "P1:3" -> Set PGA 1 to setting 3
     } else if (rx_buf[0] == 'P' && rx_buf[2] == ':') {
         int number = rx_buf[1] - '0'; // Convert char to int
         int setting = atoi(&rx_buf[3]);  // Convert string to int
 
         if (number >= 1 && number <= 2 && setting >= 0 && setting <= 7) {
             pga_number = number;
             pga_setting = setting;
 
             printk("Setting PGA %d to value %d\n", pga_number, pga_setting);
             configure_pga(pga_number, pga_setting);
         } else {
             printk("Invalid pga command!\n");
         }
     
     // Example: "M:3" -> Set Mux to setting 3 (X3)
     } else if (rx_buf[0] == 'M' && rx_buf[1] == ':' && rx_buf[2] >= '0' && rx_buf[2] <= '7') {
         int setting = rx_buf[2] - '0'; // Convert char to int
 
         if (setting >= 0 && setting <= 7) {
             printk("Setting Mux to setting %d\n", setting);
             set_mux(setting);
         } else {
             printk("Invalid mux command!\n");
         }
 
     // Example: "SCO:1.5" -> Set signal chain offset to 1.5V
     } else if (rx_buf[0] == 'S' && rx_buf[1] == 'C' && rx_buf[2] == 'O' && rx_buf[3] == ':') {
         double offset = atof(&rx_buf[4]);  // Convert string to double
 
         if (offset >= -3.3 && offset <= 3.3) {
             printk("Setting signal chain offset to %.2fV\n", offset);
             set_signal_chain_offset(offset);
         } else {
             printk("Invalid signal chain offset command!\n");
         }
 
     // Example: "SCA:50" -> Set signal chain amplification to 50x
     } else if (rx_buf[0] == 'S' && rx_buf[1] == 'C' && rx_buf[2] == 'A' && rx_buf[3] == ':') {
         double gain = atof(&rx_buf[4]);  // Convert string to double
 
         if (gain >= 1.0 && gain <= 7000.0) {
             printk("Setting signal chain amplification to %.2fx\n", gain);
             set_signal_chain_amplification(gain);
         } else {
             printk("Invalid signal chain amplification command!\n");
         }
 
     // Example: "DDIDDSSO:1.5" -> Set DDS offset to 1.5V
     } else if (rx_buf[0] == 'D' && rx_buf[1] == 'D' && rx_buf[2] == 'S' && rx_buf[3] == 'O' && rx_buf[4] == ':') {
         double offset = atof(&rx_buf[5]);  // Convert string to double
 
         if (offset >= -3.3 && offset <= 3.3) {
             printk("Setting DDS offset to %.2fV\n", offset);
             set_dds_offset(offset);
         } else {
             printk("Invalid DDS offset command!\n");
         }
 
     // Example: "IDDS" -> Run DDS initialization once
     } else if (rx_buf[0] == 'I' && rx_buf[1] == 'D' && rx_buf[2] == 'D' && rx_buf[3] == 'S') {
         printk("Starting DDS output\n");
         start_dds(1000);  // Start DDS with 1kHz sine wave
     }
 
     // Example: "SDDS:100" -> Set DDS to frequency of 100 Hz
     else if (rx_buf[0] == 'S' && rx_buf[1] == 'D' && rx_buf[2] == 'D' && rx_buf[3] == 'S' && rx_buf[4] == ':') {
         int freq = atoi(&rx_buf[5]);  // Convert string to int
 
         if (freq >= 0 && freq <= 10000) {
             printk("Setting DDS frequency to %d Hz\n", freq);
             changeDDSVal(freq);
 
         } else {
             printk("Invalid DDS frequency command!\n");
         }
 
     // Example: "DDSOFF" -> Turn off DDS output
     } else if (rx_buf[0] == 'D' && rx_buf[1] == 'D' && rx_buf[2] == 'S' && rx_buf[3] == 'O' && rx_buf[4] == 'F' && rx_buf[5] == 'F') {
         printk("Stopping DDS output\n");
         dds_sleep();  // Stop DDS output
 
     // Example: "DDSA:2" -> Amplify DDS signal by 2 (gain of 2)
     } else if (rx_buf[0] == 'D' && rx_buf[1] == 'D' && rx_buf[2] == 'S' && rx_buf[3] == 'A' && rx_buf[4] == ':') {
         double amplification = atof(&rx_buf[5]);  // Convert string to double
 
         if (amplification >= MIN_DDS_AMPLIFICATION && amplification <= MAX_DDS_AMPLIFICATION) {
             printk("Setting DDS amplification to %.2fx\n", amplification);
             set_dds_amplification(amplification);
         } else {
             printk("Invalid DDS amplification command!\n");
         }
 
     // Example: "OFF" -> Initiate power off sequence
     } else if (rx_buf[0] == 'O' && rx_buf[1] == 'F' && rx_buf[2] == 'F') {
         printk("Powering down the system...\n");
         power_down();
 
     // Example: "ON" -> Initiate power on sequence
     } else if (rx_buf[0] == 'O' && rx_buf[1] == 'N') {
         printk("Powering up the system...\n");
         power_up();
         
     } else {
         printk("Unknown command format: %s\n", rx_buf);
     }
 }
 
 // UART callback function
 static void uart_cb(const struct device *dev, struct uart_event *evt, void *user_data)
 {
     switch (evt->type) {
     case UART_RX_RDY:
         char received_char = evt->data.rx.buf[evt->data.rx.offset];
 
         // If it's a valid character, store it
         if ((received_char >= '0' && received_char <= '9') || received_char == ':' || received_char == '-' ||
             (received_char >= 'A' && received_char <= 'Z') || received_char == '\r' || received_char == '.') {
             rx_buf[rx_index++] = received_char;
 
             // If newline is received, process the command
             if (received_char == '\r') {
                 rx_buf[rx_index - 1] = '\0';  // Null-terminate
 
                 // Submit work for processing instruction
                 k_work_submit(&my_work.work);
 
                 // Reset buffer index
                 rx_index = 0;
             }
         } else {
             rx_index = 0; // Reset buffer if invalid character
         }
         break;
     case UART_RX_DISABLED:
         uart_rx_enable(dev, rx_buf, sizeof(rx_buf), RECEIVE_TIMEOUT);
         break;
     default:
         break;
     }
 }
 
 // Initialize UART and start receiving
 int uart_main(void)
 {
     // Initialize workqueue
     k_work_init(&my_work.work, offload_function);  //maybe get rid of .work if something broke.
 
     int ret;
 
     // Verify that the UART device is ready
     if (!device_is_ready(uart)) {
         printk("UART device not ready\r\n");
         return 1;
     }
 
     // Register the UART callback function
     ret = uart_callback_set(uart, uart_cb, NULL);
     if (ret) {
         return 1;
     }
 
     // Start receiving by calling uart_rx_enable() and pass it the address of the receive buffer
     ret = uart_rx_enable(uart ,rx_buf,sizeof rx_buf,RECEIVE_TIMEOUT);
     if (ret) {
         return 1;
     }
 
     return 0; // Success
 }