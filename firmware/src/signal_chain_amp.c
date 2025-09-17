/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: February 21st, 2025
 * PURPOSE: Controls each of the chips involed in the signal chain amplification
 *          process. This file contains the functions for setting the gain of the
 *          op-amp, setting the gain of the PGAs.
 */

#include "../include/spi.h"  // Include the SPI header file
#include "../include/gpio.h" // Include the GPIO header file
#include "../include/signal_chain_amp.h"  // Include the signal chain amplification header file

// Expects gains in the range of 1x to 7000x
void set_signal_chain_amplification(double desired_amplification) {
    // Ensure gain is within valid range
    if (desired_amplification < MIN_AMPLIFICATION || desired_amplification > MAX_AMPLIFICATION) {
        printk("Error: Desired amplification must be between 21x and 7000x\n");
        return;
    }

    double remaining_gain = desired_amplification / 2.0; // Minimum amplification to maintain head amp stability

    // Configure PGA 1 (1x-7x)
    uint8_t pga1_gain;
    if (remaining_gain >= 7.0) pga1_gain = 7;
    else if (remaining_gain >= 6.0) pga1_gain = 6;
    else if (remaining_gain >= 5.0) pga1_gain = 5;
    else if (remaining_gain >= 4.0) pga1_gain = 4;
    else if (remaining_gain >= 3.0) pga1_gain = 3;
    else if (remaining_gain >= 2.0) pga1_gain = 2;
    else pga1_gain = 1;  // Ensures no 0x gain
    uint8_t pga1_setting = pga1_gain; // PGA 1 setting is the same as pga1_gain
    configure_pga(1, pga1_setting);
    remaining_gain /= pga1_gain; // Update remaining gain
    printk("pga1_gain:", pga1_gain);
    // Configure PGA 2 (1x-100x)
    uint8_t pga2_setting;
    uint8_t pga2_gain = 1;
    if (remaining_gain >= 100.0) {
        pga2_gain = 100;
        pga2_setting = 7;
    } else if (remaining_gain >= 50.0) {
        pga2_gain = 50;
        pga2_setting = 6;
    } else if (remaining_gain >= 20.0) {
        pga2_gain = 20;
        pga2_setting = 5;
    } else if (remaining_gain >= 10.0) {
        pga2_gain = 10;
        pga2_setting = 4;
    } else if (remaining_gain >= 5.0) {
        pga2_gain = 5;
        pga2_setting = 3;
    } else if (remaining_gain >= 2.0) {
        pga2_gain = 2;
        pga2_setting = 2;
    } else {
        pga2_gain = 1;
        pga2_setting = 1;
    }
    configure_pga(2, pga2_setting);
    remaining_gain /= pga2_gain; // Update remaining gain
    printk("pga2_gain:", pga2_gain);
    // Set op-amp gain (variable amp)
    printk("Remaining Gain: %.2f\n", remaining_gain);
    set_opamp_gain(remaining_gain*2);
}

/*
 * Digipot channel 2 controls the offset of the signal chain.
 * The offset is set by adjusting the wiper position of digipot channel 2.
 * Vh = 3.3V, Vl = -3.3V. Select a voltage between Vh and Vl to set the offset.
 */
void set_signal_chain_offset(double desired_offset) {
    // Define the voltage range
    double VL = -3.3;  // Low voltage
    double VH = 3.3;   // High voltage

    // Ensure the input is within the valid range
    if (desired_offset < VL || desired_offset > VH) {
        printk("Error: Voltage input must be between %.2fV and %.2fV\n", VL, VH);
        return;  // Invalid input range
    }

    // Calculate the normalized wiper position
    int wiper_position = (int)((((desired_offset / VH) + 1) / 2) * 255);

    // Ensure the wiper position is within bounds (0-255)
    if (wiper_position < 0) wiper_position = 0;
    if (wiper_position > 255) wiper_position = 255;

    digipot_wiper_set(2, wiper_position);  // Set the wiper position of digipot channel 2
}
