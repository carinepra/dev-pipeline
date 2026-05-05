"""Utility functions for the orchestration pipeline."""

import os
import platform
import subprocess
from pathlib import Path


def open_file_cross_platform(file_path: str | Path) -> None:
    """
    Abre arquivo no editor/viewer padrão do sistema (cross-platform).

    Args:
        file_path: Caminho do arquivo a abrir

    Raises:
        OSError: Se não conseguir abrir o arquivo
    """
    file_path = str(file_path)

    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", file_path], check=True)
        elif system == "Windows":
            os.startfile(file_path)
        elif system == "Linux":
            subprocess.run(["xdg-open", file_path], check=True)
        else:
            raise OSError(f"Sistema operacional não suportado: {system}")
    except Exception as e:
        raise OSError(f"Erro ao abrir arquivo {file_path}: {e}")
