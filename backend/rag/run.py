import sys
import os
import uvicorn
from pathlib import Path


current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

os.environ.setdefault("PYTHONPATH", str(current_dir))

def main():
    try:
        from app.main import app
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Server startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
