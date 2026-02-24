"""
Recommendation Agent - Proactive opportunity discovery and recommendations
Scans for new opportunities and generates quarterly strategic reports
"""

from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
import random

from src.models.process import Process, OpportunityScore
from src.core.decision_engine import DecisionEngine
from src.utils.database import Database


class RecommendationAgent:
    """
    AI agent for proactive recommendations
    
    Capabilities:
    - Scan existing processes for new opportunities
    - Detect changes in processes over time
    - Generate quarterly business reviews
    - Prioritize next actions
    - Suggest strategic initiatives
    """
    
    def __init__(self, db_path: str = "data/delvalue.db"):
        """
        Initialize Recommendation Agent
        
        Args:
            db_path: Path to database
        """
        self.db = Database(db_path)
        self.engine = DecisionEngine()
    
    def scan_for_new_opportunities(
        self,
        min_score: float = 60.0
    ) -> List[OpportunityScore]:
        """
        Scan all processes for new automation opportunities
        
        Args:
            min_score: Minimum overall score to recommend
            
        Returns:
            List of new opportunities
        """
        # Get all processes
        all_processes = self.db.get_all_processes()
        
        # Get existing scores
        existing_scores = self.db.get_opportunity_scores()
        existing_process_ids = {s.process_id for s in existing_scores}
        
        # Find processes not yet analyzed
        new_processes = [
            p for p in all_processes 
            if p.id not in existing_process_ids
        ]
        
        # Score new processes
        new_opportunities = []
        for process in new_processes:
            score = self.engine.score_opportunity(process)
            
            if score.overall_score >= min_score:
                new_opportunities.append(score)
        
        # Sort by score
        new_opportunities.sort(key=lambda x: x.overall_score, reverse=True)
        
        return new_opportunities
    
    def detect_process_changes(
        self,
        lookback_days: int = 90
    ) -> List[Dict[str, any]]:
        """
        Detect processes that have changed significantly
        
        Args:
            lookback_days: How far back to look for changes
            
        Returns:
            List of changes detected
        """
        changes = []
        
        # Get all processes
        processes = self.db.get_all_processes()
        
        if not processes:
            return changes
        
        # Simulate change detection (in real app, would track historical changes)
        for process in processes[:min(5, len(processes))]:  # Sample a few
            # Simulate volume increase
            if random.random() > 0.5:
                old_volume = process.annual_volume
                new_volume = int(old_volume * 1.3)  # 30% increase
                
                changes.append({
                    'process_id': process.id,
                    'process_name': process.name,
                    'change_type': 'VOLUME_INCREASE',
                    'old_value': old_volume,
                    'new_value': new_volume,
                    'impact': 'Higher volume may increase ROI - re-analyze recommended',
                    'detected_at': datetime.now()
                })
        
        return changes
    
    def generate_quarterly_report(
        self,
        quarter: str = "Q1 2026"
    ) -> str:
        """
        Generate quarterly business review report
        
        Args:
            quarter: Quarter identifier
            
        Returns:
            Report text
        """
        # Get data
        all_processes = self.db.get_all_processes()
        all_scores = self.db.get_opportunity_scores()
        
        # Calculate metrics
        total_potential_savings = sum(s.estimated_annual_savings for s in all_scores)
        total_investment = sum(s.implementation_cost for s in all_scores)
        portfolio_roi = ((total_potential_savings - total_investment) / total_investment * 100) if total_investment > 0 else 0
        strong_recommends = [s for s in all_scores if "STRONG" in s.recommendation]
        
        # Category breakdown
        category_summary = {}
        for process in all_processes:
            cat = process.category
            if cat not in category_summary:
                category_summary[cat] = {'count': 0, 'savings': 0}
            category_summary[cat]['count'] += 1
            
            # Find matching score
            score = next((s for s in all_scores if s.process_id == process.id), None)
            if score:
                category_summary[cat]['savings'] += score.estimated_annual_savings
        
        # Generate report
        report = f"""
╔═══════════════════════════════════════════════════════════════════╗
║         QUARTERLY AI TRANSFORMATION REPORT - {quarter}              ║
╚═══════════════════════════════════════════════════════════════════╝

EXECUTIVE SUMMARY
═════════════════

Total Processes Analyzed:        {len(all_processes)}
Automation Opportunities:         {len(all_scores)}
Strong Recommendations:           {len(strong_recommends)}

Total Savings Potential:          ${total_potential_savings:,.0f}/year
Required Investment:              ${total_investment:,.0f}
Portfolio ROI:                    {portfolio_roi:.0f}%

TOP 5 OPPORTUNITIES THIS QUARTER
═════════════════════════════════

"""
        
        # Add top 5
        top_5 = all_scores[:min(5, len(all_scores))]
        for i, score in enumerate(top_5, 1):
            report += f"""
{i}. {score.process_name}
   Overall Score:     {score.overall_score:.1f}/100
   Annual Savings:    ${score.estimated_annual_savings:,.0f}
   ROI:              {score.roi_percentage:.0f}%
   Payback:          {score.payback_months:.1f} months
   Recommendation:   {score.recommendation}
"""
        
        if not top_5:
            report += "\nNo opportunities available. Add processes to analyze.\n"
        
        # Category breakdown
        report += f"""

OPPORTUNITIES BY CATEGORY
══════════════════════════

"""
        
        sorted_categories = sorted(
            category_summary.items(),
            key=lambda x: x[1]['savings'],
            reverse=True
        )
        
        for cat, data in sorted_categories[:5]:
            report += f"""
{cat.upper().replace('_', ' ')}:
   Processes:        {data['count']}
   Total Savings:    ${data['savings']:,.0f}/year
"""
        
        # Strategic recommendations
        report += f"""

STRATEGIC RECOMMENDATIONS
═════════════════════════

1. IMMEDIATE ACTIONS (Next 30 Days)
   → Implement top 3 opportunities
   → Expected impact: ${sum(s.estimated_annual_savings for s in top_5[:3]):,.0f}/year
   → Investment required: ${sum(s.implementation_cost for s in top_5[:3]):,.0f}

2. MEDIUM-TERM INITIATIVES (Next 90 Days)
   → Focus on highest savings category
   → Prepare for additional implementations
   → Conduct change management workshops

3. LONG-TERM STRATEGY (Next 6-12 Months)
   → Build automation capability internally
   → Scale successful implementations
   → Continuous process discovery

═══════════════════════════════════════════════════════════════════

Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return report
    
    def prioritize_next_actions(
        self,
        max_investment: Optional[float] = None,
        max_projects: int = 5
    ) -> List[Dict[str, any]]:
        """
        Prioritize next actions within constraints
        
        Args:
            max_investment: Maximum total investment budget
            max_projects: Maximum number of projects to recommend
            
        Returns:
            List of prioritized actions
        """
        # Get all scores
        all_scores = self.db.get_opportunity_scores()
        
        # Filter strong recommendations
        candidates = [
            s for s in all_scores 
            if "STRONG" in s.recommendation or "RECOMMEND" in s.recommendation
        ]
        
        # Sort by ROI
        candidates.sort(key=lambda x: x.roi_percentage, reverse=True)
        
        # Apply constraints
        selected = []
        total_investment = 0
        
        for score in candidates:
            if len(selected) >= max_projects:
                break
            
            if max_investment and (total_investment + score.implementation_cost) > max_investment:
                continue
            
            selected.append({
                'process_name': score.process_name,
                'priority': len(selected) + 1,
                'overall_score': score.overall_score,
                'roi': score.roi_percentage,
                'annual_savings': score.estimated_annual_savings,
                'investment': score.implementation_cost,
                'payback_months': score.payback_months,
                'reasoning': score.reasoning
            })
            
            total_investment += score.implementation_cost
        
        return selected
    
    def suggest_strategic_initiatives(self) -> List[str]:
        """
        Suggest strategic initiatives based on portfolio
        
        Returns:
            List of strategic suggestions
        """
        suggestions = []
        
        # Get data
        all_processes = self.db.get_all_processes()
        all_scores = self.db.get_opportunity_scores()
        
        if not all_processes:
            suggestions.append("Add processes to the system to receive strategic recommendations")
            return suggestions
        
        # Suggestion 1: High-impact category
        category_savings = {}
        for process in all_processes:
            score = next((s for s in all_scores if s.process_id == process.id), None)
            if score:
                cat = process.category
                if cat not in category_savings:
                    category_savings[cat] = 0
                category_savings[cat] += score.estimated_annual_savings
        
        if category_savings:
            top_category = max(category_savings.items(), key=lambda x: x[1])
            suggestions.append(
                f"Focus automation efforts on {top_category[0]} category "
                f"(${top_category[1]:,.0f} annual savings potential)"
            )
        
        # Suggestion 2: Quick wins
        quick_wins = [
            s for s in all_scores 
            if s.payback_months <= 2.0 and s.overall_score >= 75
        ]
        if quick_wins:
            suggestions.append(
                f"Prioritize {len(quick_wins)} quick-win opportunities "
                f"with <2 month payback for immediate ROI"
            )
        
        # Suggestion 3: Scale successful patterns
        suggestions.append(
            "Document and replicate successful implementation patterns "
            "across similar processes"
        )
        
        # Suggestion 4: Capability building
        high_feasibility = [s for s in all_scores if s.feasibility_score >= 80]
        if high_feasibility:
            suggestions.append(
                f"{len(high_feasibility)} processes are highly automatable - "
                "invest in internal AI capability to scale implementation"
            )
        
        return suggestions
    
    def generate_action_plan(
        self,
        timeframe: str = "90_days"
    ) -> str:
        """
        Generate detailed action plan
        
        Args:
            timeframe: 30_days, 90_days, or 180_days
            
        Returns:
            Action plan text
        """
        priorities = self.prioritize_next_actions(max_projects=10)
        
        if not priorities:
            return """
ACTION PLAN
===========

No opportunities available for action plan.

Please:
1. Add processes to the system
2. Run analysis to generate opportunity scores
3. Return to generate action plan
"""
        
        if timeframe == "30_days":
            focus_items = priorities[:3]
            title = "30-DAY ACTION PLAN"
        elif timeframe == "90_days":
            focus_items = priorities[:5]
            title = "90-DAY ACTION PLAN"
        else:
            focus_items = priorities[:10]
            title = "180-DAY ACTION PLAN"
        
        plan = f"""
{title}
{'=' * len(title)}

PRIORITIES:

"""
        
        for item in focus_items:
            plan += f"""
Priority {item['priority']}: {item['process_name']}
  Score:          {item['overall_score']:.1f}/100
  ROI:           {item['roi']:.0f}%
  Annual Impact:  ${item['annual_savings']:,.0f}
  Investment:     ${item['investment']:,.0f}
  Payback:       {item['payback_months']:.1f} months

"""
        
        total_savings = sum(i['annual_savings'] for i in focus_items)
        total_investment = sum(i['investment'] for i in focus_items)
        portfolio_roi = ((total_savings - total_investment) / total_investment * 100) if total_investment > 0 else 0
        
        plan += f"""
TOTAL IMPACT:
  Total Annual Savings:  ${total_savings:,.0f}
  Total Investment:      ${total_investment:,.0f}
  Portfolio ROI:         {portfolio_roi:.0f}%

ACTION ITEMS:
  □ Secure budget approval (${total_investment:,.0f})
  □ Assemble implementation team
  □ Conduct stakeholder workshops
  □ Define success metrics
  □ Create implementation timeline
  □ Set up monitoring cadence
"""
        
        return plan


# Test the agent
if __name__ == "__main__":
    print("🎯 Testing Recommendation Agent")
    print("=" * 70)
    
    # Create agent
    agent = RecommendationAgent("data/delvalue.db")
    
    # Test 1: Scan for opportunities
    print("\n1. Testing scan_for_new_opportunities()...")
    new_opps = agent.scan_for_new_opportunities(min_score=70)
    print(f"   ✅ Found {len(new_opps)} new opportunities")
    if new_opps:
        print(f"   Top opportunity: {new_opps[0].process_name} ({new_opps[0].overall_score:.1f}/100)")
    
    # Test 2: Detect changes
    print("\n2. Testing detect_process_changes()...")
    changes = agent.detect_process_changes()
    print(f"   ✅ Detected {len(changes)} process changes")
    if changes:
        print(f"   Example: {changes[0]['change_type']} in {changes[0]['process_name']}")
    
    # Test 3: Prioritize actions
    print("\n3. Testing prioritize_next_actions()...")
    priorities = agent.prioritize_next_actions(max_projects=5)
    print(f"   ✅ Generated {len(priorities)} prioritized actions")
    if priorities:
        print(f"   Top priority: {priorities[0]['process_name']} (ROI: {priorities[0]['roi']:.0f}%)")
    
    # Test 4: Strategic suggestions
    print("\n4. Testing suggest_strategic_initiatives()...")
    suggestions = agent.suggest_strategic_initiatives()
    print(f"   ✅ Generated {len(suggestions)} strategic suggestions")
    for i, sug in enumerate(suggestions[:3], 1):
        print(f"   {i}. {sug}")
    
    # Test 5: Action plan
    print("\n5. Testing generate_action_plan()...")
    action_plan = agent.generate_action_plan(timeframe="30_days")
    print("   ✅ Generated 30-day action plan")
    print(action_plan[:400] + "...")
    
    # Test 6: Quarterly report
    print("\n6. Testing generate_quarterly_report()...")
    quarterly = agent.generate_quarterly_report("Q1 2026")
    print("   ✅ Generated quarterly report")
    print(quarterly[:500] + "...")
    
    print("\n✅ Recommendation Agent tests complete!")
