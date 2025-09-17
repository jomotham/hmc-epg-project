/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: January 31st, 2025
 * PURPOSE: Configures SPI and CS GPIO, handles SPI communication,  
 *          and provides functions for digipot voltage control.  
 */

#ifndef SPI_H
#define SPI_H

#include <zephyr/drivers/spi.h>       // Zephyr's SPI API
#include <zephyr/drivers/gpio.h>      // Zephyr's GPIO API
#include <zephyr/logging/log.h>       // Zephyr's logging API

// SPI CS GPIO pin configuration
#define GPIO_0_CS 25  // Pin number for CS GPIO line (can be changed as needed)
extern const struct gpio_dt_spec cs_gpio;  // Define the CS GPIO spec

#define DIGIPOT_MAX_STEPS 256         // Assuming 8-bit resolution (256 steps)

// SPI configuration structure
extern const struct spi_config spi_cfg;

// Function declarations
int spi_init(void);  // SPI initialization
int spi_write_custom(uint8_t *tx_data, size_t data_len);  // SPI write
int digipot_voltage_set(uint8_t digipot_number, double desired_output_voltage);  // Set digipot voltage
int digipot_wiper_set(uint8_t digipot_channel, uint8_t wiper_position);  // Set digipot wiper position
int set_opamp_gain (double desired_opamp_gain);  // Set opamp gain (digipot channel 1)

#endif // SPI_H
