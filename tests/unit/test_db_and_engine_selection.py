from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str, injected_modules: dict[str, object] | None = None):
    module_path = REPO_ROOT / relative_path
    injected_modules = injected_modules or {}
    previous = {}

    for name, module in injected_modules.items():
        previous[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def test_db_module_initializes_engine_sessions_and_health_checks() -> None:
    state = {"create_all": 0, "connected": 0, "closed": 0, "listeners": []}

    class FakeConnection:
        def __enter__(self):
            state["connected"] += 1
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement):
            state["statement"] = statement

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    class FakeSession:
        def close(self):
            state["closed"] += 1

    def fake_create_engine(*args, **kwargs):
        state["engine_args"] = args
        state["engine_kwargs"] = kwargs
        return FakeEngine()

    def fake_listens_for(engine, event_name):
        state["listeners"].append(event_name)

        def decorator(func):
            return func

        return decorator

    def fake_sessionmaker(**kwargs):
        state["sessionmaker_kwargs"] = kwargs

        def factory():
            return FakeSession()

        return factory

    def fake_declarative_base():
        metadata = types.SimpleNamespace(create_all=lambda bind: state.__setitem__("create_all", state["create_all"] + 1))
        return types.SimpleNamespace(metadata=metadata)

    sqlalchemy_mod = types.ModuleType("sqlalchemy")
    sqlalchemy_mod.create_engine = fake_create_engine
    sqlalchemy_mod.event = types.SimpleNamespace(listens_for=fake_listens_for)
    orm_mod = types.ModuleType("sqlalchemy.orm")
    orm_mod.sessionmaker = fake_sessionmaker
    orm_mod.declarative_base = fake_declarative_base
    pool_mod = types.ModuleType("sqlalchemy.pool")
    pool_mod.QueuePool = object
    sql_mod = types.ModuleType("sqlalchemy.sql")
    sql_mod.text = lambda s: s  # Mock text() function

    # Mock settings module
    infra_mod = types.ModuleType("src.infrastructure")
    infra_mod.settings = types.SimpleNamespace(
        get_database_url=lambda: "postgresql://test:test@localhost:5432/test"
    )

    module = load_module(
        "db_under_test",
        "src/infrastructure/db.py",
        injected_modules={
            "sqlalchemy": sqlalchemy_mod,
            "sqlalchemy.orm": orm_mod,
            "sqlalchemy.pool": pool_mod,
            "sqlalchemy.sql": sql_mod,
            "src.infrastructure": infra_mod,
            "src.infrastructure.settings": infra_mod.settings,
        },
    )

    session = next(module.get_db())
    assert isinstance(session, FakeSession)
    session.close()
    module.init_db()
    assert module.health_check() is True
    assert state["engine_args"][0].startswith("postgresql://")
    assert state["create_all"] == 1
    assert state["connected"] == 1
    assert state["statement"] == "SELECT 1"
    assert state["listeners"] == ["connect", "checkin"]


def build_selection_module(nv_available: bool, nv_engine, polars_available: bool, polars_engine):
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    engines_pkg = types.ModuleType("src.engines")
    engines_pkg.__path__ = [str(REPO_ROOT / "src" / "engines")]
    src_pkg.engines = engines_pkg

    nv_mod = types.ModuleType("src.engines.nvtabular_engine")
    nv_mod.is_nvtabular_available = lambda: nv_available
    nv_mod.create_nvtabular_engine = lambda cfg: nv_engine
    polars_mod = types.ModuleType("src.engines.polars_engine")
    polars_mod.is_polars_available = lambda: polars_available
    polars_mod.create_polars_engine = lambda cfg: polars_engine

    return load_module(
        f"src.engines.selection_under_test_{nv_available}_{polars_available}_{nv_engine is not None}_{polars_engine is not None}",
        "src/engines/selection.py",
        injected_modules={
            "src": src_pkg,
            "src.engines": engines_pkg,
            "src.engines.nvtabular_engine": nv_mod,
            "src.engines.polars_engine": polars_mod,
        },
    )


def test_engine_selection_prefers_requested_or_fallback_modes(monkeypatch) -> None:
    module = build_selection_module(True, {"engine": "gpu"}, True, {"engine": "cpu"})

    assert module._as_bool("YES") is True
    assert module._normalize_mode("gpu") == "nvtabular"

    engine, metadata = module.select_feature_engine({"execution_mode": "gpu"})
    assert engine == {"engine": "gpu"}
    assert metadata["selected_engine"] == "nvtabular"

    fallback_module = build_selection_module(True, None, True, {"engine": "cpu"})
    monkeypatch.setenv("SMART_ENERGY_ENGINE", "auto")
    engine, metadata = fallback_module.select_feature_engine()
    assert engine == {"engine": "cpu"}
    assert metadata["selected_engine"] == "polars"
    assert "falling back to polars" in metadata["fallback_reason"]

    strict_module = build_selection_module(False, None, True, {"engine": "cpu"})
    try:
        strict_module.select_feature_engine({"execution_mode": "nvtabular", "strict_engine": True})
    except RuntimeError as exc:
        assert "NVTabular engine was requested" in str(exc)
    else:
        raise AssertionError("Expected strict NVTabular selection to fail")

    polars_only_module = build_selection_module(False, None, True, {"engine": "cpu"})
    engine, metadata = polars_only_module.select_feature_engine({"execution_mode": "polars"})
    assert engine == {"engine": "cpu"}
    assert metadata["selected_engine"] == "polars"