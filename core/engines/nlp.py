"""
DelValue AI — NLP / Document Processing Engine

Extracts processes, entities, and insights from unstructured documents
(PDFs, Word docs, emails, wikis). Combines classical NLP heuristics with
LLM-powered extraction for robustness.

Strategy:
  1. Document parsing (PDF/DOCX/TXT)
  2. Entity extraction (systems, people, departments, KPIs)
  3. Process classification (heuristic + LLM)
  4. Process extraction (LLM with structured JSON output)
  5. Complexity estimation from linguistic signals
"""

from __future__ import annotations

import io
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ComplexityAssessment:
    """Linguistic complexity analysis of a process description."""
    sentence_count: int
    word_count: int
    avg_sentence_length: float
    complexity_score: float  # 0-1
    decision_indicators: int
    conditional_indicators: int
    exception_indicators: int


@dataclass
class ExtractedEntities:
    systems: list[str]
    people: list[str]
    departments: list[str]
    metrics: list[str]
    tools: list[str]


class NLPEngine:
    """Document processing and NLP pipeline."""

    # Heuristic keyword sets
    SYSTEM_KEYWORDS = {
        "sap", "oracle", "salesforce", "servicenow", "workday", "netsuite",
        "jira", "confluence", "sharepoint", "dynamics", "peoplesoft",
        "tableau", "power bi", "splunk", "datadog",
    }

    CATEGORY_KEYWORDS = {
        "finance": {"invoice", "payment", "accounts payable", "accounts receivable",
                    "journal", "ledger", "reconciliation", "budget", "forecast"},
        "hr": {"onboarding", "offboarding", "payroll", "benefits", "recruitment",
               "interview", "performance review", "time off", "hiring"},
        "sales": {"lead", "opportunity", "quote", "proposal", "contract",
                  "deal", "pipeline", "commission", "customer acquisition"},
        "operations": {"inventory", "warehouse", "logistics", "scheduling",
                       "dispatch", "maintenance", "quality control"},
        "it": {"ticket", "incident", "deployment", "backup", "patch", "user access",
               "provisioning", "monitoring"},
        "customer_service": {"support ticket", "complaint", "chat", "call center",
                             "satisfaction", "resolution"},
        "procurement": {"purchase order", "vendor", "supplier", "sourcing",
                        "rfp", "rfq", "contract negotiation"},
        "legal": {"contract review", "compliance", "legal review", "nda",
                  "intellectual property", "dispute"},
        "marketing": {"campaign", "lead generation", "email marketing",
                      "social media", "content", "seo"},
    }

    DECISION_WORDS = {"if", "when", "unless", "depending", "decide", "choose",
                      "determine", "evaluate", "assess", "judgment"}
    CONDITIONAL_WORDS = {"if", "when", "unless", "while", "until", "otherwise",
                         "however", "depending", "case", "scenario"}
    EXCEPTION_WORDS = {"exception", "error", "fail", "issue", "problem",
                       "escalate", "reject", "deny", "flag"}

    def __init__(self, llm_client=None, default_model: str = "claude-sonnet-4-20250514"):
        self.llm_client = llm_client
        self.default_model = default_model

    # -- Document parsing --

    def extract_text(self, file_path: Path | str, content: Optional[bytes] = None) -> str:
        """
        Extract plain text from a document file.
        Supports PDF, DOCX, TXT.
        """
        path = Path(file_path) if file_path else None
        suffix = path.suffix.lower() if path else ""

        if content is None and path:
            content = path.read_bytes()

        if suffix == ".pdf":
            return self._extract_pdf(content)
        if suffix in (".docx",):
            return self._extract_docx(content)
        if suffix in (".txt", ".md"):
            return content.decode("utf-8", errors="ignore") if content else ""

        # Default: try to decode as text
        try:
            return content.decode("utf-8", errors="ignore") if content else ""
        except Exception as e:
            logger.warning(f"Failed to extract text from {path}: {e}")
            return ""

    @staticmethod
    def _extract_pdf(content: bytes) -> str:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("PyPDF2 not available; skipping PDF extraction")
            return ""
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""

    @staticmethod
    def _extract_docx(content: bytes) -> str:
        try:
            from docx import Document
            doc = Document(io.BytesIO(content))
            return "\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx not available; skipping DOCX extraction")
            return ""
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return ""

    # -- Entity extraction --

    def extract_entities(self, text: str) -> ExtractedEntities:
        """Extract named entities from process description text."""
        lower = text.lower()

        # Systems — keyword match
        systems = [s for s in self.SYSTEM_KEYWORDS if s in lower]

        # People — capitalized proper nouns following common patterns
        people = re.findall(
            r"\b(?:Mr\.|Ms\.|Dr\.)?\s*([A-Z][a-z]+ [A-Z][a-z]+)\b", text
        )
        # Filter out known non-person patterns
        people = [p for p in set(people) if not any(
            kw in p.lower() for kw in ["new york", "san francisco", "los angeles"]
        )][:20]

        # Departments
        dept_patterns = [
            r"\b(accounting|finance|hr|human resources|sales|marketing|"
            r"operations|procurement|legal|it|engineering|support|"
            r"customer service|logistics|supply chain)\s+(?:department|team)?\b"
        ]
        departments = []
        for pattern in dept_patterns:
            departments.extend(re.findall(pattern, lower))
        departments = list(set(departments))[:10]

        # Metrics/KPIs — patterns like "X%" or "$X" or "X hours"
        metrics = re.findall(
            r"\b\d+(?:\.\d+)?\s*(?:%|hours?|days?|minutes?|dollars?|\$|€|£)\b",
            text,
        )[:10]

        # Tools — quoted strings, TitleCase words
        tools = re.findall(r'"([A-Z][A-Za-z0-9\- ]+)"', text)[:10]

        return ExtractedEntities(
            systems=systems,
            people=people,
            departments=departments,
            metrics=metrics,
            tools=tools,
        )

    # -- Category classification --

    def classify_category(self, text: str) -> tuple[str, float]:
        """
        Classify process into a category using keyword matching.
        Returns (category, confidence).
        """
        lower = text.lower()
        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in lower)
            if hits > 0:
                scores[category] = hits

        if not scores:
            return "operations", 0.3

        total = sum(scores.values())
        best_cat = max(scores, key=scores.get)
        confidence = scores[best_cat] / total
        return best_cat, confidence

    # -- Complexity analysis --

    def analyze_complexity(self, text: str) -> ComplexityAssessment:
        """Estimate process complexity from linguistic cues."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        words = re.findall(r"\b\w+\b", text.lower())

        word_count = len(words)
        sentence_count = len(sentences)
        avg_sent_len = word_count / max(sentence_count, 1)

        decision_hits = sum(1 for w in words if w in self.DECISION_WORDS)
        conditional_hits = sum(1 for w in words if w in self.CONDITIONAL_WORDS)
        exception_hits = sum(1 for w in words if w in self.EXCEPTION_WORDS)

        # Normalize to 0-1 complexity score
        complexity = (
            0.30 * min(avg_sent_len / 30, 1.0)
            + 0.25 * min(decision_hits / 10, 1.0)
            + 0.25 * min(conditional_hits / 10, 1.0)
            + 0.20 * min(exception_hits / 5, 1.0)
        )

        return ComplexityAssessment(
            sentence_count=sentence_count,
            word_count=word_count,
            avg_sentence_length=avg_sent_len,
            complexity_score=complexity,
            decision_indicators=decision_hits,
            conditional_indicators=conditional_hits,
            exception_indicators=exception_hits,
        )

    # -- LLM-powered extraction --

    EXTRACTION_SYSTEM_PROMPT = """You are a business process analyst. Extract structured process information from the provided document.

Return ONLY valid JSON matching this schema (no markdown, no commentary):
{
  "processes": [
    {
      "name": "string (short, action-oriented)",
      "description": "string (2-3 sentences)",
      "category": "finance|hr|operations|sales|marketing|it|legal|procurement|supply_chain|customer_service|compliance|r_and_d",
      "frequency": "real_time|hourly|daily|weekly|monthly|quarterly|annually|ad_hoc",
      "duration_minutes": number,
      "annual_volume": number,
      "people_involved": number,
      "hourly_cost": number,
      "systems_used": ["string"],
      "pain_points": ["string"],
      "stakeholders": ["string"],
      "documentation_quality": "none|poor|basic|good|excellent",
      "sop_exists": boolean,
      "num_decision_points": number,
      "num_exceptions": number,
      "requires_judgment": boolean,
      "structured_data_pct": number (0-1)
    }
  ]
}

If values aren't explicitly stated, estimate reasonably based on context. Keep estimates conservative."""

    def extract_processes_from_text(
        self,
        text: str,
        max_processes: int = 10,
        model: Optional[str] = None,
    ) -> list[dict]:
        """
        Use LLM to extract structured process information from text.
        Falls back to empty list if no LLM client configured.
        """
        if not self.llm_client:
            logger.warning("No LLM client — cannot perform LLM extraction")
            return []

        truncated = text[:30_000]  # limit input size

        try:
            response = self.llm_client.messages.create(
                model=model or self.default_model,
                max_tokens=4096,
                temperature=0.2,
                system=self.EXTRACTION_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Extract up to {max_processes} business processes from this document. "
                        f"Return JSON only.\n\n<document>\n{truncated}\n</document>"
                    ),
                }],
            )
            raw = response.content[0].text if response.content else ""
            # Clean up potential markdown fences
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            data = json.loads(raw)
            return data.get("processes", [])
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return []

    def enrich_process(self, process_data: dict, description: str) -> dict:
        """
        Enrich a process dict with NLP-derived fields.
        Adds structured_data_pct, requires_judgment, etc. if not present.
        """
        complexity = self.analyze_complexity(description)
        entities = self.extract_entities(description)

        if "systems_used" not in process_data or not process_data["systems_used"]:
            process_data["systems_used"] = entities.systems

        if "stakeholders" not in process_data or not process_data["stakeholders"]:
            process_data["stakeholders"] = entities.departments

        if "num_decision_points" not in process_data:
            process_data["num_decision_points"] = complexity.decision_indicators

        if "num_exceptions" not in process_data:
            process_data["num_exceptions"] = complexity.exception_indicators

        if "requires_judgment" not in process_data:
            process_data["requires_judgment"] = complexity.decision_indicators > 3

        if "structured_data_pct" not in process_data:
            process_data["structured_data_pct"] = max(0.3, 1.0 - complexity.complexity_score * 0.5)

        return process_data
