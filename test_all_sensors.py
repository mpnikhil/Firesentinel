import time
from bme280 import BME280
try:
    from enviroplus import gas
    gas_available = True
except ImportError:
    gas_available = False
try:
    import ltr559
    ltr559_available = True
except ImportError:
    ltr559_available = False
try:
    from pms5003 import PMS5003, ReadTimeoutError
    pms5003_available = True
except ImportError:
    pms5003_available = False

from smbus2 import SMBus

print("Testing Enviro+ sensors...")
bus = SMBus(1)
bme280 = BME280(i2c_dev=bus, i2c_addr=0x76)

# BME280 sensor
temperature = bme280.get_temperature()
pressure = bme280.get_pressure()
humidity = bme280.get_humidity()
print(f"Temperature: {temperature:.2f}°C")
print(f"Pressure: {pressure:.2f}hPa")
print(f"Humidity: {humidity:.2f}%")

# Gas sensor
if gas_available:
    readings = gas.read_all()
    print(f"Oxidising: {readings.oxidising}")
    print(f"Reducing: {readings.reducing}")
    print(f"NH3: {readings.nh3}")
else:
    print("Gas sensor not available")

# Light and proximity sensor
if ltr559_available:
    proximity = ltr559.get_proximity()
    lux = ltr559.get_lux()
    print(f"Proximity: {proximity}")
    print(f"Light: {lux} lux")
else:
    print("LTR559 sensor not available")

# PMS5003 particulate sensor
if pms5003_available:
    try:
        pms5003 = PMS5003()
        readings = pms5003.read()
        print(f"PM1.0: {readings.pm_ug_per_m3(1.0)} µg/m³")
        print(f"PM2.5: {readings.pm_ug_per_m3(2.5)} µg/m³")
        print(f"PM10: {readings.pm_ug_per_m3(10)} µg/m³")
    except Exception as e:
        print(f"PMS5003 error: {e}")
else:
    print("PMS5003 sensor not available")
