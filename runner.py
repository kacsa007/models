import subprocess
import time
import requests

def run_collector():
    proc = subprocess.Popen(["python", "okx_websocket_collector.py"])
    return proc

def run_api():
    proc = subprocess.Popen(["python", "inference_api.py"])
    return proc

def test_prediction_api(instrument="BTC-USDT"):
    for _ in range(10):
        try:
            r = requests.post(
                "http://localhost:8000/predict",
                json={"instrument": instrument, "lookback_periods": 100},
                timeout=10
            )
            if r.status_code == 200:
                print("Prediction:", r.json())
            else:
                print("Failed:", r.text)
        except Exception as e:
            print("Error requesting prediction:", e)
        time.sleep(60)  # Wait 1 minute between predictions

def dynamic_model_trainer():
    # Simulate dynamic fetching/feeding for several days
    for _ in range(60*24*2):  # Simulate updates every minute for 2 days
        try:
            # invoke retraining and/or refreshing features here if needed
            print("Simulated periodic retraining/feed...")
        except Exception as e:
            print("Error in dynamic retraining:", e)
        time.sleep(60)

if __name__ == "__main__":
    # Start services
    collector_proc = run_collector()
    time.sleep(5)  # Buffer for DB start
    api_proc = run_api()
    time.sleep(10)  # Buffer for API start
    # Run tests
    test_prediction_api()
    dynamic_model_trainer()
    # Cleanup
    collector_proc.terminate()
    api_proc.terminate()
