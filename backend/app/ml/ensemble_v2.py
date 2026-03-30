"""
Production Ensemble for AnemiaLens

Combines multiple models for improved accuracy and uncertainty estimation.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from typing import Literal

from app.schemas import QualityAssessment, PatientProfileInput


class ProductionEnsemble:
    """
    Production-ready ensemble combining:
    1. archive-fusion-v8-clinical-robust (tree-based ensemble)
    2. efficientnet-b0 (deep learning vision model)
    
    Future additions:
    3. densenet121 (additional DL architecture)
    4. vision transformer (ViT)
    
    Ensemble strategy:
    - Weighted average based on model confidence
    - Disagreement-based uncertainty inflation
    - Quality-aware model selection
    """
    
    def __init__(
        self,
        v8_model: object | None = None,
        efficientnet_model: object | None = None,
        enable_ensemble: bool = True,
        ensemble_weights: dict[str, float] | None = None,
    ):
        self.v8_model = v8_model
        self.efficientnet_model = efficientnet_model
        self.enable_ensemble = enable_ensemble
        
        # Default weights (can be tuned on validation set)
        self.weights = ensemble_weights or {
            "v8": 0.55,
            "efficientnet": 0.45,
        }
        
        # Normalize weights
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}
    
    def predict(
        self,
        image: Image.Image,
        quality: QualityAssessment,
        patient_profile: PatientProfileInput | None = None,
    ) -> dict:
        """
        Make ensemble prediction.
        
        Args:
            image: Input conjunctiva image
            quality: Image quality assessment
            patient_profile: Optional patient demographics
        
        Returns:
            Dictionary with ensemble prediction and metadata
        """
        predictions = []
        
        # Get V8 prediction
        if self.v8_model is not None:
            try:
                v8_pred = self.v8_model.predict(
                    image,
                    quality,
                    patient_profile,
                )
                predictions.append(("v8", v8_pred))
            except Exception as e:
                print(f"V8 model failed: {e}")
        
        # Get EfficientNet prediction
        if self.efficientnet_model is not None:
            try:
                eff_pred = self.efficientnet_model.predict(image)
                predictions.append(("efficientnet", eff_pred))
            except Exception as e:
                print(f"EfficientNet model failed: {e}")
        
        # Handle edge cases
        if len(predictions) == 0:
            return self._fallback_prediction()
        
        if len(predictions) == 1:
            model_name, pred = predictions[0]
            return {
                **pred,
                "ensemble_used": False,
                "single_model": model_name,
            }
        
        # Ensemble fusion
        return self._fuse_predictions(predictions, quality)
    
    def _fuse_predictions(
        self,
        predictions: list[tuple[str, dict]],
        quality: QualityAssessment,
    ) -> dict:
        """
        Fuse multiple model predictions with quality-aware weighting.
        """
        # Extract hemoglobin values
        hb_values = []
        risk_values = []
        uncertainty_values = []
        model_weights = []
        
        for model_name, pred in predictions:
            hb = pred.get("predicted_hemoglobin")
            if hb is not None:
                hb_values.append(hb)
                risk_values.append(pred.get("anemia_risk", 0.5))
                uncertainty_values.append(pred.get("uncertainty", 0.3))
                
                # Weight by model priority and quality
                base_weight = self.weights.get(model_name, 0.5)
                quality_weight = self._model_quality_weight(model_name, quality)
                model_weights.append(base_weight * quality_weight)
        
        if len(hb_values) == 0:
            return self._fallback_prediction()
        
        # Normalize weights
        weight_sum = sum(model_weights)
        if weight_sum > 0:
            model_weights = [w/weight_sum for w in model_weights]
        else:
            model_weights = [1.0/len(hb_values)] * len(hb_values)
        
        # Weighted average for hemoglobin
        ensemble_hb = sum(
            hb * w for hb, w in zip(hb_values, model_weights)
        )
        
        # Weighted average for risk
        ensemble_risk = sum(
            risk * w for risk, w in zip(risk_values, model_weights)
        )
        
        # Average uncertainty
        ensemble_uncertainty = np.mean(uncertainty_values)
        
        # Disagreement-based uncertainty inflation
        if len(hb_values) > 1:
            hb_std = np.std(hb_values)
            risk_std = np.std(risk_values)
            
            # Inflate uncertainty if models disagree
            disagreement_penalty = (
                hb_std * 0.3 +  # Hemoglobin disagreement
                risk_std * 0.5  # Risk disagreement
            )
            ensemble_uncertainty = min(
                0.95,
                ensemble_uncertainty + disagreement_penalty
            )
        
        # Model agreement metric
        agreement = 1.0 - (np.std(hb_values) / 5.0) if len(hb_values) > 1 else 1.0
        agreement = max(0.0, min(1.0, agreement))
        
        return {
            "predicted_hemoglobin": round(ensemble_hb, 2),
            "anemia_risk": round(ensemble_risk, 4),
            "uncertainty": round(ensemble_uncertainty, 4),
            "ensemble_used": True,
            "model_agreement": round(agreement, 3),
            "models_contributed": [name for name, _ in predictions],
            "model_weights": dict(zip([name for name, _ in predictions], model_weights)),
            "hemoglobin_range": {
                "min": min(hb_values),
                "max": max(hb_values),
                "std": np.std(hb_values),
            },
        }
    
    def _model_quality_weight(
        self,
        model_name: str,
        quality: QualityAssessment,
    ) -> float:
        """
        Adjust model weight based on image quality.
        
        Some models are more robust to certain quality issues.
        """
        base_weight = 1.0
        
        # V8 model is sensitive to blur
        if model_name == "v8" and quality.blur_score < 60:
            base_weight *= 0.7
        
        # EfficientNet is sensitive to lighting
        if model_name == "efficientnet":
            if quality.lighting_condition in ["glare_heavy", "shadow_heavy"]:
                base_weight *= 0.75
            if quality.brightness_score < 0.2 or quality.brightness_score > 0.8:
                base_weight *= 0.8
        
        return base_weight
    
    def _fallback_prediction(self) -> dict:
        """
        Return safe fallback when all models fail.
        """
        return {
            "predicted_hemoglobin": None,
            "anemia_risk": 0.5,
            "uncertainty": 0.9,
            "ensemble_used": False,
            "fallback": True,
            "fallback_reason": "All models failed",
        }


def create_production_ensemble(
    v8_model_path: str | None = None,
    efficientnet_path: str | None = None,
    enable: bool = True,
) -> ProductionEnsemble:
    """
    Factory function to create production ensemble with auto-loading.
    """
    v8_model = None
    efficientnet_model = None
    
    if enable:
        # Load V8 model
        if v8_model_path:
            try:
                import joblib
                v8_model = joblib.load(v8_model_path)
                print(f"Loaded V8 model: {v8_model.get('version', 'unknown')}")
            except Exception as e:
                print(f"Failed to load V8 model: {e}")
        
        # Load EfficientNet
        if efficientnet_path:
            try:
                import torch
                from app.ml.efficientnet_model import load_efficientnet_checkpoint
                efficientnet_bundle = load_efficientnet_checkpoint(efficientnet_path)
                efficientnet_model = EfficientNetWrapper(efficientnet_bundle)
                print(f"Loaded EfficientNet model")
            except Exception as e:
                print(f"Failed to load EfficientNet: {e}")
    
    return ProductionEnsemble(
        v8_model=v8_model,
        efficientnet_model=efficientnet_model,
        enable_ensemble=enable,
    )


class EfficientNetWrapper:
    """
    Wrapper to make EfficientNet prediction interface consistent.
    """
    
    def __init__(self, bundle: dict):
        self.bundle = bundle
        self.model = bundle.get("model")
        self.device = bundle.get("device", "cpu")
    
    def predict(self, image: Image.Image) -> dict:
        """
        Make EfficientNet prediction.
        """
        from app.ml.efficientnet_model import predict_with_efficientnet_model
        
        result = predict_with_efficientnet_model(
            self.bundle,
            image,
            mc_passes=4,
        )
        
        return {
            "predicted_hemoglobin": result.get("predicted_hemoglobin"),
            "anemia_risk": result.get("anemia_risk", 0.5),
            "uncertainty": result.get("uncertainty", 0.3),
        }
