"""
Phase 1: Model Registry and Deployment Pipeline
Production ML model management with versioning, staging, and health checks
"""

import logging
import pickle
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import shutil

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)

@dataclass
class ModelVersion:
    """Model version metadata for registry"""
    version_id: str
    model_name: str
    algorithm: str
    created_at: datetime
    performance_metrics: Dict[str, float]
    feature_schema: List[str]
    model_size_bytes: int
    deployment_stage: str  # development, staging, production
    health_status: str  # healthy, degraded, failed
    validation_results: Dict[str, Any]
    artifacts_path: Path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'version_id': self.version_id,
            'model_name': self.model_name,
            'algorithm': self.algorithm,
            'created_at': self.created_at.isoformat(),
            'performance_metrics': self.performance_metrics,
            'feature_schema': self.feature_schema,
            'model_size_bytes': self.model_size_bytes,
            'deployment_stage': self.deployment_stage,
            'health_status': self.health_status,
            'validation_results': self.validation_results,
            'artifacts_path': str(self.artifacts_path)
        }


class ModelRegistry:
    """Production model registry with versioning and deployment management"""
    
    def __init__(self, registry_path: str = "energy_ml/mlops/registry"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        self.models_path = self.registry_path / "models"
        self.metadata_path = self.registry_path / "metadata"
        self.staging_path = self.registry_path / "staging"
        
        for path in [self.models_path, self.metadata_path, self.staging_path]:
            path.mkdir(exist_ok=True)
            
        self.registry_index = self._load_registry_index()
        
    def register_model(self, 
                      model: Any,
                      model_name: str,
                      algorithm: str,
                      performance_metrics: Dict[str, float],
                      feature_schema: List[str],
                      validation_data: Optional[Dict[str, Any]] = None) -> ModelVersion:
        """Register new model version in registry
        
        Args:
            model: Trained ML model (XGBoost, sklearn, etc.)
            model_name: Name identifier for model family
            algorithm: Algorithm type (xgboost, lightgbm, etc.)
            performance_metrics: Validation metrics (MAPE, RMSE, etc.)
            feature_schema: List of expected feature names
            validation_data: Optional validation results
            
        Returns:
            ModelVersion object with metadata
        """
        # Generate version ID based on model hash and timestamp
        model_bytes = pickle.dumps(model)
        model_hash = hashlib.md5(model_bytes).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        version_id = f"{model_name}-{timestamp}-{model_hash}"
        
        # Create model artifacts directory
        artifacts_path = self.models_path / version_id
        artifacts_path.mkdir(exist_ok=True)
        
        # Save model artifacts
        model_file = artifacts_path / "model.joblib"
        metadata_file = artifacts_path / "metadata.json"
        
        # Save model
        joblib.dump(model, model_file)
        
        # Run health checks
        health_status, validation_results = self._run_health_checks(
            model, feature_schema, validation_data
        )
        
        # Create version metadata
        model_version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            algorithm=algorithm,
            created_at=datetime.now(),
            performance_metrics=performance_metrics,
            feature_schema=feature_schema,
            model_size_bytes=len(model_bytes),
            deployment_stage="development",
            health_status=health_status,
            validation_results=validation_results,
            artifacts_path=artifacts_path
        )
        
        # Save metadata
        with open(metadata_file, 'w') as f:
            json.dump(model_version.to_dict(), f, indent=2)
            
        # Update registry index
        if model_name not in self.registry_index:
            self.registry_index[model_name] = []
            
        self.registry_index[model_name].append({
            'version_id': version_id,
            'created_at': model_version.created_at.isoformat(),
            'stage': 'development',
            'health': health_status,
            'metrics': performance_metrics
        })
        
        self._save_registry_index()
        
        logger.info(f"Registered model version: {version_id}")
        return model_version
        
    def promote_to_staging(self, version_id: str) -> bool:
        """Promote model version to staging environment
        
        Args:
            version_id: Model version to promote
            
        Returns:
            Success status
        """
        model_version = self.get_model_version(version_id)
        if not model_version:
            raise ValueError(f"Model version not found: {version_id}")
            
        # Validate model meets staging criteria
        if not self._validate_staging_criteria(model_version):
            raise ValueError(f"Model {version_id} does not meet staging criteria")
            
        # Copy to staging area
        staging_path = self.staging_path / version_id
        if staging_path.exists():
            shutil.rmtree(staging_path)
            
        shutil.copytree(model_version.artifacts_path, staging_path)
        
        # Update deployment stage
        model_version.deployment_stage = "staging"
        self._update_model_metadata(model_version)
        
        logger.info(f"Promoted model to staging: {version_id}")
        return True
        
    def deploy_to_production(self, 
                           version_id: str,
                           canary_percentage: float = 10.0) -> bool:
        """Deploy model version to production with canary release
        
        Args:
            version_id: Model version to deploy
            canary_percentage: Percentage of traffic for canary (0-100)
            
        Returns:
            Success status
        """
        model_version = self.get_model_version(version_id)
        if not model_version:
            raise ValueError(f"Model version not found: {version_id}")
            
        if model_version.deployment_stage != "staging":
            raise ValueError(f"Model must be in staging before production deployment")
            
        # Validate production criteria
        if not self._validate_production_criteria(model_version):
            raise ValueError(f"Model {version_id} does not meet production criteria")
            
        # Create production symlink
        production_link = self.models_path / "production"
        if production_link.exists():
            production_link.unlink()
            
        production_link.symlink_to(model_version.artifacts_path, target_is_directory=True)
        
        # Update deployment stage
        model_version.deployment_stage = "production"
        self._update_model_metadata(model_version)
        
        # Create canary deployment record
        canary_config = {
            'version_id': version_id,
            'percentage': canary_percentage,
            'deployed_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        canary_file = self.registry_path / "canary_config.json"
        with open(canary_file, 'w') as f:
            json.dump(canary_config, f, indent=2)
        
        logger.info(f"Deployed model to production: {version_id} (canary: {canary_percentage}%)")
        return True
        
    def get_production_model(self) -> Optional[Any]:
        """Load current production model
        
        Returns:
            Loaded production model or None if not found
        """
        production_link = self.models_path / "production"
        if not production_link.exists():
            logger.warning("No production model deployed")
            return None
            
        model_file = production_link / "model.joblib"
        if not model_file.exists():
            logger.error("Production model file missing")
            return None
            
        try:
            return joblib.load(model_file)
        except Exception as e:
            logger.error(f"Failed to load production model: {e}")
            return None
            
    def get_model_version(self, version_id: str) -> Optional[ModelVersion]:
        """Get model version metadata
        
        Args:
            version_id: Version identifier
            
        Returns:
            ModelVersion object or None if not found
        """
        metadata_file = self.models_path / version_id / "metadata.json"
        if not metadata_file.exists():
            return None
            
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
                
            metadata['created_at'] = datetime.fromisoformat(metadata['created_at'])
            metadata['artifacts_path'] = Path(metadata['artifacts_path'])
            
            return ModelVersion(**metadata)
        except Exception as e:
            logger.error(f"Failed to load model version {version_id}: {e}")
            return None
            
    def list_model_versions(self, 
                          model_name: str,
                          stage: Optional[str] = None) -> List[ModelVersion]:
        """List all versions of a model
        
        Args:
            model_name: Model name to filter by
            stage: Optional deployment stage filter
            
        Returns:
            List of ModelVersion objects
        """
        if model_name not in self.registry_index:
            return []
            
        versions = []
        for version_info in self.registry_index[model_name]:
            version = self.get_model_version(version_info['version_id'])
            if version and (stage is None or version.deployment_stage == stage):
                versions.append(version)
                
        return sorted(versions, key=lambda x: x.created_at, reverse=True)
        
    def cleanup_old_versions(self, 
                           model_name: str,
                           keep_versions: int = 5) -> int:
        """Clean up old model versions, keeping most recent ones
        
        Args:
            model_name: Model name to clean up
            keep_versions: Number of versions to keep
            
        Returns:
            Number of versions deleted
        """
        versions = self.list_model_versions(model_name)
        if len(versions) <= keep_versions:
            return 0
            
        # Keep production, staging, and most recent development versions
        protected_versions = set()
        for version in versions:
            if version.deployment_stage in ['production', 'staging']:
                protected_versions.add(version.version_id)
                
        # Keep most recent development versions
        dev_versions = [v for v in versions if v.deployment_stage == 'development']
        for version in dev_versions[:keep_versions-len(protected_versions)]:
            protected_versions.add(version.version_id)
            
        # Delete unprotected versions
        deleted_count = 0
        for version in versions:
            if version.version_id not in protected_versions:
                try:
                    shutil.rmtree(version.artifacts_path)
                    deleted_count += 1
                    logger.info(f"Deleted old model version: {version.version_id}")
                except Exception as e:
                    logger.error(f"Failed to delete version {version.version_id}: {e}")
                    
        # Update registry index
        self.registry_index[model_name] = [
            v for v in self.registry_index[model_name]
            if v['version_id'] in protected_versions
        ]
        self._save_registry_index()
        
        return deleted_count
        
    def _run_health_checks(self, 
                          model: Any,
                          feature_schema: List[str],
                          validation_data: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """Run model health checks
        
        Args:
            model: Model to check
            feature_schema: Expected feature names
            validation_data: Optional validation dataset
            
        Returns:
            Tuple of (health_status, validation_results)
        """
        results = {}
        
        try:
            # Check if model is callable
            if not hasattr(model, 'predict'):
                return "failed", {"error": "Model missing predict method"}
                
            # Test prediction with dummy data
            dummy_features = np.random.random((1, len(feature_schema)))
            pred = model.predict(dummy_features)
            
            results['dummy_prediction'] = float(pred[0]) if hasattr(pred, '__getitem__') else float(pred)
            
            # Validate prediction format
            if np.isnan(results['dummy_prediction']) or np.isinf(results['dummy_prediction']):
                return "failed", {"error": "Model produces invalid predictions", "results": results}
                
            # Check feature importance (for tree models)
            if hasattr(model, 'feature_importances_'):
                importance_dict = {
                    feature: float(importance) 
                    for feature, importance in zip(feature_schema, model.feature_importances_)
                }
                results['feature_importance'] = importance_dict
                
                # Warn if any feature has zero importance
                zero_importance = [f for f, imp in importance_dict.items() if imp == 0]
                if zero_importance:
                    results['warnings'] = f"Features with zero importance: {zero_importance}"
                    
            # Performance validation if data provided
            if validation_data:
                X_val = validation_data.get('X')
                y_val = validation_data.get('y')
                
                if X_val is not None and y_val is not None:
                    y_pred = model.predict(X_val)
                    
                    mape = mean_absolute_percentage_error(y_val, y_pred)
                    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
                    
                    results['validation_mape'] = float(mape)
                    results['validation_rmse'] = float(rmse)
                    
                    # Health status based on validation performance
                    if mape > 0.15:  # >15% error
                        return "degraded", results
                        
            return "healthy", results
            
        except Exception as e:
            return "failed", {"error": str(e), "results": results}
            
    def _validate_staging_criteria(self, model_version: ModelVersion) -> bool:
        """Validate model meets staging deployment criteria"""
        criteria = []
        
        # Health check
        criteria.append(model_version.health_status == "healthy")
        
        # Performance criteria
        mape = model_version.performance_metrics.get('mape', float('inf'))
        criteria.append(mape < 0.12)  # <12% error for staging
        
        # Model size reasonable
        criteria.append(model_version.model_size_bytes < 50 * 1024 * 1024)  # <50MB
        
        # Feature schema not empty
        criteria.append(len(model_version.feature_schema) > 0)
        
        return all(criteria)
        
    def _validate_production_criteria(self, model_version: ModelVersion) -> bool:
        """Validate model meets production deployment criteria"""
        criteria = []
        
        # All staging criteria
        criteria.append(self._validate_staging_criteria(model_version))
        
        # Stricter performance for production
        mape = model_version.performance_metrics.get('mape', float('inf'))
        criteria.append(mape < 0.10)  # <10% error for production
        
        # Validation results exist
        criteria.append('validation_mape' in model_version.validation_results)
        
        # Model not too old (within 30 days)
        age = datetime.now() - model_version.created_at
        criteria.append(age < timedelta(days=30))
        
        return all(criteria)
        
    def _load_registry_index(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load registry index from disk"""
        index_file = self.registry_path / "index.json"
        if not index_file.exists():
            return {}
            
        try:
            with open(index_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load registry index: {e}")
            return {}
            
    def _save_registry_index(self):
        """Save registry index to disk"""
        index_file = self.registry_path / "index.json"
        try:
            with open(index_file, 'w') as f:
                json.dump(self.registry_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry index: {e}")
            
    def _update_model_metadata(self, model_version: ModelVersion):
        """Update model metadata file"""
        metadata_file = model_version.artifacts_path / "metadata.json"
        try:
            with open(metadata_file, 'w') as f:
                json.dump(model_version.to_dict(), f, indent=2)
                
            # Update registry index
            for model_versions in self.registry_index.values():
                for version_info in model_versions:
                    if version_info['version_id'] == model_version.version_id:
                        version_info['stage'] = model_version.deployment_stage
                        version_info['health'] = model_version.health_status
                        break
                        
            self._save_registry_index()
            
        except Exception as e:
            logger.error(f"Failed to update model metadata: {e}")


# Singleton registry instance
_registry_instance = None

def get_model_registry() -> ModelRegistry:
    """Get global model registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry()
    return _registry_instance