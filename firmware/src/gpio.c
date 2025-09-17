/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: January 22nd, 2025
 * PURPOSE: This file enables writing to GPIO pins for controlling the PGA chip.
 */

#include "../include/gpio.h"  // Include the GPIO header file

// Function to configure GPIO pins as output
void gpio_init(void) {
    // Configure GPIO pins to output
    nrf_gpio_cfg_output(GPIO_PIN_08);  // PGA 1's G2 pin
    nrf_gpio_cfg_output(GPIO_PIN_07);  // PGA 1's G1 pin
    nrf_gpio_cfg_output(GPIO_PIN_06);  // PGA 1's G0 pin

    nrf_gpio_cfg_output(GPIO_PIN_09);  // PGA 2's G2 pin
    nrf_gpio_cfg_output(GPIO_PIN_10);  // PGA 2's G1 pin
    nrf_gpio_cfg_output(GPIO_PIN_11);  // PGA 2's G0 pin

    // Enable pins for the positive and negative power supplies
    nrf_gpio_cfg_output(GPIO_PIN_15);  // P_EN pin
    nrf_gpio_cfg_output(GPIO_PIN_14);  // N_EN pin

    // SPI pins
    nrf_gpio_cfg_output(GPIO_P1_00);  // WP SPI pin
    nrf_gpio_cfg_output(GPIO_P1_04);  // HOLD SPI pin

    // MUX GPIO Pins
    nrf_gpio_cfg_output(MUXA_PIN);  // MUXA pin
    nrf_gpio_cfg_output(MUXB_PIN);  // MUXB pin
    nrf_gpio_cfg_output(MUXC_PIN);  // MUXC pin
    nrf_gpio_cfg_output(EN_PIN);    // EN pin
}


// This function will define how the PGA operates (configurable with 8 settings)
int configure_pga(int pga_number, int pga_setting) {
    // Make sure we inputted a valid gain setting (0-7)
    if (pga_setting < 0 || pga_setting > 7) {
        return -1; // Return an error for invalid settings
    }

    // Shift pga_setting down to get bits
    int g2 = (pga_setting >> 2) & 0x01;  // Get the 3rd bit
    int g1 = (pga_setting >> 1) & 0x01;  // Get the 2nd bit
    int g0 = pga_setting & 0x01;         // Get the 1st bit

    // Set GPIO pins based on extracted bits
    if (pga_number == 1) {
        nrf_gpio_pin_write(GPIO_PIN_06, g0);  // Set G0
        nrf_gpio_pin_write(GPIO_PIN_07, g1);  // Set G1
        nrf_gpio_pin_write(GPIO_PIN_08, g2);  // Set G2
    } else if (pga_number == 2) {
        nrf_gpio_pin_write(GPIO_PIN_09, g0);  // Set G0
        nrf_gpio_pin_write(GPIO_PIN_10, g1);  // Set G1
        nrf_gpio_pin_write(GPIO_PIN_11, g2);  // Set G2
    }
    return 0;  // Success
}


void set_mux(uint8_t mux_setting) {
    // Make sure we inputted a valid mux setting (0-7)
    if (mux_setting > 7) {
        return; // Return an error for invalid settings
    }

    // Shift mux_setting down to get bits
    int MUXC = (mux_setting >> 2) & 0x01;  // Get the 3rd bit (msb)
    int MUXB = (mux_setting >> 1) & 0x01;  // Get the 2nd bit
    int MUXA = mux_setting & 0x01;         // Get the 1st bit (lsb)

    // Set GPIO pins based on extracted bits
    printk("MUXA: %d, MUXB: %d, MUXC: %d\n", MUXA, MUXB, MUXC);
    nrf_gpio_pin_write(EN_PIN, 0);  // Enable the MUX
    nrf_gpio_pin_write(MUXA_PIN, MUXA);  // Set MUXA
    nrf_gpio_pin_write(MUXB_PIN, MUXB);  // Set MUXB
    nrf_gpio_pin_write(MUXC_PIN, MUXC);  // Set MUXC
}


void power_up(void) {
    // Power up the positive and negative power supplies
    nrf_gpio_pin_write(GPIO_PIN_15, 1);  // Power up the positive supply
    k_msleep(500);                        // Small delay for stability
    nrf_gpio_pin_write(GPIO_PIN_14, 1);  // Power up the negative supply
    config_default_settings(); 
}


void power_down(void) {
    // Change MUX setting to 10K
    set_mux(0);
    // Enter sleep mode on the DDS
    dds_sleep();
    // Turn off gains and offsets
    set_signal_chain_amplification(2.0); // Set Minimum Signal Chain Amplification
    set_dds_amplification(-1);           // Set DDS amplification to -1x
    set_signal_chain_offset(0);          // Set Signal Chain Offset to 0
    set_dds_offset(0);                   // Set DDS Offset to 0
    
    // Power down the positive and negative power supplies
    nrf_gpio_pin_write(GPIO_PIN_14, 0);  // Power down the negative supply
    k_msleep(500);                       // Small delay for stability
    nrf_gpio_pin_write(GPIO_PIN_15, 0);  // Power down the positive supply
}