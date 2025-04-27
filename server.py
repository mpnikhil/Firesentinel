#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template_string
import json
import os
import base64
from datetime import datetime
import threading
from pathlib import Path

# Configuration
PORT = 8000
SAVE_DIR = Path("received_alerts")

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
        
        # Save the image if present
        if 'image' in data:
            img_data = base64.b64decode(data['image'])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = SAVE_DIR / f"alert_{timestamp}.jpg"
            
            with open(img_path, 'wb') as f:
                f.write(img_data)
            
            print(f"📸 Image saved to: {img_path}")
        
        # Send success response
        return jsonify({"status": "alert_received"})
        
    except Exception as e:
        print(f"Error processing alert: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def run_server():
    """Run the Flask server in a thread"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    
if __name__ == "__main__":
    try:
        print(f"🚀 Server starting at http://0.0.0.0:{PORT}")
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