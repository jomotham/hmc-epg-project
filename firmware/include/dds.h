/*
 * NAME: Julia Hansen
 * EMAIL: juhansen@g.hmc.edu
 * DATE: 03/04/25
 * PURPOSE: Configures setup for DDS for the nrf5340 dk
*/

#ifndef DDS_H
#define DDS_H


#include "spi.h"

#define MIN_DDS_AMPLIFICATION -5 // Calculated via G = -(Rh/10kOhm) where Rh = 50kOhm.
#define MAX_DDS_AMPLIFICATION 0 // Calculated via G = -(Rh/10kOhm) where Rh = 50kOhm.

/**
 * @brief Writes a 16-bit value to a DDS register.
 * 
 * Sends a command or data to the DDS (Direct Digital Synthesis) module via SPI.
 * 
 * @param value The 16-bit register value to be written.
 * 
 * @retval int Returns 0 on success, or a negative error code on failure.
 */
int dds_write_reg(uint16_t value);

/**
 * @brief Starts the DDS signal generation.
 * 
 * Configures and starts generating a waveform using the DDS module.
 * 
 * @retval int Returns 0 on success, or a negative error code on failure.
 */
int start_dds(uint16_t frequency);

/**
 * @brief Function to calculate frequency values to pass in to dds_write_reg
 * @param freq Frequency value, ie. 1000 Hz
 * @param result pointer to array where FREQLSB and FREQMSB will be written to 
 */
void frequency(int freq, uint16_t* result);

/**
 * @brief Function to convert binary string to hex
 * @param binaryString pointer to char array containing bits 
 */
uint16_t binaryToHex(const char* binaryString);

/**
 * @brief Converts frequency value in decimal to binary
 * @param value Frequency value in decimal 
 * @param binaryString pointer to a character array to write bits to 
 */
void convertToBinary(uint16_t value, char* binaryString);

/**
 * @brief Turns off DDS, sending a DC signal
 * @retval 1 upon sucess and 0 if not sucessful
 */
int dds_sleep(void);

/**
 * @brief Writes data to the DDS
 * @param inputFreq Frequency value to send to DDS
 */
void changeDDSVal(uint16_t inputFreq);


/**
 * @brief Sets the gain of the signal chain amplification.
 * 
 * Adjusts the gain of the signal chain amplification by configuring each chip
 * to achieve the desired amplification factor.
 *
 * @param desired_amplification The target gain for the signal chain, specified as a double.
 *                              Must be within the range [MIN_DDS_AMPLIFICATION, MAX_DDS_AMPLIFICATION].
 * 
 * @retval void This function does not return a value.
 */
void set_dds_amplification(double desired_amplification);

/**
 * @brief Sets the DC offset of the DDS output signal.
 * 
 * Adjusts the signal offset to shift the waveform's baseline voltage.
 * 
 * @param desired_offset The target offset voltage in volts, within the valid range.
 * 
 * @retval void This function does not return a value.
 */
void set_dds_offset(double desired_offset);


#endif // DDS_H