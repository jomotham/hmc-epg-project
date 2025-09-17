/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: January 22nd, 2025
 * PURPOSE: Configures and manages ADC functionality for the nRF5340DK.  
 * 
 */

#ifndef ADC_H
#define ADC_H

#include <zephyr/drivers/adc.h>

// ADC configuration macros
#define ADC_RESOLUTION    12    // 12-bit resolution (0-4095 range)
#define ADC_CHANNEL       0     // Channel 0 (may vary depending on the sensor or pin)
#define ADC_PORT          SAADC_CH_PSELN_PSELN_AnalogInput0 // AIN0
#define ADC_REFERENCE     ADC_REF_INTERNAL // Reference voltage (0.6V)
#define ADC_GAIN          ADC_GAIN_1_5  // Gain of 1.5

// Initialize ADC
void adc_init(void);

// Start an ADC read and process the value
int adc_read_value(void);

// Declare a buffer for storing the ADC readings
extern int16_t data_buffer[1];

#endif // ADC_H