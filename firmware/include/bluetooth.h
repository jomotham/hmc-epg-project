/*
 * NAME: Julia Hansen
 * EMAIL: juhansen@g.hmc.edu
 * DATE: 03/02/25
 * PURPOSE: Configures setup for bluetooth low energy for the nrf5340 dk
*/

#ifndef BLUETOOTH_H
#define BLUETOOTH_H 

#include <stdio.h>
#include <stdint.h> 

// UUID of Custom Service
#define BT_UUID_MY_CUSTOM_SERV_VAL BT_UUID_128_ENCODE(0x445817d2, 0x9e86, 4216, 8054, 0x703dc002ef41)
#define BT_UUID_MY_CUSTOM_SERVICE BT_UUID_DECLARE_128(BT_UUID_MY_CUSTOM_SERV_VAL)

// UUID of ADC Characteristic
#define BT_UUID_MY_ADC_CHRC_VAL BT_UUID_128_ENCODE(0x445817d2, 0x9e86, 4216, 8054, 0x703dc002ef42)
#define BT_UUID_MY_ADC_CHRC BT_UUID_DECLARE_128(BT_UUID_MY_ADC_CHRC_VAL)

// UUID of PY_READ Characteristic
#define BT_UUID_PY_READ_CHRC_VAL BT_UUID_128_ENCODE(0x445817d2, 0x9e86, 4216, 8054, 0x703dc002ef43)
#define BT_UUID_PY_READ_CHRC BT_UUID_DECLARE_128(BT_UUID_PY_READ_CHRC_VAL)


/** 
 * @brief Function to read data from ADC and pass it through to BLE
 * @param conn Bluetooth connection
 * @param attr GATT attribute referring to the read characteristic 
 * @param buf Buffer storing the data being read from the attribute.
 * 			  The client can access the data by reading from this buffer.
 * @param len The length of the buffer
 * @param offset Offset value specifying where to start reading from the buffer if the attribute data is too large
 * @retval The number of bytes read from the buffer 
*/
ssize_t my_read_adc_function(struct bt_conn *conn,
				const struct bt_gatt_attr *attr, void *buf,
				uint16_t len, uint16_t offset);

/** 
 * @brief Function to write data from the UI into a buffer
 * @param conn Bluetooth connection
 * @param attr GATT attribute referring to the write characteristic 
 * @param buf Buffer storing the data being written from the attribute.
 * 			  The client can write the data to this buffer.
 * @param len The length of the buffer
 * @param offset Offset value specifying where to write to the buffer if the attribute data is too large
 * @param flags Additional write flags 
 * @retval The length of the buffer 
*/
ssize_t write_custom_value(struct bt_conn *conn, 
				const struct bt_gatt_attr *attr, const void *buf, 
				uint16_t len, uint16_t offset, uint8_t flags);

/**
 * @brief Debug function to ensure that Python and Nordic can notify each other
 * @param attr GATT attribute referring to the notify characteristic
 * @param value Value representing the notification status between Python and Nordic
 */
static void adc_ccc_cfg_changed(const struct bt_gatt_attr *attr, uint16_t value);

/**
 * @brief Callback function for when BLE is ready
 * @param err Error thrown if BLE is not ready
*/

void bt_ready(int err);

/**
 * @brief Initializing BT and calling bt_ready when BT is 
 * initialized and ready for connection
*/
int init_ble(void);

/**
 *@brief Receives ADC data from ADC thread
 *@param msg_adc Buffer contatining the timestamp, voltage values 
 */
void receive_adc(char *msg_adc);

/**
 * @brief Keeps track of the start variable for the
 * start_received function in main.c
 * @return Boolean value of start
 */
bool ble_start_received(void);

/**
 * @brief Keeps track of the on variable for the
 * on_received function in main.c
 * @return Boolean value of on
 */
bool ble_on_received(void);

/**
 * @brief Starts Bluetooth and sets up advertisement 
 */
int start_ble(void);


#endif //BLUETOOTH_H