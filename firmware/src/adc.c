/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: January 22nd, 2025
 * PURPOSE: This file enables ADC reading from the AIN0 pin on the
 *			nRF5340dk board. 
 */

#include <stdio.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/adc.h>
#include "../include/adc.h"  // Include the ADC header file

//#define SLEEP_TIME_MS   1000 // 1 second delay between ADC reads. 

/* The devicetree node identifier for the "adc" label defined within the device tree */
#define ADC_NODE DT_NODELABEL(adc)

static const struct device *adc_device = DEVICE_DT_GET(ADC_NODE);

struct adc_channel_cfg channel0_cfg = {
    .gain = ADC_GAIN,
    .reference = ADC_REFERENCE,
    .acquisition_time = ADC_ACQ_TIME_DEFAULT,
    .channel_id = ADC_CHANNEL,
#ifdef CONFIG_ADC_NRFX_SAADC
    .input_positive = ADC_PORT
#endif
};

int16_t data_buffer[1];

struct adc_sequence sequence = {
    .channels = BIT(ADC_CHANNEL),
    .buffer = data_buffer,
    .buffer_size = sizeof(data_buffer),
    .resolution = ADC_RESOLUTION
};

// ADC initialization function
void adc_init(void)
{
    int err;

    if (!device_is_ready(adc_device)) {
        printk("ADC device not ready\n");
        return;
    }
    
    err = adc_channel_setup(adc_device, &channel0_cfg);
    if (err != 0) {
        printk("ADC channel setup failed with error %d.\n", err);
    }
}

// ADC read function (returns ADC value in millivolts)
int adc_read_value(void)
{
    int err;
    int32_t mv_value = 0;

    err = adc_read(adc_device, &sequence);
    if (err != 0) {
        printk("ADC reading failed with error %d.\n", err);
        return err;
    }

    mv_value = data_buffer[0];
    int32_t adc_vref = adc_ref_internal(adc_device);
    adc_raw_to_millivolts(adc_vref, ADC_GAIN, ADC_RESOLUTION, &mv_value);
    
	// Print ADC Voltage
    //printk("ADC Voltage: %d mV\n", mv_value);
    return mv_value;
}
