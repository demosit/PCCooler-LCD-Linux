from pathlib import Path

def find_sensor(driver):
    for name_file in Path("/sys/class/hwmon").glob("hwmon*/name"):
        if name_file.read_text().strip() == driver:
            sensor = name_file.parent / "temp1_input"
            if sensor.exists():
                return sensor
    return None

def read_temp(driver):
    sensor = find_sensor(driver)
    if sensor:
        return float(sensor.read_text().strip()) / 1000
    return None

