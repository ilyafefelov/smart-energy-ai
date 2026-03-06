"""
Phase 1: Model Registry and Deployment Pipeline
Production ML model management with versioning, staging, and health checks
"""

import importlib.util
import logging
import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
import shutil
import sys

import joblib
import numpy as np
from xgboost import XGBRegressor

try:
    from energy_ml.mlops.model_registry_support import (
        build_registry_index_entry,
        evaluate_model_health,
        generate_version_id,
        load_model_version_metadata,
        model_version_to_dict,
        read_json_file,
        update_registry_index_entry,
        validate_production_criteria,
        validate_staging_criteria,
        write_json_file,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.mlops.model_registry_support"
    _SUPPORT_PATH = Path(__file__).with_name("model_registry_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load model registry support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    build_registry_index_entry = _SUPPORT_MODULE.build_registry_index_entry
    evaluate_model_health = _SUPPORT_MODULE.evaluate_model_health
    generate_version_id = _SUPPORT_MODULE.generate_version_id
    load_model_version_metadata = _SUPPORT_MODULE.load_model_version_metadata
    model_version_to_dict = _SUPPORT_MODULE.model_version_to_dict
    read_json_file = _SUPPORT_MODULE.read_json_file
    update_registry_index_entry = _SUPPORT_MODULE.update_registry_index_entry
    validate_production_criteria = _SUPPORT_MODULE.validate_production_criteria
    validate_staging_criteria = _SUPPORT_MODULE.validate_staging_criteria
    write_json_file = _SUPPORT_MODULE.write_json_file

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
        return model_version_to_dict(self)


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
        model_bytes = pickle.dumps(model)
        now = datetime.now()
        version_id = generate_version_id(model_name, model_bytes, now)
        
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
            created_at=now,
            performance_metrics=performance_metrics,
            feature_schema=feature_schema,
            model_size_bytes=len(model_bytes),
            deployment_stage="development",
            health_status=health_status,
            validation_results=validation_results,
            artifacts_path=artifacts_path
        )
        
        # Save metadata
        write_json_file(metadata_file, model_version.to_dict())
            
        # Update registry index
        if model_name not in self.registry_index:
            self.registry_index[model_name] = []

        self.registry_index[model_name].append(
            build_registry_index_entry(version_id, model_version.created_at, health_status, performance_metrics)
        )
        
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

            return ModelVersion(**load_model_version_metadata(metadata))
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
        return evaluate_model_health(model, feature_schema, validation_data)
            
    def _validate_staging_criteria(self, model_version: ModelVersion) -> bool:
        """Validate model meets staging deployment criteria"""
        return validate_staging_criteria(model_version)
        
    def _validate_production_criteria(self, model_version: ModelVersion) -> bool:
        """Validate model meets production deployment criteria"""
        return validate_production_criteria(model_version, datetime.now())
        
    def _load_registry_index(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load registry index from disk"""
        index_file = self.registry_path / "index.json"
        try:
            return read_json_file(index_file, {})
        except Exception as e:
            logger.error(f"Failed to load registry index: {e}")
            return {}
            
    def _save_registry_index(self):
        """Save registry index to disk"""
        index_file = self.registry_path / "index.json"
        try:
            write_json_file(index_file, self.registry_index)
        except Exception as e:
            logger.error(f"Failed to save registry index: {e}")
            
    def _update_model_metadata(self, model_version: ModelVersion):
        """Update model metadata file"""
        metadata_file = model_version.artifacts_path / "metadata.json"
        try:
            write_json_file(metadata_file, model_version.to_dict())
            self.registry_index = update_registry_index_entry(self.registry_index, model_version)
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