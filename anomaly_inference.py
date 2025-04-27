import numpy as np
import joblib
import time

class AnomalyDetector:
    def __init__(self, model_path='anomaly_detection_model.joblib', 
                 scaler_path='scaler.joblib'):
        """Initialize the anomaly detector with the Random Forest model and scaler."""
        try:
            # Load the Random Forest model
            self.model = joblib.load(model_path)
            
            # Load the scaler
            self.scaler = joblib.load(scaler_path)
            
            # Load feature names if available
            try:
                self.feature_names = joblib.load('feature_names.joblib')
                print(f"Loaded features: {self.feature_names}")
            except:
                self.feature_names = None
                print("Feature names not found, will use order-based inference")
            
            print("Anomaly detection model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
        
    def preprocess(self, features):
        """Scale the input features using the saved scaler."""
        # Convert to numpy array if it's not already
        if not isinstance(features, np.ndarray):
            features = np.array(features)
            
        # Reshape if it's a single sample
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
            
        # Apply scaling using the saved scaler
        features_scaled = self.scaler.transform(features)
        return features_scaled
    
    def predict(self, features):
        """Make a prediction with the Random Forest model."""
        # Preprocess the features
        input_data = self.preprocess(features)
        
        # Run inference
        start_time = time.time()
        
        # Get predicted probabilities
        probabilities = self.model.predict_proba(input_data)
        # Get the probability of the abnormal class (index 1)
        abnormal_prob = probabilities[0][1]
        
        # Make prediction
        prediction = self.model.predict(input_data)[0]
        
        inference_time = time.time() - start_time
        
        # Convert to text condition
        condition = "abnormal" if prediction == 1 else "normal"
        
        return {
            "raw_score": float(abnormal_prob),
            "prediction": int(prediction),
            "condition": condition,
            "inference_time_ms": inference_time * 1000
        }

# Example usage
if __name__ == "__main__":
    # Create an example input (temperature, humidity, pressure, gas_oxidising, gas_reducing, gas_nh3)
    example_input = [31.5, 23.1, 1007.2, 4500, 280000, 12000]
    
    # Initialize the detector
    detector = AnomalyDetector()
    
    # Make a prediction
    result = detector.predict(example_input)
    
    # Print results
    print(f"Input: {example_input}")
    print(f"Prediction: {result['condition']} (score: {result['raw_score']:.4f})")
    print(f"Inference time: {result['inference_time_ms']:.2f} ms") 