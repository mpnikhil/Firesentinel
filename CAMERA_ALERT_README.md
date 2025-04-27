# FireSentinel Camera Alert System

A client-server system to monitor environmental sensors on a Raspberry Pi 5, take photos when abnormal conditions are detected, and send alerts to a MacBook server.

## System Components

1. **Raspberry Pi 5 Client**: Monitors environmental sensors, detects anomalies, takes photos, and sends alerts
2. **MacBook Server (Flask)**: Receives alerts and photos from the Raspberry Pi

## Setup Instructions

### MacBook Server Setup

1. Install required packages:
   ```
   pip install -r requirements_server.txt
   ```

2. Run the server:
   ```
   python server.py
   ```

3. The server will start on port 8000 and create a directory called `received_alerts` to store incoming images.

4. Note your MacBook's IP address on your local network:
   ```
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

### Raspberry Pi 5 Client Setup

1. Install required system packages for the camera:
   ```
   sudo apt update
   sudo apt install -y python3-picamera2 python3-libcamera
   ```

2. Install required Python packages:
   ```
   pip install -r requirements_rpi_camera.txt
   ```

3. Set the server IP address as an environment variable:
   ```bash
   export FIRESENTINEL_SERVER_HOST="your_macbook_ip"
   ```

   You can add this to your ~/.bashrc file to make it permanent:
   ```bash
   echo 'export FIRESENTINEL_SERVER_HOST="your_macbook_ip"' >> ~/.bashrc
   ```

   Alternatively, you can set the server address when running the client:
   ```bash
   FIRESENTINEL_SERVER_HOST="your_macbook_ip" python rpi_camera_client.py
   ```

4. (Optional) Customize settings with environment variables:
   ```bash
   # Change the threshold for consecutive abnormal readings (default is 10)
   export FIRESENTINEL_THRESHOLD="15"
   
   # Change the server port (default is 8000)
   export FIRESENTINEL_SERVER_PORT="8080"
   ```

5. Run the client:
   ```
   python rpi_camera_client.py
   ```

6. During runtime, you can type 'server' to change the server address interactively.

## How It Works

1. The Raspberry Pi continuously monitors environmental sensors (temperature, humidity, pressure, gas).
2. An anomaly detection model evaluates sensor readings to determine if conditions are normal or abnormal.
3. When 10 consecutive abnormal readings are detected, the system:
   - Takes a photo using the Raspberry Pi HQ Camera
   - Sends the photo and sensor data to the MacBook server
   - Logs the alert on both sides
4. The MacBook Flask server saves the received images with timestamps and displays alert information.

## Architecture

- **Server**: Flask web server running on the MacBook
- **Client**: Python application running on the Raspberry Pi
- **Communication**: RESTful API over HTTP
- **Data Format**: JSON with base64-encoded images

## Customization

- Adjust the `FIRESENTINEL_THRESHOLD` environment variable to change how many consecutive abnormal readings trigger an alert (default is 10).
- Modify camera settings in the initialization section of `rpi_camera_client.py` to adjust resolution, quality, etc.
- Change the server port by setting the `FIRESENTINEL_SERVER_PORT` environment variable or modifying the `PORT` variable in `server.py`.

## Troubleshooting

- **Camera issues**: Ensure the camera is properly connected to the Raspberry Pi 5 and enabled in raspi-config
- **Connection errors**: Check network connectivity, firewall settings, and that both devices are on the same network
- **Sensor errors**: Verify that all Enviro+ sensors are properly connected and functioning

## License

This project is open-source and free to use and modify. 