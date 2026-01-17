"""Dataset reader service for reading prompts from Dataset folder or S3."""

import csv
import gzip
import io
import json
from pathlib import Path
from typing import Generator, List, Optional, Union
from urllib.parse import urlparse

import boto3
import requests
import structlog
from botocore.exceptions import ClientError

logger = structlog.get_logger(__name__)


class DatasetReader:
    """Service to read prompts from Dataset folder or S3."""

    def __init__(self, dataset_path: Optional[Union[str, Path]] = None, s3_config: Optional[dict] = None):
        """
        Initialize dataset reader.

        Args:
            dataset_path: Path to Dataset folder. If None, uses Dataset/ relative to project root.
            s3_config: Optional S3 configuration for downloading files from S3.
                      Should contain 'bucket', 'region', and optionally 'access_key', 'secret_key'.
        """
        if dataset_path is None:
            # Look for Dataset/ folder relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            dataset_path = project_root / "Dataset"

        self.dataset_path = Path(dataset_path)
        self.s3_config = s3_config or {}
        self.s3_client = None

        if not self.dataset_path.exists():
            logger.warning("Dataset folder not found", path=str(self.dataset_path))
        else:
            logger.info("Dataset reader initialized", path=str(self.dataset_path))

        # Initialize S3 client if config provided
        if self.s3_config:
            self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3 client with provided configuration."""
        try:
            s3_kwargs = {
                "region_name": self.s3_config.get("region", "us-east-1")
            }

            # Add credentials if provided
            if "access_key" in self.s3_config and "secret_key" in self.s3_config:
                s3_kwargs["aws_access_key_id"] = self.s3_config["access_key"]
                s3_kwargs["aws_secret_access_key"] = self.s3_config["secret_key"]

            self.s3_client = boto3.client("s3", **s3_kwargs)
            logger.info("S3 client initialized", region=s3_kwargs["region_name"])
        except Exception as e:
            logger.error("Failed to initialize S3 client", error=str(e))
            self.s3_client = None

    def _is_s3_url(self, url: str) -> bool:
        """Check if URL is an S3 URL."""
        return url.startswith("s3://") or url.startswith("https://") and "s3." in url

    def _parse_s3_url(self, s3_url: str) -> tuple[str, str]:
        """Parse S3 URL to extract bucket and key."""
        if s3_url.startswith("s3://"):
            # s3://bucket/key format
            path = s3_url[5:]  # Remove 's3://'
            bucket, key = path.split("/", 1)
            return bucket, key
        elif s3_url.startswith("https://"):
            # https://bucket.s3.region.amazonaws.com/key format
            parsed = urlparse(s3_url)
            bucket = parsed.netloc.split(".")[0]
            key = parsed.path.lstrip("/")
            return bucket, key
        else:
            raise ValueError(f"Invalid S3 URL format: {s3_url}")

    def _download_from_s3(self, s3_url: str, chunk_size: int = 8192) -> Generator[bytes, None, None]:
        """
        Download file from S3 in chunks to avoid loading large files into memory.

        Args:
            s3_url: S3 URL (s3://bucket/key or https://bucket.s3.region.amazonaws.com/key)
            chunk_size: Size of chunks to download

        Yields:
            Chunks of file data
        """
        if not self.s3_client:
            raise ValueError("S3 client not initialized")

        bucket, key = self._parse_s3_url(s3_url)

        try:
            # Get object metadata first
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            total_size = response["ContentLength"]

            logger.info("Starting S3 download", bucket=bucket, key=key, size=total_size)

            # Download in chunks
            start_byte = 0
            while start_byte < total_size:
                end_byte = min(start_byte + chunk_size - 1, total_size - 1)

                range_header = f"bytes={start_byte}-{end_byte}"
                response = self.s3_client.get_object(
                    Bucket=bucket, Key=key, Range=range_header
                )

                chunk = response["Body"].read()
                if chunk:
                    yield chunk

                start_byte += chunk_size

        except ClientError as e:
            logger.error("S3 download failed", bucket=bucket, key=key, error=str(e))
            raise

    def read_file_chunked(self, file_path: Union[str, Path], chunk_size: int = 1000) -> Generator[List[dict], None, None]:
        """
        Read file in chunks to avoid memory issues with large files.

        Args:
            file_path: Path to file (local) or S3 URL
            chunk_size: Number of records to yield per chunk

        Yields:
            Chunks of records
        """
        if isinstance(file_path, str) and self._is_s3_url(file_path):
            # Handle S3 URL
            yield from self._read_s3_file_chunked(file_path, chunk_size)
        else:
            # Handle local file
            file_path = Path(file_path)
            yield from self._read_local_file_chunked(file_path, chunk_size)

    def _read_s3_file_chunked(self, s3_url: str, chunk_size: int = 1000) -> Generator[List[dict], None, None]:
        """Read S3 file in chunks."""
        buffer = []
        line_count = 0

        try:
            # Download file in chunks and process line by line
            accumulated_data = b""

            for chunk in self._download_from_s3(s3_url):
                accumulated_data += chunk

                # Process complete lines
                lines = accumulated_data.split(b"\n")
                accumulated_data = lines.pop()  # Keep incomplete line

                for line in lines:
                    if line.strip():
                        try:
                            # Try to parse as JSON
                            data = json.loads(line.decode("utf-8"))
                            buffer.append(data)
                            line_count += 1

                            if len(buffer) >= chunk_size:
                                yield buffer
                                buffer = []

                        except json.JSONDecodeError:
                            # Try as plain text (one prompt per line)
                            prompt_text = line.decode("utf-8").strip()
                            if prompt_text:
                                buffer.append({"text": prompt_text, "source": "s3"})
                                line_count += 1

                                if len(buffer) >= chunk_size:
                                    yield buffer
                                    buffer = []

            # Process remaining data
            if accumulated_data.strip():
                try:
                    data = json.loads(accumulated_data.decode("utf-8"))
                    buffer.append(data)
                except json.JSONDecodeError:
                    prompt_text = accumulated_data.decode("utf-8").strip()
                    if prompt_text:
                        buffer.append({"text": prompt_text, "source": "s3"})

            # Yield remaining buffer
            if buffer:
                yield buffer

            logger.info("S3 file processing completed", url=s3_url, lines_processed=line_count)

        except Exception as e:
            logger.error("Error processing S3 file", url=s3_url, error=str(e))
            raise

    def _read_local_file_chunked(self, file_path: Path, chunk_size: int = 1000) -> Generator[List[dict], None, None]:
        """Read local file in chunks."""
        buffer = []

        try:
            # Detect file type and read accordingly
            if file_path.suffix.lower() in [".json", ".jsonl"]:
                yield from self._read_json_file_chunked(file_path, chunk_size)
            elif file_path.suffix.lower() == ".csv":
                yield from self._read_csv_file_chunked(file_path, chunk_size)
            elif file_path.suffix.lower() in [".txt", ".wp_source", ".wp_target"]:
                yield from self._read_text_file_chunked(file_path, chunk_size)
            else:
                logger.warning("Unsupported file type, treating as text", file=str(file_path))
                yield from self._read_text_file_chunked(file_path, chunk_size)

        except Exception as e:
            logger.error("Error processing local file", file=str(file_path), error=str(e))
            raise

    def _read_json_file_chunked(self, file_path: Path, chunk_size: int = 1000) -> Generator[List[dict], None, None]:
        """Read JSON/JSONL file in chunks."""
        buffer = []

        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix.lower() == ".jsonl":
                # JSON Lines format - one JSON object per line
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            buffer.append(data)

                            if len(buffer) >= chunk_size:
                                yield buffer
                                buffer = []
                        except json.JSONDecodeError as e:
                            logger.warning("Invalid JSON line", file=str(file_path), line=line_num, error=str(e))
            else:
                # Regular JSON file
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        buffer.append(item)
                        if len(buffer) >= chunk_size:
                            yield buffer
                            buffer = []
                else:
                    # Single object
                    buffer.append(data)
                    if len(buffer) >= chunk_size:
                        yield buffer
                        buffer = []

        if buffer:
            yield buffer

    def _read_csv_file_chunked(self, file_path: Path, chunk_size: int = 1000) -> Generator[List[dict], None, None]:
        """Read CSV file in chunks."""
        buffer = []

        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # For our prompt clustering CSV format, ensure content field is present
                if 'content' in row and row['content'].strip():
                    # Add source metadata
                    row['source'] = 'csv'
                    row['file_path'] = str(file_path)
                    buffer.append(row)
                    if len(buffer) >= chunk_size:
                        yield buffer
                        buffer = []

        if buffer:
            yield buffer

    def _read_text_file_chunked(self, file_path: Path, chunk_size: int = 1000) -> Generator[List[dict], None, None]:
        """Read text file in chunks (one prompt per line)."""
        buffer = []

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    buffer.append({"text": line, "source": "file", "line": line_num})
                    if len(buffer) >= chunk_size:
                        yield buffer
                        buffer = []

        if buffer:
            yield buffer

    def _read_json(self, file_path: Path) -> Generator[dict, None, None]:
        """
        Read JSON file and yield prompts.

        Args:
            file_path: Path to JSON file

        Yields:
            Prompt data dictionaries
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, list):
                # List of prompts
                for item in data:
                    yield item
            elif isinstance(data, dict):
                # Single object or object with prompts array
                if "prompts" in data:
                    for item in data["prompts"]:
                        yield item
                elif "data" in data:
                    for item in data["data"]:
                        yield item
                else:
                    # Single prompt object
                    yield data

        except json.JSONDecodeError as e:
            logger.error("JSON decode error", file=str(file_path), error=str(e))
            raise
        except Exception as e:
            logger.error("Error reading JSON file", file=str(file_path), error=str(e))
            raise

    def _read_jsonl(self, file_path: Path) -> Generator[dict, None, None]:
        """
        Read JSONL file and yield prompts.

        Args:
            file_path: Path to JSONL file

        Yields:
            Prompt data dictionaries
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        yield data
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "JSONL line decode error",
                            file=str(file_path),
                            line=line_num,
                            error=str(e),
                        )
                        continue

        except Exception as e:
            logger.error("Error reading JSONL file", file=str(file_path), error=str(e))
            raise

    def _read_csv(self, file_path: Path) -> Generator[dict, None, None]:
        """
        Read CSV file and yield prompts.

        Args:
            file_path: Path to CSV file

        Yields:
            Prompt data dictionaries (row as dict)
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # For our prompt clustering CSV format, ensure content field is present
                    if 'content' in row and row['content'].strip():
                        # Add source metadata
                        row['source'] = 'csv'
                        row['file_path'] = str(file_path)
                        yield row

        except Exception as e:
            logger.error("Error reading CSV file", file=str(file_path), error=str(e))
            raise

    def _read_txt(self, file_path: Path) -> Generator[dict, None, None]:
        """
        Read TXT file and yield prompts (one per line).

        Args:
            file_path: Path to TXT file

        Yields:
            Prompt data dictionaries with 'content' key
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    yield {"content": line, "line_number": line_num}

        except Exception as e:
            logger.error("Error reading TXT file", file=str(file_path), error=str(e))
            raise

    def _extract_prompt_content(self, data: dict) -> Optional[str]:
        """
        Extract prompt content from data dictionary.

        Args:
            data: Data dictionary

        Returns:
            Prompt content string or None
        """
        # Try common field names
        for field in ["prompt", "content", "text", "message", "input", "query"]:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict) and "content" in value:
                    return value["content"]

        # If no standard field, try to get first string value
        for key, value in data.items():
            if isinstance(value, str) and value.strip():
                return value

        return None

    def read_file(self, file_path: Union[str, Path]) -> Generator[dict, None, None]:
        """
        Read prompts from a file based on its extension.

        Args:
            file_path: Path to file

        Yields:
            Prompt data dictionaries

        Raises:
            ValueError: If file format is not supported
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        logger.debug("Reading file", file=str(file_path), format=suffix)

        if suffix == ".json":
            yield from self._read_json(file_path)
        elif suffix == ".jsonl":
            yield from self._read_jsonl(file_path)
        elif suffix == ".csv":
            yield from self._read_csv(file_path)
        elif suffix in [".txt", ".text"]:
            yield from self._read_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def list_files(self) -> List[Union[Path, str]]:
        """
        List all supported files from local folder and configured S3 URLs.

        Returns:
            List of file paths (Path objects) and S3 URLs (strings)
        """
        files = []

        # Add local files
        if self.dataset_path.exists():
            supported_extensions = {".json", ".jsonl", ".csv", ".txt", ".text", ".wp_source", ".wp_target"}
            for file_path in self.dataset_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    files.append(file_path)

        # Add configured S3 URLs
        s3_urls = self.s3_config.get("urls", [])
        files.extend(s3_urls)

        logger.info("Found dataset sources",
                   local_files=len(files) - len(s3_urls),
                   s3_urls=len(s3_urls),
                   path=str(self.dataset_path))
        return files

    def read_all(self) -> Generator[tuple[Path, dict], None, None]:
        """
        Read all prompts from all files in dataset folder.

        Yields:
            Tuples of (file_path, prompt_data)
        """
        files = self.list_files()

        for file_path in files:
            try:
                logger.info("Processing file", file=str(file_path))
                file_count = 0

                for prompt_data in self.read_file(file_path):
                    file_count += 1
                    yield file_path, prompt_data

                logger.info("File processed", file=str(file_path), prompts=file_count)

            except Exception as e:
                logger.error(
                    "Error processing file, continuing",
                    file=str(file_path),
                    error=str(e),
                )
                # Continue processing other files
                continue


def get_dataset_reader(dataset_path: Optional[Union[str, Path]] = None) -> DatasetReader:
    """
    Get dataset reader instance.

    Args:
        dataset_path: Optional path to Dataset folder

    Returns:
        DatasetReader instance
    """
    from src.config.settings import get_settings

    # Get S3 configuration from settings
    settings = get_settings()
    s3_config = {}

    # Check if S3 config is available in settings
    if hasattr(settings, 'aws') and hasattr(settings.aws, 's3'):
        s3_config = {
            "bucket": getattr(settings.aws.s3, 'bucket', ''),
            "region": getattr(settings.aws.s3, 'region', 'us-east-1'),
        }

        # Add S3 URLs from config (supports both list and comma-separated string)
        s3_urls = getattr(settings.aws.s3, 'dataset_urls', [])
        if isinstance(s3_urls, str):
            # Handle comma-separated string from environment variable
            s3_urls = [url.strip() for url in s3_urls.split(',') if url.strip()]
        elif not s3_urls:
            s3_urls = []

        if s3_urls:
            s3_config["urls"] = s3_urls

        # Also check for individual S3 URL environment variables (fallback)
        import os
        s3_url_vars = [os.getenv(f"S3_DATASET_URL_{i}") for i in range(1, 10) if os.getenv(f"S3_DATASET_URL_{i}")]
        if s3_url_vars:
            s3_config.setdefault("urls", []).extend(s3_url_vars)

    return DatasetReader(dataset_path=dataset_path, s3_config=s3_config)

