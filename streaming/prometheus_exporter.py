# prometheus_exporter.py
from prometheus_client import start_http_server, Gauge

# Exporter 시작
def start_prometheus_exporter(port=8000):
    start_http_server(port)

# 메트릭 정의
fms_device_online = Gauge('fms_device_online', 'Device Online Status (1=Online, 0=Offline)', ['device_id'])

fms_sensor1_value = Gauge('fms_sensor1_value', 'Sensor 1 Value (°C)', ['device_id'])
fms_sensor2_value = Gauge('fms_sensor2_value', 'Sensor 2 Value (%)', ['device_id'])
fms_sensor3_value = Gauge('fms_sensor3_value', 'Sensor 3 Value (PSI)', ['device_id'])

fms_motor1_rpm = Gauge('fms_motor1_rpm', 'Motor 1 RPM', ['device_id'])
fms_motor2_rpm = Gauge('fms_motor2_rpm', 'Motor 2 RPM', ['device_id'])
fms_motor3_rpm = Gauge('fms_motor3_rpm', 'Motor 3 RPM', ['device_id'])

fms_failure_rate = Gauge('fms_failure_rate', 'Failure Rate (%)', ['device_id'])
fms_data_quality_score = Gauge('fms_data_quality_score', 'Data Quality Score (%)', ['device_id'])