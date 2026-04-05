import docker
import os
import subprocess
from typing import Dict, Optional, List

class SandboxManager:
    """
    Manages isolated Docker containers for testing Arvis's self-improvement scripts.
    Ensures that any new version of Arvis is tested in a safe environment before
    being presented for a Production update.
    """
    def __init__(self, image: str = "python:3.10-slim"):
        try:
            self.client = docker.from_env()
        except Exception as e:
            # Fallback for environments where Docker might not be reachable yet
            print(f"Warning: Docker not reachable ({e}). Sandbox operations will fail.")
            self.client = None
        self.image = image

    def run_test(self, code_dir: str, command: str, timeout: int = 300) -> Dict:
        """
        Runs a specific test command inside the sandbox.
        :param code_dir: Path to the code to be tested.
        :param command: The command to execute (e.g., 'pytest tests/').
        :param timeout: Time limit for the test in seconds.
        :return: Execution results (stdout, stderr, exit_code).
        """
        if not self.client:
            return {"error": "Docker client not initialized", "exit_code": -1}

        abs_path = os.path.abspath(code_dir)
        
        try:
            # Mounting the provided code directory as /workspace
            container = self.client.containers.run(
                image=self.image,
                command=command,
                volumes={abs_path: {'bind': '/workspace', 'mode': 'rw'}},
                working_dir='/workspace',
                detach=False,
                auto_remove=True,
                mem_limit="512m",
                cpu_quota=50000, # 50% of one CPU
                network_disabled=False # Per user request for 24/7 internet
            )
            return {
                "output": container.decode('utf-8'),
                "exit_code": 0
            }
        except docker.errors.ContainerError as e:
            return {
                "output": e.stderr.decode('utf-8'),
                "error": str(e),
                "exit_code": e.exit_status
            }
        except Exception as e:
            return {
                "error": str(e),
                "exit_code": -1
            }

    def provision_environment(self, requirements_path: str):
        """
        Optionally pre-build or provision a container with necessary libraries
        for testing complex logic.
        """
        pass
