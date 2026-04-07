import json
import logging
import time
from pathlib import Path


class PerformanceLoggerService:
    _instance = None

    def __new__(cls, log_dir: str = "logs/performance"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = "logs/performance"):
        if not getattr(self, "_initialized", False):
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)

            self.logger = logging.getLogger("performance_logger")
            self.logger.setLevel(logging.INFO)

            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)

            date_str = time.strftime("%Y-%m-%d")
            log_file = self.log_dir / f"performance-{date_str}.log"
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(self._json_formatter())
            self.logger.addHandler(file_handler)

            self.logger.propagate = False

            self.operations = {}
            self._initialized = True

    @classmethod
    def get_instance(cls, log_dir: str = "logs/performance"):
        if cls._instance is None:
            return cls(log_dir)
        return cls._instance

    def _json_formatter(self):
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                return json.dumps(record.msg)

        return JSONFormatter()

    def start_operation(self, operation_id: str, metadata: dict = None):
        metadata = metadata or {}
        self.operations[operation_id] = {
            "start_time": time.time(),
            "steps": [],
            "metadata": metadata,
        }

    def start_step(self, operation_id: str, step_name: str):
        operation = self.operations.get(operation_id)
        if not operation:
            self.logger.warning(
                {"event": "missing_operation", "operation_id": operation_id}
            )
            return

        operation["steps"].append({"name": step_name, "start_time": time.time()})

    def end_step(self, operation_id: str, step_name: str, additional_data: dict = None):
        additional_data = additional_data or {}
        operation = self.operations.get(operation_id)
        if not operation:
            self.logger.warning(
                {"event": "missing_operation", "operation_id": operation_id}
            )
            return

        step = next(
            (
                s
                for s in operation["steps"]
                if s["name"] == step_name and "end_time" not in s
            ),
            None,
        )
        if not step:
            self.logger.warning(
                {
                    "event": "missing_step",
                    "operation_id": operation_id,
                    "step_name": step_name,
                }
            )
            return

        step["end_time"] = time.time()
        step["duration"] = int(
            (step["end_time"] - step["start_time"]) * 1000
        )
        step["start_time"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.gmtime(step["start_time"])
        )
        step["end_time"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.gmtime(step["end_time"])
        )
        step["additional_data"] = additional_data

    def end_operation(
        self, operation_id: str, status: str = "success", additional_data: dict = None
    ):
        additional_data = additional_data or {}
        operation = self.operations.pop(operation_id, None)
        if not operation:
            self.logger.warning(
                {"event": "missing_operation", "operation_id": operation_id}
            )
            return

        end_time = time.time()
        duration = int((end_time - operation["start_time"]) * 1000)
        log_data = {
            "event": "operation_completed",
            "operation_id": operation_id,
            "status": status,
            "duration": duration,
            "start_time": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.gmtime(operation["start_time"])
            ),
            "end_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(end_time)),
            "steps": operation["steps"],
            "metadata": {**operation["metadata"], **additional_data},
        }
        self.logger.info(log_data)
