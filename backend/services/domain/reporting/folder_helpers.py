#!/usr/bin/env python3
"""Utilities for discovering client and tenant folders under the downloads directory."""

from __future__ import annotations

from pathlib import Path
from typing import List

from backend.services.core.config import DEFAULT_CLIENT

BACKEND_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BACKEND_DIR.parent / "downloads"


def _list_directories(path: Path) -> List[Path]:
    if not path.exists():
        return []
    return sorted([child for child in path.iterdir() if child.is_dir()], key=lambda p: p.name)


def list_client_folders(base_dir: Path | None = None) -> List[Path]:
    """Return directories under the downloads root representing clients."""
    root = Path(base_dir) if base_dir is not None else DOWNLOADS_DIR
    return _list_directories(root)


def list_tenant_folders(client_token: str = DEFAULT_CLIENT, base_dir: Path | None = None) -> List[Path]:
    """Return directories for a given client token (tenant/floor folders)."""
    root = Path(base_dir) if base_dir is not None else DOWNLOADS_DIR
    return _list_directories(root / client_token)


__all__ = ["list_client_folders", "list_tenant_folders"]

