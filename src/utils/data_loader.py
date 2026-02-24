"""
Utility functions for loading and managing synthetic test data
"""

import json
from pathlib import Path
from typing import List
from src.models.process import Process, ProcessCategory


def load_synthetic_processes(filepath: str = "data/synthetic/processes.json") -> List[Process]:
    """
    Load synthetic processes from JSON file
    
    Args:
        filepath: Path to JSON file with process data
        
    Returns:
        List of Process objects
    """
    file_path = Path(filepath)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Synthetic data file not found: {filepath}")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    processes = []
    for item in data:
        try:
            process = Process(**item)
            processes.append(process)
        except Exception as e:
            print(f"Error loading process '{item.get('name', 'Unknown')}': {e}")
            continue
    
    return processes


# Test
if __name__ == "__main__":
    processes = load_synthetic_processes()
    print(f"✅ Loaded {len(processes)} synthetic processes")
    print("\nProcesses:")
    for i, p in enumerate(processes, 1):
        print(f"{i}. {p.name} ({p.category}) - {p.annual_volume:,}/year")