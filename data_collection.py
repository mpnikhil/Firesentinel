import time
import board
import busio
from adafruit_bme280 import Adafruit_BME280_I2C
from enviroplus import gas
from ltr559 import LTR559
import csv
from datetime import datetime

# Initialize sensors
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = Adafruit_BME280_I2C(i2c)
ltr559 = LTR559()

# Set up data collection
def collect_data(filename, condition, duration_seconds=180, sample_rate=1):
    """
    Collect sensor data for specified duration
    filename: output CSV file
    condition: 'normal', 'incense', 'hairdryer', etc.
    duration_seconds: how long to collect data
    sample_rate: samples per second
    """
    # Create/open file with headers
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['timestamp', 'temperature', 'humidity', 'pressure', 
                         'gas_oxidising', 'gas_reducing', 'gas_nh3', 'light', 'condition'])
        
        print(f"Starting data collection for condition: {condition}")
        print(f"Duration: {duration_seconds} seconds")
        print("Press Ctrl+C to stop early")
        
        start_time = time.time()
        sample_count = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                # Read sensor values
                timestamp = datetime.now().isoformat()
                temperature = bme280.temperature
                humidity = bme280.relative_humidity
                pressure = bme280.pressure
                
                gas_readings = gas.read_all()
                oxidising = gas_readings.oxidising
                reducing = gas_readings.reducing
                nh3 = gas_readings.nh3
                
                light = ltr559.get_lux()
                
                # Write data
                writer.writerow([timestamp, temperature, humidity, pressure, 
                                oxidising, reducing, nh3, light, condition])
                
                # Print status
                sample_count += 1
                if sample_count % 10 == 0:
                    print(f"Samples: {sample_count}, Temp: {temperature:.1f}°C, Humidity: {humidity:.1f}%, Light: {light:.1f} lux")
                
                # Wait for next sample
                time.sleep(1/sample_rate)
                
        except KeyboardInterrupt:
            print("Data collection stopped early")
        
        print(f"Collected {sample_count} samples for condition: {condition}")
        print(f"Data saved to {filename}")

collect_data('data/normal.csv', 'normal')