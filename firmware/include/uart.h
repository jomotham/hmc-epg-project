/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: February 5th, 2025
 * PURPOSE: Configures UART for communication with the EPG device. 
 */

 #ifndef UART_H
 #define UART_H
 
 #include <zephyr/drivers/uart.h>    // Zephyr's UART API
 
 int uart_main(void);               // Main function for UART configuration
 
 // UART device name
 
 #endif