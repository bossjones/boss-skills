---
description: A skill with inline code blocks
allowed-tools:
    - Read
    - Bash
---

# Bad Skill

This skill has executable code inline.

## Steps

### 1. Run the linter

Execute the following script:

```bash
#!/bin/bash
set -euo pipefail
find . -name "*.ts" -exec eslint {} \;
echo "Linting complete"
```

### 2. Fix issues

Run the fixer:

```python
import subprocess
result = subprocess.run(["eslint", "--fix", "."], capture_output=True)
print(result.stdout.decode())
```
