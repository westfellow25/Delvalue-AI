"""
Database module for DelValue AI
Handles persistence of processes, scores, and decision traces
"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import json

from src.models.process import Process, OpportunityScore, DecisionTrace


class Database:
    """SQLite database for DelValue AI"""
    
    def __init__(self, db_path: str = "data/delvalue.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Processes table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS processes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            frequency TEXT NOT NULL,
            duration_minutes REAL NOT NULL,
            annual_volume INTEGER NOT NULL,
            people_involved INTEGER NOT NULL,
            hourly_cost REAL NOT NULL,
            systems_used TEXT,
            pain_points TEXT,
            stakeholders TEXT,
            dependencies TEXT,
            documentation_quality TEXT,
            sop_exists INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            source TEXT
        )
        """)
        
        # Opportunity scores table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunity_scores (
            opportunity_id TEXT PRIMARY KEY,
            process_id TEXT NOT NULL,
            process_name TEXT NOT NULL,
            feasibility_score REAL NOT NULL,
            value_score REAL NOT NULL,
            risk_score REAL NOT NULL,
            overall_score REAL NOT NULL,
            estimated_annual_savings REAL NOT NULL,
            implementation_cost REAL NOT NULL,
            roi_percentage REAL NOT NULL,
            payback_months REAL NOT NULL,
            risk_level TEXT NOT NULL,
            risk_factors TEXT,
            automation_feasibility TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            reasoning TEXT NOT NULL,
            confidence_level REAL NOT NULL,
            analyzed_at TEXT NOT NULL,
            FOREIGN KEY (process_id) REFERENCES processes (id)
        )
        """)
        
        # Decision traces table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_traces (
            trace_id TEXT PRIMARY KEY,
            process_id TEXT NOT NULL,
            opportunity_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            decision_date TEXT NOT NULL,
            decision_maker TEXT,
            predicted_roi REAL NOT NULL,
            predicted_annual_savings REAL NOT NULL,
            predicted_implementation_cost REAL NOT NULL,
            predicted_payback_months REAL NOT NULL,
            actual_roi REAL,
            actual_annual_savings REAL,
            actual_implementation_cost REAL,
            actual_payback_months REAL,
            implementation_start_date TEXT,
            implementation_end_date TEXT,
            implementation_status TEXT,
            variance_roi REAL,
            variance_savings REAL,
            variance_cost REAL,
            lessons_learned TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (process_id) REFERENCES processes (id),
            FOREIGN KEY (opportunity_id) REFERENCES opportunity_scores (opportunity_id)
        )
        """)
        
        self.conn.commit()
    
    def save_process(self, process: Process) -> bool:
        """
        Save or update a process
        
        Args:
            process: Process object to save
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO processes (
                id, name, description, category, frequency,
                duration_minutes, annual_volume, people_involved, hourly_cost,
                systems_used, pain_points, stakeholders, dependencies,
                documentation_quality, sop_exists, created_at, updated_at, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                process.id,
                process.name,
                process.description,
                process.category,
                process.frequency,
                process.duration_minutes,
                process.annual_volume,
                process.people_involved,
                process.hourly_cost,
                json.dumps(process.systems_used),
                json.dumps(process.pain_points),
                json.dumps(process.stakeholders),
                json.dumps(process.dependencies),
                process.documentation_quality,
                1 if process.sop_exists else 0,
                process.created_at.isoformat(),
                process.updated_at.isoformat() if process.updated_at else None,
                process.source
            ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving process: {e}")
            return False
    
    def get_process(self, process_id: str) -> Optional[Process]:
        """
        Get a process by ID
        
        Args:
            process_id: Process ID
            
        Returns:
            Process object or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM processes WHERE id = ?", (process_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_process(row)
    
    def get_all_processes(self) -> List[Process]:
        """
        Get all processes
        
        Returns:
            List of Process objects
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM processes ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        return [self._row_to_process(row) for row in rows]
    
    def delete_process(self, process_id: str) -> bool:
        """
        Delete a process
        
        Args:
            process_id: Process ID
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("DELETE FROM processes WHERE id = ?", (process_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting process: {e}")
            return False
    
    def save_opportunity_score(self, score: OpportunityScore) -> bool:
        """
        Save or update an opportunity score
        
        Args:
            score: OpportunityScore object
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO opportunity_scores (
                opportunity_id, process_id, process_name,
                feasibility_score, value_score, risk_score, overall_score,
                estimated_annual_savings, implementation_cost,
                roi_percentage, payback_months,
                risk_level, risk_factors,
                automation_feasibility, recommendation, reasoning,
                confidence_level, analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score.opportunity_id,
                score.process_id,
                score.process_name,
                score.feasibility_score,
                score.value_score,
                score.risk_score,
                score.overall_score,
                score.estimated_annual_savings,
                score.implementation_cost,
                score.roi_percentage,
                score.payback_months,
                score.risk_level,
                json.dumps(score.risk_factors),
                score.automation_feasibility,
                score.recommendation,
                score.reasoning,
                score.confidence_level,
                score.analyzed_at.isoformat()
            ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving opportunity score: {e}")
            return False
    
    def get_opportunity_scores(self, process_id: Optional[str] = None) -> List[OpportunityScore]:
        """
        Get opportunity scores
        
        Args:
            process_id: Optional process ID to filter by
            
        Returns:
            List of OpportunityScore objects
        """
        cursor = self.conn.cursor()
        
        if process_id:
            cursor.execute(
                "SELECT * FROM opportunity_scores WHERE process_id = ? ORDER BY overall_score DESC",
                (process_id,)
            )
        else:
            cursor.execute("SELECT * FROM opportunity_scores ORDER BY overall_score DESC")
        
        rows = cursor.fetchall()
        return [self._row_to_opportunity_score(row) for row in rows]
    
    def save_decision_trace(self, trace: DecisionTrace) -> bool:
        """
        Save or update a decision trace
        
        Args:
            trace: DecisionTrace object
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO decision_traces (
                trace_id, process_id, opportunity_id,
                decision, decision_date, decision_maker,
                predicted_roi, predicted_annual_savings,
                predicted_implementation_cost, predicted_payback_months,
                actual_roi, actual_annual_savings,
                actual_implementation_cost, actual_payback_months,
                implementation_start_date, implementation_end_date,
                implementation_status,
                variance_roi, variance_savings, variance_cost,
                lessons_learned, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trace.trace_id,
                trace.process_id,
                trace.opportunity_id,
                trace.decision,
                trace.decision_date.isoformat(),
                trace.decision_maker,
                trace.predicted_roi,
                trace.predicted_annual_savings,
                trace.predicted_implementation_cost,
                trace.predicted_payback_months,
                trace.actual_roi,
                trace.actual_annual_savings,
                trace.actual_implementation_cost,
                trace.actual_payback_months,
                trace.implementation_start_date.isoformat() if trace.implementation_start_date else None,
                trace.implementation_end_date.isoformat() if trace.implementation_end_date else None,
                trace.implementation_status,
                trace.variance_roi,
                trace.variance_savings,
                trace.variance_cost,
                trace.lessons_learned,
                trace.created_at.isoformat(),
                trace.updated_at.isoformat() if trace.updated_at else None
            ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving decision trace: {e}")
            return False
    
    def _row_to_process(self, row) -> Process:
        """Convert database row to Process object"""
        return Process(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            category=row['category'],
            frequency=row['frequency'],
            duration_minutes=row['duration_minutes'],
            annual_volume=row['annual_volume'],
            people_involved=row['people_involved'],
            hourly_cost=row['hourly_cost'],
            systems_used=json.loads(row['systems_used']) if row['systems_used'] else [],
            pain_points=json.loads(row['pain_points']) if row['pain_points'] else [],
            stakeholders=json.loads(row['stakeholders']) if row['stakeholders'] else [],
            dependencies=json.loads(row['dependencies']) if row['dependencies'] else [],
            documentation_quality=row['documentation_quality'],
            sop_exists=bool(row['sop_exists']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            source=row['source']
        )
    
    def _row_to_opportunity_score(self, row) -> OpportunityScore:
        """Convert database row to OpportunityScore object"""
        return OpportunityScore(
            opportunity_id=row['opportunity_id'],
            process_id=row['process_id'],
            process_name=row['process_name'],
            feasibility_score=row['feasibility_score'],
            value_score=row['value_score'],
            risk_score=row['risk_score'],
            overall_score=row['overall_score'],
            estimated_annual_savings=row['estimated_annual_savings'],
            implementation_cost=row['implementation_cost'],
            roi_percentage=row['roi_percentage'],
            payback_months=row['payback_months'],
            risk_level=row['risk_level'],
            risk_factors=json.loads(row['risk_factors']) if row['risk_factors'] else [],
            automation_feasibility=row['automation_feasibility'],
            recommendation=row['recommendation'],
            reasoning=row['reasoning'],
            confidence_level=row['confidence_level'],
            analyzed_at=datetime.fromisoformat(row['analyzed_at'])
        )
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Test the database
if __name__ == "__main__":
    from src.models.process import ProcessCategory
    
    print("🗄️ Testing Database")
    print("=" * 70)
    
    # Create database
    db = Database("data/test.db")
    
    # Create test process
    test_process = Process(
        name="Test Process",
        description="This is a test process for database validation",
        category=ProcessCategory.FINANCE,
        frequency="daily",
        duration_minutes=30,
        annual_volume=250,
        people_involved=3,
        hourly_cost=50,
        systems_used=["System A", "System B"],
        pain_points=["Pain 1", "Pain 2"],
        stakeholders=["Person 1", "Person 2"],
        source="test"
    )
    
    # Test save
    print("\n1. Testing save_process()...")
    success = db.save_process(test_process)
    print(f"   {'✅' if success else '❌'} Save: {success}")
    
    # Test get
    print("\n2. Testing get_process()...")
    retrieved = db.get_process(test_process.id)
    print(f"   {'✅' if retrieved else '❌'} Retrieved: {retrieved.name if retrieved else 'None'}")
    
    # Test get_all
    print("\n3. Testing get_all_processes()...")
    all_processes = db.get_all_processes()
    print(f"   ✅ Found {len(all_processes)} processes")
    
    # Test delete
    print("\n4. Testing delete_process()...")
    success = db.delete_process(test_process.id)
    print(f"   {'✅' if success else '❌'} Deleted: {success}")
    
    # Verify deletion
    all_processes = db.get_all_processes()
    print(f"   ✅ Remaining processes: {len(all_processes)}")
    
    db.close()
    
    print("\n✅ Database tests complete!")