"""S3-backed pickle IO manager with deterministic key naming and retry semantics."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import pickle
import re
from typing import Any, Iterable, Optional

from dagster import IOManager, IOManagerDefinition, fs_io_manager
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)


def _sanitize_key_segment(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._=-]+", "_", str(value).strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "unknown"


def _normalize_prefix(prefix: str) -> str:
    value = str(prefix).strip().strip("/")
    return value or "smart-energy-ai/assets"


@dataclass(frozen=True)
class S3PickleIOManagerConfig:
    """Configuration for the S3-backed pickle IO manager."""

    s3_bucket: str
    key_prefix: str = "smart-energy-ai/assets"
    region_name: Optional[str] = None
    max_retries: int = 3


class S3PickleIOManager(IOManager):
    """Persist Dagster asset payloads in S3 using pickle serialization."""

    def __init__(
        self,
        config: S3PickleIOManagerConfig,
        *,
        s3_client: Any = None,
    ) -> None:
        self._config = S3PickleIOManagerConfig(
            s3_bucket=config.s3_bucket,
            key_prefix=_normalize_prefix(config.key_prefix),
            region_name=config.region_name,
            max_retries=max(1, int(config.max_retries)),
        )
        self._s3_bucket = self._config.s3_bucket
        self._key_prefix = self._config.key_prefix
        self._region_name = self._config.region_name
        self._max_retries = self._config.max_retries
        self._s3_client = s3_client or self._create_s3_client(self._config.region_name)

    @staticmethod
    def _create_s3_client(region_name: Optional[str]):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for S3 IO manager. Install boto3 or unset S3_IO_MANAGER_BUCKET."
            ) from exc

        return boto3.client("s3", region_name=region_name) if region_name else boto3.client("s3")

    def _build_key(self, identifier: Iterable[str], partition_key: Optional[str]) -> str:
        normalized_identifier = [_sanitize_key_segment(segment) for segment in identifier]
        key_body = "/".join(normalized_identifier)
        if partition_key:
            key_body = f"{key_body}/partition={_sanitize_key_segment(partition_key)}"
        return f"{self._key_prefix}/{key_body}.pickle"

    def _key_for_output_context(self, context) -> str:
        partition_key = getattr(context, "partition_key", None)
        return self._build_key(context.get_identifier(), partition_key)

    def _key_for_input_context(self, context) -> str:
        upstream = context.upstream_output
        partition_key = getattr(upstream, "partition_key", None)
        return self._build_key(upstream.get_identifier(), partition_key)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _put_bytes(self, key: str, payload: bytes) -> None:
        self._s3_client.put_object(Bucket=self._s3_bucket, Key=key, Body=payload)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _get_bytes(self, key: str) -> bytes:
        response = self._s3_client.get_object(Bucket=self._s3_bucket, Key=key)
        return response["Body"].read()

    def handle_output(self, context, obj: Any) -> None:
        key = self._key_for_output_context(context)
        payload = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

        self._put_bytes(key, payload)
        context.add_output_metadata(
            {
                "storage": "s3",
                "s3_bucket": self._s3_bucket,
                "s3_key": key,
                "key_prefix": self._key_prefix,
            }
        )

    def load_input(self, context):
        key = self._key_for_input_context(context)
        payload = self._get_bytes(key)
        return pickle.loads(payload)


def build_asset_io_manager_from_env() -> IOManagerDefinition:
    """Build S3-backed IO manager when configured, otherwise fallback to local filesystem."""
    settings = get_settings()
    s3 = settings.s3

    if not s3.is_configured:
        logger.info("S3 not configured; using filesystem IO manager")
        return fs_io_manager

    try:
        manager = S3PickleIOManager(
            S3PickleIOManagerConfig(
                s3_bucket=s3.bucket,
                key_prefix=s3.key_prefix,
                region_name=s3.region,
                max_retries=s3.max_retries,
            ),
        )
    except Exception as exc:
        logger.warning(
            "Falling back to filesystem IO manager because S3 IO manager init failed: %s",
            exc,
        )
        return fs_io_manager

    return IOManagerDefinition.hardcoded_io_manager(manager)
