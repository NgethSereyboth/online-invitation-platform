E-invitation-website installer hotfix: Python exit code 9009
===============================================================

The original setup could mistake the Windows Microsoft Store "python" or "py"
App Execution Alias for a working Python installation. The alias can exist even
when no usable Python interpreter is installed. When setup later tried to create
.venv, Windows returned exit code 9009 (command/interpreter unavailable).

This fixed setup:
- verifies that Python actually executes successfully;
- rejects broken Windows Store aliases;
- looks for Python installed outside PATH;
- installs Python 3.13 or falls back to Python 3.12 when needed;
- reports the exact Python command if a later Python operation fails.

You can safely run SETUP_EINVITE_COMPLETE.bat again. Git, Node.js, cloudflared,
and Docker already installed by the previous attempt will be detected/reused.
