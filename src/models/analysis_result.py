"""
Analysis result models for Terrain Tunneling Calculator.

This module provides models for storing and presenting comprehensive
analysis results including volume calculations, cost estimates, and engineering insights.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import numpy as np
import math
from datetime import datetime

from models.volume_calculator import VolumeCalculationResult, ExcavationZone, MaterialType


class AnalysisType(Enum):
    """Types of analysis that can be performed."""
    VOLUME_CALCULATION = "volume_calculation"
    COST_ESTIMATION = "cost_estimation"
    STRUCTURAL_ANALYSIS = "structural_analysis"
    GRADIENT_ANALYSIS = "gradient_analysis"
    MATERIAL_ANALYSIS = "material_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    ENVIRONMENTAL_IMPACT = "environmental_impact"


class CostCategory(Enum):
    """Categories of construction costs."""
    EXCAVATION = "excavation"
    SUPPORT = "support"
    LINING = "lining"
    VENTILATION = "ventilation"
    EQUIPMENT = "equipment"
    LABOR = "labor"
    OVERHEAD = "overhead"
    CONTINGENCY = "contingency"


class RiskLevel(Enum):
    """Risk levels for construction projects."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CostEstimate:
    """Cost estimation for tunnel construction."""
    total_cost: float = 0.0
    excavation_cost: float = 0.0
    support_cost: float = 0.0
    lining_cost: float = 0.0
    ventilation_cost: float = 0.0
    equipment_cost: float = 0.0
    labor_cost: float = 0.0
    overhead_cost: float = 0.0
    contingency_cost: float = 0.0

    # Cost breakdown by category
    category_breakdown: Dict[str, float] = field(default_factory=dict)

    # Unit costs
    excavation_rate: float = 0.0  # Cost per cubic meter
    support_rate: float = 0.0      # Cost per meter
    lining_rate: float = 0.0        # Cost per square meter

    # Currency and units
    currency: str = "USD"
    cost_per_day: float = 0.0      # Daily construction cost
    total_days: int = 0

    def get_cost_breakdown_percentage(self) -> Dict[str, float]:
        """Get cost breakdown as percentages."""
        if self.total_cost == 0:
            return {}

        breakdown = {}
        for category, cost in self.category_breakdown.items():
            breakdown[category] = (cost / self.total_cost) * 100

        return breakdown

    def validate(self) -> bool:
        """Validate cost estimate data."""
        if self.total_cost < 0:
            return False

        # Check that categories sum to total
        category_sum = sum(self.category_breakdown.values())
        if abs(category_sum - self.total_cost) > 0.01 * self.total_cost:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert cost estimate to dictionary."""
        return {
            'total_cost': self.total_cost,
            'excavation_cost': self.excavation_cost,
            'support_cost': self.support_cost,
            'lining_cost': self.lining_cost,
            'ventilation_cost': self.ventilation_cost,
            'equipment_cost': self.equipment_cost,
            'labor_cost': self.labor_cost,
            'overhead_cost': self.overhead_cost,
            'contingency_cost': self.contingency_cost,
            'category_breakdown': self.category_breakdown,
            'breakdown_percentage': self.get_cost_breakdown_percentage(),
            'excavation_rate': self.excavation_rate,
            'support_rate': self.support_rate,
            'lining_rate': self.lining_rate,
            'currency': self.currency,
            'cost_per_day': self.cost_per_day,
            'total_days': self.total_days,
            'is_valid': self.validate()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CostEstimate':
        """Create cost estimate from dictionary."""
        return cls(
            total_cost=data.get('total_cost', 0.0),
            excavation_cost=data.get('excavation_cost', 0.0),
            support_cost=data.get('support_cost', 0.0),
            lining_cost=data.get('lining_cost', 0.0),
            ventilation_cost=data.get('ventilation_cost', 0.0),
            equipment_cost=data.get('equipment_cost', 0.0),
            labor_cost=data.get('labor_cost', 0.0),
            overhead_cost=data.get('overhead_cost', 0.0),
            contingency_cost=data.get('contingency_cost', 0.0),
            category_breakdown=data.get('category_breakdown', {}),
            excavation_rate=data.get('excavation_rate', 0.0),
            support_rate=data.get('support_rate', 0.0),
            lining_rate=data.get('lining_rate', 0.0),
            currency=data.get('currency', 'USD'),
            cost_per_day=data.get('cost_per_day', 0.0),
            total_days=data.get('total_days', 0)
        )


@dataclass
class StructuralAnalysis:
    """Structural analysis results for tunnel design."""
    tunnel_stability_rating: str = "unknown"
    rock_mass_rating: float = 0.0
    support_requirements: List[str] = field(default_factory=list)
    recommended_support_system: str = "unknown"
    deformation_estimate: float = 0.0
    safety_factor: float = 1.0
    monitoring_recommendations: List[str] = field(default_factory=list)
    max_stress: float = 0.0
    stress_distribution: Dict[str, float] = field(default_factory=dict)
    critical_sections: List[Tuple[float, float, str]] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate structural analysis data."""
        return (0.0 <= self.rock_mass_rating <= 100.0 and
                self.safety_factor > 0.0 and
                self.max_stress >= 0.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert structural analysis to dictionary."""
        return {
            'tunnel_stability_rating': self.tunnel_stability_rating,
            'rock_mass_rating': self.rock_mass_rating,
            'support_requirements': self.support_requirements,
            'recommended_support_system': self.recommended_support_system,
            'deformation_estimate': self.deformation_estimate,
            'safety_factor': self.safety_factor,
            'monitoring_recommendations': self.monitoring_recommendations,
            'max_stress': self.max_stress,
            'stress_distribution': self.stress_distribution,
            'critical_sections': self.critical_sections,
            'is_valid': self.validate()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuralAnalysis':
        """Create structural analysis from dictionary."""
        return cls(
            tunnel_stability_rating=data.get('tunnel_stability_rating', 'unknown'),
            rock_mass_rating=data.get('rock_mass_rating', 0.0),
            support_requirements=data.get('support_requirements', []),
            recommended_support_system=data.get('recommended_support_system', 'unknown'),
            deformation_estimate=data.get('deformation_estimate', 0.0),
            safety_factor=data.get('safety_factor', 1.0),
            monitoring_recommendations=data.get('monitoring_recommendations', []),
            max_stress=data.get('max_stress', 0.0),
            stress_distribution=data.get('stress_distribution', {}),
            critical_sections=data.get('critical_sections', [])
        )


@dataclass
class RiskAssessment:
    """Risk assessment for tunnel construction."""
    overall_risk_level: RiskLevel = RiskLevel.LOW
    risk_factors: List[Dict[str, Any]] = field(default_factory=list)
    mitigation_strategies: List[str] = field(default_factory=list)
    high_risk_areas: List[Tuple[float, float, str]] = field(default_factory=list)
    confidence_level: float = 0.0
    assessment_date: Optional[datetime] = None

    def get_risk_score(self) -> float:
        """Calculate overall risk score."""
        risk_scores = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MODERATE: 2.0,
            RiskLevel.HIGH: 3.0,
            RiskLevel.CRITICAL: 4.0
        }

        if not self.risk_factors:
            return risk_scores[RiskLevel.LOW]

        total_score = 0.0
        for factor in self.risk_factors:
            risk_type = factor.get('level', RiskLevel.LOW)
            if isinstance(risk_type, str):
                risk_type = RiskLevel(risk_type.lower())
            weight = factor.get('weight', 1.0)
            total_score += risk_scores.get(risk_type, 1.0) * weight

        return min(total_score, 4.0)

    def validate(self) -> bool:
        """Validate risk assessment data."""
        return self.confidence_level >= 0.0 and self.confidence_level <= 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert risk assessment to dictionary."""
        return {
            'overall_risk_level': self.overall_risk_level.value,
            'risk_factors': self.risk_factors,
            'mitigation_strategies': self.mitigation_strategies,
            'high_risk_areas': self.high_risk_areas,
            'confidence_level': self.confidence_level,
            'risk_score': self.get_risk_score(),
            'assessment_date': self.assessment_date.isoformat() if self.assessment_date else None,
            'is_valid': self.validate()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskAssessment':
        """Create risk assessment from dictionary."""
        overall_risk = RiskLevel(data.get('overall_risk_level', 'low'))

        assessment_date = None
        if data.get('assessment_date'):
            assessment_date = datetime.fromisoformat(data['assessment_date'])

        return cls(
            overall_risk_level=overall_risk,
            risk_factors=data.get('risk_factors', []),
            mitigation_strategies=data.get('mitigation_strategies', []),
            high_risk_areas=data.get('high_risk_areas', []),
            confidence_level=data.get('confidence_level', 0.0),
            assessment_date=assessment_date
        )


@dataclass
class EnvironmentalImpact:
    """Environmental impact assessment."""
    total_excavated_volume: float = 0.0
    surface_disturbance_area: float = 0.0
    affected_water_bodies: List[str] = field(default_factory=list)
    vegetation_impact: str = "minimal"
    noise_impact_radius: float = 0.0
    dust_generation_estimate: float = 0.0
    mitigation_measures: List[str] = field(default_factory=list)

    def calculate_impact_score(self) -> float:
        """Calculate environmental impact score."""
        score = 0.0

        # Volume impact
        if self.total_excavated_volume > 0:
            score += min(self.total_excavated_volume / 1000, 10.0)

        # Surface disturbance
        if self.surface_disturbance_area > 0:
            score += min(self.surface_disturbance_area / 100, 5.0)

        # Water body impact
        score += len(self.affected_water_bodies) * 2.0

        # Mitigation measures reduce score
        score = max(0, score - len(self.mitigation_measures))

        return score

    def validate(self) -> bool:
        """Validate environmental impact data."""
        return (self.total_excavated_volume >= 0 and
                self.surface_disturbance_area >= 0 and
                self.noise_impact_radius >= 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert environmental impact to dictionary."""
        return {
            'total_excavated_volume': self.total_excavated_volume,
            'surface_disturbance_area': self.surface_disturbance_area,
            'affected_water_bodies': self.affected_water_bodies,
            'vegetation_impact': self.vegetation_impact,
            'noise_impact_radius': self.noise_impact_radius,
            'dust_generation_estimate': self.dust_generation_estimate,
            'mitigation_measures': self.mitigation_measures,
            'impact_score': self.calculate_impact_score(),
            'is_valid': self.validate()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentalImpact':
        """Create environmental impact from dictionary."""
        return cls(
            total_excavated_volume=data.get('total_excavated_volume', 0.0),
            surface_disturbance_area=data.get('surface_disturbance_area', 0.0),
            affected_water_bodies=data.get('affected_water_bodies', []),
            vegetation_impact=data.get('vegetation_impact', 'minimal'),
            noise_impact_radius=data.get('noise_impact_radius', 0.0),
            dust_generation_estimate=data.get('dust_generation_estimate', 0.0),
            mitigation_measures=data.get('mitigation_measures', [])
        )


@dataclass
class AnalysisResult:
    """Complete analysis result for tunnel project."""

    # Basic project information
    project_name: str = ""
    tunnel_name: str = ""
    analysis_date: Optional[datetime] = None
    analyst_name: str = ""
    analysis_type: AnalysisType = AnalysisType.VOLUME_CALCULATION

    # Volume calculation results
    volume_calculation: Optional[VolumeCalculationResult] = None

    # Cost estimation
    cost_estimate: Optional[CostEstimate] = None

    # Structural analysis
    structural_analysis: Optional[StructuralAnalysis] = None

    # Risk assessment
    risk_assessment: Optional[RiskAssessment] = None

    # Environmental impact
    environmental_impact: Optional[EnvironmentalImpact] = None

    # Summary metrics
    summary_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    # Metadata
    calculation_time: float = 0.0
    data_sources: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def get_summary(self) -> Dict[str, Any]:
        """Get analysis summary."""
        summary = {
            'project_name': self.project_name,
            'tunnel_name': self.tunnel_name,
            'analysis_type': self.analysis_type.value,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None,
            'analyst': self.analyst_name
        }

        if self.volume_calculation:
            summary['volume'] = {
                'total': self.volume_calculation.total_volume,
                'excavation_zones': len(self.volume_calculation.excavation_zones),
                'accuracy': self.volume_calculation.accuracy_estimate,
                'material_breakdown': self.volume_calculation.get_material_breakdown()
            }

        if self.cost_estimate:
            summary['cost'] = {
                'total': self.cost_estimate.total_cost,
                'currency': self.cost_estimate.currency,
                'per_day': self.cost_estimate.cost_per_day,
                'duration_days': self.cost_estimate.total_days,
                'breakdown': self.cost_estimate.get_cost_breakdown_percentage()
            }

        if self.structural_analysis:
            summary['structural'] = {
                'stability': self.structural_analysis.tunnel_stability_rating,
                'rock_mass_rating': self.structural_analysis.rock_mass_rating,
                'safety_factor': self.structural_analysis.safety_factor
            }

        if self.risk_assessment:
            summary['risk'] = {
                'overall_level': self.risk_assessment.overall_risk_level.value,
                'risk_score': self.risk_assessment.get_risk_score(),
                'confidence': self.risk_assessment.confidence_level,
                'risk_factors_count': len(self.risk_assessment.risk_factors)
            }

        if self.environmental_impact:
            summary['environmental'] = {
                'impact_score': self.environmental_impact.calculate_impact_score(),
                'volume_excavated': self.environmental_impact.total_excavated_volume,
                'surface_disturbance': self.environmental_impact.surface_disturbance_area
            }

        summary.update(self.summary_metrics)
        summary['recommendations'] = self.recommendations

        return summary

    def add_recommendation(self, recommendation: str):
        """Add a recommendation to the analysis."""
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)

    def validate(self) -> bool:
        """Validate analysis result."""
        # Basic validation
        if not self.project_name or not self.tunnel_name:
            return False

        # Validate each analysis component
        components = [
            self.volume_calculation,
            self.cost_estimate,
            self.structural_analysis,
            self.risk_assessment,
            self.environmental_impact
        ]

        for component in components:
            if component and hasattr(component, 'validate'):
                if not component.validate():
                    return False

        return True

    def export_to_dict(self) -> Dict[str, Any]:
        """Export analysis result to dictionary."""
        return {
            'project_name': self.project_name,
            'tunnel_name': self.tunnel_name,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None,
            'analyst_name': self.analyst_name,
            'analysis_type': self.analysis_type.value,
            'volume_calculation': self.volume_calculation.to_dict() if self.volume_calculation else None,
            'cost_estimate': self.cost_estimate.to_dict() if self.cost_estimate else None,
            'structural_analysis': self.structural_analysis.to_dict() if self.structural_analysis else None,
            'risk_assessment': self.risk_assessment.to_dict() if self.risk_assessment else None,
            'environmental_impact': self.environmental_impact.to_dict() if self.environment_impact else None,
            'summary_metrics': self.summary_metrics,
            'recommendations': self.recommendations,
            'calculation_time': self.calculation_time,
            'data_sources': self.data_sources,
            'assumptions': self.assumptions,
            'limitations': self.limitations,
            'summary': self.get_summary(),
            'is_valid': self.validate()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Create analysis result from dictionary."""
        # Create components
        volume_calculation = None
        if data.get('volume_calculation'):
            volume_calculation = VolumeCalculationResult.from_dict(data['volume_calculation'])

        cost_estimate = None
        if data.get('cost_estimate'):
            cost_estimate = CostEstimate.from_dict(data['cost_estimate'])

        structural_analysis = None
        if data.get('structural_analysis'):
            structural_analysis = StructuralAnalysis.from_dict(data['structural_analysis'])

        risk_assessment = None
        if data.get('risk_assessment'):
            risk_assessment = RiskAssessment.from_dict(data['risk_assessment'])

        environmental_impact = None
        if data.get('environmental_impact'):
            environmental_impact = EnvironmentalImpact.from_dict(data['environmental_impact'])

        analysis_date = None
        if data.get('analysis_date'):
            analysis_date = datetime.fromisoformat(data['analysis_date'])

        return cls(
            project_name=data.get('project_name', ''),
            tunnel_name=data.get('tunnel_name', ''),
            analysis_date=analysis_date,
            analyst_name=data.get('analyst_name', ''),
            analysis_type=AnalysisType(data.get('analysis_type', 'volume_calculation')),
            volume_calculation=volume_calculation,
            cost_estimate=cost_estimate,
            structural_analysis=structural_analysis,
            risk_assessment=risk_assessment,
            environmental_impact=environmental_impact,
            summary_metrics=data.get('summary_metrics', {}),
            recommendations=data.get('recommendations', []),
            calculation_time=data.get('calculation_time', 0.0),
            data_sources=data.get('data_sources', []),
            assumptions=data.get('assumptions', []),
            limitations=data.get('limitations', [])
        )

    def export_to_csv(self, filename: str) -> None:
        """Export analysis result to CSV file."""
        import csv

        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Write header
            writer.writerow(['Metric', 'Value', 'Unit', 'Description'])

            # Write summary metrics
            summary = self.get_summary()
            for key, value in summary.items():
                if isinstance(value, dict):
                    continue  # Skip nested dictionaries
                writer.writerow([key, value, '', 'Summary metric'])

            # Write volume calculation details
            if self.volume_calculation:
                writer.writerow(['Total Volume', self.volume_calculation.total_volume, 'm3', 'Total excavation volume'])
                writer.writerow(['Accuracy', self.volume_calculation.accuracy_estimate, '', 'Accuracy estimate'])
                writer.writerow(['Excavation Zones', len(self.volume_calculation.excavation_zones), '', 'Number of excavation zones'])

            # Write cost details
            if self.cost_estimate:
                writer.writerow(['Total Cost', self.cost_estimate.total_cost, self.cost_estimate.currency, 'Total project cost'])
                writer.writerow(['Cost per Day', self.cost_estimate.cost_per_day, self.cost_estimate.currency, 'Daily construction cost'])

            # Write structural analysis details
            if self.structural_analysis:
                writer.writerow(['Rock Mass Rating', self.structural_analysis.rock_mass_rating, '', 'Rock mass rating'])
                writer.writerow(['Safety Factor', self.structural_analysis.safety_factor, '', 'Design safety factor'])

            # Write risk assessment details
            if self.risk_assessment:
                writer.writerow(['Risk Level', self.risk_assessment.overall_risk_level.value, '', 'Overall risk level'])
                writer.writerow(['Risk Score', self.risk_assessment.get_risk_score(), '', 'Calculated risk score'])

            # Write environmental impact details
            if self.environmental_impact:
                writer.writerow(['Impact Score', self.environment_impact.calculate_impact_score(), '', 'Environmental impact score'])
                writer.writerow(['Excavated Volume', self.environmentalimpact.total_excavated_volume, 'm3', 'Total excavated volume'])

    def export_to_json(self, filename: str) -> None:
        """Export analysis result to JSON file."""
        import json

        data = self.export_to_dict()
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)