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
import numpy as np

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

# Import TFLite runtime for wildfire detection model
try:
    import tflite_runtime.interpreter as tflite
    from PIL import Image
    tflite_available = True
    logger.info("TFLite runtime available. Wildfire detection enabled.")
except ImportError:
    logger.warning("TFLite runtime not available. Wildfire detection will be disabled.")
    logger.warning("Install with: pip install tflite-runtime")
    tflite_available = False

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

# Threshold configuration
ABNORMAL_THRESHOLD = int(os.environ.get("FIRESENTINEL_THRESHOLD", "10"))  # Number of consecutive abnormal readings to trigger alert
FIRE_DETECTION_THRESHOLD = float(os.environ.get("FIRE_THRESHOLD", "0.5"))  # Minimum confidence score to confirm fire
WILDFIRE_MODEL_PATH = os.environ.get("WILDFIRE_MODEL_PATH", "quantized_wildfire_model.tflite")  # Path to TFLite model

logger.info(f"Server URL: {SERVER_URL}")
logger.info(f"Abnormal threshold: {ABNORMAL_THRESHOLD}")
logger.info(f"Fire detection threshold: {FIRE_DETECTION_THRESHOLD}")
logger.info(f"Wildfire model path: {WILDFIRE_MODEL_PATH}")

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

# Initialize TFLite model for fire detection if available
fire_detector = None
if tflite_available and camera_available:
    try:
        # Check if model file exists
        if os.path.exists(WILDFIRE_MODEL_PATH):
            logger.info(f"Loading TFLite model from {WILDFIRE_MODEL_PATH}")
            fire_detector = tflite.Interpreter(model_path=WILDFIRE_MODEL_PATH)
            fire_detector.allocate_tensors()
            logger.info("Fire detection model loaded successfully")
        else:
            logger.error(f"TFLite model file not found at {WILDFIRE_MODEL_PATH}")
            logger.error("Fire detection will be disabled")
            fire_detector = None
    except Exception as e:
        logger.error(f"Error loading TFLite model: {e}")
        logger.error("Fire detection will be disabled")
        fire_detector = None

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
            return None, None
        
        try:
            logger.info("Capturing photo...")
            
            # Initialize a new camera instance for each capture
            picam2 = Picamera2()
            
            # Use the still configuration mode instead of preview for higher quality
            config = picam2.create_still_configuration()
            picam2.configure(config)
            
            # Start the camera
            picam2.start()
            time.sleep(2)  # Increased warmup time
            
            # Create a BytesIO object to store the image data
            buffer = BytesIO()
            
            # Generate timestamp for the image filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            image_filename = f"alert_image_{timestamp}.jpg"
            
            # Capture an image and save it to disk
            logger.info(f"Saving image to {image_filename}")
            picam2.capture_file(image_filename)
            
            # Capture an image and save it to the BytesIO buffer
            picam2.capture_file(buffer, format="jpeg")
            buffer.seek(0)
            
            # Convert to base64 for sending over HTTP
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Properly close the camera
            picam2.close()
            
            logger.info("Photo captured successfully")
            return image_base64, image_filename
            
        except Exception as e:
            logger.error(f"Error capturing photo: {e}")
            # Try to get more detailed error information
            import traceback
            logger.error(traceback.format_exc())
            return None, None
    
    def detect_fire_in_image(self, image_path):
        """Use the TFLite model to detect fire in the image."""
        if not tflite_available or fire_detector is None:
            logger.warning("Fire detection not available, skipping fire detection")
            return False, 0.0
        
        try:
            logger.info(f"Running fire detection on {image_path}")
            
            # Load and preprocess image
            input_size = 224  # Standard input size for most image classification models
            img = Image.open(image_path).convert('RGB')
            img = img.resize((input_size, input_size))
            
            # Convert to numpy array and keep as uint8 (0-255)
            img_array = np.array(img, dtype=np.uint8)
            img_array = np.expand_dims(img_array, axis=0)
            
            # Get input and output details
            input_details = fire_detector.get_input_details()
            output_details = fire_detector.get_output_details()
            
            # Set input tensor
            fire_detector.set_tensor(input_details[0]['index'], img_array)
            
            # Run inference
            start_time = time.time()
            fire_detector.invoke()
            inference_time = time.time() - start_time
            
            # Get output tensor
            output = fire_detector.get_tensor(output_details[0]['index'])
            
            # Convert quantized output to probability (if using uint8 quantization)
            if output.dtype == np.uint8:
                # Get scale and zero point from output details
                scale = output_details[0]['quantization'][0]
                zero_point = output_details[0]['quantization'][1]
                # Dequantize the output
                score = (output[0][0] - zero_point) * scale
            else:
                score = float(output[0][0])
            
            # Determine if fire is detected based on threshold
            is_fire_detected = score >= FIRE_DETECTION_THRESHOLD
            
            logger.info(f"Fire detection result: {is_fire_detected} (confidence: {score:.4f}, inference time: {inference_time*1000:.2f} ms)")
            
            # Save a copy of the image with the detection result
            detection_filename = f"fire_detection_{time.strftime('%Y%m%d-%H%M%S')}.jpg"
            with open(image_path, "rb") as src_file:
                with open(detection_filename, "wb") as dst_file:
                    dst_file.write(src_file.read())
            
            # Append detection result to the filename
            result_text = f"_FIRE_{score:.2f}" if is_fire_detected else f"_NOFIRE_{score:.2f}"
            os.rename(detection_filename, detection_filename.replace(".jpg", f"{result_text}.jpg"))
            
            return is_fire_detected, score
            
        except Exception as e:
            logger.error(f"Error during fire detection: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, 0.0
    
    def send_alert(self, sensor_data):
        """Send alert with image to the server if fire is detected."""
        # First capture an image
        image_data, image_filename = self.capture_image()
        
        fire_detected = False
        fire_score = 0.0
        
        # Check for fire in the image if available
        if image_filename and os.path.exists(image_filename):
            fire_detected, fire_score = self.detect_fire_in_image(image_filename)
            
            # If fire detection is available but no fire detected, don't send alert
            if fire_detector is not None and not fire_detected:
                logger.info("No fire detected in image, skipping alert")
                return False
        
        # Convert NumPy types to Python native types for JSON serialization
        alert_data = {
            "timestamp": float(time.time()),
            "abnormal_count": int(self.abnormal_count),
            "last_reading": {
                "temperature": float(sensor_data["temperature"]),
                "humidity": float(sensor_data["humidity"]),
                "pressure": float(sensor_data["pressure"]),
                "gas_oxidising": float(sensor_data["gas_oxidising"]),
                "gas_reducing": float(sensor_data["gas_reducing"]),
                "gas_nh3": float(sensor_data["gas_nh3"])
            },
            "fire_detected": bool(fire_detected),
            "fire_confidence": float(fire_score)
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
                json=alert_data,
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
                            # Send alert to server (only proceeds if fire is detected or fire detection unavailable)
                            alert_sent = self.send_alert(sensor_data)
                            # Reset counter after sending alert
                            if alert_sent:
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

def test_fire_detection(image_path=None):
    """Test the fire detection functionality."""
    if not tflite_available or fire_detector is None:
        logger.error("Cannot test fire detection: TFLite or model not available")
        return
    
    if image_path is None or not os.path.exists(image_path):
        # Take a test image
        if not camera_available:
            logger.error("Cannot test fire detection: Camera not available")
            return
            
        try:
            # Capture an image
            picam2 = Picamera2()
            config = picam2.create_still_configuration()
            picam2.configure(config)
            picam2.start()
            time.sleep(2)
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            image_path = f"fire_test_{timestamp}.jpg"
            picam2.capture_file(image_path)
            picam2.close()
            
            logger.info(f"Captured test image: {image_path}")
        except Exception as e:
            logger.error(f"Error capturing test image: {e}")
            return
    
    try:
        # Process the image for fire detection
        logger.info(f"Testing fire detection on image: {image_path}")
        
        # Load and preprocess image
        input_size = 224
        img = Image.open(image_path).convert('RGB')
        img = img.resize((input_size, input_size))
        
        # Convert to numpy array as uint8 (0-255)
        img_array = np.array(img, dtype=np.uint8)
        img_array = np.expand_dims(img_array, axis=0)
        
        # Get input and output details
        input_details = fire_detector.get_input_details()
        output_details = fire_detector.get_output_details()
        
        # Set input tensor
        fire_detector.set_tensor(input_details[0]['index'], img_array)
        
        # Run inference
        start_time = time.time()
        fire_detector.invoke()
        inference_time = time.time() - start_time
        
        # Get output tensor
        output = fire_detector.get_tensor(output_details[0]['index'])
        
        # Convert quantized output to probability
        if output.dtype == np.uint8:
            # Get scale and zero point from output details
            scale = output_details[0]['quantization'][0]
            zero_point = output_details[0]['quantization'][1]
            # Dequantize the output
            score = (output[0][0] - zero_point) * scale
        else:
            score = float(output[0][0])
        
        # Determine if fire is detected based on threshold
        is_fire_detected = score >= FIRE_DETECTION_THRESHOLD
        
        logger.info(f"Fire detection test result: {'FIRE DETECTED' if is_fire_detected else 'NO FIRE'}")
        logger.info(f"Confidence score: {score:.4f}")
        logger.info(f"Threshold: {FIRE_DETECTION_THRESHOLD}")
        logger.info(f"Inference time: {inference_time*1000:.2f} ms")
        
        return is_fire_detected, score
        
    except Exception as e:
        logger.error(f"Error testing fire detection: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, 0.0

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
                time.sleep(2)
                test_picam.capture_file("camera_test.jpg")
                test_picam.close()
                logger.info("Camera test successful! Test image saved as camera_test.jpg")
                
                # Test fire detection with the test image
                if tflite_available and fire_detector is not None:
                    logger.info("Testing fire detection with test image...")
                    test_fire_detection("camera_test.jpg")
            except Exception as e:
                logger.error(f"Camera test failed: {e}")
                camera_available = False
        
        # Create and start the monitor
        monitor = CameraSensorMonitor()
        monitor.start()
        
        # Keep the main thread alive
        while True:
            command = input("Type 'exit' to stop, 'server' to set server address, 'test' to test camera, 'fire' to test fire detection, or press Enter: ")
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
                        time.sleep(2)
                        timestamp = time.strftime("%Y%m%d-%H%M%S")
                        test_filename = f"camera_test_{timestamp}.jpg"
                        test_picam.capture_file(test_filename)
                        test_picam.close()
                        logger.info(f"Camera test successful! Test image saved as {test_filename}")
                    except Exception as e:
                        logger.error(f"Camera test failed: {e}")
                else:
                    logger.warning("Camera is not available for testing")
            elif command.lower() == 'fire':
                # Test fire detection
                if tflite_available and fire_detector is not None:
                    image_path = input("Enter path to image (leave blank to capture new image): ")
                    if image_path.strip() == "":
                        image_path = None
                    test_fire_detection(image_path)
                else:
                    logger.warning("Fire detection is not available")
    
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Stop the monitor
        if 'monitor' in locals():
            monitor.stop() 