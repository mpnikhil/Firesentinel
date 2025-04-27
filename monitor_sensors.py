import time
from bme280 import BME280
from enviroplus import gas
from ltr559 import LTR559
from smbus2 import SMBus

# Initialize sensors
bus = SMBus(1)
bme280 = BME280(i2c_dev=bus, i2c_addr=0x76)
ltr559_sensor = LTR559()

print("Starting sensor monitoring. Press Ctrl+C to stop.")
print("-----------------------------------------------")

try:
    while True:
        # Read BME280 sensor
        temperature = bme280.get_temperature()
        humidity = bme280.get_humidity()
        pressure = bme280.get_pressure()
        
        # Read gas sensor
        gas_readings = gas.read_all()
        oxidising = gas_readings.oxidising
        reducing = gas_readings.reducing
        nh3 = gas_readings.nh3
        
        # Read light sensor
        light = ltr559_sensor.get_lux()
        
        # Clear screen and print readings
        print("\033[2J\033[H")  # Clear screen
        print("Sensor Readings:")
        print("-----------------------------------------------")
        print(f"Temperature: {temperature:.2f}°C")
        print(f"Humidity: {humidity:.2f}%")
        print(f"Pressure: {pressure:.2f}hPa")
        print("-----------------------------------------------")
        print(f"Gas - Oxidising: {oxidising:.2f}")
        print(f"Gas - Reducing: {reducing:.2f}")
        print(f"Gas - NH3: {nh3:.2f}")
        print("-----------------------------------------------")
        print(f"Light: {light:.2f} lux")
        print("-----------------------------------------------")
        print("Press Ctrl+C to stop")
        
        # Wait before next reading
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\nMonitoring stopped by user")