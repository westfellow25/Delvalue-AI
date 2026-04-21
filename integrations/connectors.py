"""
Integration registry — central registry for all enterprise connectors.
Enables runtime configuration and connector discovery.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConnectorType(str, Enum):
    ERP = "erp"
    CRM = "crm"
    RPA = "rpa"
    ITSM = "itsm"
    HRIS = "hris"
    DOCUMENT_STORE = "document_store"


@dataclass
class ConnectorInfo:
    name: str
    type: ConnectorType
    vendor: str
    description: str
    config_schema: dict
    capabilities: list[str]


AVAILABLE_CONNECTORS: dict[str, ConnectorInfo] = {
    "sap": ConnectorInfo(
        name="SAP ERP",
        type=ConnectorType.ERP,
        vendor="SAP",
        description="Connect to SAP ECC/S4HANA for transaction and workflow event extraction",
        config_schema={
            "host": "string",
            "client": "string",
            "username": "string",
            "password": "string (secret)",
        },
        capabilities=["transaction_logs", "workflow_data", "master_data_processes"],
    ),
    "oracle_ebs": ConnectorInfo(
        name="Oracle E-Business Suite",
        type=ConnectorType.ERP,
        vendor="Oracle",
        description="Oracle EBS / Fusion for financial and HR process data",
        config_schema={
            "host": "string",
            "username": "string",
            "password": "string (secret)",
        },
        capabilities=["gl_transactions", "ap_ar_processes", "hr_lifecycle"],
    ),
    "salesforce": ConnectorInfo(
        name="Salesforce CRM",
        type=ConnectorType.CRM,
        vendor="Salesforce",
        description="Extract sales, service, and approval process data from Salesforce",
        config_schema={
            "instance_url": "string",
            "client_id": "string",
            "client_secret": "string (secret)",
            "username": "string",
            "password": "string (secret)",
            "security_token": "string (secret)",
        },
        capabilities=["opportunity_lifecycle", "case_management", "approval_processes"],
    ),
    "servicenow": ConnectorInfo(
        name="ServiceNow",
        type=ConnectorType.ITSM,
        vendor="ServiceNow",
        description="ITSM incident, change, and problem process extraction",
        config_schema={
            "instance": "string",
            "username": "string",
            "password": "string (secret)",
        },
        capabilities=["incident_lifecycle", "change_management", "problem_resolution"],
    ),
    "workday": ConnectorInfo(
        name="Workday HCM",
        type=ConnectorType.HRIS,
        vendor="Workday",
        description="HR processes: onboarding, offboarding, performance, comp",
        config_schema={
            "tenant": "string",
            "client_id": "string",
            "client_secret": "string (secret)",
        },
        capabilities=["onboarding", "offboarding", "comp_cycles"],
    ),
    "uipath": ConnectorInfo(
        name="UiPath Orchestrator",
        type=ConnectorType.RPA,
        vendor="UiPath",
        description="Pull RPA execution data; push automation recommendations as drafts",
        config_schema={
            "orchestrator_url": "string",
            "tenant": "string",
            "client_id": "string",
            "client_secret": "string (secret)",
        },
        capabilities=["bot_executions", "process_deployment", "outcome_tracking"],
    ),
    "automation_anywhere": ConnectorInfo(
        name="Automation Anywhere",
        type=ConnectorType.RPA,
        vendor="Automation Anywhere",
        description="Control Room integration for bot execution history",
        config_schema={
            "control_room_url": "string",
            "username": "string",
            "api_key": "string (secret)",
        },
        capabilities=["bot_executions", "workload_analytics"],
    ),
    "sharepoint": ConnectorInfo(
        name="Microsoft SharePoint",
        type=ConnectorType.DOCUMENT_STORE,
        vendor="Microsoft",
        description="Pull process documentation for NLP extraction",
        config_schema={
            "site_url": "string",
            "client_id": "string",
            "client_secret": "string (secret)",
        },
        capabilities=["document_ingestion", "wiki_mining"],
    ),
}


def list_connectors(connector_type: Optional[ConnectorType] = None) -> list[ConnectorInfo]:
    """List available connectors, optionally filtered by type."""
    if connector_type is None:
        return list(AVAILABLE_CONNECTORS.values())
    return [c for c in AVAILABLE_CONNECTORS.values() if c.type == connector_type]


def get_connector_info(name: str) -> Optional[ConnectorInfo]:
    return AVAILABLE_CONNECTORS.get(name)
