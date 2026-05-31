import os
import sys

# Ensure backend package is importable as 'app'
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

import pytest

if __name__ == '__main__':
    raise SystemExit(pytest.main(["backend/tests", "-q"]))
