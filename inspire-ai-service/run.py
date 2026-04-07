import asyncio
import os
import signal
import socket
from asyncio.subprocess import Process

import dotenv
import rich
from pathlib import Path

# Load environment variables
dotenv.load_dotenv()

# Import settings after loading environment
from app.settings import settings  # noqa: E402

# Define app host and port
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))


def dev():
    """Run the application in development mode."""
    asyncio.run(start_development_server())


def prod():
    """Run the application in production mode."""
    asyncio.run(start_production_server())


async def start_development_server():
    """
    Start the backend development server with hot reloading.

    Raises:
        SystemError: If server fails to start
    """
    rich.print("\n[bold blue]===== STARTING DEVELOPMENT SERVER =====[/bold blue]")

    try:
        # Check if port is available
        if not _is_port_available(APP_PORT):
            raise SystemError(
                f"Port {APP_PORT} is not available! Please change the port in .env file or kill the process running on this port."
            )

        # Start backend process
        process = await _run_backend(envs={"ENVIRONMENT": "dev"})

        try:
            await process.wait()
        except (asyncio.CancelledError, KeyboardInterrupt):
            rich.print("\n[bold yellow]Shutting down...[/bold yellow]")
        finally:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()

    except Exception as e:
        raise SystemError(f"Failed to start development server: {e!s}") from e


async def start_production_server():
    """
    Start the production server using uvicorn with multiple workers.

    Raises:
        SystemError: If server fails to start
    """
    process = None
    try:
        rich.print("\n[bold blue]===== STARTING PRODUCTION SERVER =====[/bold blue]")

        workers = os.getenv("SERVER_WORKERS", "4")

        # Check if port is available
        if not _is_port_available(APP_PORT):
            raise SystemError(
                f"Port {APP_PORT} is not available! Please change the port in .env file or kill the process running on this port."
            )

        envs = {"ENVIRONMENT": "prod"}
        rich.print("\n[bold]Starting production server with uvicorn...[/bold]")
        rich.print(f"[bold]Using {workers} worker processes[/bold]")

        poetry_executable = _get_poetry_executable()
        cmd = [
            poetry_executable,
            "run",
            "uvicorn",
            "main:app",
            "--host",
            APP_HOST,
            "--port",
            str(APP_PORT),
            "--workers",
            workers,
            "--limit-max-requests",
            "1000",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env={**os.environ, **(envs or {})},
        )

        await asyncio.sleep(3)
        if process.returncode is not None:
            raise RuntimeError("Could not start production server")

        rich.print(
            f"\n[bold green]Production server is running with {workers} workers. Access it at http://{APP_HOST}:{APP_PORT}[/bold green]"
        )

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda: asyncio.create_task(_shutdown(process))
            )

        await process.wait()

    except asyncio.CancelledError:
        pass
    except Exception as e:
        rich.print(f"[bold red]Error: {e!s}[/bold red]")
        raise SystemError(f"Failed to start production server: {e!s}") from e
    finally:
        if process is not None:
            await _shutdown(process)


async def _shutdown(process):
    """Gracefully shutdown the server process"""
    if process.returncode is None:
        rich.print("\n[bold yellow]Shutting down gracefully...[/bold yellow]")
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=10)
            rich.print("[bold green]Server shutdown complete[/bold green]")
        except TimeoutError:
            rich.print("[bold red]Force killing the server...[/bold red]")
            process.kill()
            await process.wait()


async def _run_backend(envs: dict[str, str | None] = {}) -> Process:
    """
    Start the backend development server.

    Returns:
        Process: The backend process
    """
    # Merge environment variables
    envs = {**os.environ, **(envs or {})}

    rich.print(f"\n[bold]Starting app on port {APP_PORT}...[/bold]")
    poetry_executable = _get_poetry_executable()
    process = await asyncio.create_subprocess_exec(
        poetry_executable,
        "run",
        "uvicorn",
        "main:app",
        "--reload",
        "--host",
        APP_HOST,
        "--port",
        str(APP_PORT),
        env=envs,
    )

    # Wait for port to start
    timeout = 90
    for _ in range(timeout):
        await asyncio.sleep(1)
        if process.returncode is not None:
            raise RuntimeError("Could not start backend dev server")
        if _is_server_running(APP_PORT):
            rich.print(
                f"\n[bold green]App is running. You can access it at http://{APP_HOST}:{APP_PORT}[/bold green]"
            )
            return process

    # Timeout, kill the process
    process.terminate()
    raise TimeoutError(f"Backend dev server failed to start within {timeout} seconds")


def _get_poetry_executable() -> str:
    """
    Check for available Poetry executables and return the preferred one.
    Returns 'poetry' if installed, falls back to 'poetry.cmd'.
    Raises SystemError if neither is installed.

    Returns:
        str: The full path to the available Poetry executable
    """
    from shutil import which

    poetry_cmds = ["poetry", "poetry.cmd"]
    for cmd in poetry_cmds:
        cmd_path = which(cmd)
        if cmd_path is not None:
            return cmd_path
    raise SystemError("Poetry is not installed. Please install Poetry first.")


def _is_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect(("localhost", port))
        except ConnectionRefusedError:
            return True  # Port is available
        except OSError:
            return True  # Other socket errors likely mean port is available
        except Exception:
            return False
        return False  # Connection succeeded, port is in use


def _is_server_running(port: int) -> bool:
    """Check if a server is running on the specified port."""
    return not _is_port_available(port)


if __name__ == "__main__":
    # Command line interface
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "dev":
            dev()
        elif command == "prod":
            prod()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: dev, prod")
            sys.exit(1)
    else:
        print("Please specify a command: dev, prod")
        sys.exit(1)
