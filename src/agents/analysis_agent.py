"""
Analysis Agent - LLM-powered process analysis and recommendation generation
Uses Claude to add intelligent reasoning to Decision Engine scores
"""

import os
from typing import List, Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

from src.models.process import Process, OpportunityScore
from src.core.decision_engine import DecisionEngine

# Load environment variables
load_dotenv()


class AnalysisAgent:
    """
    AI agent for analyzing automation opportunities
    
    Combines:
    - Decision Engine (quantitative scoring)
    - Claude LLM (qualitative reasoning and recommendations)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        """
        Initialize Analysis Agent
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or parameters")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.engine = DecisionEngine()
    
    def analyze_process(
        self,
        process: Process,
        include_llm_reasoning: bool = True
    ) -> OpportunityScore:
        """
        Analyze a single process
        
        Args:
            process: Process to analyze
            include_llm_reasoning: Whether to enhance with LLM reasoning
            
        Returns:
            OpportunityScore with analysis
        """
        # Get quantitative score from Decision Engine
        score = self.engine.score_opportunity(process)
        
        # Enhance with LLM reasoning if requested
        if include_llm_reasoning:
            enhanced_reasoning = self._generate_llm_reasoning(process, score)
            # Update the score with enhanced reasoning
            score.reasoning = enhanced_reasoning
        
        return score
    
    def _generate_llm_reasoning(
        self,
        process: Process,
        score: OpportunityScore
    ) -> str:
        """
        Generate enhanced reasoning using Claude
        
        Args:
            process: The process being analyzed
            score: Initial score from Decision Engine
            
        Returns:
            Enhanced reasoning text
        """
        prompt = f"""You are an AI transformation consultant analyzing automation opportunities.

Process Details:
- Name: {process.name}
- Category: {process.category}
- Description: {process.description}
- Frequency: {process.frequency}
- Duration: {process.duration_minutes} minutes per execution
- Annual Volume: {process.annual_volume:,} executions/year
- People Involved: {process.people_involved}
- Systems Used: {', '.join(process.systems_used) if process.systems_used else 'None'}
- Pain Points: {', '.join(process.pain_points) if process.pain_points else 'None identified'}

Quantitative Analysis Results:
- Overall Score: {score.overall_score:.1f}/100
- Feasibility: {score.feasibility_score:.1f}/100 ({score.automation_feasibility})
- Value: {score.value_score:.1f}/100
- Risk: {score.risk_score:.1f}/100 ({score.risk_level})
- Estimated Annual Savings: ${score.estimated_annual_savings:,.0f}
- Implementation Cost: ${score.implementation_cost:,.0f}
- ROI: {score.roi_percentage:.0f}%
- Payback: {score.payback_months:.1f} months

Risk Factors Identified:
{chr(10).join('- ' + rf for rf in score.risk_factors)}

Your task: Provide a concise, executive-level recommendation (2-3 sentences) that:
1. Explains WHY this is a {score.recommendation} opportunity
2. Highlights the most compelling business case aspect
3. Mentions the key risk or consideration to address

Be specific, actionable, and data-driven. Focus on business value, not technical details."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract text from response
            reasoning = message.content[0].text.strip()
            return reasoning
            
        except Exception as e:
            print(f"Warning: LLM reasoning failed: {e}")
            # Fallback to original reasoning
            return score.reasoning
    
    def analyze_portfolio(
        self,
        processes: List[Process],
        top_n: Optional[int] = None
    ) -> List[OpportunityScore]:
        """
        Analyze multiple processes and rank them
        
        Args:
            processes: List of processes to analyze
            top_n: Return only top N opportunities (None = all)
            
        Returns:
            Ranked list of OpportunityScores
        """
        print(f"Analyzing {len(processes)} processes...")
        
        # Analyze each process
        scores = []
        for i, process in enumerate(processes, 1):
            print(f"  [{i}/{len(processes)}] Analyzing: {process.name}")
            score = self.analyze_process(process, include_llm_reasoning=True)
            scores.append(score)
        
        # Sort by overall score
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Return top N if specified
        if top_n:
            return scores[:top_n]
        
        return scores
    
    def generate_executive_summary(
        self,
        scores: List[OpportunityScore],
        top_n: int = 5
    ) -> str:
        """
        Generate executive summary of top opportunities
        
        Args:
            scores: List of scored opportunities
            top_n: Number of top opportunities to highlight
            
        Returns:
            Executive summary text
        """
        top_opportunities = scores[:top_n]
        
        total_potential_savings = sum(s.estimated_annual_savings for s in top_opportunities)
        total_implementation_cost = sum(s.implementation_cost for s in top_opportunities)
        
        summary = f"""EXECUTIVE SUMMARY: AI Automation Opportunities

Analyzed {len(scores)} business processes and identified top {top_n} automation candidates.

TOP {top_n} OPPORTUNITIES:
"""
        
        for i, score in enumerate(top_opportunities, 1):
            summary += f"""
{i}. {score.process_name}
   Score: {score.overall_score:.1f}/100 | ROI: {score.roi_percentage:.0f}% | Payback: {score.payback_months:.1f}mo
   Annual Savings: ${score.estimated_annual_savings:,.0f} | Investment: ${score.implementation_cost:,.0f}
   Recommendation: {score.recommendation}
"""
        
        summary += f"""
PORTFOLIO FINANCIALS:
- Total Annual Savings Potential: ${total_potential_savings:,.0f}
- Total Implementation Investment: ${total_implementation_cost:,.0f}
- Portfolio ROI: {((total_potential_savings - total_implementation_cost) / total_implementation_cost * 100):.0f}%

RECOMMENDATION:
Start with the top 3 opportunities for immediate impact. Expected payback within {top_opportunities[0].payback_months:.0f}-{top_opportunities[2].payback_months:.0f} months.
"""
        
        return summary


# Test the agent
if __name__ == "__main__":
    from src.utils.data_loader import load_synthetic_processes
    
    print("🤖 Testing Analysis Agent with LLM")
    print("=" * 70)
    
    # Load test data
    processes = load_synthetic_processes()
    
    # Create agent
    agent = AnalysisAgent()
    
    # Test with single process
    print("\n1. Single Process Analysis:")
    print("-" * 70)
    test_process = processes[0]  # Invoice Processing
    score = agent.analyze_process(test_process, include_llm_reasoning=True)
    
    print(f"Process: {score.process_name}")
    print(f"Score: {score.overall_score:.1f}/100")
    print(f"Recommendation: {score.recommendation}")
    print(f"\nLLM-Enhanced Reasoning:")
    print(score.reasoning)
    
    # Test portfolio analysis (top 5)
    print("\n\n2. Portfolio Analysis (Top 5):")
    print("-" * 70)
    top_scores = agent.analyze_portfolio(processes, top_n=5)
    
    print("\nTop 5 Opportunities:")
    for i, s in enumerate(top_scores, 1):
        print(f"{i}. {s.process_name}: {s.overall_score:.1f}/100 ({s.recommendation})")
    
    # Generate executive summary
    print("\n\n3. Executive Summary:")
    print("=" * 70)
    summary = agent.generate_executive_summary(top_scores)
    print(summary)