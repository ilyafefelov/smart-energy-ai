import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[2]
USER_CONFIG_PATH = ROOT / "energy_ml" / "user_config.py"
OPTIMIZATION_ENGINE_PATH = ROOT / "energy_ml" / "mlops" / "optimization_engine.py"


def load_modules():
    package = types.ModuleType("energy_ml")
    package.__path__ = [str(ROOT / "energy_ml")]
    mlops_package = types.ModuleType("energy_ml.mlops")
    mlops_package.__path__ = [str(ROOT / "energy_ml" / "mlops")]

    sys.modules.setdefault("energy_ml", package)
    sys.modules.setdefault("energy_ml.mlops", mlops_package)

    user_config_spec = importlib.util.spec_from_file_location("energy_ml.user_config", USER_CONFIG_PATH)
    user_config_module = importlib.util.module_from_spec(user_config_spec)
    assert user_config_spec is not None and user_config_spec.loader is not None
    sys.modules[user_config_spec.name] = user_config_module
    user_config_spec.loader.exec_module(user_config_module)

    optimization_spec = importlib.util.spec_from_file_location(
        "energy_ml.mlops.optimization_engine", OPTIMIZATION_ENGINE_PATH
    )
    optimization_module = importlib.util.module_from_spec(optimization_spec)
    assert optimization_spec is not None and optimization_spec.loader is not None
    sys.modules[optimization_spec.name] = optimization_module
    optimization_spec.loader.exec_module(optimization_module)

    return optimization_module, user_config_module


OPTIMIZATION_MODULE, USER_CONFIG_MODULE = load_modules()
OptimizationEngine = OPTIMIZATION_MODULE.OptimizationEngine
UserConfigModel = USER_CONFIG_MODULE.UserConfigModel


def test_get_user_strategy_success_returns_stable_envelope():
    engine = OptimizationEngine()
    config = UserConfigModel(
        optimization_strategy="max_earn",
        custom_optimization_weights={"earnings": 0.9},
    )

    strategy = engine.get_user_strategy(config)

    assert strategy["success"] is True
    assert strategy["error"] is None
    assert strategy["strategy"] == "max_earn"
    assert strategy["weights"]["earnings"] == 0.9
    assert set(strategy.keys()) == {
        "strategy",
        "description",
        "weights",
        "constraints",
        "custom_weights",
        "timestamp",
        "success",
        "error",
    }


def test_get_user_strategy_error_preserves_public_envelope():
    engine = OptimizationEngine()

    class ExplodingUserConfig:
        def __getattribute__(self, _name):
            raise RuntimeError("config lookup failed")

    strategy = engine.get_user_strategy(ExplodingUserConfig())

    assert strategy["success"] is False
    assert strategy["strategy"] == "balanced"
    assert strategy["error"] == "config lookup failed"
    assert strategy["weights"] == OptimizationEngine.OPTIMIZATION_STRATEGIES["balanced"]["weights"]
    assert strategy["constraints"] == OptimizationEngine.OPTIMIZATION_STRATEGIES["balanced"]["constraints"]
    assert set(strategy.keys()) == {
        "strategy",
        "description",
        "weights",
        "constraints",
        "custom_weights",
        "timestamp",
        "success",
        "error",
    }