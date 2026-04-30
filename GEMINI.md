# Shell discipline
The default operating environment for this project is Windows PowerShell.

Do not use Unix/bash-only commands unless the user explicitly says they are using Git Bash, WSL, Linux, or macOS.

Avoid these by default:
- grep
- sed
- awk
- find
- xargs
- rm -rf
- cat when PowerShell-native commands are better
- chmod/chown
- curl syntax that only works in bash

Use PowerShell-native commands instead.

Examples:
- Instead of:
  ls -R . | grep -i "lesson\|learned"

  Use:
  Get-ChildItem -Recurse | Where-Object { $_.Name -match "lesson|learned" }

- Instead of:
  grep -R "df-messenger" -n .

  Use:
  Get-ChildItem -Recurse -File | Select-String -Pattern "df-messenger"

- Instead of:
  cat file.txt

  Use:
  Get-Content file.txt

- Instead of:
  rm -rf folder

  Use:
  Remove-Item folder -Recurse -Force

- Instead of:
  find . -name "*.ts"

  Use:
  Get-ChildItem -Recurse -Filter "*.ts"

Rule:
Before giving or running shell commands, identify the active shell. If unknown, assume Windows PowerShell.

Failure rule:
If a command fails because it is bash/Linux-specific, do not retry the same command. Translate it to PowerShell, explain the correction briefly, and continue.

Search exclusion rule:
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
