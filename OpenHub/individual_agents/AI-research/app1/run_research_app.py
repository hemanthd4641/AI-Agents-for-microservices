import subprocess
import time
import sys
import os

def run_app():
    print("🚀 Starting AI Research & Blog App...")
    
    # 1. Start Backend (FastAPI) on port 8001
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8001"],
        shell=True
    )
    
    print("⏳ Waiting for backend to warm up...")
    time.sleep(5)
    
    # 2. Start Frontend (Streamlit) on port 8505 (different from travel planner)
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend.py", "--server.port", "8505"],
        shell=True
    )
    
    print("\n✅ BOTH SERVICES ARE RUNNING!")
    print("🔗 Backend API: http://localhost:8001")
    print("🔗 Frontend UI: http://localhost:8505")
    print("\nPress Ctrl+C to stop both services.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        backend_process.terminate()
        frontend_process.terminate()
        print("Done.")

if __name__ == "__main__":
    run_app()
