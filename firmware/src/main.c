/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: February 25th, 2025
 * PURPOSE: This file This file contains the main function for the EPG project, serving as 
 * 		    the central entry point for the firmware. It orchestrates all sensor 
 * 		    interactions and coordinates the operation of various components. 
 * 		    The goal is to integrate all essential functionalities (ADC, SPI 
 * 		    communication, and GPIO control) into a single firmware package that 
 * 		    can be flashed onto the nRF5340-DK board.
 */

#include <stdio.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>
LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);


#include "../include/adc.h"
#include "../include/gpio.h"
#include "../include/spi.h"
#include "../include/uart.h"
#include "../include/dds.h"
#include "../include/bluetooth.h"

#define SLEEP_TIME_MS       50
#define SAMPLE_PERIOD_MS    10  // Should be 17ms for 60Hz sampling rate
#define STACKSIZE           1024
#define ADC_THREAD_PRIORITY 7
#define UART_THREAD_PRIORITY 7
#define RECEIVE_TIMEOUT     100


#define UART_DEVICE_NODE DT_NODELABEL(uart0)
const struct device *uart_dev = DEVICE_DT_GET(UART_DEVICE_NODE);

// Define thread stacks
K_THREAD_STACK_DEFINE(adc_stack, STACKSIZE);
K_THREAD_STACK_DEFINE(uart_stack, STACKSIZE);

// Define thread control blocks
struct k_thread adc_thread_data;
struct k_thread uart_thread_data;

// Buffer for UART reception
static char command_buffer[32];
static int cmd_index = 0;
static volatile bool start_received = false;
static volatile bool on_recieved = false;

// UART callback function
static void uart_cb(const struct device *dev, struct uart_event *evt, void *user_data) {
    switch (evt->type) {
    case UART_RX_RDY:
        char received_char = evt->data.rx.buf[evt->data.rx.offset];

        // Store only valid characters
        if ((received_char >= '0' && received_char <= '9') || received_char == ':' || received_char == '-' ||
            (received_char >= 'A' && received_char <= 'Z') || received_char == '\r' || received_char == '.') {

            command_buffer[cmd_index++] = received_char;

            // If newline (ENTER key) is received, check the command
            if (received_char == '\r') {
                command_buffer[cmd_index - 1] = '\0';  // Null-terminate the string

                if (strcmp(command_buffer, "START") == 0) {
                    LOG_INF("Received START command.\n");
                    start_received = true;
                } else if (strcmp(command_buffer, "ON") == 0) {
                    LOG_INF("Received ON command.\n");
                    on_recieved = true;
                } else {
                    LOG_DBG("Invalid command: %s\n", command_buffer);
                }

                // Reset buffer for next input
                cmd_index = 0;
            }
        } else {
            cmd_index = 0;  // Reset if invalid character received
        }
        break;

    case UART_RX_DISABLED:
        uart_rx_enable(dev, command_buffer, sizeof(command_buffer), RECEIVE_TIMEOUT);
        break;

    default:
        break;
    }
}


// Function to wait for "START" command
void wait_for_start_command(void) {
    LOG_INF("Waiting for START command...\n");

    // Start receiving UART data
    uart_rx_enable(uart_dev, command_buffer, sizeof(command_buffer), RECEIVE_TIMEOUT);

    // Wait until "START" is received
    while (!start_received) {
        start_received = ble_start_received();
        k_msleep(10); // Check every 10 ms
    }
}

// Function to wait for "ON" command
void wait_for_on_command(void) {
    LOG_INF("Waiting for ON command...\n");

    // Start receiving UART data
    uart_rx_enable(uart_dev, command_buffer, sizeof(command_buffer), RECEIVE_TIMEOUT);

    // Wait until "ON" is received
    while (!on_recieved) {
        on_recieved = ble_on_received();
        k_msleep(10); // Check every 10 ms
    }
}

// Function to initialize the system with default settings
void config_default_settings() {
    LOG_INF("Default");
    set_dds_offset(-0.341);      // Set DDS offset for zero-centered AC
    set_dds_amplification(-1); // Set DDS amplification to -1x
    start_dds(1000);           // Initialize the DDS (1kHz sine wave)
    set_signal_chain_amplification(2.0); // Minimum amplification
    set_signal_chain_offset(0.6);        // Default offset for AC verification
}

static char msg_adc[32];

// ADC thread function
void adc_thread(char *msg) {
    // initialize_dds();
    // adc_init();
    while (1) {
        int adc_value = adc_read_value();
        int timestamp = k_uptime_get();

        char msg[32];
        snprintf(msg, sizeof(msg), "%u,%d\r\n", timestamp, adc_value);

        for (int i = 0; msg[i] != '\0'; i++) {
        //    uart_poll_out(uart_dev, msg[i]);
            msg_adc[i] = msg[i];
        }

        receive_adc(msg_adc);
      

        // // Print ADC value every second (every 60 samples)
        // if (sample_count % interval == 0) {
        //    LOG_INF("Timestamp: %u ms, ADC Value: %d", timestamp, adc_value);
        // }

        k_msleep(SAMPLE_PERIOD_MS);
    }
}

// UART thread function
void uart_thread(void) {
    // k_msleep(4000);
    // spi_init();
    // gpio_init();

    while (1) {
        uart_main();
        k_msleep(SLEEP_TIME_MS);
    }
}

// Main function
int main(void) {
    // Verify that the UART device is ready
      if (!device_is_ready(uart_dev)) {
        LOG_ERR("UART device not ready.\n");
        return 1;
    }

    // Set up UART callback
    uart_callback_set(uart_dev, uart_cb, NULL);

    start_ble();

    // Wait for "ON" command before turning on the system
    wait_for_on_command();

    // Initialize
    adc_init();
    gpio_init();
    spi_init();
    k_msleep(1000); // Small delay for stability
    config_default_settings();
   
    
    // Wait for the START command before proceeding (start data collection)
    wait_for_start_command();

    // Add command to stop ADC thread and one to reset

    // Start the system
    LOG_INF("Starting data collection!\n");

    // Create ADC thread
    k_thread_create(&adc_thread_data, adc_stack, K_THREAD_STACK_SIZEOF(adc_stack),
                    adc_thread, NULL, NULL, NULL,
                    ADC_THREAD_PRIORITY, 0, K_NO_WAIT);

    // Create UART thread
    k_thread_create(&uart_thread_data, uart_stack, K_THREAD_STACK_SIZEOF(uart_stack),
                    uart_thread, NULL, NULL, NULL,
                    UART_THREAD_PRIORITY, 0, K_NO_WAIT);

    while (1) {
        k_msleep(1000);
    }
}
