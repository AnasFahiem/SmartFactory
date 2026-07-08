import paho.mqtt.client as mqtt
import json
import joblib
import pandas as pd
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

# ==========================================
# 1. إعدادات MQTT (HiveMQ Cloud الخاص بالمشروع)
# ==========================================
MQTT_BROKER = os.getenv("MQTT_BROKER", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "factory/#")

# ==========================================
# 2. إعدادات البريد الإلكتروني للإنذارات
# ==========================================
# يرجى تعديلها ببيانات البريد الخاص بك (يجب استخدام App Password وليس الباسورد العادي)
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")

# ==========================================
# 3. تحميل الموديل
# ==========================================
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'factory_anomaly_model.pkl')
if os.path.exists(MODEL_PATH):
    ml_model = joblib.load(MODEL_PATH)
    print("AI Model loaded successfully.")
else:
    ml_model = None
    print(f"Warning: Model not found at {MODEL_PATH}. Please run train_factory_ai.py first.")

def send_email_alert(alert_message):
    """دالة لإرسال إيميل تحذيري للمسؤول"""
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        print("\n[MOCK EMAIL ALERT]")
        print(alert_message)
        print("==================\n")
        return
        
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = "🚨 [URGENT] Factory AI Anomaly Alert"
        
        msg.attach(MIMEText(alert_message, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email alert sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected successfully to HiveMQ Cloud MQTT Broker!")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"Failed to connect, return code {reason_code}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"Received message on {msg.topic}: {payload}")
    
    # Ignore our own ai_alert messages to avoid loops
    if msg.topic == "factory/ai_alert":
        return
    
    try:
        data = json.loads(payload)
        
        # استخراج المتغيرات
        # The frontend/backend expects: temperature, humidity, gas_alarm
        temp = data.get("temperature", 25.0)
        hum = data.get("humidity", 45.0)
        gas = data.get("gas_alarm", False)
        
        # تحويل قيمة الغاز لـ 0 أو 1
        gas_val = 1.0 if gas else 0.0
        
        if ml_model is not None:
            # تجهيز البيانات للتوقع بنفس ترتيب التدريب:
            # 'temperature', 'humidity', 'gas_alarm'
            features = pd.DataFrame([{
                'temperature': float(temp),
                'humidity': float(hum),
                'gas_alarm': gas_val
            }])
            
            # التوقع (IsolationForest returns 1 for normal, -1 for anomaly)
            prediction = ml_model.predict(features)[0]
            
            if prediction == -1: # Anomaly detected
                alert_text = f"""
🚨 SYSTEM DETECTED AN ANOMALY IN FACTORY SENSORS 🚨

Sensor Readings:
- Temperature: {temp} °C
- Humidity: {hum} %
- Gas Alarm: {'ACTIVE' if gas else 'CLEAR'}

Immediate inspection is required!
"""
                print(">>> ANOMALY DETECTED BY AI MODEL <<<")
                send_email_alert(alert_text)
                
                # Publish the AI alert back to the cloud so the dashboard can pick it up
                alert_payload = json.dumps({
                    "ai_alert": True,
                    "message": f"Danger: Temp {temp}°C, Hum {hum}%"
                })
                client.publish("factory/ai_alert", alert_payload)
            else:
                print("Readings are normal.")
                
    except json.JSONDecodeError:
        print("Error: Could not decode JSON.")
    except Exception as e:
        print(f"Error processing message: {e}")

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"AI Monitor is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"Dummy Web Server started on port {port} for Render.com free tier")
    server.serve_forever()

if __name__ == "__main__":
    print("Starting Factory AI Monitor...")

    if not MQTT_BROKER or not MQTT_USER or not MQTT_PASS:
        print("MQTT settings are missing. Set MQTT_BROKER, MQTT_USER, and MQTT_PASS in .env.")
        raise SystemExit(1)
    
    # Start the dummy web server in a background thread
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="AI_Monitor_Script")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    
    # HiveMQ Cloud requires TLS
    client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("Disconnecting...")
        client.disconnect()
    except Exception as e:
        print(f"Connection failed: {e}")
