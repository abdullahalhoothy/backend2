# Integration_test_runner.py

#!/usr/bin/env python3
"""
Integration Test Runner with dependency support

This module starts the FastAPI server in test mode and runs integration tests against it.
Tests can have dependencies and are run in the correct order.
"""

import os
import sys
import time
import subprocess
import logging
from http.client import HTTPConnection
from contextlib import contextmanager
import json
import asyncio
import importlib.util
from typing import Dict, List, Set, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Test dependency configuration
TEST_DEPENDENCIES = {
    "test_fetch_dataset": ["test_user"],  # fetch_dataset depends on user tests
    # Add more dependencies here as needed
}


class TestServerManager:
    """Manages starting and stopping the test server"""

    def __init__(self, test_port=8080):
        self.test_port = test_port
        self.server_process = None

    def setup_test_environment(self):
        """Set up test environment - only sets TEST_MODE"""
        logger.info("Setting up test environment...")
        os.environ["TEST_MODE"] = "true"
        logger.info("Test environment set up successfully")

    def start_server(self, timeout=120):
        """Start the FastAPI server in test mode"""
        logger.info(f"Starting test server on port {self.test_port}...")

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "fastapi_app:app",
            "--reload",
            "--host", "localhost",
            "--port", str(self.test_port),
        ]

        with open("secrets_test/postgres_db.json", "r") as file:
            config = json.load(file)
            db_url = config["DATABASE_URL"]

        env = os.environ.copy()
        env.update({
            "TEST_MODE": "true",
            "PORT": str(self.test_port),
            "DATABASE_URL": db_url
        })

        try:
            logger.info("Launching server with command: " + " ".join(cmd))
            
            self.server_process = subprocess.Popen(
                cmd,
                env=env,
                cwd=os.getcwd(),
            )

            logger.info("Server process started, waiting for it to be ready...")

            if self._wait_for_server(timeout):
                logger.info(f"✅ Test server started successfully on port {self.test_port}")
                return True
            else:
                logger.error("❌ Server failed to start within timeout")
                self.stop_server()
                return False

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False

    def _wait_for_server(self, timeout):
        """Wait for server to be ready to accept connections"""
        start_time = time.time()
        check_interval = 2
        last_check_time = 0

        while time.time() - start_time < timeout:
            current_time = time.time()
            
            if self.server_process.poll() is not None:
                logger.error("Server process terminated unexpectedly")
                return False
            
            if current_time - last_check_time >= check_interval:
                try:
                    conn = HTTPConnection(f"localhost:{self.test_port}")
                    conn.request("GET", "/fastapi/fetch_acknowlg_id")
                    response = conn.getresponse()
                    conn.close()

                    if response.status in [200, 404]:
                        return True

                except (ConnectionRefusedError, OSError):
                    elapsed = current_time - start_time
                    logger.info(f"Server not ready yet (after {elapsed:.1f}s)...")
                
                last_check_time = current_time

            time.sleep(0.5)

        return False

    def stop_server(self):
        """Stop the test server"""
        if self.server_process:
            logger.info("Stopping test server...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Graceful shutdown failed, force killing server")
                self.server_process.kill()
                self.server_process.wait()

            self.server_process = None
            logger.info("Test server stopped")

    def cleanup(self):
        """Clean up test environment"""
        logger.info("Cleaning up test environment...")
        self.stop_server()
        os.environ.pop("TEST_MODE", None)
        logger.info("Test environment cleaned up")


def load_test_module(test_name: str):
    """Dynamically load a test module"""
    module_path = f"tests/integration/{test_name}.py"
    spec = importlib.util.spec_from_file_location(test_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_test_order(test_modules: List[str]) -> List[str]:
    """Determine the order to run tests based on dependencies"""
    # Create a graph of dependencies
    visited = set()
    order = []
    
    def visit(test: str):
        if test in visited:
            return
        visited.add(test)
        
        # Visit dependencies first
        if test in TEST_DEPENDENCIES:
            for dep in TEST_DEPENDENCIES[test]:
                if dep in test_modules:
                    visit(dep)
        
        order.append(test)
    
    # Visit all test modules
    for test in test_modules:
        visit(test)
    
    return order


async def run_test_module(test_name: str, api_base_url: str) -> bool:
    """Run a single test module"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Running {test_name}...")
    logger.info(f"{'='*60}")
    
    try:
        module = load_test_module(test_name)
        
        # Get the main test runner function
        if hasattr(module, f"run_{test_name.replace('test_', '')}_tests"):
            test_func = getattr(module, f"run_{test_name.replace('test_', '')}_tests")
            result = await test_func(api_base_url)
            
            if result:
                logger.info(f"✅ {test_name} completed successfully")
            else:
                logger.error(f"❌ {test_name} failed")
            
            return result
        else:
            logger.error(f"No test runner function found in {test_name}")
            return False
            
    except Exception as e:
        logger.error(f"Error running {test_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


@contextmanager
def test_server_context(test_port):
    """Context manager for test server lifecycle"""
    manager = TestServerManager(test_port)

    try:
        manager.setup_test_environment()
        if not manager.start_server():
            raise RuntimeError("Failed to start test server")


        yield {
            "port": test_port,
            "base_url": f"http://localhost:{test_port}",
            "api_base": f"http://localhost:{test_port}/fastapi",
        }

    finally:
        manager.cleanup()


async def run_all_tests(api_base_url: str, test_directory: str) -> bool:
    """Run all tests in dependency order"""
    # Find all test modules
    test_modules = []
    for file in os.listdir(test_directory):
        if file.startswith("test_") and file.endswith(".py"):
            test_modules.append(file[:-3])  # Remove .py extension
    
    # Get ordered list based on dependencies
    test_order = get_test_order(test_modules)
    
    logger.info(f"Test execution order: {test_order}")
    
    # Run tests in order
    all_passed = True
    for test_name in test_order:
        passed = await run_test_module(test_name, api_base_url)
        if not passed:
            all_passed = False
            # Continue running other tests even if one fails
    
    return all_passed


def main():
    """Main entry point"""
    logger.info("🧪 Starting Integration Test Runner...")
    logger.info("This will start the server in TEST_MODE and run integration tests")

    success = False

    with test_server_context(test_port=8080) as server_info:
        logger.info(f"🚀 Server running at: {server_info['base_url']}")

        # Run all tests
        success = asyncio.run(
            run_all_tests(
                api_base_url=server_info["api_base"],
                test_directory="tests/integration"
            )
        )

    if success:
        logger.info("\n✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()