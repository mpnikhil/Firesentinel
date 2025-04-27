# Anomaly Detection for Raspberry Pi 5

This project implements a small Random Forest model for detecting anomalies in sensor data on a Raspberry Pi 5. The model is trained to distinguish between normal and abnormal environmental conditions based on sensor readings.

## Overview

The system uses the following sensors:
- Temperature, humidity, and pressure (via BME280)
- Gas sensors (oxidizing, reducing, NH3)

The trained model is small enough to run efficiently on a Raspberry Pi 5, making real-time predictions to identify abnormal environmental conditions.

## Requirements

### Hardware
- Raspberry Pi 5
- Enviro+ sensor board or compatible sensors:
  - BME280 temperature, humidity and pressure sensor
  - MICS6814 analog gas sensor
- Two LEDs (optional) for status indication: 
  - Green LED for normal state
  - Red LED for abnormal state

### Software Dependencies
```
pip install numpy pandas scikit-learn joblib
pip install RPi.GPIO smbus2 enviroplus
```

For the Enviro+ library, you may need to follow installation instructions at: 
https://github.com/pimoroni/enviroplus-python

## Files in this Project

- `anomaly_detection_model.py` - Script to train the Random Forest model for anomaly detection
- `anomaly_detection_model.joblib` - The trained Random Forest model file
- `scaler.joblib` - The scaler for preprocessing data
- `feature_names.joblib` - Feature names for model interpretation
- `anomaly_inference.py` - Class for making predictions with the Random Forest model
- `rpi_sensor_monitor.py` - Main script for monitoring sensors and making predictions
- `README.md` - This documentation file

## Setup Instructions

1. Clone this repository to your Raspberry Pi 5:
   ```
   git clone <repository_url>
   cd <repository_directory>
   ```

2. Install the required dependencies:

   **On Raspberry Pi 5:**
   ```
   # Install system packages for GPIO control
   sudo apt install python3-gpiod libgpiod-dev libgpiod2 gpiod
   
   # Install Python dependencies
   pip install -r requirements_rpi.txt
   ```

   **On development machines (Mac/PC):**
   ```
   pip install -r requirements.txt
   ```

3. Connect the sensors and LEDs:
   - Connect your Enviro+ board to the Raspberry Pi
   - (Optional) Connect LEDs to the specified GPIO pins (16 for normal, 26 for abnormal)

4. Run the training script to generate the model (if it doesn't already exist):
   ```
   python anomaly_detection_model.py
   ```
   This will create the Random Forest model and scaler files.

5. Make the monitoring script executable:
   ```
   chmod +x rpi_sensor_monitor.py
   ```

## Usage

Run the monitoring script to start anomaly detection:
```
./rpi_sensor_monitor.py
```

The script will:
- Read sensor data continuously
- Make predictions using the Random Forest model
- Log the status (normal or abnormal) and sensor readings
- Update LEDs to indicate the current status (if connected)

You can also import the `SensorMonitor` class from `rpi_sensor_monitor.py` into your own Python projects to integrate anomaly detection with other applications.

## Customization

### Adjusting LED Pins
The default GPIO pins for LEDs are:
- Normal status LED: GPIO 16
- Abnormal status LED: GPIO 26

To change these, modify the `NORMAL_LED_PIN` and `ABNORMAL_LED_PIN` variables in `rpi_sensor_monitor.py`.

### Retraining the Model
If you have different sensors or want to retrain the model with your own data:

1. Collect your data in CSV files with the same format as the training data
2. Modify the file paths in `anomaly_detection_model.py` to point to your data
3. Run the training script again:
   ```
   python anomaly_detection_model.py
   ```

4. For fine-tuning the Random Forest parameters, you can modify these settings in the training script:
   ```python
   rf_model = RandomForestClassifier(
       n_estimators=100,  # Number of trees (increase for better accuracy)
       max_depth=10,      # Maximum depth of trees
       min_samples_split=5,
       min_samples_leaf=2,
       random_state=42,
       n_jobs=-1  # Use all available cores
   )
   ```

## Testing Without Sensors

The code includes a simulation mode that generates fake sensor data for testing without physical sensors. This mode is automatically activated if the required sensor libraries are not found.

## Important Notes for Raspberry Pi 5

The Raspberry Pi 5 has a different GPIO architecture than previous models. Here's what you need to know:

1. **GPIO Library**: This project uses `gpiod` instead of `RPi.GPIO` for controlling GPIO pins on Raspberry Pi 5. The older `RPi.GPIO` library is not compatible with Raspberry Pi 5.

2. **LED Pin Configuration**: The default GPIO pins for LEDs can be found in `rpi_sensor_monitor.py`:
   - Normal status LED: GPIO 16
   - Abnormal status LED: GPIO 26

3. **GPIO Command Line Tools**: For debugging GPIO issues, you can use the command line tools provided by gpiod:
   ```
   # List available GPIO chips
   gpiodetect
   
   # Show information about GPIO lines
   gpioinfo
   
   # Set a GPIO line manually (for testing)
   gpioset gpiochip0 16=1
   ```

## License

[Your license information here] 