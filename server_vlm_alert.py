#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template_string
import json
import os
import base64
from datetime import datetime
import threading
from pathlib import Path
import logging
from integrations.validation_and_alert import validate_and_alert, alert

# Configuration
PORT = 8000
SAVE_DIR = Path("received_alerts")

# Set up logging
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Create directory for saving images if it doesn't exist
SAVE_DIR.mkdir(exist_ok=True)

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def home():
    """Home page with basic server status information"""
    return render_template_string("""
    <html>
    <head>
        <title>FireSentinel Alert Server</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #d62728; }
            .status { font-size: 18px; margin: 20px 0; padding: 10px; background-color: #f0f0f0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>FireSentinel Alert Server</h1>
        <div class="status">Server is running and ready to receive alerts from Raspberry Pi.</div>
        <p>Alerts and images are saved in the <code>received_alerts</code> directory.</p>
        <p>This server includes VLM-based fire detection and Twilio phone alerts.</p>
    </body>
    </html>
    """)

@app.route('/alert', methods=['POST'])
def receive_alert():
    """Endpoint to receive alerts from Raspberry Pi"""
    try:
        data = request.json
        
        # Log alert information
        print("\n🚨 ALERT RECEIVED 🚨")
        print(f"Timestamp: {datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Consecutive abnormal readings: {data['abnormal_count']}")
        print(f"Last sensor readings: {data['last_reading']}")
        
        response_data = {
            "status": "alert_received",
            "timestamp": datetime.now().isoformat()
        }
        
        # Save and process the image if present
        if 'image' in data:
            img_data = base64.b64decode(data['image'])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = SAVE_DIR / f"alert_{timestamp}.jpg"
            
            with open(img_path, 'wb') as f:
                f.write(img_data)
            
            print(f"📸 Image saved to: {img_path}")
            
            # Call validate_and_alert from integrations
            result = validate_and_alert(str(img_path))
            print(f"🔍 VLM Analysis Result: {result}")
            
            # If fire detected, send alert
            if result == "YES":
                alert_sent = alert(result)
                print("🚨 Alert sent!" if alert_sent else "❌ Alert failed to send")
                response_data.update({
                    "fire_detected": True,
                    "alert_sent": alert_sent
                })
            else:
                response_data.update({
                    "fire_detected": False,
                    "validation_result": result
                })
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error processing alert: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def run_server():
    """Run the Flask server in a thread"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    
if __name__ == "__main__":
    try:
        # Check for required environment variables
        required_vars = ["ANTHROPIC_API_KEY", "TWILIO_ACCOUNT_SID", 
                        "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            print("⚠️  Missing required environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
            print("\nPlease set these environment variables before starting the server.")
            exit(1)
            
        print(f"🚀 Enhanced Alert Server starting at http://0.0.0.0:{PORT}")
        print(f"Alerts will be saved to: {SAVE_DIR.absolute()}")
        
        # Start server in separate thread
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Keep main thread running
        while True:
            command = input("Type 'exit' to stop the server: ")
            if command.lower() == 'exit':
                break
                
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    finally:
        print("Server shutdown") 