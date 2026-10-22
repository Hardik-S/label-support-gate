# Local acceptance

From the repository root, use a new virtual environment. The setup step downloads the build backend; the subsequent source install is noneditable and uses that installed backend without index access. Runtime checks are offline. The acceptance helper performs its own checks in a further temporary environment and imports the installed package rather than the source tree.

```powershell
python -m venv .accept-venv
.\.accept-venv\Scripts\python.exe -m pip install setuptools wheel
.\.accept-venv\Scripts\python.exe -m pip install --no-index --no-deps --no-build-isolation .
.\.accept-venv\Scripts\python.exe acceptance.py
```

The test suite creates a fresh temporary virtual environment, installs the project noneditably, checks package import/version and command exit codes 0, 1, and 2, and exercises the installed command's help, invalid arguments, and privacy behavior. CI repeats this on Ubuntu and Windows using Python 3.10 and 3.13.
