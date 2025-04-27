#!/usr/bin/env python3
import os
import base64
import anthropic
import logging
from pathlib import Path
from io import BytesIO
from typing import Optional, Tuple
import requests
from twilio.rest import Client

# Set up logging
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

def validate_and_alert(image_path: str) -> str:
    """
    Takes an image and sends it to Claude for fire detection validation.
    
    Args:
        image_path: Path to the image file taken by Raspberry Pi
        
    Returns:
        str: "YES" if fire is detected, "NO" if no fire is detected
    """
    try:
        # Get API key from environment variable
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable not set")
            return "ERROR: API key not set"
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Read and encode the image
        image_data = _read_image(image_path)
        if not image_data:
            return "ERROR: Could not read image"
        
        # Prepare the prompt
        prompt = "Here is an image taken out in the wild. Do you detect any fires or potential fires or wildfires in this image? Reply with a YES or NO."
        
        # Call Claude with the image
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            temperature=0,
            system="You are a fire detection expert. Your job is to analyze images and determine if there are fires or potential fires present. Respond only with YES or NO.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}}
                    ]
                }
            ]
        )
        
        # Extract and process the response
        response_text = message.content[0].text.strip()
        
        # Extract just the YES or NO
        if "YES" in response_text.upper():
            logger.info("Fire detected in the image!")
            return "YES"
        elif "NO" in response_text.upper():
            logger.info("No fire detected in the image.")
            return "NO"
        else:
            logger.warning(f"Unexpected response from Claude: {response_text}")
            return response_text
        
    except Exception as e:
        logger.error(f"Error in validate_and_alert: {e}")
        return f"ERROR: {str(e)}"
        
def alert(detection_result: str, phone_number: str = "+14129613475", sensor_id: str = "3738") -> bool:
    """
    Make a phone call using Twilio to alert about fire detection.
    
    Args:
        detection_result: "YES" or "NO" from validate_and_alert function
        phone_number: The phone number to call
        sensor_id: ID of the sensor that detected the fire
        
    Returns:
        bool: True if alert was successful, False otherwise
    """
    if detection_result.upper() != "YES":
        logger.info("No fire detected, no alert necessary")
        return True
    
    try:
        # Get required API keys from environment variables
        twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")
        
        # Check if all required credentials are available
        if not all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
            missing = []
            if not twilio_account_sid: missing.append("TWILIO_ACCOUNT_SID")
            if not twilio_auth_token: missing.append("TWILIO_AUTH_TOKEN")
            if not twilio_phone_number: missing.append("TWILIO_PHONE_NUMBER")
            
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            return False
        
        # Create Twilio client
        client = Client(twilio_account_sid, twilio_auth_token)
        
        # Create message to be spoken
        message_text = f"Alert! A fire has been detected by sensor {sensor_id}. Please take immediate action."
        
        # Use Twilio's <Say> verb in TwiML to have Twilio speak the message directly
        twiml = f'<Response><Say voice="woman" loop="3">{message_text}</Say></Response>'
        
        # Make the call
        call = client.calls.create(
            twiml=twiml,
            to=phone_number,
            from_=twilio_phone_number
        )
        
        logger.info(f"Alert call initiated with SID: {call.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Error in alert function: {e}")
        return False
        
def _read_image(image_path: str) -> Optional[str]:
    """Read an image file and return it as a base64 encoded string."""
    try:
        path = Path(image_path)
        if not path.exists():
            logger.error(f"Image file not found: {image_path}")
            return None
            
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error reading image: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    import sys
    import time
    
    if len(sys.argv) < 2:
        print("Usage: python validation_and_alert.py <image_path>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    result = validate_and_alert(image_path)
    print(result)
    
    # If fire detected, send alert
    if result == "YES":
        alert_sent = alert(result)
        print(f"Alert {'sent successfully' if alert_sent else 'failed'}") 