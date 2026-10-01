import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import check  # noqa: E402


class StructureCheckTests(unittest.TestCase):
    def test_flags_long_functions_many_params_and_bare_except(self):
        body = "\n".join(["    x = 1"] * 60)
        source = f"def long():\n{body}\n\ndef wide(a, b, c, d, e, f):\n    pass\n\ntry:\n    pass\nexcept:\n    pass\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
            handle.write(source)
        errors = check.python_errors(Path(handle.name))
        Path(handle.name).unlink()
        self.assertEqual(len(errors), 3, errors)


if __name__ == "__main__":
    unittest.main()
