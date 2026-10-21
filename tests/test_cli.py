import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from label_support_gate.cli import evaluate


class GateTests(unittest.TestCase):
    def test_minimum_zero_empty_rows(self):
        self.assertEqual(evaluate('{"labels":["b","a"],"minimum":0}', ""),
                         {"status": "valid", "record_count": 0, "insufficient_label_indices": []})

    def test_ordered_indices_and_exact_unicode(self):
        policy = json.dumps({"labels": ["é", "e\u0301", "x"], "minimum": 2}, ensure_ascii=False)
        rows = '{"id":"秘密","label":"é"}\n'
        self.assertEqual(evaluate(policy, rows), {"status": "insufficient_support", "record_count": 1,
                         "insufficient_label_indices": [1, 2, 3]})

    def test_valid_count_and_crlf(self):
        self.assertEqual(evaluate('{"labels":["x"],"minimum":2}',
                                  '{"id":"1","label":"x"}\r\n{"id":"2","label":"x"}\r'),
                         {"status": "valid", "record_count": 2, "insufficient_label_indices": []})

    def test_reject_policy_shapes_and_boolean_minimum(self):
        for policy in ('{"labels":["x"],"minimum":true}', '{"labels":["x","x"],"minimum":0}',
                       '{"labels":[],"minimum":0}', '{"labels":["x"],"minimum":1000001}',
                       '{"labels":["x"],"minimum":0,"extra":1}', '{"labels":["x"],"minimum":0,"labels":["y"]}',
                       '{"labels":["\\ud800"],"minimum":0}', '{"labels":["x"],"minimum":NaN}'):
            with self.subTest(policy=policy):
                self.assertIsNone(evaluate(policy, '{"id":"1","label":"x"}'))

    def test_reject_bad_rows(self):
        policy = '{"labels":["x"],"minimum":0}'
        for rows in ('{"id":"1","label":"unknown"}', '{"id":"","label":"x"}',
                     '{"id":"1","label":"x"}\n{"id":"1","label":"x"}',
                     '{"id":"1","label":"x","extra":0}', '{"id":"1","label":"x","id":"2"}',
                     '\n', '{"id":"1","label":"x"}\n\n', '{"id":"1","label":"x"}\u2028'):
            with self.subTest(rows=rows):
                self.assertIsNone(evaluate(policy, rows))

    def test_deep_json_fails_closed(self):
        self.assertIsNone(evaluate('{"labels":[[[[[0]]]]],"minimum":0}', ''))
        self.assertIsNone(evaluate('{"labels":["x"],"minimum":0}', '{"id":"1","label":"x","nested":' + '[' * 2000 + '0' + ']' * 2000 + '}'))

    def test_invalid_policy_does_not_skip_rows_parser(self):
        # A malformed policy cannot make malformed rows look valid; public outcome is invalid.
        self.assertIsNone(evaluate('{', '{"id":"1","label":"x","id":"2"}'))


class InstalledCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.venv = cls.root / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(cls.venv)], check=True)
        cls.python = cls.venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cls.pip = cls.venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
        source = Path(__file__).resolve().parents[1]
        wheelhouse = cls.root / "wheelhouse"
        wheelhouse.mkdir()
        subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                        "--wheel-dir", str(wheelhouse), str(source)], check=True,
                       stdout=subprocess.DEVNULL)
        wheel = next(wheelhouse.glob("label_support_gate-*.whl"))
        subprocess.run([str(cls.pip), "install", "--no-index", "--no-deps", str(wheel)], check=True,
                       stdout=subprocess.DEVNULL)
        cls.exe = cls.venv / ("Scripts/label-support-gate.exe" if os.name == "nt" else "bin/label-support-gate")
        cls.policy = cls.root / "policy.json"
        cls.rows = cls.root / "rows.jsonl"
        cls.policy.write_text('{"labels":["x"],"minimum":1}', encoding="utf-8")
        cls.rows.write_text('{"id":"1","label":"x"}\n', encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run([str(self.exe), *map(str, args)], capture_output=True, text=True)

    def test_installed_import_and_version(self):
        out = subprocess.check_output([str(self.python), "-c", "import label_support_gate; print(label_support_gate.__version__)"])
        self.assertEqual(out.decode().strip(), "0.1.0")

    def test_installed_exit_codes(self):
        self.assertEqual(self.run_cli(self.policy, self.rows).returncode, 0)
        self.rows.write_text('', encoding="utf-8")
        self.assertEqual(self.run_cli(self.policy, self.rows).returncode, 1)
        self.policy.write_text('{', encoding="utf-8")
        self.assertEqual(self.run_cli(self.policy, self.rows).returncode, 2)

    def test_installed_help_and_invalid_argv_privacy(self):
        self.assertEqual(self.run_cli("--help").returncode, 0)
        self.assertEqual(self.run_cli("--bad", "secret-path").stdout, '{"status":"invalid_input"}\n')
        for args in (("secret-path", self.rows), (self.policy, self.rows, "extra")):
            result = self.run_cli(*args)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (2, '{"status":"invalid_input"}\n', ""))

    def test_invalid_file_output_never_leaks_inputs(self):
        self.policy.write_text('{"labels":["PRIVATE_LABEL"],"minimum":1}', encoding="utf-8")
        self.rows.write_text('{"id":"PRIVATE_ID","label":"unknown"}', encoding="utf-8")
        result = self.run_cli(self.policy, self.rows)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, '{"status":"invalid_input"}\n', ""))
        self.assertNotIn("PRIVATE", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
