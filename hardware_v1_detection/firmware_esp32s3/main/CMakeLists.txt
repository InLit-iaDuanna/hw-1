idf_component_register(
    SRCS
        "app_main.c"
        "bmi160.c"
        "bmx055.c"
        "i2c_bus.c"
        "packet.c"
        "tca9548a.c"
    INCLUDE_DIRS "."
    REQUIRES driver esp_driver_gpio esp_driver_usb_serial_jtag esp_timer esp_wifi nvs_flash
)
