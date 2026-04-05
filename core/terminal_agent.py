import subprocess
import os
import sys

class TerminalAgent:
    """
    Arvis's autonomous terminal execution engine.
    Designed for unconstrained, high-performance system interaction.
    Per user request, this agent can execute commands without constant permission,
    except for sensitive self-upgrade operations.
    """
    def __init__(self, working_dir: str = "."):
        self.working_dir = os.path.abspath(working_dir)

    def execute(self, command: str) -> dict:
        """
        Executes a shell command on the host system.
        :param command: The shell command to run.
        :return: Execution results including stdout, stderr, and exit_code.
        """
        # Note: In production, we'd add some safety checks to prevent self-deletion,
        # but per unconstrained requirement, we prioritize execution.
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=120 # Prevent infinite loops
            )
            
            # Windows 'Command not found' usually appears in stderr or returns specific non-zero codes
            if result.returncode != 0 and any(err in result.stderr.lower() for err in ["not recognized", "not found"]):
                # Specific 'Tool missing' report as requested
                tool_name = command.split()[0] if command.split() else "this command"
                return {
                    "error": f"Apologies, Sir. The tool '{tool_name}' is not currently available on your PC.",
                    "exit_code": result.returncode,
                    "stderr": result.stderr
                }

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out.", "exit_code": -1}
        except Exception as e:
            return {"error": str(e), "exit_code": -1}

    def write_file(self, path: str, content: str):
        """Allows Arvis to directly write or modify local code."""
        abs_path = os.path.join(self.working_dir, path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def read_file(self, path: str) -> str:
        """Allows Arvis to read local context for reasoning."""
        abs_path = os.path.join(self.working_dir, path)
        if os.path.exists(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "File not found."

if __name__ == "__main__":
    agent = TerminalAgent()
    # Test execution
    res = agent.execute("ls -R")
    print(res["stdout"])
