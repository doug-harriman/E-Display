# AI Agent Instructions for mizuno-chip

## Project Overview
This project generates images for an E-Ink display.

## Project Structure
```
arduino/                  # Arduino code for E-Ink display
docs/                     # Documentation files
kindle/                   # Kindle-specific code and assets, no longer used.
server/                   # Backend server code
trmnl-7.5in-diy-kit/      # Terminal E-Ink documentation and mechanical files, not used.
```

The remaining instructions apply only to the `server/` directory.

## Environment Setup
- **Python**: 3.13 (see `.python-version`)
- **Package manager**: uv (see `pyproject.toml`)

## Development Standards

### Package Management
Use UV for all Python package operations:
```bash
uv sync          # Install dependencies
uv add <package> # Add new package
uv pip install <package>  # Install specific package
```

### Code Organization
- **Prefer classes over functions** unless the function is simple and standalone
- Use object-oriented design for related functionality
- Functions acceptable for: single-purpose utilities, one-off scripts, simple transformations

### Method Naming
- Methods should use `snake_case`
- Method names should be of the form `<noun>_<noun>_<verb>` with as many nouns as needed, with the nouns going from more general to more specific, ending with the verb.
- Method names shoud never include the method's class name as the first noun.  It is understood that any class method refers to that method.
- For data conversion methods, use the pattern `to_<data_type>` and `from_<data_type>`, e.g. `.to_dict()`, `.from_xlsx()`, `.to_binary()`, `.from_base64()`.  The "from" methods should be classmethods.


### Documentation Requirements
All methods MUST include docstrings with examples:
```python
def calculate_angle(self, loft: float, lie: float) -> float:
    """
    Calculate the composite angle from loft and lie values.

    Args:
        loft: Loft angle in degrees
        lie: Lie angle in degrees

    Returns:
        Composite angle in degrees

    Example:
        >>> calc = AngleCalculator()
        >>> calc.calculate_angle(24.0, 62.5)
        66.85
    """
    return math.sqrt(loft**2 + lie**2)
```

### Property Accessors
Use property decorators with type checking:
```python
class ClubData:
    def __init__(self):
        self._loft: float = 0.0

    @property
    def loft(self) -> float:
        """Loft angle in degrees (read-only)."""
        return self._loft

    @loft.setter
    def loft(self, value: float) -> None:
        """Set loft angle with type validation."""
        if not isinstance(value, (int, float)):
            raise TypeError(f"Loft must be numeric, got {type(value)}")
        if value < 12.0:
            raise ValueError(f"Loft must be >= 12°, got {value}")
        self._loft = float(value)
```

### Type Hints
All function/method parameters and return values MUST have type hints:
```python
from typing import Dict, List, Optional

def encode_clubs(clubs: List[Dict[str, any]], order_id: int) -> bytes:
    """Encode club data to binary format."""
    pass
```

### File Names as Parameters and Outputs

- `pathlib` should be used for file and path handling and modifications.
- Any method that takes a file name as a parameter should:
  - Provide a default file name.
  - Use `pathlib.Path` or `str` as the parameter type.
  - Use 'pathlib.Path` to verify that the file name is valid.
  - If the file name does not have the correct default extension, replace the extension with the correct one.
- Any method that outputs a file should return the file name as a `pathlib.Path` object.
- Use `kebab-case` for all method and function default file names
- File names should be descriptive of their purpose, e.g., `order-qr-code.png`.

