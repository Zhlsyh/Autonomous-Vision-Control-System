#include <atomic>
#include <cstdint>
#include <cstdlib>

#include "esp_random.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <freertos/timers.h>

static const char *TAG = "industrial_gateway";
static constexpr float OVERHEAT_LIMIT = 60.0F;

struct SensorData {
  float voltage;
  float current;
  uint32_t timestamp;
};

static QueueHandle_t telemetryQueue;
static std::atomic<bool> emergencyState{false};

static void vHeartbeatCallback(TimerHandle_t timer) {
  (void)timer;
  ESP_LOGI(TAG, "[TIMER] System Heartbeat: Alive & Running...");
}

static void vTaskSafetyMonitor(void *pvParameters) {
  (void)pvParameters;

  for (;;) {
    const float tempReading =
        30.0F + static_cast<float>(esp_random() % 400U) / 10.0F;

    if (tempReading >= OVERHEAT_LIMIT) {
      emergencyState.store(true, std::memory_order_relaxed);
      ESP_LOGE(TAG,
               "[CRITICAL ALERT] Suhu Kritis Terdeteksi: %.1f C! "
               "Mematikan Beban...",
               tempReading);
    } else {
      emergencyState.store(false, std::memory_order_relaxed);
    }

    vTaskDelay(pdMS_TO_TICKS(500));
  }
}

static void vTaskSensorProducer(void *pvParameters) {
  (void)pvParameters;
  SensorData sensorData{};

  for (;;) {
    if (!emergencyState.load(std::memory_order_relaxed)) {
      sensorData.voltage =
          210.0F + static_cast<float>(esp_random() % 200U) / 10.0F;
      sensorData.current =
          1.0F + static_cast<float>(esp_random() % 140U) / 10.0F;
      sensorData.timestamp =
          static_cast<uint32_t>(esp_timer_get_time() / 1000);

      if (xQueueSend(telemetryQueue, &sensorData, pdMS_TO_TICKS(100)) != pdPASS) {
        ESP_LOGW(TAG, "[WARN] Telemetry Queue Full! Data terbuang.");
      } else {
        ESP_LOGI(TAG, "[PRODUCER] Data ADC berhasil dikirim ke Queue.");
      }
    }

    vTaskDelay(pdMS_TO_TICKS(1000));
  }
}

static void vTaskCloudConsumer(void *pvParameters) {
  (void)pvParameters;
  SensorData receivedData{};

  for (;;) {
    if (xQueueReceive(telemetryQueue, &receivedData, portMAX_DELAY) == pdTRUE) {
      ESP_LOGI(TAG,
               "[CLOUD] Publishing Data via MQTT/HTTP: "
               "Tegangan=%.1f V, Arus=%.1f A, Waktu=%u ms",
               receivedData.voltage, receivedData.current,
               static_cast<unsigned int>(receivedData.timestamp));

      vTaskDelay(pdMS_TO_TICKS(1500));
    }
  }
}

extern "C" void app_main(void) {
  ESP_LOGI(TAG, "Memulai FreeRTOS Industrial Gateway (ESP-IDF / ESP32)");

  telemetryQueue = xQueueCreate(5, sizeof(SensorData));
  if (telemetryQueue == nullptr) {
    ESP_LOGE(TAG, "Gagal membuat telemetry queue.");
    std::abort();
  }

  TimerHandle_t heartbeatTimer = xTimerCreate(
      "HeartbeatTimer", pdMS_TO_TICKS(5000), pdTRUE, nullptr,
      vHeartbeatCallback);
  if (heartbeatTimer == nullptr) {
    ESP_LOGE(TAG, "Gagal membuat heartbeat timer.");
    std::abort();
  }
  if (xTimerStart(heartbeatTimer, 0) != pdPASS) {
    ESP_LOGE(TAG, "Gagal memulai heartbeat timer.");
    std::abort();
  }

  if (xTaskCreatePinnedToCore(vTaskSafetyMonitor, "SafetyTask", 2048, nullptr,
                              3, nullptr, 1) != pdPASS) {
    ESP_LOGE(TAG, "Gagal membuat SafetyTask.");
    std::abort();
  }
  if (xTaskCreatePinnedToCore(vTaskSensorProducer, "ProducerTask", 2048,
                              nullptr, 2, nullptr, 1) != pdPASS) {
    ESP_LOGE(TAG, "Gagal membuat ProducerTask.");
    std::abort();
  }
  if (xTaskCreatePinnedToCore(vTaskCloudConsumer, "ConsumerTask", 4096,
                              nullptr, 1, nullptr, 0) != pdPASS) {
    ESP_LOGE(TAG, "Gagal membuat ConsumerTask.");
    std::abort();
  }
}