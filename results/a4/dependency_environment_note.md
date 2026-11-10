# Dependency/environment note — preserved execution caveat

The complete A2+A4 test suite passed in the provided Python 3.13.5 execution environment using the exact package versions listed in `requirements-a4.lock`.

Two environment-level limitations were observed and retained:

1. `python -m pip check` reports an unrelated pre-existing global environment conflict: `moviepy 2.2.1` requires `pillow<12.0,>=9.2.0`, while the shared environment has Pillow 12.3.0. Neither MoviePy nor Pillow is a dependency of this project or used by the A4 application/tests.
2. A clean isolated virtual environment was created, but installing the lock file could not be completed because DNS/network access to the package index was unavailable in the execution environment. The isolated-install attempt is not represented as successful.

The project tests and local Uvicorn smoke check were executed in the provided environment. A user cloning the repository should install `requirements.txt` in a network-enabled environment and rerun all checks. Do not interpret this note as production dependency certification.
