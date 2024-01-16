"""Public api for opyplus epgm package."""
__all__ = ["default_external_files_dir_name", "Epgm", "FileContent"]

from .epgm import Epgm, default_external_files_dir_name
from .file_content import FileContent
