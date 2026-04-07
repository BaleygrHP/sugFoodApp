from gevent import monkey
monkey.patch_all()

import asyncio
import os
import dotenv
import rich

# Load .env
dotenv.load_dotenv(override=True)

CELERY_CONCURRENCY = os.getenv("INFRA__TASK_QUEUE__CONCURRENCY", "1")
CELERY_POOL_TYPE = os.getenv("INFRA__TASK_QUEUE__POOL_TYPE", "solo")
CELERY_MAX_TASKS_PER_CHILD = os.getenv("INFRA__TASK_QUEUE__MAX_TASK_PER_CHILDS", "100")


async def start_celery_worker():
    rich.print("[bold blue]===== STARTING CELERY WORKER =====[/bold blue]")

    try:
        poetry_executable = _get_poetry_executable()
        cmd = [
            poetry_executable,
            "run",
            "celery",
            "-A",
            "app.tasks",
            "worker",
            "--pool",
            CELERY_POOL_TYPE,
            "--loglevel",
            "info",
            "--concurrency",
            CELERY_CONCURRENCY,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=os.environ.copy(),
        )

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
        raise SystemError(f"Failed to start Celery worker: {e!s}") from e


def _get_poetry_executable() -> str:
    from shutil import which

    for cmd in ["poetry", "poetry.cmd"]:
        if which(cmd):
            return which(cmd)
    raise SystemError("Poetry is not installed. Please install it first.")


def main():
    asyncio.run(start_celery_worker())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "main":
            main()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: main")
            sys.exit(1)
    else:
        print("Please specify a command: main")
        sys.exit(1)
