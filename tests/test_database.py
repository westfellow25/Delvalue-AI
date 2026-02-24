"""
Tests for Database operations
"""

import pytest
import tempfile
import os
from src.utils.database import Database
from src.models.process import Process, ProcessCategory

class TestDatabase:
    """Test Database operations"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = Database(path)
        yield db
        db.close()
        os.unlink(path)
    
    @pytest.fixture
    def sample_process(self):
        """Create sample process"""
        return Process(
            name="Test Process",
            description="This is a test process for database operations",
            category=ProcessCategory.FINANCE,
            frequency="daily",
            duration_minutes=30,
            annual_volume=1000,
            people_involved=5,
            hourly_cost=50.0,
            systems_used=["System A"],
            pain_points=["Pain 1"],
            stakeholders=["Person 1"]
        )
    
    def test_save_process(self, temp_db, sample_process):
        """Test saving a process"""
        result = temp_db.save_process(sample_process)
        
        assert result is True
    
    def test_get_process(self, temp_db, sample_process):
        """Test retrieving a process"""
        temp_db.save_process(sample_process)
        
        retrieved = temp_db.get_process(sample_process.id)
        
        assert retrieved is not None
        assert retrieved.name == sample_process.name
        assert retrieved.id == sample_process.id
    
    def test_get_all_processes(self, temp_db, sample_process):
        """Test retrieving all processes"""
        temp_db.save_process(sample_process)
        
        all_processes = temp_db.get_all_processes()
        
        assert len(all_processes) >= 1
        assert any(p.id == sample_process.id for p in all_processes)
    
    def test_delete_process(self, temp_db, sample_process):
        """Test deleting a process"""
        temp_db.save_process(sample_process)
        
        result = temp_db.delete_process(sample_process.id)
        
        assert result is True
        
        retrieved = temp_db.get_process(sample_process.id)
        assert retrieved is None
    
    def test_update_process(self, temp_db, sample_process):
        """Test updating a process"""
        temp_db.save_process(sample_process)
        
        # Modify and save again
        sample_process.name = "Updated Name"
        temp_db.save_process(sample_process)
        
        retrieved = temp_db.get_process(sample_process.id)
        assert retrieved.name == "Updated Name"
