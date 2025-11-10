#!/usr/bin/env python3

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bench.generate.src.generation_controller import main

if __name__ == "__main__":
    main()
