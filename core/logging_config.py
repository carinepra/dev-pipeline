"""Setup de logging para o pipeline."""

import logging
from pathlib import Path

from rich.logging import RichHandler


def setup_logging(story_key: str, log_dir: Path) -> logging.Logger:
    """
    Setup dual logging: console (Rich) + file (detailed).

    Args:
        story_key: Issue key (ex: HUB-1234)
        log_dir: Diretório para salvar logs

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(f"pipeline.{story_key}")
    logger.setLevel(logging.DEBUG)

    # Remover handlers antigos (evitar duplicação)
    logger.handlers.clear()

    # Console handler (INFO+) com Rich
    console_handler = RichHandler(
        level=logging.INFO, show_time=True, show_path=False, markup=True, rich_tracebacks=True
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    # File handler (DEBUG+)
    log_dir.mkdir(exist_ok=True, parents=True)
    log_file = log_dir / f"pipeline-{story_key}.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info(f"Logging configurado: console (INFO+) e arquivo (DEBUG+) -> {log_file}")

    return logger
