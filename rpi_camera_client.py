#!/usr/bin/env python3
import time
import sys
import os
import threading
import requests
import json
import base64
from io import BytesIO
import logging
import socket
from pathlib import Path
from anomaly_inference import AnomalyDetector
from collections import deque

# Set up logging
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Import sensor-related libraries
from enviroplus import gas
from bme280 import BME280
from smbus2 import SMBus

# Import picamera2 for the Raspberry Pi camera module
try:
    from picamera2 import Picamera2
    camera_available = True
except ImportError:
    logger.warning("PiCamera2 not available. Camera features will be disabled.")
    camera_available = False

# Configuration
# Get server address from environment variable or use default
SERVER_HOST = os.environ.get("FIRESENTINEL_SERVER_HOST", "")
SERVER_PORT = os.environ.get("FIRESENTINEL_SERVER_PORT", "8000")
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/alert"

# If server host not set, try to auto-discover on first run
if not SERVER_HOST:
    logger.warning("Server host not set. Will attempt to use default gateway.")
    try:
        # Get default gateway IP (usually the router)
        import netifaces
        gws = netifaces.gateways()
        gateway = gws['default'][netifaces.AF_INET][0]
        SERVER_URL = f"http://your_macbook_ip:8000/alert"
        logger.info(f"Please set the server address manually by editing this file or using environment variables")
    except:
        logger.warning("Could not determine gateway IP. Please set FIRESENTINEL_SERVER_HOST environment variable")
        SERVER_URL = "http://your_macbook_ip:8000/alert"

ABNORMAL_THRESHOLD = int(os.environ.get("FIRESENTINEL_THRESHOLD", "10"))  # Number of consecutive abnormal readings to trigger alert

logger.info(f"Server URL: {SERVER_URL}")
logger.info(f"Abnormal threshold: {ABNORMAL_THRESHOLD}")

# Initialize BME280 sensor
bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)

# Test if camera is available by trying to initialize it once
if camera_available:
    try:
        test_cam = Picamera2()
        test_cam.close()
        logger.info("Camera module is available")
    except Exception as e:
        logger.error(f"Error testing camera: {e}")
        camera_available = False

# Allow sensors to stabilize
time.sleep(1.0)
logger.info("Sensors initialized")

class CameraSensorMonitor:
    def __init__(self, model_path=None):
        """Initialize the sensor monitor."""
        self.running = False
        self.current_status = "unknown"
        self.abnormal_count = 0  # Counter for consecutive abnormal readings
        self.status_history = deque(maxlen=20)  # Keep track of recent statuses
        
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
    
    def capture_image(self):
        """Capture an image from the camera using the still configuration."""
        if not camera_available:
            logger.warning("Attempted to capture image but camera is not available")
            return None
        
        try:
            logger.info("Capturing photo...")
            
            # Initialize a new camera instance for each capture (similar to rpicam-still)
            picam2 = Picamera2()
            
            # Use the still configuration mode instead of preview for higher quality
            config = picam2.create_still_configuration()
            picam2.configure(config)
            
            # Start the camera
            picam2.start()
            time.sleep(1)  # Brief warmup
            
            # Create a BytesIO object to store the image data
            buffer = BytesIO()
            
            # Capture an image and save it to the BytesIO buffer
            picam2.capture_file(buffer, format="jpeg")
            buffer.seek(0)
            
            # Also save a copy to disk for debugging
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            picam2.capture_file(f"alert_image_{timestamp}.jpg")
            
            # Convert to base64 for sending over HTTP
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Properly close the camera
            picam2.close()
            
            logger.info("Photo captured successfully")
            return image_base64
            
        except Exception as e:
            logger.error(f"Error capturing photo: {e}")
            # Try to get more detailed error information
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def send_alert(self, sensor_data):
        """Send alert with image to the server."""
        # First capture an image
        image_data = self.capture_image()
        
        # Prepare the alert data
        alert_data = {
            "timestamp": time.time(),
            "abnormal_count": self.abnormal_count,
            "last_reading": sensor_data
        }
        
        # Add image if available
        if image_data:
            alert_data["image"] = image_data
            logger.info("Image included in alert data")
        else:
            logger.warning("No image available to include in alert")
        
        try:
            # Send to server
            logger.info(f"Sending alert to server: {SERVER_URL}")
            response = requests.post(
                SERVER_URL, 
                json=alert_data,  # Use json parameter instead of data for proper JSON encoding
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Alert sent successfully")
                return True
            else:
                logger.error(f"Failed to send alert: HTTP {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
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
                    
                    # Track status history
                    self.status_history.append(self.current_status)
                    
                    # Update abnormal counter
                    if self.current_status == "abnormal":
                        self.abnormal_count += 1
                        
                        # Check if we've reached the threshold for alert
                        if self.abnormal_count >= ABNORMAL_THRESHOLD:
                            logger.warning(f"ALERT! {self.abnormal_count} consecutive abnormal readings detected")
                            # Send alert to server
                            self.send_alert(sensor_data)
                            # Reset counter after sending alert
                            self.abnormal_count = 0
                    else:
                        # Reset counter when normal reading is detected
                        self.abnormal_count = 0
                    
                    # Output status
                    status_output = {
                        "timestamp": time.time(),
                        "status": result["condition"],
                        "confidence": result["raw_score"],
                        "sensor_data": sensor_data,
                        "inference_time_ms": result["inference_time_ms"],
                        "abnormal_count": self.abnormal_count
                    }
                    
                    # Log the result
                    logger.info(
                        f"Status: {result['condition']} (score: {result['raw_score']:.4f}) - "
                        f"Abnormal count: {self.abnormal_count}/{ABNORMAL_THRESHOLD} - "
                        f"Temp: {sensor_data['temperature']:.1f}°C, "
                        f"Humidity: {sensor_data['humidity']:.1f}%, "
                        f"Pressure: {sensor_data['pressure']:.1f}hPa"
                    )
                    
                    # Print status in JSON format 
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
        # Check if we can capture an image before starting
        if camera_available:
            logger.info("Testing camera before starting monitoring...")
            try:
                test_picam = Picamera2()
                test_config = test_picam.create_still_configuration()
                test_picam.configure(test_config)
                test_picam.start()
                time.sleep(1)
                test_picam.capture_file("camera_test.jpg")
                test_picam.close()
                logger.info("Camera test successful! Test image saved as camera_test.jpg")
            except Exception as e:
                logger.error(f"Camera test failed: {e}")
                camera_available = False
        
        # Create and start the monitor
        monitor = CameraSensorMonitor()
        monitor.start()
        
        # Keep the main thread alive
        while True:
            command = input("Type 'exit' to stop the monitoring, 'server' to set server address, 'test' to test camera, or press Enter to continue: ")
            if command.lower() == 'exit':
                break
            elif command.lower() == 'server':
                new_host = input("Enter server IP address: ")
                os.environ["FIRESENTINEL_SERVER_HOST"] = new_host
                SERVER_URL = f"http://{new_host}:{SERVER_PORT}/alert"
                logger.info(f"Server URL updated to: {SERVER_URL}")
            elif command.lower() == 'test':
                # Test the camera
                if camera_available:
                    try:
                        logger.info("Testing camera...")
                        test_picam = Picamera2()
                        test_config = test_picam.create_still_configuration()
                        test_picam.configure(test_config)
                        test_picam.start()
                        time.sleep(1)
                        timestamp = time.strftime("%Y%m%d-%H%M%S")
                        test_picam.capture_file(f"camera_test_{timestamp}.jpg")
                        test_picam.close()
                        logger.info(f"Camera test successful! Test image saved as camera_test_{timestamp}.jpg")
                    except Exception as e:
                        logger.error(f"Camera test failed: {e}")
                else:
                    logger.warning("Camera is not available for testing")
    
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Stop the monitor
        if 'monitor' in locals():
            monitor.stop() 