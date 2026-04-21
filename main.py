import os
import sys
from pathlib import Path

# Add src to path for discoverability
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from aether.core.engine import query_aether

if __name__ == "__main__":
    test_query = "What is the relationship between base_scout.py and scout_core.py?"
    
    print(f"Querying Aether: {test_query}\n")
    try:
        result = query_aether(test_query)
        print(f"RESULT:\n{result}")
    except Exception as e:
        print(f"Error: {e}")
