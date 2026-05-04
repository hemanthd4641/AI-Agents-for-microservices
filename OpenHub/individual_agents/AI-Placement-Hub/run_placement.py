import subprocess
import time
import sys
import os

def run_placement():
    print("🚀 Starting AI Placement & Career Hub...")
    
    # 1. Start Backend (FastAPI) on port 8004
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8004"],
        shell=True
    )
    
    print("⏳ Waiting for Recruiters and Mentors to warm up (10s)...")
    time.sleep(10)
    
    # 2. Start Frontend (Streamlit) on port 8509
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend.py", "--server.port", "8509"],
        shell=True
    )
    
    print("\n✅ PLACEMENT HUB IS LIVE!")
    print("🔗 Career Dashboard: http://localhost:8509")
    print("\nPress Ctrl+C to stop the services.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        backend_process.terminate()
        frontend_process.terminate()
        print("Done.")

if __name__ == "__main__":
    run_placement()
