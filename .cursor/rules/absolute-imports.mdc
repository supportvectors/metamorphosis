---
description:
globs:
alwaysApply: false
---
# Cursor AI Rules: Absolute Imports Standard
# Universal rule for enforcing absolute imports across all Python projects

## Python Import Standards

### ABSOLUTE IMPORTS ONLY
- **NEVER use relative imports** (imports starting with `.` or `..`)
- **ALWAYS use absolute imports** for internal modules starting with your project's root package name
- **Examples of CORRECT imports:**
  ```python
  from myproject.exceptions import CustomException
  from myproject.utils import helper_function
  from myproject.models.user import User
  from myproject import config
  ```
- **Examples of INCORRECT imports (NEVER USE):**
  ```python
  from .exceptions import CustomException          # ❌ WRONG
  from ..utils import helper_function             # ❌ WRONG
  from . import config                           # ❌ WRONG
  from ...models.user import User                # ❌ WRONG
  ```

### Why Absolute Imports?
- **Better IDE support**: Autocomplete, go-to-definition, refactoring
- **Clearer dependencies**: Explicit module paths show relationships
- **Easier refactoring**: Moving files doesn't break imports
- **Consistent across team**: No confusion about import styles
- **Tool compatibility**: Works better with linters, formatters, and analyzers

### Import Organization
1. **Standard library imports** (os, pathlib, typing, etc.)
2. **Third-party imports** (requests, pandas, fastapi, etc.)
3. **Internal absolute imports** (your_project.*)
4. **Separate each group with a blank line**

### When suggesting code changes:
- If you see a relative import, immediately convert it to absolute import
- Always use the full `project_name.module.submodule` path
- Ensure imports are grouped and sorted correctly
- Add missing imports with absolute paths

## Implementation Guidelines

### For New Projects:
- Decide on your root package name (usually your project name)
- Configure your IDE/editor to prefer absolute imports
- Set up linting rules to catch relative imports
- Use tools like `ruff` or `flake8` with `flake8-tidy-imports`

### For Existing Projects:
- Gradually convert relative imports to absolute imports
- Use automated tools where possible (`ruff --fix`, `autoflake`, etc.)
- Update your development environment configuration
- Add linting rules to prevent future relative imports

### Project Structure Recommendations:
```
your-project/
├── src/
│   └── your_project/          # Root package
│       ├── __init__.py
│       ├── main.py
│       └── submodule/
│           ├── __init__.py
│           └── module.py
├── tests/
│   └── test_*.py
├── pyproject.toml
└── README.md
```

### Linting Configuration

#### Ruff Configuration (ruff.toml or pyproject.toml):
```toml
[tool.ruff.lint]
select = ["TID"]  # Enable tidy imports

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"  # Ban ALL relative imports
```

#### Flake8 Configuration (.flake8):
```ini
[flake8]
select = TID
ban-relative-imports = true
```

### IDE Configuration

#### VS Code (settings.json):
```json
{
  "python.analysis.autoImportCompletions": true,
  "ruff.lint.select": ["TID"],
  "ruff.lint.flake8-tidy-imports": {
    "ban-relative-imports": "all"
  }
}
```

## Code Quality Standards

### Testing
- All new functionality must include corresponding tests
- Test files should be in the `tests/` directory
- Test imports should use absolute paths: `from your_project.module import Class`

### Documentation
- All public methods and classes must have docstrings
- Use type hints for all function parameters and return values
- Follow Google/NumPy docstring format

### Error Handling
- Use custom exceptions from your project's exception module
- Always provide meaningful error messages
- Log errors appropriately using your configured logger

## When writing or suggesting code:
1. **FIRST** check all imports and convert any relative imports to absolute
2. Ensure proper import grouping and sorting
3. Add type hints where missing
4. Include appropriate error handling
5. Add or update docstrings for new/modified functions
6. Consider test coverage implications

## Common Patterns to Convert:

### Module Imports:
```python
# ❌ WRONG (relative)
from . import utils
from .config import settings

# ✅ CORRECT (absolute)
from myproject import utils
from myproject.config import settings
```

### Class/Function Imports:
```python
# ❌ WRONG (relative)
from .models import User
from ..services.auth import authenticate

# ✅ CORRECT (absolute)
from myproject.models import User
from myproject.services.auth import authenticate
```

### Sibling Module Imports:
```python
# ❌ WRONG (relative)
from .helper import utility_function

# ✅ CORRECT (absolute)  
from myproject.utils.helper import utility_function
```

Remember: **ABSOLUTE IMPORTS ARE MANDATORY** - this is non-negotiable for maintaining code quality and developer experience across all projects.

---

*Apply this rule consistently across all Python projects for better maintainability, IDE support, and team collaboration.*
