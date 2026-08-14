import sys
import unittest
class TestInspect(unittest.TestCase):
    def test_inspect(self):
        print("SYS MODULES FASTAPI:", sys.modules.get('fastapi'))
