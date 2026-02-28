# tests/conftest.py
import pytest
import asyncio
import subprocess
import time
import psutil
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'energy_ml'))

@pytest.fixture(scope="session")
def dashboard_server():
    """Start dashboard server for testing."""
    try:
        # Check if npm is available
        subprocess.run(['npm', '--version'], check=True, capture_output=True)
        
        # Start Nuxt dev server
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd="dashboard",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(15)
        
        yield process
        
        # Cleanup
        try:
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except:
            process.terminate()
            process.wait()
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("Dashboard server not available")

@pytest.fixture(scope="session")  
def python_api_server():
    """Start Python ML API server for testing."""
    try:
        process = subprocess.Popen(
            ["python", "ml_integration_api.py"],
            cwd="energy_ml",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE  
        )
        
        time.sleep(5)
        
        yield process
        
        process.kill()
        
    except Exception as e:
        pytest.skip(f"Python API server not available: {e}")

# Test data factories
@pytest.fixture
def sample_battery_config():
    """Sample battery configuration for testing."""
    return {
        "type": "LFP",
        "capacity_kwh": 10.0,
        "efficiency": 0.95,
        "max_power_kw": 5.0
    }

@pytest.fixture 
def sample_control_command():
    """Sample control command for testing."""
    return {
        "command": "charge",
        "power_kw": 2.5,
        "duration_minutes": 60,
        "reason": "Test command"
    }

@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    import pandas as pd
    import numpy as np
    
    return pd.DataFrame({
        'timestamp': pd.date_range('2026-01-01', periods=24, freq='H'),
        'price_uah_kwh': np.random.uniform(1.5, 3.0, 24),
        'demand_kw': np.random.uniform(0.5, 2.0, 24)
    })

@pytest.fixture
def mock_battery():
    """Mock battery instance for testing."""
    try:
        from energy_ml.simulator.battery_physics import LFPBatteryModel
        return LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
    except ImportError:
        pytest.skip("Battery models not available")

@pytest.fixture
def mock_controller():
    """Mock controller instance for testing."""
    try:
        from energy_ml.control.inverter_controller import VirtualInverterController
        return VirtualInverterController(battery_capacity_kwh=10.0, max_power_kw=5.0)
    except ImportError:
        pytest.skip("Control system not available")

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    # Ensure clean state
    os.environ['TESTING'] = 'true'
    yield
    # Cleanup after test
    if 'TESTING' in os.environ:
        del os.environ['TESTING']

# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )

# Skip tests based on missing dependencies
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle missing dependencies."""
    skip_playwright = pytest.mark.skip(reason="Playwright not installed")
    skip_httpx = pytest.mark.skip(reason="httpx not installed")
    
    for item in items:
        # Skip Playwright tests if not available
        try:
            import playwright
        except ImportError:
            if "playwright" in str(item.fspath).lower() or "e2e" in str(item.fspath):
                item.add_marker(skip_playwright)
                
        # Skip httpx tests if not available
        try:
            import httpx
        except ImportError:
            if "httpx" in str(item.nodeid) or "api" in str(item.fspath).lower():
                item.add_marker(skip_httpx)

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_battery_state(soc=0.5, soh=0.98, temperature=25.0):
        """Create a battery state for testing."""
        try:
            from energy_ml.simulator.battery_physics import BatteryState
            return BatteryState(
                soc=soc,
                soh=soh,
                temperature_c=temperature,
                cycles_completed=100.0,
                current_power_kw=0.0,
                voltage=48.0,
                internal_resistance=0.05
            )
        except ImportError:
            return None
    
    @staticmethod 
    def create_control_action(command="charge", power=2.5):
        """Create a control action for testing."""
        try:
            from energy_ml.control.inverter_controller import ControlAction, ControlCommand
            from datetime import datetime
            
            return ControlAction(
                command=ControlCommand(command),
                power_kw=power,
                reason="Test action",
                user_id="test",
                timestamp=datetime.now()
            )
        except ImportError:
            return None

# Make factory available as fixture
@pytest.fixture
def test_data_factory():
    """Test data factory fixture."""
    return TestDataFactory()

# Performance test helpers
@pytest.fixture
def performance_timer():
    """Timer for performance tests."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.time()
            
        def stop(self):
            self.end_time = time.time()
            
        @property
        def elapsed(self):
            if self.start_time is None or self.end_time is None:
                return None
            return self.end_time - self.start_time
            
    return Timer()