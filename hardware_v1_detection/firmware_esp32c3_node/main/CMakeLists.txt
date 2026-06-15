idf_component_register(
    SRCS
        "app_main.c"
        "bmi160.c"
        "i2c_bus.c"
    INCLUDE_DIRS "."
    REQUIRES driver esp_driver_gpio esp_driver_tsens esp_timer esp_wifi nvs_flash
)
