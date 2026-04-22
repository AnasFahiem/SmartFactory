import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

def generate_training_data(num_samples=2000):
    """
    توليد بيانات افتراضية لتدريب موديل Anomaly Detection 
    للمصنع الذكي بناءً على السينسورز الحقيقية
    """
    np.random.seed(42)
    
    # 1. بيانات طبيعية (80% من البيانات)
    n_normal = int(num_samples * 0.8)
    temp_normal = np.random.normal(loc=25.0, scale=3.0, size=n_normal)
    hum_normal = np.random.normal(loc=45.0, scale=5.0, size=n_normal)
    gas_normal = np.zeros(n_normal) # لا يوجد إنذار غاز
    
    # 2. بيانات شاذة / خطر (20% من البيانات)
    n_anomaly = num_samples - n_normal
    # حرارة عالية جداً أو غاز
    temp_anomaly = np.random.normal(loc=45.0, scale=5.0, size=n_anomaly)
    hum_anomaly = np.random.normal(loc=30.0, scale=10.0, size=n_anomaly)
    # بعضها به إنذار غاز والبعض لا
    gas_anomaly = np.random.choice([0, 1], size=n_anomaly, p=[0.3, 0.7])
    
    # دمج البيانات
    temp = np.concatenate([temp_normal, temp_anomaly])
    hum = np.concatenate([hum_normal, hum_anomaly])
    gas = np.concatenate([gas_normal, gas_anomaly])
    
    # إنشاء DataFrame
    df = pd.DataFrame({
        'temperature': temp,
        'humidity': hum,
        'gas_alarm': gas
    })
    
    return df

if __name__ == "__main__":
    print("Generating factory data for training...")
    data = generate_training_data()
    
    print("Training Isolation Forest (Anomaly Detection) model...")
    # IsolationForest is perfect for unsupervised anomaly detection
    model = IsolationForest(contamination=0.15, random_state=42)
    model.fit(data)
    
    # إنشاء مجلد models إذا لم يكن موجود
    os.makedirs('models', exist_ok=True)
    model_path = os.path.join('models', 'factory_anomaly_model.pkl')
    
    joblib.dump(model, model_path)
    print(f"Model trained successfully and saved to: {model_path}")
