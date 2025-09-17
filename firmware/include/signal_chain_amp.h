/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: February 22nd, 2025
 * PURPOSE: This file contains the functions for setting the gain of the
 *          op-amp (variable amp) and setting the gain of the PGAs.
 */

#ifndef SIGNAL_CHAIN_AMP_H
#define SIGNAL_CHAIN_AMP_H

#include <zephyr/drivers/spi.h>       // Zephyr's SPI API
#include <zephyr/drivers/gpio.h>      // Zephyr's GPIO API
#include <zephyr/logging/log.h>       // Zephyr's logging API

#define MAX_AMPLIFICATION 7000 // Maximum amplification factor for the signal chain
#define MIN_AMPLIFICATION 2   // Minimum amplification factor for the signal chain (since 2x minimum headstage for stability)


/**
 * @brief Sets the gain of the signal chain amplification.
 * 
 * Adjusts the gain of the signal chain amplification by configuring each chip
 * to achieve the desired amplification factor.
 *
 * @param desired_amplification The target gain for the signal chain, specified as a double.
 *                              Must be within the range [MIN_AMPLIFICATION, MAX_AMPLIFICATION].
 * 
 * @retval void This function does not return a value.
 */
void set_signal_chain_amplification(double desired_amplification);


/**
 * @brief Sets the offset of the signal chain signal.
 * 
 * Adjusts the offset of the signal chain to the specified value. This is done
 * by adjusting digipot channel 2's wiper connected to the U6B OFFSET_AMP in the signal chain.
 *
 * @param desired_offset The target offset for the signal chain signal, specified as a double.
 * 
 * @retval void This function does not return a value.
 */
void set_signal_chain_offset(double desired_offset);


#endif // SIGNAL_CHAIN_AMP_H