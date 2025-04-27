
# Wildfire Detection Inference Script for Raspberry Pi 5
# Save this as wildfire_detection.py on your Pi

import numpy as np
import tflite_runtime.interpreter as tflite
from PIL import Image
import time
import cv2
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Wildfire Detection on Raspberry Pi')
parser.add_argument('--model', type=str, default='wildfire_model_quantized.tflite', 
                    help='Path to TFLite model')
parser.add_argument('--image', type=str, required=True, 
                    help='Path to image file to test')
parser.add_argument('--threshold', type=float, default=0.5, 
                    help='Detection threshold (0-1)')
args = parser.parse_args()

def load_image(image_path, input_size=224):
    # Load and preprocess image
    img = Image.open(image_path).convert('RGB')
    img = img.resize((input_size, input_size))
    img_array = np.array(img, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

def detect_fire(interpreter, image_data, threshold=0.5):
    # Get input and output details
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Set input tensor
    interpreter.set_tensor(input_details[0]['index'], image_data)
    
    # Run inference
    start_time = time.time()
    interpreter.invoke()
    inference_time = time.time() - start_time
    
    # Get output tensor
    output = interpreter.get_tensor(output_details[0]['index'])
    score = output[0][0]
    
    return score, inference_time

def main():
    # Load TFLite model
    interpreter = tflite.Interpreter(model_path=args.model)
    interpreter.allocate_tensors()
    
    # Load and preprocess image
    image_data = load_image(args.image)
    
    # Perform detection
    score, inference_time = detect_fire(interpreter, image_data, args.threshold)
    
    # Display results
    result = "FIRE DETECTED!" if score >= args.threshold else "No fire detected."
    print(f"Result: {result}")
    print(f"Confidence: {score:.4f}")
    print(f"Inference time: {inference_time*1000:.2f} ms")
    
    # Visualize result on image (optional)
    img = cv2.imread(args.image)
    cv2.putText(img, f"{result} ({score:.4f})", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255) if score >= args.threshold else (0, 255, 0), 2)
    cv2.imshow("Wildfire Detection", img)
    cv2.waitKey(0)

if __name__ == "__main__":
    main()
