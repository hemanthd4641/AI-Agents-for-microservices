import subprocess
import time
import sys
import os

def run_backend():
    print("🚀 Starting Unified Backend (FastAPI)...")
    # Disable telemetry/tracing to prevent crashes
    env = os.environ.copy()
    env["CREWAI_TRACING_ENABLED"] = "false"
    env["OTEL_SDK_DISABLED"] = "true"
    env["CREWAI_TELEMETRY_OPT_OUT"] = "true"
    
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env
    )

def run_frontend():
    print("🎨 Starting Unified Frontend (Streamlit)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "frontend/main.py"],
            check=True
        )
    except KeyboardInterrupt:
        print("\nStopping agents...")

if __name__ == "__main__":
    # Change to the project root directory if necessary
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    backend_proc = run_backend()
    
    # Wait for backend to initialize
    print("⏳ Waiting for backend to warm up...")
    time.sleep(5) 
    
    try:
        run_frontend()
    finally:
        print("🛑 Shutting down backend...")
        backend_proc.terminate()
        backend_proc.wait()
        print("✅ Goodbye!")
