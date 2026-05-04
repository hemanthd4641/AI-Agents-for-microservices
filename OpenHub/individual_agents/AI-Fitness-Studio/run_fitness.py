import subprocess
import time
import sys
import os

def run_fitness():
    print("🚀 Starting AI Fitness & Nutrition Studio...")
    
    # 1. Start Backend (FastAPI) on port 8003
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8003"],
        shell=True
    )
    
    print("⏳ Waiting for Coach to warm up...")
    time.sleep(5)
    
    # 2. Start Frontend (Streamlit) on port 8507
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend.py", "--server.port", "8507"],
        shell=True
    )
    
    print("\n✅ FITNESS STUDIO IS LIVE!")
    print("🔗 Training Dashboard: http://localhost:8507")
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
    run_fitness()
