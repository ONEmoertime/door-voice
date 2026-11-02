idf_component_register(
    SRCS "main.c" "net.c" "door.c" "secure.c"
    INCLUDE_DIRS "."
    REQUIRES nvs_flash esp_wifi esp_event esp_netif esp_websocket_client
             driver esp_timer mbedtls json
)
