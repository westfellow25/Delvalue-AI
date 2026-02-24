"""
Decision Engine - Core scoring and ranking logic
Calculates feasibility, value, risk, and ROI for automation opportunities
"""

from typing import List, Dict, Tuple
import math
from src.models.process import Process, OpportunityScore, AutomationFeasibility, RiskLevel


class DecisionEngine:
    """
    Core decision engine for process automation prioritization
    
    Uses multi-factor scoring:
    - Feasibility: How easy to automate (repetitiveness, standardization)
    - Value: Potential savings (time, cost, scale)
    - Risk: Implementation risks (complexity, change management)
    """
    
    def __init__(
        self,
        feasibility_weight: float = 0.3,
        value_weight: float = 0.5,
        risk_weight: float = 0.2
    ):
        """
        Initialize Decision Engine
        
        Args:
            feasibility_weight: Weight for feasibility score (default 0.3)
            value_weight: Weight for value score (default 0.5)
            risk_weight: Weight for risk score (default 0.2)
        """
        # Validate weights sum to 1.0
        total = feasibility_weight + value_weight + risk_weight
        assert abs(total - 1.0) < 0.01, f"Weights must sum to 1.0, got {total}"
        
        self.weights = {
            'feasibility': feasibility_weight,
            'value': value_weight,
            'risk': risk_weight
        }
    
    def calculate_feasibility_score(self, process: Process) -> Tuple[float, List[str]]:
        """
        Calculate automation feasibility (0-100)
        
        Factors:
        - Repetitiveness: Higher volume = easier to justify automation
        - Standardization: Well-documented processes easier to automate
        - System complexity: Fewer systems = easier integration
        
        Returns:
            Tuple of (score, reasoning_factors)
        """
        score = 0.0
        factors = []
        
        # 1. Repetitiveness (0-40 points)
        if process.annual_volume >= 10000:
            score += 40
            factors.append(f"Very high volume ({process.annual_volume:,}/year)")
        elif process.annual_volume >= 5000:
            score += 35
            factors.append(f"High volume ({process.annual_volume:,}/year)")
        elif process.annual_volume >= 1000:
            score += 25
            factors.append(f"Good volume ({process.annual_volume:,}/year)")
        elif process.annual_volume >= 500:
            score += 15
            factors.append(f"Medium volume ({process.annual_volume:,}/year)")
        else:
            score += 10
            factors.append(f"Lower volume ({process.annual_volume:,}/year)")
        
        # 2. Standardization/Documentation (0-30 points)
        doc_score = 0
        if process.sop_exists:
            doc_score += 15
            factors.append("SOP exists")
        
        if len(process.description) > 500:
            doc_score += 15
            factors.append("Well documented")
        elif len(process.description) > 200:
            doc_score += 10
            factors.append("Adequately documented")
        else:
            doc_score += 5
            factors.append("Limited documentation")
        
        score += doc_score
        
        # 3. System Complexity (0-30 points)
        num_systems = len(process.systems_used)
        if num_systems == 0:
            complexity_score = 30
            factors.append("No system dependencies")
        elif num_systems == 1:
            complexity_score = 25
            factors.append("Single system (simple integration)")
        elif num_systems == 2:
            complexity_score = 20
            factors.append("Two systems (moderate integration)")
        elif num_systems <= 4:
            complexity_score = 15
            factors.append(f"{num_systems} systems (complex integration)")
        else:
            complexity_score = 5
            factors.append(f"{num_systems} systems (very complex)")
        
        score += complexity_score
        
        return min(score, 100.0), factors
    
    def calculate_value_score(self, process: Process) -> Tuple[float, List[str]]:
        """
        Calculate potential business value (0-100)
        
        Based on:
        - Annual cost (time × volume × hourly rate)
        - Scale (number of people impacted)
        - Pain points (quality improvements beyond cost)
        
        Returns:
            Tuple of (score, reasoning_factors)
        """
        factors = []
        
        # Calculate annual cost
        hours_per_execution = process.duration_minutes / 60.0
        annual_hours = hours_per_execution * process.annual_volume
        annual_cost = annual_hours * process.hourly_cost
        
        factors.append(f"Annual cost: ${annual_cost:,.0f}")
        
        # Base score on annual cost
        if annual_cost >= 500000:
            score = 100
            factors.append("Very high value ($500k+ annual)")
        elif annual_cost >= 200000:
            score = 85
            factors.append("High value ($200k-500k annual)")
        elif annual_cost >= 100000:
            score = 70
            factors.append("Significant value ($100k-200k annual)")
        elif annual_cost >= 50000:
            score = 55
            factors.append("Good value ($50k-100k annual)")
        elif annual_cost >= 20000:
            score = 40
            factors.append("Medium value ($20k-50k annual)")
        elif annual_cost >= 10000:
            score = 25
            factors.append("Lower value ($10k-20k annual)")
        else:
            score = 15
            factors.append("Low value (<$10k annual)")
        
        # Bonus for scale (people impacted)
        if process.people_involved >= 50:
            score = min(score + 15, 100)
            factors.append(f"Wide impact ({process.people_involved} people)")
        elif process.people_involved >= 20:
            score = min(score + 10, 100)
            factors.append(f"Significant impact ({process.people_involved} people)")
        elif process.people_involved >= 10:
            score = min(score + 5, 100)
            factors.append(f"Good impact ({process.people_involved} people)")
        
        # Bonus for pain points (quality improvements)
        if len(process.pain_points) >= 4:
            score = min(score + 5, 100)
            factors.append("Multiple pain points to address")
        
        return min(score, 100.0), factors
    
    def calculate_risk_score(self, process: Process) -> Tuple[float, List[str]]:
        """
        Calculate implementation risk (0-100, lower = better)
        
        Risk factors:
        - System complexity (more systems = more risk)
        - Change management (more people = more resistance)
        - Process category (finance/legal = higher compliance risk)
        - Dependencies (more dependencies = more risk)
        
        Returns:
            Tuple of (score, risk_factors)
        """
        risk = 0.0
        risk_factors = []
        
        # 1. System Integration Risk (0-35 points)
        num_systems = len(process.systems_used)
        if num_systems >= 6:
            risk += 35
            risk_factors.append(f"Very high integration complexity ({num_systems} systems)")
        elif num_systems >= 4:
            risk += 25
            risk_factors.append(f"High integration complexity ({num_systems} systems)")
        elif num_systems >= 2:
            risk += 15
            risk_factors.append(f"Moderate integration complexity ({num_systems} systems)")
        elif num_systems == 1:
            risk += 5
            risk_factors.append("Low integration risk (single system)")
        
        # 2. Change Management Risk (0-30 points)
        if process.people_involved >= 50:
            risk += 30
            risk_factors.append(f"Major change management ({process.people_involved} people)")
        elif process.people_involved >= 20:
            risk += 20
            risk_factors.append(f"Significant change management ({process.people_involved} people)")
        elif process.people_involved >= 10:
            risk += 12
            risk_factors.append(f"Moderate change management ({process.people_involved} people)")
        elif process.people_involved >= 5:
            risk += 5
            risk_factors.append("Limited change management needed")
        
        # 3. Category-Based Risk (0-20 points)
        high_risk_categories = ["finance", "legal", "hr"]
        medium_risk_categories = ["customer_service", "sales"]
        
        if process.category in high_risk_categories:
            risk += 20
            risk_factors.append(f"High regulatory/compliance risk ({process.category})")
        elif process.category in medium_risk_categories:
            risk += 10
            risk_factors.append(f"Moderate compliance considerations ({process.category})")
        
        # 4. Dependency Risk (0-15 points)
        if len(process.dependencies) >= 5:
            risk += 15
            risk_factors.append("Many process dependencies")
        elif len(process.dependencies) >= 3:
            risk += 10
            risk_factors.append("Several process dependencies")
        elif len(process.dependencies) >= 1:
            risk += 5
            risk_factors.append("Some process dependencies")
        
        return min(risk, 100.0), risk_factors
    
    def calculate_roi(
        self,
        process: Process,
        automation_percentage: float = 0.70
    ) -> Dict[str, float]:
        """
        Calculate ROI metrics
        
        Args:
            process: Process to analyze
            automation_percentage: Expected automation rate (default 70%)
        
        Returns:
            Dictionary with financial metrics
        """
        # Calculate current annual cost
        hours_per_execution = process.duration_minutes / 60.0
        annual_hours = hours_per_execution * process.annual_volume
        current_annual_cost = annual_hours * process.hourly_cost
        
        # Calculate savings (conservative: 70% automation)
        hours_saved = annual_hours * automation_percentage
        annual_savings = hours_saved * process.hourly_cost
        
        # Estimate implementation cost (heuristic)
        # Base: $10k
        # +$3k per system integration
        # +$2k per 10 people (change management)
        # +$5k if high-risk category
        
        base_cost = 10000
        integration_cost = len(process.systems_used) * 3000
        change_mgmt_cost = (process.people_involved // 10) * 2000
        
        category_premium = 5000 if process.category in ["finance", "legal"] else 0
        
        implementation_cost = (
            base_cost +
            integration_cost +
            change_mgmt_cost +
            category_premium
        )
        
        # Calculate ROI metrics
        net_savings_year1 = annual_savings - implementation_cost
        
        if implementation_cost > 0:
            roi_percentage = (net_savings_year1 / implementation_cost) * 100
            payback_months = (implementation_cost / annual_savings) * 12 if annual_savings > 0 else 999
        else:
            roi_percentage = 0
            payback_months = 0
        
        # 3-year NPV (simple, no discount)
        npv_3year = (annual_savings * 3) - implementation_cost
        
        return {
            'current_annual_cost': current_annual_cost,
            'annual_savings': annual_savings,
            'implementation_cost': implementation_cost,
            'net_savings_year1': net_savings_year1,
            'roi_percentage': roi_percentage,
            'payback_months': payback_months,
            'npv_3year': npv_3year
        }
    
    def score_opportunity(self, process: Process) -> OpportunityScore:
        """
        Score a single automation opportunity
        
        Returns complete OpportunityScore with all metrics
        """
        # Calculate component scores
        feasibility_score, feasibility_factors = self.calculate_feasibility_score(process)
        value_score, value_factors = self.calculate_value_score(process)
        risk_score, risk_factors = self.calculate_risk_score(process)
        
        # Calculate weighted overall score
        # Note: For risk, we invert (100 - risk) so lower risk = higher score
        overall_score = (
            feasibility_score * self.weights['feasibility'] +
            value_score * self.weights['value'] +
            (100 - risk_score) * self.weights['risk']
        )
        
        # Calculate ROI metrics
        roi_metrics = self.calculate_roi(process)
        
        # Determine feasibility category
        if feasibility_score >= 70:
            feasibility_cat = AutomationFeasibility.HIGH
        elif feasibility_score >= 40:
            feasibility_cat = AutomationFeasibility.MEDIUM
        else:
            feasibility_cat = AutomationFeasibility.LOW
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 50:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 30:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        # Generate recommendation
        if overall_score >= 75 and roi_metrics['roi_percentage'] >= 150:
            recommendation = "STRONG RECOMMEND"
            reasoning = (
                f"High-value opportunity with {roi_metrics['roi_percentage']:.0f}% ROI. "
                f"Feasibility: {feasibility_score:.0f}/100, Value: {value_score:.0f}/100. "
                f"Payback in {roi_metrics['payback_months']:.1f} months."
            )
        elif overall_score >= 60 and roi_metrics['roi_percentage'] >= 100:
            recommendation = "RECOMMEND"
            reasoning = (
                f"Solid opportunity with {roi_metrics['roi_percentage']:.0f}% ROI. "
                f"Feasibility: {feasibility_score:.0f}/100, Value: {value_score:.0f}/100."
            )
        elif overall_score >= 45:
            recommendation = "CONSIDER"
            reasoning = (
                f"Moderate opportunity. {roi_metrics['roi_percentage']:.0f}% ROI, "
                f"but consider feasibility ({feasibility_score:.0f}/100) and risks."
            )
        else:
            recommendation = "DEPRIORITIZE"
            reasoning = (
                f"Lower priority. Focus on higher-value opportunities first. "
                f"Score: {overall_score:.0f}/100"
            )
        
        # Combine all reasoning factors
        all_factors = (
            ["Feasibility: " + f for f in feasibility_factors] +
            ["Value: " + f for f in value_factors] +
            ["Risk: " + f for f in risk_factors]
        )
        
        # Calculate confidence (simple heuristic based on data completeness)
        confidence = 0.7  # Base confidence
        if process.sop_exists:
            confidence += 0.1
        if len(process.description) > 300:
            confidence += 0.1
        if len(process.pain_points) >= 3:
            confidence += 0.05
        
        confidence = min(confidence, 0.95)
        
        return OpportunityScore(
            process_id=process.id,
            process_name=process.name,
            feasibility_score=feasibility_score,
            value_score=value_score,
            risk_score=risk_score,
            overall_score=overall_score,
            estimated_annual_savings=roi_metrics['annual_savings'],
            implementation_cost=roi_metrics['implementation_cost'],
            roi_percentage=roi_metrics['roi_percentage'],
            payback_months=roi_metrics['payback_months'],
            risk_level=risk_level,
            risk_factors=risk_factors,
            automation_feasibility=feasibility_cat,
            recommendation=recommendation,
            reasoning=reasoning,
            confidence_level=confidence
        )
    
    def rank_opportunities(self, processes: List[Process]) -> List[OpportunityScore]:
        """
        Score and rank multiple processes
        
        Returns list sorted by overall_score (descending)
        """
        scores = [self.score_opportunity(p) for p in processes]
        
        # Sort by overall score (highest first)
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        return scores


# Test the engine
if __name__ == "__main__":
    from src.models.process import ProcessCategory
    
    # Create test process
    test_process = Process(
        name="Invoice Processing",
        description="Manual review and approval of vendor invoices in accounts payable. Process involves data entry, validation, approval routing, and payment scheduling.",
        category=ProcessCategory.FINANCE,
        frequency="200x/day",
        duration_minutes=15,
        annual_volume=50000,
        people_involved=5,
        hourly_cost=45,
        systems_used=["SAP", "Email", "Excel"],
        pain_points=["Manual data entry", "Frequent errors", "Slow approval", "Lack of visibility"],
        stakeholders=["CFO", "AP Manager", "Finance Team"],
        sop_exists=True
    )
    
    # Create engine and score
    engine = DecisionEngine()
    score = engine.score_opportunity(test_process)
    
    print("✅ Decision Engine Test")
    print("=" * 60)
    print(f"Process: {score.process_name}")
    print(f"Overall Score: {score.overall_score:.1f}/100")
    print(f"Recommendation: {score.recommendation}")
    print(f"\nScores:")
    print(f"  Feasibility: {score.feasibility_score:.1f}/100")
    print(f"  Value: {score.value_score:.1f}/100")
    print(f"  Risk: {score.risk_score:.1f}/100 ({score.risk_level})")
    print(f"\nFinancials:")
    print(f"  Annual Savings: ${score.estimated_annual_savings:,.0f}")
    print(f"  Implementation Cost: ${score.implementation_cost:,.0f}")
    print(f"  ROI: {score.roi_percentage:.0f}%")
    print(f"  Payback: {score.payback_months:.1f} months")
    print(f"\nReasoning: {score.reasoning}")
    print(f"\nRisk Factors:")
    for rf in score.risk_factors:
        print(f"  - {rf}")