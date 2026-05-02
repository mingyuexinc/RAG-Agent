import os
import subprocess
import sys
import time
from pathlib import Path

import requests

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from infra.logs.logger_config import initialize_log_system

initialize_log_system()


def modelscope_quickstart(name):
    return (
        "Welcome to ModelScope, "
        + name
        + "!! This is RAG Agent - an intelligent Q&A system based on Retrieval-Augmented Generation."
    )


class ExistingBackendProcess:
    """No-op process handle used when a backend is already running."""

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


def check_dependencies():
    required_modules = {
        "uvicorn": "uvicorn",
        "requests": "requests",
        "gradio": "gradio",
    }

    missing = []
    for module, package in required_modules.items():
        try:
            __import__(module)
            print(f"OK: {package} installed")
        except ImportError:
            missing.append(package)
            print(f"Missing dependency: {package}")

    if missing:
        print(f"Please install missing dependencies: pip install {' '.join(missing)}")
        return False

    return True


def _candidate_backend_ports():
    from infra.config.server_config import ServerConfig

    expected_port = ServerConfig.get_port()
    if expected_port == 8001:
        return [8001, 8000, 15181]
    return [8000, 8001, 15181]


def _is_modelscope_env():
    cwd = os.getcwd()
    pwd = os.getenv("PWD", "")
    return "/home/studio_service" in cwd or "/home/studio_service" in pwd


def _set_frontend_backend_url(backend_url: str):
    from frontend.services import api_client

    api_client.base_url = backend_url
    print(f"API client configured: {backend_url}")


def _find_existing_backend():
    for port in _candidate_backend_ports():
        url = f"http://127.0.0.1:{port}"
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                return url
        except requests.exceptions.RequestException:
            continue
    return None


def _wait_for_backend(backend_process, timeout_seconds: int = None):
    if timeout_seconds is None:
        timeout_seconds = 75 if _is_modelscope_env() else 20

    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        if backend_process.poll() is not None:
            print(f"Backend process exited early with code {backend_process.returncode}")
            return None

        for port in _candidate_backend_ports():
            url = f"http://127.0.0.1:{port}"
            try:
                response = requests.get(f"{url}/health", timeout=2)
                if response.status_code == 200:
                    return url
                last_error = f"{url}/health returned HTTP {response.status_code}"
            except requests.exceptions.RequestException as exc:
                last_error = exc
        time.sleep(1)

    if last_error:
        print(f"Backend health check failed: {last_error}")
    return None


def start_backend_server():
    try:
        existing_backend_url = _find_existing_backend()
        if existing_backend_url:
            print(f"Backend already running, reusing: {existing_backend_url}")
            _set_frontend_backend_url(existing_backend_url)
            return ExistingBackendProcess()

        print("Starting backend API server...")
        backend_env = os.environ.copy()
        backend_env["RAG_AGENT_RELOAD"] = "0"

        backend_process = subprocess.Popen(
            [sys.executable, "app/main.py"],
            cwd=project_root,
            env=backend_env,
        )

        backend_url = _wait_for_backend(backend_process)
        if backend_url:
            print(f"Backend API server started: {backend_url}")
            _set_frontend_backend_url(backend_url)
            return backend_process

        print("Backend API server failed to start")
        try:
            backend_process.terminate()
        except Exception:
            pass
        return None

    except Exception as exc:
        print(f"Failed to start backend server: {exc}")
        return None


def create_demo():
    if not check_dependencies():
        return None

    backend_process = start_backend_server()
    if not backend_process:
        print("Backend service is unavailable; frontend cannot start")
        return None

    try:
        from frontend.app import RAGAgentFrontend

        frontend = RAGAgentFrontend()
        demo = frontend.create_interface()
        demo._backend_process = backend_process
        return demo

    except Exception as exc:
        print(f"Frontend startup failed: {exc}")
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
        except Exception:
            try:
                backend_process.kill()
            except Exception:
                pass
        return None


demo = create_demo()

if demo is not None:
    demo.launch()
else:
    print("Demo application was not created")
