#!/usr/bin/env python3
import time
import sys
import os
import threading
from anomaly_inference import AnomalyDetector
from pathlib import Path
import json

# Set up logging
import logging
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Import sensor-related libraries
from enviroplus import gas
from bme280 import BME280
from smbus2 import SMBus

# Initialize BME280 sensor
bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)

# Allow sensors to stabilize
time.sleep(1.0)
logger.info("Sensors initialized")

class SensorMonitor:
    def __init__(self, model_path=None):
        """Initialize the sensor monitor."""
        self.running = False
        self.current_status = "unknown"
        
        # Find the model files
        if model_path is None:
            script_dir = Path(__file__).parent.absolute()
            model_path = script_dir / "anomaly_detection_model.joblib"
            scaler_path = script_dir / "scaler.joblib"
        else:
            model_path = Path(model_path)
            scaler_path = model_path.parent / "scaler.joblib"
        
        # Check if files exist
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler file not found: {scaler_path}")
        
        # Initialize the anomaly detector
        self.detector = AnomalyDetector(
            model_path=str(model_path),
            scaler_path=str(scaler_path)
        )
        
        logger.info("Sensor monitor initialized with Random Forest model")
    
    def read_sensor_data(self):
        """Read data from sensors."""
        # Read from sensors
        temperature = bme280.get_temperature()
        humidity = bme280.get_humidity()
        pressure = bme280.get_pressure()
        
        gas_data = gas.read_all()
        gas_oxidising = gas_data.oxidising
        gas_reducing = gas_data.reducing
        gas_nh3 = gas_data.nh3
            
        return {
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "gas_oxidising": gas_oxidising,
            "gas_reducing": gas_reducing,
            "gas_nh3": gas_nh3
        }
    
    def monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self.running:
                try:
                    # Read sensor data
                    sensor_data = self.read_sensor_data()
                    
                    # Prepare features in the same order as the training data
                    features = [
                        sensor_data["temperature"],
                        sensor_data["humidity"],
                        sensor_data["pressure"],
                        sensor_data["gas_oxidising"],
                        sensor_data["gas_reducing"],
                        sensor_data["gas_nh3"]
                    ]
                    
                    # Make prediction
                    result = self.detector.predict(features)
                    self.current_status = result["condition"]
                    
                    # Output clear format for status (ideal for later server integration)
                    status_output = {
                        "timestamp": time.time(),
                        "status": result["condition"],
                        "confidence": result["raw_score"],
                        "sensor_data": sensor_data,
                        "inference_time_ms": result["inference_time_ms"]
                    }
                    
                    # Log the result
                    logger.info(
                        f"Status: {result['condition']} (score: {result['raw_score']:.4f}) - "
                        f"Temp: {sensor_data['temperature']:.1f}°C, "
                        f"Humidity: {sensor_data['humidity']:.1f}%, "
                        f"Pressure: {sensor_data['pressure']:.1f}hPa, "
                        f"Gas: {sensor_data['gas_oxidising']:.0f}/{sensor_data['gas_reducing']:.0f}/{sensor_data['gas_nh3']:.0f}"
                    )
                    
                    # Print status in JSON format (will be useful for remote server later)
                    print(json.dumps(status_output))
                
                except Exception as e:
                    logger.error(f"Error in sensor reading or inference: {e}")
                
                # Sleep for a bit
                time.sleep(2)
        
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
    
    def start(self):
        """Start the monitoring thread."""
        if self.running:
            logger.warning("Monitoring is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Monitoring started")
    
    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        
        logger.info("Monitoring stopped")

if __name__ == "__main__":
    try:
        # Create and start the monitor
        monitor = SensorMonitor()
        monitor.start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Stop the monitor
        if 'monitor' in locals():
            monitor.stop() 