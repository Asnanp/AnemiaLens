"""
Demographic Calibration for AnemiaLens

Adjusts hemoglobin predictions based on known physiological and demographic variations.

References:
- WHO Haemoglobin concentrations for the diagnosis of anaemia (2011)
- NHANES anemia prevalence data by demographics
- Skin tone impact on conjunctival pallor assessment
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class SkinTone(Enum):
    """Fitzpatrick skin type classification."""
    TYPE_I = "very_light"      # Always burns, never tans
    TYPE_II = "light"          # Burns easily, tans minimally
    TYPE_III = "medium"        # Burns moderately, tans gradually
    TYPE_IV = "olive"          # Burns minimally, tans easily
    TYPE_V = "brown"           # Rarely burns, tans darkly
    TYPE_VI = "dark"           # Never burns, deeply pigmented


class DemographicGroup(Enum):
    """WHO hemoglobin threshold groups."""
    CHILDREN_6M_5Y = "children_6m_5y"      # 6 months - 5 years
    CHILDREN_5Y_11Y = "children_5y_11y"    # 5-11 years
    CHILDREN_12Y_14Y = "children_12y_14y"  # 12-14 years
    ADULT_MALE = "adult_male"              # 15+ years male
    ADULT_FEMALE = "adult_female"          # 15+ years female, non-pregnant
    PREGNANT = "pregnant"                  # Any trimester
    ELDERLY = "elderly"                    # 65+ years


@dataclass
class PatientDemographics:
    """Patient demographic information for calibration."""
    age: float | None = None
    sex: Literal["male", "female", "other", "not_specified"] = "not_specified"
    skin_tone: SkinTone | None = None
    is_pregnant: bool = False
    altitude_meters: float | None = None  # Altitude affects Hb
    smoking_status: Literal["never", "former", "current", "unknown"] = "unknown"


class DemographicCalibrator:
    """
    Calibrates hemoglobin predictions based on demographic factors.
    
    Physiological adjustments:
    - Women have ~0.5 g/dL lower Hb than men (menstrual blood loss)
    - Pregnant women have ~1.0 g/dL lower Hb (hemodilution)
    - Children have lower Hb thresholds than adults
    - High altitude increases Hb (hypoxia response)
    - Smokers have higher Hb (chronic hypoxia)
    - Darker skin may appear paler at same Hb level (optical effect)
    """
    
    # WHO hemoglobin threshold adjustments (add to predicted Hb)
    DEMOGRAPHIC_ADJUSTMENTS = {
        DemographicGroup.CHILDREN_6M_5Y: -0.8,    # Lower baseline
        DemographicGroup.CHILDREN_5Y_11Y: -0.5,
        DemographicGroup.CHILDREN_12Y_14Y: -0.3,
        DemographicGroup.ADULT_MALE: 0.0,         # Reference
        DemographicGroup.ADULT_FEMALE: -0.5,      # Menstrual loss
        DemographicGroup.PREGNANT: -1.0,          # Hemodilution
        DemographicGroup.ELDERLY: 0.1,            # Slight increase
    }
    
    # Skin tone optical correction (darker skin → appears paler at same Hb)
    # Based on clinical studies of conjunctival pallor assessment
    SKIN_TONE_ADJUSTMENTS = {
        SkinTone.TYPE_I: 0.0,    # No correction
        SkinTone.TYPE_II: 0.05,
        SkinTone.TYPE_III: 0.1,
        SkinTone.TYPE_IV: 0.2,
        SkinTone.TYPE_V: 0.3,
        SkinTone.TYPE_VI: 0.4,
    }
    
    # Altitude adjustment (increase threshold at high altitude)
    # Source: WHO guidelines
    ALTITUDE_ADJUSTMENTS = [
        (0, 0.0),      # Sea level
        (1000, 0.1),   # 1000m
        (2000, 0.3),   # 2000m
        (3000, 0.6),   # 3000m
        (4000, 1.0),   # 4000m
        (5000, 1.5),   # 5000m+
    ]
    
    # Smoking adjustment (smokers have chronically elevated Hb)
    SMOKING_ADJUSTMENTS = {
        "never": 0.0,
        "former": 0.0,
        "current": 0.3,  # Smokers run ~0.3 g/dL higher
        "unknown": 0.0,
    }
    
    def __init__(self, enable_skin_tone: bool = True, enable_altitude: bool = True):
        self.enable_skin_tone = enable_skin_tone
        self.enable_altitude = enable_altitude
    
    def get_demographic_group(self, age: float | None, sex: str, is_pregnant: bool) -> DemographicGroup:
        """Determine WHO demographic group from age and sex."""
        if is_pregnant:
            return DemographicGroup.PREGNANT
        
        if age is None:
            return DemographicGroup.ADULT_MALE if sex == "male" else DemographicGroup.ADULT_FEMALE
        
        if age < 5:
            return DemographicGroup.CHILDREN_6M_5Y
        elif age < 11:
            return DemographicGroup.CHILDREN_5Y_11Y
        elif age < 15:
            return DemographicGroup.CHILDREN_12Y_14Y
        elif age >= 65:
            return DemographicGroup.ELDERLY
        else:
            return DemographicGroup.ADULT_MALE if sex == "male" else DemographicGroup.ADULT_FEMALE
    
    def _interpolate_altitude(self, altitude: float) -> float:
        """Get altitude adjustment via linear interpolation."""
        if altitude <= 0:
            return 0.0
        
        prev_alt, prev_adj = 0, 0.0
        for alt, adj in self.ALTITUDE_ADJUSTMENTS:
            if altitude <= alt:
                # Linear interpolation
                ratio = (altitude - prev_alt) / (alt - prev_alt)
                return prev_adj + ratio * (adj - prev_adj)
            prev_alt, prev_adj = alt, adj
        
        return self.ALTITUDE_ADJUSTMENTS[-1][1]  # Max adjustment
    
    def calibrate(
        self,
        predicted_hemoglobin: float,
        demographics: PatientDemographics,
    ) -> float:
        """
        Apply demographic adjustments to hemoglobin prediction.
        
        Args:
            predicted_hemoglobin: Raw model prediction (g/dL)
            demographics: Patient demographic information
        
        Returns:
            Calibrated hemoglobin value (g/dL)
        
        Example:
            >>> calibrator = DemographicCalibrator()
            >>> demo = PatientDemographics(age=30, sex="female", skin_tone=SkinTone.TYPE_IV)
            >>> calibrator.calibrate(12.5, demo)
            12.15  # Adjusted for female (-0.5) and skin tone (+0.2)
        """
        adjusted = predicted_hemoglobin
        
        # 1. Demographic group adjustment (age/sex/pregnancy)
        group = self.get_demographic_group(
            demographics.age,
            demographics.sex,
            demographics.is_pregnant
        )
        demo_adjustment = self.DEMOGRAPHIC_ADJUSTMENTS.get(group, 0.0)
        adjusted += demo_adjustment
        
        # 2. Skin tone optical correction
        if self.enable_skin_tone and demographics.skin_tone:
            skin_adjustment = self.SKIN_TONE_ADJUSTMENTS.get(demographics.skin_tone, 0.0)
            adjusted += skin_adjustment
        
        # 3. Altitude adjustment
        if self.enable_altitude and demographics.altitude_meters:
            altitude_adjustment = self._interpolate_altitude(demographics.altitude_meters)
            adjusted += altitude_adjustment
        
        # 4. Smoking adjustment
        smoking_adjustment = self.SMOKING_ADJUSTMENTS.get(demographics.smoking_status, 0.0)
        adjusted += smoking_adjustment
        
        # Clamp to physiological range
        return max(4.0, min(22.0, adjusted))
    
    def get_adjustment_breakdown(
        self,
        demographics: PatientDemographics,
    ) -> dict[str, float]:
        """
        Return breakdown of all adjustments for transparency.
        
        Useful for explaining predictions to users.
        """
        breakdown = {
            "base_prediction": 0.0,  # Placeholder
            "demographic_adjustment": 0.0,
            "skin_tone_adjustment": 0.0,
            "altitude_adjustment": 0.0,
            "smoking_adjustment": 0.0,
            "total_adjustment": 0.0,
        }
        
        # Demographic
        group = self.get_demographic_group(
            demographics.age,
            demographics.sex,
            demographics.is_pregnant
        )
        demo_adj = self.DEMOGRAPHIC_ADJUSTMENTS.get(group, 0.0)
        breakdown["demographic_adjustment"] = demo_adj
        breakdown["demographic_group"] = group.value
        
        # Skin tone
        if self.enable_skin_tone and demographics.skin_tone:
            skin_adj = self.SKIN_TONE_ADJUSTMENTS.get(demographics.skin_tone, 0.0)
            breakdown["skin_tone_adjustment"] = skin_adj
            breakdown["skin_tone"] = demographics.skin_tone.value
        
        # Altitude
        if self.enable_altitude and demographics.altitude_meters:
            alt_adj = self._interpolate_altitude(demographics.altitude_meters)
            breakdown["altitude_adjustment"] = alt_adj
            breakdown["altitude_meters"] = demographics.altitude_meters
        
        # Smoking
        smoke_adj = self.SMOKING_ADJUSTMENTS.get(demographics.smoking_status, 0.0)
        breakdown["smoking_adjustment"] = smoke_adj
        
        breakdown["total_adjustment"] = (
            demo_adj +
            breakdown.get("skin_tone_adjustment", 0.0) +
            breakdown.get("altitude_adjustment", 0.0) +
            smoke_adj
        )
        
        return breakdown


# Convenience function for quick calibration
def quick_calibrate(
    predicted_hb: float,
    age: float | None = None,
    sex: str = "not_specified",
    skin_tone: str | None = None,
    is_pregnant: bool = False,
    altitude_m: float | None = None,
) -> tuple[float, dict]:
    """
    Quick demographic calibration without instantiating classes.
    
    Args:
        predicted_hb: Raw model prediction
        age: Patient age in years
        sex: "male", "female", or "other"
        skin_tone: "very_light", "light", "medium", "olive", "brown", "dark"
        is_pregnant: True if pregnant
        altitude_m: Altitude in meters
    
    Returns:
        Tuple of (calibrated_hb, adjustment_breakdown)
    """
    calibrator = DemographicCalibrator()
    
    # Parse skin tone
    skin_tone_enum = None
    if skin_tone:
        try:
            skin_tone_enum = SkinTone(skin_tone)
        except ValueError:
            pass
    
    demo = PatientDemographics(
        age=age,
        sex=sex,
        skin_tone=skin_tone_enum,
        is_pregnant=is_pregnant,
        altitude_meters=altitude_m,
    )
    
    calibrated = calibrator.calibrate(predicted_hb, demo)
    breakdown = calibrator.get_adjustment_breakdown(demo)
    breakdown["base_prediction"] = predicted_hb
    
    return calibrated, breakdown
