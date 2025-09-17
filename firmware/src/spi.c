/*
 * NAME: Dimitri Avila
 * EMAIL: davila@hmc.edu
 * DATE: January 31st, 2025
 * PURPOSE: This file contains definitions for transmitting messages via SPI.
 */

 #include "../include/spi.h"  // Include the SPI header file
 #include "../include/gpio.h" // Include the Digipot header file
 
 LOG_MODULE_REGISTER(DIGIPOT, LOG_LEVEL_INF);
 
 #define SPI_DEV DT_NODELABEL(spi1)
 #define MY_GPIO0 DT_NODELABEL(gpio1)  // GPIO for CS line
 
 const struct device *gpio0_dev = DEVICE_DT_GET(MY_GPIO0);
 
 // SPI CS GPIO pin configuration (specific to your setup)
 const struct gpio_dt_spec cs_gpio = SPI_CS_GPIOS_DT_SPEC_GET(DT_NODELABEL(x9250));
 
 // SPI configuration structure (Master mode, 500 kHz, 8-bit data)
 const struct spi_config spi_cfg = {
     .frequency = 500000, // 500 kHz
     .operation =  SPI_OP_MODE_MASTER | SPI_WORD_SET(8) | SPI_TRANSFER_MSB,
     .slave = 0,
     .cs = {
         .gpio = SPI_CS_GPIOS_DT_SPEC_GET(DT_NODELABEL(x9250)), // CS pin configuration
         .delay = 0      // No additional delay
     }
 };
 
 // Function to initialize the SPI device
 int spi_init(void) {
     const struct device *spi_dev = DEVICE_DT_GET(SPI_DEV);
     
     // ????? 
     nrf_gpio_pin_write(GPIO_P1_04, 1);  // Set Hold to logical high (active low pin)
 
 
     if (!device_is_ready(spi_dev)) {
         LOG_ERR("SPI device not ready");
         return -1;
     }
 
     LOG_INF("SPI initialized.");
     return 0;
 }
 
 // Function to write data via SPI
 int spi_write_custom(uint8_t *tx_data, size_t data_len) {
     const struct device *spi_dev = DEVICE_DT_GET(SPI_DEV);
 
     struct spi_buf tx_buf = {
         .buf = tx_data,
         .len = data_len
     };
 
     struct spi_buf_set tx_set = {
         .buffers = &tx_buf,
         .count = 1
     };
 
     // Perform SPI Write
     int ret = spi_write(spi_dev, &spi_cfg, &tx_set);
     if (ret != 0) {
         printk("SPI Write failed: %d", ret);
         return ret;
     } else {
         printk("Sent Write Instruction: ");
         for (size_t i = 0; i < data_len; i++) {
                 printk("%p ", tx_data[i]);
                 }
         printk("\n");
     }
 
     // Successful SPI Write
     return 0;
 }
 
 /*
  * This function is used to set the output voltage of a specified Digi-Pot
  * WCR = Wiper Counter Register, and we write to it in order to change wiper position.
  */
 int digipot_voltage_set(uint8_t digipot_number, double desired_output_voltage) {
     
     double digipot_voltage_range = 6.6; // -3.3 to +3.3 volts = 6.6v of range on a digipot (V_l to V_h)
     int num_settings = 255; // 8-bit digipots give us 256 discreet settings.
 
     // printk("desired output voltage = %lf\n", desired_output_voltage);
 
     // Convert voltage to wiper position (scaling to 0-255)
     uint8_t wiper_position = (int)(((desired_output_voltage + 3.3) / digipot_voltage_range) * num_settings);
     // printk("wiper position = %d\n", wiper_position);
 
     // WCR address calculation (assuming digipot_number is 0 to 3)
     uint8_t wcr_address = 0xA0 + digipot_number;
     uint8_t tx_data[3] = {0x50, wcr_address, wiper_position};
 
     // Perform WCR Write
     int ret = spi_write_custom(tx_data, sizeof(tx_data));
 
     if (ret != 0) {
         printk("SPI Write failed: %d", ret);
         return ret;
     }
 
     return 0;
 }
 
 
 // Function to set the wiper position of a digipot
 int digipot_wiper_set(uint8_t digipot_channel, uint8_t wiper_position) {
 
     // WCR address calculation (assuming digipot_number is 0 to 3)
     uint8_t wcr_address = 0xA0 + digipot_channel;
     uint8_t tx_data[3] = {0x50, wcr_address, wiper_position};
 
     // Perform WCR Write
     int ret = spi_write_custom(tx_data, sizeof(tx_data));
 
     if (ret != 0) {
         printk("SPI Write failed: %d", ret);
         return ret;
     }
 
     return 0;
 }
 
 
 
 
 // /*
 //  * Set the gain factor of the specified digi-pot.  (OLD FUNCTION)
 //  */
 // void digipot_gain_set(uint8_t digipot_number, uint8_t desired_opamp_gain) {
 
 //     // Ensure gain is greater than 1 (for non-inverting config)
 //     if (desired_opamp_gain < 1.0) {
 //         return;
 //     }
 
 //     // TODO: make a struct for each pot, then we can do pot.vh or pot.vl to get these set values per pot, as well as pot.wcr_address.
 //     // V_h/V_l = gain
 
 //     // Calculate required resistance ratio
 //     float resistance_ratio = desired_opamp_gain - 1.0;
 
 //     // Convert resistance ratio to wiper position
 //     uint8_t wiper_position = (uint8_t)((resistance_ratio/ (1 + resistance_ratio)) * (DIGIPOT_MAX_STEPS - 1));
 
 //     // Send the command to set the digipot
 //     uint8_t wcr_address = 0xA0 + digipot_number; // digipot_number should be a value between 0 and 3 
 //     uint8_t tx_data[3] = {0x50, wcr_address, wiper_position};
 //     spi_write_custom(tx_data, sizeof(tx_data));
         
 // }
 
 
 
 /*
  * Set the gain factor of the opamp controlled via digipot 1. (For channel 1 of digipot)
  * Pass in the desired gain factor as a float, and gain AFTER considering the 21x gain
  * from the headstage amplifier. 
  * 
  * Example: if we want 32x gain total, we would calculate 32/21(headamp) = 1.52, then 
  *          pass in 1.52 as the desired opamp gain.
  * 
  *          We need a function (or add it here) to determine how much gain the opamp should produce,
  *          and limit the amount of gain to like 10x or something to prevent saturation.
  */
 int set_opamp_gain(double desired_opamp_gain) {
     // Ensure gain is at least 2 (prevents op amp from becoming unstable)
     if (desired_opamp_gain < 2.0) { 
         printk("Error: Gain must be greater than or equal to 1.0\n");
         return 1;
     } else if (desired_opamp_gain > 255.0) {
         printk("Error: Gain must be less than or equal to 255.0\n");
         return 1;
     }
 
     // Calculate required resistance ratio
     uint8_t wiper_position = (DIGIPOT_MAX_STEPS - 1) / desired_opamp_gain; // Wiper Position = 255 / Gain
 
     // Send the command to set the digipot
     uint8_t wcr_address = 0xA1; // digipot channel 1 (A0 + 1 = A1).
     uint8_t tx_data[3] = {0x50, wcr_address, wiper_position};
     spi_write_custom(tx_data, sizeof(tx_data));
 
     return 0; // Success
 }
 
 
 
 // // Function to read data via SPI
 // int spi_read_custom(uint8_t *tx_data, size_t tx_len, uint8_t *rx_data, size_t rx_len) {
 //     const struct device *spi_dev = DEVICE_DT_GET(SPI_DEV);
 
 //     // Transmit buffer (e.g., instruction/address for read)
 //     struct spi_buf tx_buf = {
 //         .buf = tx_data,
 //         .len = tx_len
 //     };
 
 //     // Receive buffer (to hold the data read from SPI)
 //     struct spi_buf rx_buf = {
 //         .buf = rx_data,
 //         .len = rx_len
 //     };
 
 //     // Combine buffers into sets
 //     struct spi_buf_set tx_set = {
 //         .buffers = &tx_buf,
 //         .count = 1
 //     };
 //     struct spi_buf_set rx_set = {
 //         .buffers = &rx_buf,
 //         .count = 1
 //     };
 
 //     // Perform SPI transaction
 //     int ret = spi_transceive(spi_dev, &spi_cfg, &tx_set, &rx_set);
 //     if (ret != 0) {
 //         printk("SPI Read failed: %d\n", ret);
 //         return ret;
 //     } else {
 //         /* Connect MISO to MOSI for loopback */
 // 		printk("TX sent: 0x%02x, 0x%02x, 0x%02x\n", tx_data[0], tx_data[1], tx_data[2]);
 // 		printk("RX recv: 0x%02x, 0x%02x, 0x%02x\n", rx_data[0], rx_data[1], rx_data[2]);
 
 //         // printk("Received: ");
 //         // for (size_t i = 0; i < rx_len; i++) {
 //         //     printk("0x%02X ", rx_data[i]);
 //         // }
 //         printk("\n");
 //     }
 
 //     // Delay to simulate timing requirements, if needed
 //     k_msleep(1000);
 
     
 
 //     return 0; // Success
 // }