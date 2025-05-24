#!/usr/bin/env python3
"""
Integration Test Runner

This module starts the FastAPI server in test mode and runs integration tests against it.
The test configuration is read from JSON files in the 'test_secrets' directory.

Usage:
    python test_runner.py [test_directory]
    python test_runner.py tests/integration/
"""

import os
import sys
import time
import subprocess
import logging
from http.client import HTTPConnection
from contextlib import contextmanager
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TestServerManager:
    """Manages starting and stopping the test server"""

    def __init__(self, test_port=8080):
        self.test_port = test_port
        self.server_process = None

    def setup_test_environment(self):
        """Set up test environment - only sets TEST_MODE"""
        logger.info("Setting up test environment...")

        # Only set TEST_MODE environment variable
        os.environ["TEST_MODE"] = "true"

        logger.info("Test environment set up successfully")

    def start_server(self, timeout=120):
        """Start the FastAPI server in test mode"""
        logger.info(f"Starting test server on port {self.test_port}...")

        # Create modified startup command for test mode (corrected to match your debug config)
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "fastapi_app:app",  # Corrected from "main:app" to match your config
            "--reload",
            "--host", "localhost",  # Using localhost like your debug config
            "--port", str(self.test_port),
        ]

        with open("secrets_test/postgres_db.json", "r") as file:
                config = json.load(file)
                db_url = config["DATABASE_URL"]

        # Set environment for subprocess
        env = os.environ.copy()
        env.update({
            "TEST_MODE": "true",
            "PORT": str(self.test_port),
            "DATABASE_URL": db_url
        })

        try:
            # Start server process WITHOUT capturing output - let it print directly to console
            logger.info("Launching server with command: " + " ".join(cmd))
            
            self.server_process = subprocess.Popen(
                cmd,
                env=env,
                cwd=os.getcwd(),
                # No stdout/stderr pipes - output goes directly to console like normal server startup
            )

            logger.info("Server process started, waiting for it to be ready...")

            # Wait for server to be ready
            if self._wait_for_server(timeout):
                logger.info(f"✅ Test server started successfully on port {self.test_port}")
                return True
            else:
                logger.error("❌ Server failed to start within timeout")
                self._print_server_status()
                self.stop_server()
                return False

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False

    def _print_server_status(self):
        """Print server process status for debugging"""
        if self.server_process:
            poll_result = self.server_process.poll()
            if poll_result is not None:
                logger.error(f"Server process exited with code: {poll_result}")
            else:
                logger.info("Server process is still running")

    def _wait_for_server(self, timeout):
        """Wait for server to be ready to accept connections"""
        start_time = time.time()
        check_interval = 2  # Check every 2 seconds
        last_check_time = 0

        while time.time() - start_time < timeout:
            current_time = time.time()
            
            # Check if process is still alive
            if self.server_process.poll() is not None:
                logger.error("Server process terminated unexpectedly")
                return False
            
            # Only check server every check_interval seconds
            if current_time - last_check_time >= check_interval:
                try:
                    conn = HTTPConnection(f"localhost:{self.test_port}")
                    conn.request("GET", "/fastapi/fetch_acknowlg_id")
                    response = conn.getresponse()
                    conn.close()

                    if response.status in [200, 404]:  # Server is responding
                        return True
                        
                    logger.info(f"Server responded with status {response.status}, waiting...")

                except (ConnectionRefusedError, OSError) as e:
                    elapsed = current_time - start_time
                    logger.info(f"Server not ready yet (after {elapsed:.1f}s), continuing to wait...")
                
                last_check_time = current_time

            time.sleep(0.5)

        return False

    def stop_server(self):
        """Stop the test server"""
        if self.server_process:
            logger.info("Stopping test server...")

            try:
                # Try graceful shutdown first
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown failed
                logger.warning("Graceful shutdown failed, force killing server")
                self.server_process.kill()
                self.server_process.wait()

            self.server_process = None
            logger.info("Test server stopped")

    def cleanup(self):
        """Clean up test environment"""
        logger.info("Cleaning up test environment...")

        # Stop server
        self.stop_server()

        # Remove TEST_MODE environment variable
        os.environ.pop("TEST_MODE", None)

        logger.info("Test environment cleaned up")


@contextmanager
def test_server_context(test_port):
    """Context manager for test server lifecycle"""
    manager = TestServerManager(test_port)

    try:
        # Setup test environment
        manager.setup_test_environment()

        # Start server
        if not manager.start_server():
            raise RuntimeError("Failed to start test server")

        # Yield server info
        yield {
            "port": test_port,
            "base_url": f"http://localhost:{test_port}",
            "api_base": f"http://localhost:{test_port}/fastapi",
        }

    finally:
        # Always cleanup
        manager.cleanup()


def run_tests(test_port, test_directory, verbose=True):
    """Run integration tests with test server"""

    success = False

    with test_server_context(test_port) as server_info:
        logger.info(f"🚀 Server running at: {server_info['base_url']}")

        # Set test server URL for tests to use
        os.environ["TEST_SERVER_URL"] = server_info["api_base"]

        # Run tests using pytest
        try:
            import pytest

            # Build pytest arguments
            pytest_args = [
                test_directory,
                "-v" if verbose else "",
                "--tb=short",
                f"--maxfail=5",  # Stop after 5 failures
            ]

            # Filter out empty strings
            pytest_args = [arg for arg in pytest_args if arg]

            logger.info(f"Running tests with: pytest {' '.join(pytest_args)}")

            # Run tests
            exit_code = pytest.main(pytest_args)
            success = exit_code == 0

        except ImportError:
            logger.error("pytest not found. Install with: pip install pytest")
            return False
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False

    return success


def main():
    """Main entry point"""
    
    logger.info("🧪 Starting Integration Test Runner...")
    logger.info("This will start the server in TEST_MODE and run integration tests")

    # Run tests
    success = run_tests(test_port=8080, test_directory="tests/integration", verbose=True)

    if success:
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()