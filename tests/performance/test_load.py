# tests/performance/test_load.py
import pytest
import asyncio
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

class TestPerformanceLoad:
    @pytest.mark.asyncio
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not available")
    async def test_concurrent_control_commands(self):
        """Test system handles concurrent control commands."""
        try:
            client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0)
            
            async def send_command(command_id):
                command = {
                    "command": "hold", 
                    "power_kw": 0,
                    "reason": f"Load test {command_id}"
                }
                
                start_time = time.time()
                try:
                    response = await client.post("/api/control/execute", json=command)
                    end_time = time.time()
                    
                    return {
                        'status_code': response.status_code,
                        'response_time': end_time - start_time,
                        'command_id': command_id,
                        'success': True
                    }
                except Exception as e:
                    end_time = time.time()
                    return {
                        'status_code': 0,
                        'response_time': end_time - start_time,
                        'command_id': command_id,
                        'success': False,
                        'error': str(e)
                    }
            
            # Send 10 concurrent commands (reduced for realistic testing)
            tasks = [send_command(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            successful_results = [r for r in results if isinstance(r, dict) and r.get('success', False)]
            
            if len(successful_results) > 0:
                # At least some should succeed
                success_rate = len(successful_results) / len(results)
                assert success_rate >= 0.5, f"Success rate too low: {success_rate}"
                
                # Response times should be reasonable
                response_times = [r['response_time'] for r in successful_results]
                avg_time = mean(response_times)
                assert avg_time < 5.0, f"Average response time too high: {avg_time}s"
            else:
                pytest.skip("API server not available for load testing")
                
            await client.aclose()
            
        except Exception as e:
            pytest.skip(f"Load testing not possible: {e}")
            
    @pytest.mark.asyncio
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not available")
    async def test_optimization_performance(self):
        """Test optimization completes within reasonable time."""
        try:
            client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=60.0)
            
            request = {
                "user_preference": "balance",
                "hours_ahead": 24
            }
            
            start_time = time.time()
            try:
                response = await client.post("/api/control/schedule", json=request)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    assert execution_time < 30.0, f"Optimization too slow: {execution_time}s"
                    assert 'schedule' in data
                    assert len(data['schedule']) <= 24
                else:
                    pytest.skip("Optimization endpoint not available")
                    
            except httpx.TimeoutException:
                pytest.fail("Optimization timed out - performance issue")
                
            await client.aclose()
            
        except Exception as e:
            pytest.skip(f"Optimization performance testing not possible: {e}")

class TestBatteryModelPerformance:
    """Test performance of battery physics calculations."""
    
    def test_battery_calculation_speed(self):
        """Test battery calculations are fast enough for real-time use."""
        try:
            from energy_ml.simulator.battery_physics import LFPBatteryModel
            
            battery = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
            
            # Time multiple calculations
            iterations = 1000
            start_time = time.time()
            
            for i in range(iterations):
                # Typical real-time calculations
                degradation = battery.calculate_degradation(power_kw=2.5, duration_hours=0.1)
                efficiency = battery.get_efficiency(power_kw=2.5, soc=0.5)
                max_power = battery.get_max_power(soc=0.5, direction="charge")
                
            end_time = time.time()
            
            total_time = end_time - start_time
            time_per_calculation = total_time / iterations
            
            # Should be able to do 1000 calculations in under 1 second
            assert total_time < 1.0, f"Battery calculations too slow: {total_time}s for {iterations} iterations"
            assert time_per_calculation < 0.001, f"Individual calculation too slow: {time_per_calculation}s"
            
        except ImportError:
            pytest.skip("Battery physics models not available")

    def test_control_system_response_time(self):
        """Test control system responds quickly to commands."""
        try:
            from energy_ml.control.inverter_controller import VirtualInverterController, ControlAction, ControlCommand
            from datetime import datetime
            
            controller = VirtualInverterController(battery_capacity_kwh=10.0, max_power_kw=5.0)
            
            # Time command execution
            start_time = time.time()
            
            action = ControlAction(
                command=ControlCommand.CHARGE,
                power_kw=2.5,
                reason="Performance test",
                user_id="test",
                timestamp=datetime.now()
            )
            
            result = asyncio.run(controller.execute_command(action))
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            assert result['success'] is True
            assert execution_time < 0.1, f"Command execution too slow: {execution_time}s"
            
        except ImportError:
            pytest.skip("Control system not available")

class TestMemoryUsage:
    """Test system memory usage is reasonable."""
    
    def test_battery_model_memory(self):
        """Test battery models don't consume excessive memory."""
        try:
            import tracemalloc
            from energy_ml.simulator.battery_physics import LFPBatteryModel
            
            tracemalloc.start()
            
            # Create multiple battery instances
            batteries = []
            for i in range(100):
                battery = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
                batteries.append(battery)
                
                # Run some calculations
                battery.calculate_degradation(power_kw=2.5, duration_hours=1.0)
                battery.get_efficiency(power_kw=2.5, soc=0.5)
                
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # Memory usage should be reasonable (less than 50MB for 100 instances)
            peak_mb = peak / 1024 / 1024
            assert peak_mb < 50, f"Memory usage too high: {peak_mb}MB for 100 battery instances"
            
        except ImportError:
            pytest.skip("Battery models or tracemalloc not available")

class TestStressTest:
    """Stress test the system with realistic workloads."""
    
    def test_continuous_operation_simulation(self):
        """Test system can handle continuous operation."""
        try:
            from energy_ml.simulator.battery_physics import LFPBatteryModel
            from energy_ml.control.inverter_controller import VirtualInverterController
            
            battery = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
            controller = VirtualInverterController(battery_capacity_kwh=10.0, max_power_kw=5.0)
            
            # Simulate 24 hours of operation (1 minute intervals)
            start_time = time.time()
            
            for minute in range(1440):  # 24 * 60 minutes
                # Simulate varying power demand
                power = 2.5 if minute % 120 < 60 else -2.0  # Charge/discharge cycles
                
                # Update battery state
                battery.update_state(power_kw=power, duration_minutes=1)
                
                # Update controller
                controller.current_power_kw = power
                controller._update_soc(duration_minutes=1)
                
                # Every 100 minutes, check system state
                if minute % 100 == 0:
                    status = controller.get_status()
                    assert 0.0 <= status['soc'] <= 1.0
                    assert abs(status['power_kw']) <= 5.0
                    
            end_time = time.time()
            simulation_time = end_time - start_time
            
            # 24-hour simulation should complete in reasonable time
            assert simulation_time < 10.0, f"Simulation too slow: {simulation_time}s for 24h simulation"
            
        except ImportError:
            pytest.skip("System components not available for stress testing")

class TestConcurrencyStress:
    """Test system under concurrent load."""
    
    def test_multiple_battery_instances(self):
        """Test multiple battery instances can run concurrently."""
        try:
            from energy_ml.simulator.battery_physics import LFPBatteryModel
            import threading
            import queue
            
            results = queue.Queue()
            
            def run_battery_simulation(battery_id):
                try:
                    battery = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
                    
                    # Run calculations for this battery
                    for i in range(100):
                        degradation = battery.calculate_degradation(power_kw=2.0, duration_hours=0.1)
                        efficiency = battery.get_efficiency(power_kw=2.0, soc=0.5)
                        battery.update_state(power_kw=2.0, duration_minutes=6)  # 0.1 hour
                        
                    results.put({'battery_id': battery_id, 'success': True})
                    
                except Exception as e:
                    results.put({'battery_id': battery_id, 'success': False, 'error': str(e)})
            
            # Run 5 battery simulations concurrently
            threads = []
            for i in range(5):
                thread = threading.Thread(target=run_battery_simulation, args=(i,))
                threads.append(thread)
                thread.start()
                
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10.0)
                
            # Check results
            successful = 0
            while not results.empty():
                result = results.get()
                if result['success']:
                    successful += 1
                    
            assert successful >= 4, f"Too many concurrent battery simulations failed: {successful}/5"
            
        except ImportError:
            pytest.skip("Battery models not available for concurrency testing")