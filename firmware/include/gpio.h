/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: January 22nd, 2025
 * PURPOSE: Configures GPIO pins and provides functions for PGA control. 
 */

#ifndef GPIO_H
#define GPIO_H

#include <zephyr/drivers/gpio.h>    // Zephyr's GPIO API
#include <zephyr/kernel.h>          // Include for k_sleep()
#include <hal/nrf_gpio.h>           // Nordic's low-level GPIO functions

// Define GPIO Pins
#define GPIO_PIN_08 NRF_GPIO_PIN_MAP(1, 15)  // PGA 1's G2 pin
#define GPIO_PIN_07 NRF_GPIO_PIN_MAP(1, 14)  // PGA 1's G1 pin
#define GPIO_PIN_06 NRF_GPIO_PIN_MAP(1, 13)  // PGA 1's G0 pin

#define GPIO_PIN_11 NRF_GPIO_PIN_MAP(1, 3)  // PGA 2's G2 pin
#define GPIO_PIN_10 NRF_GPIO_PIN_MAP(1, 2) // PGA 2's G1 pin
#define GPIO_PIN_09 NRF_GPIO_PIN_MAP(0, 27) // PGA 2's G0 pin

// MUX pins 
#define EN_PIN NRF_GPIO_PIN_MAP(1, 4)      // Mux enable pin
#define MUXA_PIN NRF_GPIO_PIN_MAP(1, 5)    // MUXA pin
#define MUXB_PIN NRF_GPIO_PIN_MAP(1, 6)     // MUXB pin
#define MUXC_PIN NRF_GPIO_PIN_MAP(1, 7)     // MUXC pin


#define GPIO_PIN_15 NRF_GPIO_PIN_MAP(0, 6) // P_EN pin
#define GPIO_PIN_14 NRF_GPIO_PIN_MAP(0, 5) // N_EN pin

#define GPIO_P1_00 NRF_GPIO_PIN_MAP(0, 13) // WP SPI pin
#define GPIO_P1_04 NRF_GPIO_PIN_MAP(0, 29) // HOLD SPI pin





// Function declarations
void gpio_init(void);  // Initialize GPIO pins
int configure_pga(int pga_number, int pga_setting); // Configure the PGA with the given gain setting
void set_mux(uint8_t mux_setting); // Set the MUX to the specified setting
void power_up(void); // Power up the positive and negative power supplies
void power_down(void); // Power down the positive and negative power supplies

#endif // GPIO_H