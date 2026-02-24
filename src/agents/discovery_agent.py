"""
Discovery Agent - Document parsing and process extraction
Converts unstructured documents into structured Process data using LLM
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
import PyPDF2
import docx
from anthropic import Anthropic
from dotenv import load_dotenv

from src.models.process import Process, ProcessCategory

# Load environment
load_dotenv()


class DiscoveryAgent:
    """
    AI agent for discovering and extracting process information from documents
    
    Capabilities:
    - Parse PDF, DOCX, TXT files
    - Extract process information using LLM
    - Convert to structured Process model
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        """
        Initialize Discovery Agent
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required for Discovery Agent")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = model
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            raise Exception(f"Error reading PDF: {e}")
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from DOCX file
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Extracted text content
        """
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            raise Exception(f"Error reading DOCX: {e}")
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """
        Extract text from TXT file
        
        Args:
            file_path: Path to TXT file
            
        Returns:
            File content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            raise Exception(f"Error reading TXT: {e}")
    
    def extract_text_from_file(self, file_path: str) -> str:
        """
        Auto-detect file type and extract text
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted text
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return self.extract_text_from_pdf(str(file_path))
        elif extension in ['.docx', '.doc']:
            return self.extract_text_from_docx(str(file_path))
        elif extension == '.txt':
            return self.extract_text_from_txt(str(file_path))
        else:
            raise ValueError(f"Unsupported file type: {extension}")
    
    def extract_process_from_text(
        self,
        text: str,
        source: Optional[str] = None
    ) -> Process:
        """
        Extract structured process information from text using LLM
        
        Args:
            text: Document text content
            source: Optional source identifier
            
        Returns:
            Structured Process object
        """
        prompt = f"""You are an expert business process analyst. Extract structured process information from the following document.

Document:
{text}

Your task: Extract a single business process from this document and output ONLY a valid JSON object with these exact fields:

{{
  "name": "Process name (string, max 200 chars)",
  "description": "Detailed process description (string, min 50 chars)",
  "category": "One of: finance, operations, sales, customer_service, hr, it, marketing, legal, other",
  "frequency": "How often it runs (e.g., 'daily', '100x/day', 'weekly', 'monthly')",
  "duration_minutes": <number>,
  "annual_volume": <number of executions per year>,
  "people_involved": <number>,
  "hourly_cost": <number, default 50 if unknown>,
  "systems_used": ["system1", "system2"],
  "pain_points": ["pain point 1", "pain point 2"],
  "stakeholders": ["stakeholder 1", "stakeholder 2"],
  "dependencies": ["dependency 1"],
  "sop_exists": true or false
}}

CRITICAL RULES:
1. Output ONLY the JSON object, no explanation before or after
2. All string values must use double quotes
3. Make reasonable estimates for missing numerical values
4. If frequency is vague, estimate annual_volume conservatively
5. duration_minutes should be average time per execution
6. Ensure the JSON is valid and can be parsed

Output the JSON now:"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract JSON from response
            response_text = message.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            # Parse JSON
            import json
            process_data = json.loads(response_text)
            
            # Add source
            if source:
                process_data['source'] = source
            
            # Create Process object
            process = Process(**process_data)
            
            return process
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse LLM response as JSON: {e}\nResponse: {response_text}")
        except Exception as e:
            raise Exception(f"Error extracting process: {e}")
    
    def discover_from_file(self, file_path: str) -> Process:
        """
        Complete discovery workflow: file → text → process
        
        Args:
            file_path: Path to document file
            
        Returns:
            Extracted Process object
        """
        print(f"📄 Reading file: {file_path}")
        
        # Extract text
        text = self.extract_text_from_file(file_path)
        
        print(f"📝 Extracted {len(text)} characters")
        print(f"🤖 Analyzing with LLM...")
        
        # Extract process
        process = self.extract_process_from_text(
            text,
            source=f"file:{Path(file_path).name}"
        )
        
        print(f"✅ Discovered process: {process.name}")
        
        return process
    
    def discover_from_text_input(self, text: str) -> Process:
        """
        Discover process from direct text input
        
        Args:
            text: Process description text
            
        Returns:
            Extracted Process object
        """
        print(f"🤖 Analyzing text input ({len(text)} chars)...")
        
        process = self.extract_process_from_text(
            text,
            source="manual_input"
        )
        
        print(f"✅ Discovered process: {process.name}")
        
        return process


# Test the agent
if __name__ == "__main__":
    import sys
    
    print("🔍 Testing Discovery Agent")
    print("=" * 70)
    
    # Check if API key is available
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("\n❌ ANTHROPIC_API_KEY not configured")
        print("Discovery Agent requires valid API key to function.")
        print("\nTo test:")
        print("1. Get API key from: https://console.anthropic.com/settings/keys")
        print("2. Update .env file with your key")
        print("3. Run this test again")
        sys.exit(1)
    
    try:
        # Create agent
        agent = DiscoveryAgent()
        
        # Test with sample text
        sample_text = """
        Process: Monthly Expense Report Reconciliation
        
        Our finance team manually reconciles employee expense reports every month.
        The process involves:
        
        1. Collecting expense reports from 150 employees via email
        2. Manually entering data into Excel spreadsheets
        3. Cross-checking receipts against credit card statements
        4. Routing to managers for approval
        5. Processing reimbursements through payroll system
        
        This takes approximately 45 minutes per report, and we process about 1800 reports annually.
        The finance team (5 people) spends significant time on this.
        
        Current systems used: Email, Excel, Concur (expense management), Payroll system
        
        Pain points:
        - Manual data entry is error-prone
        - Lost receipts cause delays
        - Inconsistent policy enforcement
        - Slow approval cycles
        
        Stakeholders: CFO, Finance Manager, Department Heads, All Employees
        """
        
        print("\n1. Testing text-based discovery:")
        print("-" * 70)
        
        process = agent.discover_from_text_input(sample_text)
        
        print(f"\nExtracted Process:")
        print(f"  Name: {process.name}")
        print(f"  Category: {process.category}")
        print(f"  Annual Volume: {process.annual_volume:,}")
        print(f"  Duration: {process.duration_minutes} min")
        print(f"  People: {process.people_involved}")
        print(f"  Systems: {', '.join(process.systems_used)}")
        print(f"  Pain Points: {len(process.pain_points)}")
        
        print("\n✅ Discovery Agent working!")
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)