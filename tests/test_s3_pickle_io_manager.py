"""Tests for S3 Pickle IO manager key conventions and fault tolerance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dagster import fs_io_manager

from src.io_managers.s3_pickle_io_manager import S3PickleIOManager, build_asset_io_manager_from_env


class _FakeBody:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class _FakeS3Client:
    def __init__(self, fail_put_times: int = 0, fail_get_times: int = 0) -> None:
        self.storage: Dict[str, bytes] = {}
        self._fail_put_times = fail_put_times
        self._fail_get_times = fail_get_times

    def put_object(self, Bucket: str, Key: str, Body: bytes) -> None:
        if self._fail_put_times > 0:
            self._fail_put_times -= 1
            raise RuntimeError("transient put failure")
        self.storage[f"{Bucket}/{Key}"] = Body

    def get_object(self, Bucket: str, Key: str) -> Dict[str, Any]:
        if self._fail_get_times > 0:
            self._fail_get_times -= 1
            raise RuntimeError("transient get failure")
        payload = self.storage[f"{Bucket}/{Key}"]
        return {"Body": _FakeBody(payload)}


@dataclass
class _StubOutputContext:
    identifier: List[str]
    partition_key: Optional[str] = None
    metadata: Dict[str, Any] = None

    def get_identifier(self) -> List[str]:
        return self.identifier

    def add_output_metadata(self, metadata: Dict[str, Any]) -> None:
        self.metadata = metadata


@dataclass
class _StubUpstreamOutput:
    identifier: List[str]
    partition_key: Optional[str] = None

    def get_identifier(self) -> List[str]:
        return self.identifier


@dataclass
class _StubInputContext:
    upstream_output: _StubUpstreamOutput


def test_s3_key_is_deterministic_and_partition_scoped() -> None:
    manager = S3PickleIOManager(
        s3_bucket="test-bucket",
        key_prefix="smart-energy-ai/assets",
        s3_client=_FakeS3Client(),
    )

    key = manager._build_key(
        ["tenant", "client_001_kyiv_mall", "client_data_client_001_kyiv_mall", "result"],
        partition_key="2026-03-03",
    )

    assert key == (
        "smart-energy-ai/assets/tenant/client_001_kyiv_mall/"
        "client_data_client_001_kyiv_mall/result/partition=2026-03-03.pickle"
    )


def test_handle_output_and_load_input_roundtrip() -> None:
    client = _FakeS3Client()
    manager = S3PickleIOManager(
        s3_bucket="test-bucket",
        key_prefix="smart-energy-ai/assets",
        s3_client=client,
    )

    output_context = _StubOutputContext(
        identifier=["tenant", "client_001_kyiv_mall", "client_data_client_001_kyiv_mall", "result"],
        partition_key="2026-03-03",
    )
    payload = {"tenant": "client_001_kyiv_mall", "value": 42}

    manager.handle_output(output_context, payload)

    assert output_context.metadata["s3_bucket"] == "test-bucket"
    assert "partition=2026-03-03" in output_context.metadata["s3_key"]

    input_context = _StubInputContext(
        upstream_output=_StubUpstreamOutput(
            identifier=output_context.identifier,
            partition_key=output_context.partition_key,
        )
    )

    loaded = manager.load_input(input_context)
    assert loaded == payload


def test_retries_transient_s3_failures() -> None:
    client = _FakeS3Client(fail_put_times=2, fail_get_times=2)
    manager = S3PickleIOManager(
        s3_bucket="test-bucket",
        key_prefix="smart-energy-ai/assets",
        s3_client=client,
    )

    output_context = _StubOutputContext(
        identifier=["tenant", "client_001_kyiv_mall", "client_data_client_001_kyiv_mall", "result"],
        partition_key=None,
    )

    manager.handle_output(output_context, {"ok": True})

    input_context = _StubInputContext(
        upstream_output=_StubUpstreamOutput(identifier=output_context.identifier, partition_key=None)
    )
    loaded = manager.load_input(input_context)

    assert loaded == {"ok": True}


def test_env_builder_falls_back_without_bucket(monkeypatch) -> None:
    monkeypatch.delenv("S3_IO_MANAGER_BUCKET", raising=False)
    io_manager_def = build_asset_io_manager_from_env()
    assert io_manager_def == fs_io_manager
