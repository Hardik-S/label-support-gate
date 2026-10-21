# Local acceptance

From the repository root, use a new virtual environment and an offline, noneditable install. The acceptance helper performs its own checks in a further temporary environment and imports the installed package rather than the source tree.

```powershell
py -3.10 -m venv .accept-venv
.\.accept-venv\Scripts\python.exe -m pip install --no-index --no-deps --no-build-isolation .
.\.accept-venv\Scripts\python.exe acceptance.py
```

The test suite creates a fresh temporary virtual environment, installs the project noneditably, checks package import/version and command exit codes 0, 1, and 2, and exercises the installed command's help, invalid arguments, and privacy behavior. CI repeats this on Ubuntu and Windows using Python 3.10 and 3.13.
