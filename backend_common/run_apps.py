from fastapi_app import app
import uvicorn
import logging


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
