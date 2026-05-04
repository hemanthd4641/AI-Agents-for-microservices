import subprocess
import time

# 1. Start the Backend (FastAPI)
backend = subprocess.Popen(["python", "-m", "uvicorn", "TravelPlanner:app", "--host", "0.0.0.0", "--port", "8000"], shell=True)

# Give the backend a moment to start
time.sleep(2)

# 2. Start the Frontend (Streamlit)
frontend = subprocess.Popen(["python", "-m", "streamlit", "run", "TravelPlanner_Streamlit.py"], shell=True)

try:
    # Keep the script running while both processes are active
    backend.wait()
    frontend.wait()
except KeyboardInterrupt:
    # Stop both if you press Ctrl+C
    backend.terminate()
    frontend.terminate()
