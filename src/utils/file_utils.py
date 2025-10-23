"""
File I/O utilities for Terrain Tunneling Calculator.

This module provides utilities for reading, writing, and managing files,
with a focus on JSON contour files and export formats.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import hashlib

from .validation import ValidationResult, ValidationSeverity, ValidationFramework


class FileOperationError(Exception):
    """Base exception for file operations."""
    pass


class FileNotFoundError(FileOperationError):
    """Raised when a required file is not found."""
    pass


class InvalidFileFormatError(FileOperationError):
    """Raised when a file has invalid format."""
    pass


class FileTooLargeError(FileOperationError):
    """Raised when a file exceeds size limits."""
    pass


class FileUtils:
    """Utility class for file operations."""

    def __init__(self, max_file_size_mb: int = 100):
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.logger = logging.getLogger(__name__)

    def read_json_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Read and parse a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            InvalidFileFormatError: If file is not valid JSON
            FileTooLargeError: If file exceeds size limit
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.stat().st_size > self.max_file_size_bytes:
            raise FileTooLargeError(
                f"File too large: {file_path} ({file_path.stat().st_size} bytes > {self.max_file_size_bytes} bytes)"
            )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.logger.info(f"Successfully loaded JSON file: {file_path}")
            return data

        except json.JSONDecodeError as e:
            raise InvalidFileFormatError(f"Invalid JSON format in {file_path}: {str(e)}")
        except Exception as e:
            raise FileOperationError(f"Error reading file {file_path}: {str(e)}")

    def write_json_file(self, file_path: Union[str, Path], data: Dict[str, Any],
                        indent: int = 2, ensure_dir: bool = True) -> None:
        """
        Write data to a JSON file.

        Args:
            file_path: Path to the output file
            data: Data to write
            indent: JSON indentation level
            ensure_dir: Create parent directories if they don't exist

        Raises:
            FileOperationError: If writing fails
        """
        file_path = Path(file_path)

        if ensure_dir:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create backup if file exists
            if file_path.exists():
                backup_path = file_path.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                file_path.rename(backup_path)
                self.logger.info(f"Created backup: {backup_path}")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)

            self.logger.info(f"Successfully wrote JSON file: {file_path}")

        except Exception as e:
            raise FileOperationError(f"Error writing file {file_path}: {str(e)}")

    def read_text_file(self, file_path: Union[str, Path]) -> str:
        """
        Read a text file.

        Args:
            file_path: Path to the text file

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
            FileOperationError: If reading fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.logger.info(f"Successfully read text file: {file_path}")
            return content

        except Exception as e:
            raise FileOperationError(f"Error reading file {file_path}: {str(e)}")

    def write_text_file(self, file_path: Union[str, Path], content: str,
                        ensure_dir: bool = True) -> None:
        """
        Write content to a text file.

        Args:
            file_path: Path to the output file
            content: Content to write
            ensure_dir: Create parent directories if they don't exist

        Raises:
            FileOperationError: If writing fails
        """
        file_path = Path(file_path)

        if ensure_dir:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"Successfully wrote text file: {file_path}")

        except Exception as e:
            raise FileOperationError(f"Error writing file {file_path}: {str(e)}")

    def file_exists(self, file_path: Union[str, Path]) -> bool:
        """Check if a file exists."""
        return Path(file_path).exists()

    def get_file_size(self, file_path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        file_path = Path(file_path)
        return file_path.stat().st_size if file_path.exists() else 0

    def get_file_hash(self, file_path: Union[str, Path]) -> str:
        """Calculate MD5 hash of a file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)

        return hash_md5.hexdigest()

    def create_directory(self, dir_path: Union[str, Path]) -> None:
        """Create a directory if it doesn't exist."""
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Created directory: {dir_path}")

    def list_files(self, directory: Union[str, Path],
                  pattern: str = "*", recursive: bool = False) -> List[Path]:
        """
        List files in a directory.

        Args:
            directory: Directory to search
            pattern: File pattern to match
            recursive: Whether to search recursively

        Returns:
            List of matching file paths
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))

        # Return only files, not directories
        return [f for f in files if f.is_file()]

    def get_file_extension(self, file_path: Union[str, Path]) -> str:
        """Get the file extension (including the dot)."""
        return Path(file_path).suffix.lower()

    def validate_file_extension(self, file_path: Union[str, Path],
                               allowed_extensions: List[str]) -> bool:
        """Validate that a file has an allowed extension."""
        ext = self.get_file_extension(file_path)
        return ext in [e.lower() for e in allowed_extensions]

    def get_unique_filename(self, file_path: Union[str, Path],
                            extension: Optional[str] = None) -> Path:
        """
        Get a unique filename by adding a number if the file already exists.

        Args:
            file_path: Desired file path
            extension: Optional custom extension

        Returns:
            Unique file path
        """
        file_path = Path(file_path)

        if extension:
            file_path = file_path.with_suffix(extension)

        if not file_path.exists():
            return file_path

        # Add counter to filename
        counter = 1
        stem = file_path.stem
        parent = file_path.parent
        suffix = file_path.suffix

        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    def copy_file(self, source: Union[str, Path], destination: Union[str, Path]) -> None:
        """
        Copy a file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Raises:
            FileNotFoundError: If source doesn't exist
            FileOperationError: If copy fails
        """
        source = Path(source)
        destination = Path(destination)

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        try:
            # Create destination directory if needed
            destination.parent.mkdir(parents=True, exist_ok=True)

            import shutil
            shutil.copy2(source, destination)

            self.logger.info(f"Copied file from {source} to {destination}")

        except Exception as e:
            raise FileOperationError(f"Error copying file {source} to {destination}: {str(e)}")

    def delete_file(self, file_path: Union[str, Path],
                    missing_ok: bool = False) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to file to delete
            missing_ok: Whether to ignore if file doesn't exist

        Returns:
            True if file was deleted, False otherwise
        """
        file_path = Path(file_path)

        if not file_path.exists():
            if missing_ok:
                return False
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        try:
            file_path.unlink()
            self.logger.info(f"Deleted file: {file_path}")
            return True

        except Exception as e:
            raise FileOperationError(f"Error deleting file {file_path}: {str(e)}")

    def ensure_directory_exists(self, dir_path: Union[str, Path]) -> None:
        """Ensure a directory exists, creating it if necessary."""
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)

    def clean_directory(self, directory: Union[str, Path],
                        keep_hidden: bool = True) -> int:
        """
        Clean a directory by removing all files and subdirectories.

        Args:
            directory: Directory to clean
            keep_hidden: Whether to keep hidden files and directories

        Returns:
            Number of items removed
        """
        directory = Path(directory)
        removed_count = 0

        if not directory.exists():
            return 0

        for item in directory.iterdir():
            if keep_hidden and item.name.startswith('.'):
                continue

            if item.is_file():
                item.unlink()
                removed_count += 1
            elif item.is_dir():
                # Recursively remove directory
                removed_count += len(list(item.rglob('*')))
                import shutil
                shutil.rmtree(item)

        self.logger.info(f"Cleaned directory {directory}, removed {removed_count} items")
        return removed_count