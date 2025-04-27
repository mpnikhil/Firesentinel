import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import os

# File paths
normal_file = "/Users/nikhilpujari/hackathon/final_training_data/normal2.csv"
abnormal1_file = "/Users/nikhilpujari/hackathon/final_training_data/abnormal1.csv"
abnormal2_file = "/Users/nikhilpujari/hackathon/final_training_data/abnormal2.csv"

# Load data
normal_data = pd.read_csv(normal_file)
abnormal1_data = pd.read_csv(abnormal1_file)
abnormal2_data = pd.read_csv(abnormal2_file)

# Combine all data
all_data = pd.concat([normal_data, abnormal1_data, abnormal2_data], axis=0)

# Split features and labels
X = all_data.drop('condition', axis=1)
y = all_data['condition'].map({'normal': 0, 'abnormal': 1})

# Extract feature names for later reference
feature_names = X.columns.tolist()
joblib.dump(feature_names, 'feature_names.joblib')
print(f"Features: {feature_names}")

# Normalize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Save scaler for inference
joblib.dump(scaler, 'scaler.joblib')

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# Build a Random Forest model
print("Building Random Forest model...")
rf_model = RandomForestClassifier(
    n_estimators=100,  # Number of trees
    max_depth=10,      # Maximum depth of trees
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1  # Use all available cores
)

# Train the model
print("Training model...")
rf_model.fit(X_train, y_train)

# Make predictions on test data
y_pred = rf_model.predict(X_test)
y_prob = rf_model.predict_proba(X_test)[:, 1]

# Evaluate the model
accuracy = accuracy_score(y_test, y_pred)
print(f"Test accuracy: {accuracy:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['normal', 'abnormal']))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Get feature importance
feature_importance = rf_model.feature_importances_
feature_importance_dict = dict(zip(feature_names, feature_importance))
print("\nFeature Importance:")
for feature, importance in sorted(feature_importance_dict.items(), key=lambda x: x[1], reverse=True):
    print(f"{feature}: {importance:.4f}")

# Save the model
model_filename = 'anomaly_detection_model.joblib'
joblib.dump(rf_model, model_filename)
print(f"\nRandom Forest model saved to '{model_filename}'")

# Print model size
model_size = os.path.getsize(model_filename) / 1024
print(f"Model size: {model_size:.2f} KB") 