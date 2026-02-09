import logging
import sys
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


def get_log_file_path(filename: str = "mcp_server.log") -> str:
    try:
        project_root = Path(__file__).parent.parent.parent
        log_dir = project_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / filename
        log_path.touch(exist_ok=True)
        return str(log_path)
    except (OSError, PermissionError):
        pass

    try:
        home_dir = Path.home() / ".mcp" / "logs"
        home_dir.mkdir(parents=True, exist_ok=True)
        log_path = home_dir / filename
        log_path.touch(exist_ok=True)
        return str(log_path)
    except (OSError, PermissionError):
        pass

    try:
        tmp_dir = Path("/tmp") / "mcp_logs"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        log_path = tmp_dir / filename
        log_path.touch(exist_ok=True)
        return str(log_path)
    except (OSError, PermissionError):
        pass

    return None


def setup_logger(
        name: str = "mcp",
        json_mode: bool = False,
        level: int = logging.INFO,
        log_file: Optional[str] = None,
        console_output: bool = True,
        use_stderr: bool = False,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        use_rotation: bool = True,
) -> logging.Logger:

    log = logging.getLogger(name)
    log.setLevel(level)

    if log.handlers:
        return log

    if json_mode:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    if console_output:
        stream = sys.stderr if use_stderr else sys.stdout
        console_handler = logging.StreamHandler(stream)
        console_handler.setFormatter(formatter)
        log.addHandler(console_handler)

    if log_file:
        try:
            log_path = Path(log_file)
            if log_path.parent != Path("."):
                log_path.parent.mkdir(parents=True, exist_ok=True)

            if use_rotation:
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding="utf-8",
                )
            else:
                file_handler = logging.FileHandler(
                    log_file,
                    mode="a",
                    encoding="utf-8",
                )

            file_handler.setFormatter(formatter)
            log.addHandler(file_handler)

            if use_stderr or not console_output:
                sys.stderr.write(f"Logging to file: {log_file}\n")

        except Exception as e:
            sys.stderr.write(f"Warning: Could not create log file {log_file}: {e}\n")
            sys.stderr.write("Continuing with console logging only.\n")

    log.propagate = False

    return log



logger = setup_logger(
    "mcp",
    console_output=True,
    use_stderr=True,
    level=logging.DEBUG,
)
