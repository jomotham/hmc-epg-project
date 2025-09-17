/*
 * NAME: Julia Hansen
 * EMAIL: juhansen@g.hmc.edu
 * DATE: 03/04/25
 * PURPOSE: This file allows the DDS to be initialized and set to different
 *          output frequencies. 
*/

// Our headerfile
#include "../include/dds.h"


#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>


// Include header file for SPI API, GPIO and device tree
#include <zephyr/drivers/spi.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>


#include <stdio.h>
#include <stdlib.h>
#include <math.h>


// For defining GPIO pins
#include <hal/nrf_gpio.h>


// Define GPIO Pin for FSYNC
#define FSYNC   NRF_GPIO_PIN_MAP(1, 8)


LOG_MODULE_REGISTER(DDS, LOG_LEVEL_INF);


uint16_t CTRL = 0x2000; //          0010 0000 0000 0000
uint16_t FREQ1_CTRL_EN = 0x2800;//  0010 0100 0000 0000
uint16_t FREQ0_LSB = 0x60C5;  //    0110 0000 1100 0101
uint16_t FREQ0_MSB = 0x4000;  //    0100 0000 0000 0000
uint16_t PHASE0 = 0xC000;     //    0110 0000 0000 0000


// Get device structure for DDS node
#define SPIOP   SPI_WORD_SET(8) | SPI_TRANSFER_MSB | SPI_MODE_CPOL // SPI word size is 8 bits, MSB should be transferred first, and clock has polarity of 1
struct spi_dt_spec spispec = SPI_DT_SPEC_GET(DT_NODELABEL(x9837), SPIOP, 0);

// Function to write data to register
int dds_write_reg(uint16_t value)
{
    int err;

    /* Declare a tx buffer having 16 bit data */
    // Split 16-bit value into two 8-bit parts
    uint8_t tx_buf[2];
    tx_buf[0] = (value >> 8) & 0xFF; // MSB
    tx_buf[1] = value & 0xFF;        // LSB
    //uint16_t tx_buf[] = {reg, value};
    struct spi_buf      tx_spi_buf      = {.buf = tx_buf, .len = sizeof(tx_buf)};
    struct spi_buf_set  tx_spi_buf_set  = {.buffers = &tx_spi_buf, .count = 1};


    /* Call the spi_write_dt function with SPISPEC to write buffers */
    err = spi_write_dt(&spispec, &tx_spi_buf_set);
    if (err < 0) {
        LOG_ERR("spi_write_dt() failed, err %d", err);
        return err;
    }

    return 0;
}

// Function to convert uint16_t to binary string
void convertToBinary(uint16_t value, char* binaryString) {
    for (int i = 15; i >= 0; i--) {
        binaryString[15 - i] = (value & (1 << i)) ? '1' : '0';

    }
    binaryString[16] = '\0'; // Null-terminate the string
}


// Function to convert binary string to hex
uint16_t binaryToHex(const char* binaryString) {
    return (uint16_t)strtol(binaryString, NULL, 2);
}


// Function to calculate frequency values
void frequency(int freq, uint16_t* result) {
    // Calculate the output frequency
    uint16_t freqOut = (uint16_t)((freq * pow(2, 28)) / 16000000);
    char binaryString[17];
    convertToBinary(freqOut, binaryString);
    // 1000 Hz = 0000011010001101
    // 1 Hz = 0000000000010001

    // Prepare binary substrings
    char FREQ0_LSB_String[17] = "01";             // FREQ0 register designation
    strncat(FREQ0_LSB_String, binaryString + 2, 14);  // 14 more bits to make it 16 bits in total
    char FREQ0_MSB_String[17] = "0100000000000000";  // Assume desired frequency is small enough to have an empty MSB

    // Convert binary substrings to hex
    uint16_t FREQ0_LSB = binaryToHex(FREQ0_LSB_String);
    uint16_t FREQ0_MSB = binaryToHex(FREQ0_MSB_String);
   
    // Store results in the provided array
    result[0] = FREQ0_LSB;
    result[1] = FREQ0_MSB;
   
    // Print the results
    printk("FREQ0_LSB: 0x%X\n", FREQ0_LSB);
    printk("FREQ0_MSB: 0x%X\n", FREQ0_MSB);
}

void changeDDSVal(uint16_t inputFreq) {
    // Configure FSYNC pin
    nrf_gpio_pin_set(FSYNC); // Set FSYNC high initially

    uint16_t newfreq[2];

    frequency(inputFreq, newfreq);

    // Prepare to load LSB and MSB
    dds_write_reg(0x2000); // Set DB13 to 1, DB12 to 0, and reset to 0

    // Write 14 LSBs to FREQ0 bits 0-13
    dds_write_reg(newfreq[0]);
    
    // Write 14 MSBs to FREQ0 to bits 14-28
    dds_write_reg(newfreq[1]);
    LOG_INF("SPI is initialized!");
}

// Function to set the frequency of the DDS
int start_dds(uint16_t inputFreq) {
    uint16_t freq[2];

    frequency(inputFreq, freq);

    // Configure FSYNC pin
	nrf_gpio_cfg_output(FSYNC);
	nrf_gpio_pin_set(FSYNC); // Set FSYNC high initially

		// Check to see if SPI is ready
        int err;
        err = spi_is_ready_dt(&spispec);
        if (!err) {
                LOG_ERR("Error: SPI device is not ready, err: %d", err);
                return 0;
        }

		LOG_INF("SPI is initialized!");

		// Set DB13 to 1, DB12 to 0, and reset to 1
		dds_write_reg(0x2100);  

		// Write 14 LSBs to FREQ0 bits 0-13
		dds_write_reg(freq[0]);
		
		// Write 14 MSBs to FREQ0 to bits 14-28
		dds_write_reg(freq[1]);

		// Write PHASE0
		dds_write_reg(PHASE0);
		
		// Output sine wave, set reset to 0
		dds_write_reg(CTRL);

		return 0;
}



// Function to sleep dds
int dds_sleep(void) {

    // Configure FSYNC pin
    nrf_gpio_cfg_output(FSYNC);
    nrf_gpio_pin_set(FSYNC); // Set FSYNC high initially


    // Check to see if SPI is ready
    int err;
    err = spi_is_ready_dt(&spispec);
    if (!err) {
            LOG_ERR("Error: SPI device is not ready, err: %d", err);
            return 0;
    }

    LOG_INF("SPI is initialized!");


    // Set Control Register (SLEEP)
    dds_write_reg(0x00C0); // 0000 0000 1100 0000
    // dds_write_reg(0x00B0); // 0b0000 0000 1000 0000

    return 1; // Success
}


// Set the amplification
void set_dds_amplification(double desired_amplification) {
    // Ensure the input is within the valid range
    if (desired_amplification < MIN_DDS_AMPLIFICATION || desired_amplification > MAX_DDS_AMPLIFICATION) {
        printk("Error: Voltage input must be between %.2dV and %.2dV\n", MIN_DDS_AMPLIFICATION, MAX_DDS_AMPLIFICATION);
        return;  // Invalid input range
    }

    // Calculate the wiper position
    //int wiper_position = (((2958 * desired_amplification)/125) + 255); // 4.64 K resistor
    int wiper_position = (51 * (desired_amplification + 5)); // 10 K resistor
    
    // Ensure the wiper position is within bounds (0-255)
    if (wiper_position < 0) wiper_position = 0;
    if (wiper_position > 255) wiper_position = 255;

    digipot_wiper_set(0, wiper_position);  // Set the wiper position of digipot channel 0
}



// TODO: set the offset for AC voltage only! (just zero centering the signal). Offset can be variable for DC.
void set_dds_offset(double desired_offset) {
    // Define the voltage range
    double VL = -3.3;  // Low voltage
    double VH = 3.3;   // High voltage

    // Ensure the input is within the valid range
    if (desired_offset < VL || desired_offset > VH) {
        printk("Error: Voltage input must be between %.2fV and %.2fV\n", VL, VH);
        return;  // Invalid input range
    }

    double zero_center_offset = -0.341;  // Offset for zero-centering the signal

    // Calculate the normalized wiper position
    int wiper_position = (int)(((((desired_offset) / VH) + 1) / 2) * 255);

    // int wiper_position = (int)((((VH - desired_offset) / (VH - VL)) * 255));

    // Ensure the wiper position is within bounds (0-255)
    if (wiper_position < 0) wiper_position = 0;
    if (wiper_position > 255) wiper_position = 255;

    digipot_wiper_set(3, wiper_position);  // Set the wiper position of digipot channel 3
}