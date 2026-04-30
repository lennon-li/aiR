## Windows PowerShell shell mismatch

Mistake:
The agent used Linux/bash commands in a Windows PowerShell environment, for example:
ls -R . | grep -i "lesson\|learned"

Error:
PowerShell does not recognize grep by default.

Correction:
Default to PowerShell commands unless the user explicitly states Git Bash, WSL, Linux, or macOS.

Correct command:
Get-ChildItem -Recurse | Where-Object { $_.Name -match "lesson|learned" }

Prevention:
Before running commands, check shell assumptions. Do not use grep/sed/awk/find/xargs/rm -rf unless bash/Linux is confirmed.

When searching the repo, exclude generated/dependency folders by default:
- node_modules
- .next
- dist
- build
- .git
- renv
- .Rproj.user
- __pycache__

Never run broad recursive text searches over the whole repo without excluding dependency/build directories.
