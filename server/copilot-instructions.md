# AI Agent Instructions for mizuno-chip

## Project Overview
Golf club manufacturing data tools for Mizuno. Two independent modules for processing golf club specifications and order data:
- **loft-lie-angle-plots**: Visualization of club specifications using Plotly
- **qr-codes**: Binary encoding/QR code generation for manufacturing orders

## Project Structure
```
loft-lie-angle-plots/    # Club spec visualization
  club_grouping.py       # Main script: generates interactive HTML plots
  iron-model-loft-lie-spec.csv  # Source data
  clubs.html, clubs-series.html  # Generated outputs
qr-codes/                # Order data QR encoding
  job_qr_codes.py        # Full encode/decode workflow with binary format
  order-example.xlsx     # Sample input format
```

## Environment Setup
- **Python**: 3.13 (see `.python-version`)
- **Package manager**: uv (see `pyproject.toml`)
- **Key dependency**: `simplexity-se` is a LOCAL package at `../simplexity_se/` - it's a custom Plotly wrapper (EasyFig)
- Run scripts directly: `python qr-codes/job_qr_codes.py` or `python loft-lie-angle-plots/club_grouping.py`
- **IMPORTANT**: Always activate the UV virtual environment before running tests or generating documentation:
  ```bash
  source .venv/bin/activate
  ```

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

## Data Formats & Encoding

### QR Code Binary Format
Custom compact binary encoding in [job_qr_codes.py](../qr-codes/job_qr_codes.py):
- **Angle quantization**: All angles (loft/lie) are transformed before encoding:
  - Subtract 12°, divide by 0.25, store as 8-bit int (0-255 range)
  - Allows 0.25° precision with ±0.125° tolerance after round-trip
- **Structure**: Order# (64-bit) → Yield (32-bit float) → Handedness+ClubCount (8-bit bit-packed) → [Club code (2 bytes) + 4 angles (4×8-bit)]*
  - **Bit-packing**: Bit 7 = handedness (0='L', 1='R'), Bits 0-6 = club count (0-127)
- **Club codes**: 2-character ASCII (e.g., "5I", "PW"), "NA" clubs are skipped

### XLSX Input Format (QR codes)
Expected structure in `order-example.xlsx`:
- B1: Order number (int)
- B2: Handedness ("L" or "R")
- B3: Material yield (float)
- Row 6: Headers
- Rows 7-18: 12 clubs max, columns: Club | Loft Initial | Lie Initial | Loft Target | Lie Target

## Key Patterns

### Plotly Visualization via simplexity-se
**REQUIRED**: All plots MUST use the `EasyFig` wrapper from `simplexity_se` module. Never use raw Plotly figures.

```python
from simplexity_se import EasyFig

# Use EasyFig to create the figure
fig = EasyFig()

# Plot the data
fig.plot(loft_values, y=lie_values, mode="markers+lines", name="Club Series")

# Use EasyFig's simplified property access
fig.xlabel = "Loft Angle (degrees)"
fig.ylabel = "Lie Angle (degrees)"
fig.title = "Plot Title"
fig.to_html("output.html")
```

### QR Code Workflow
Complete encode/decode cycle in `job_qr_codes.py`:
1. `read_xlsx()` → Dict
2. `encode_to_binary()` → bytes (custom compact format)
3. `encode_to_base64()` → str
4. `generate_qr()` → PNG file
5. `decode_qr()` → Dict (requires cv2 + pyzbar)

Optional imports pattern: cv2/pyzbar for decoding - degrades gracefully with `QR_DECODE_AVAILABLE` flag

## Common Tasks

**Generate club spec plots:**
```bash
cd loft-lie-angle-plots
python club_grouping.py  # Outputs clubs.html, clubs-series.html
```

**Generate QR codes from order data:**
```bash
cd qr-codes
python job_qr_codes.py  # Uses order-example.xlsx, outputs order_qr_code.png
```

**Install dependencies:**
```bash
uv sync  # Installs from pyproject.toml, including local simplexity-se
```

**Run tests:**
```bash
source .venv/bin/activate  # Activate virtual environment first
pytest                     # Run all tests from project root
```

**Generate documentation:**
```bash
source .venv/bin/activate  # Activate virtual environment first
mkdocs build              # Build documentation
mkdocs serve              # Serve documentation locally
```

**Note:** Tests use pytest and must be run from the project root directory with the virtual environment activated.

## Important Constraints
- Angles must be ≥12° (encoding subtracts 12°)
- Max 12 clubs per order (XLSX rows 7-18)
- Club codes exactly 2 characters
- Handedness must be "L" or "R" (case-insensitive, normalized to uppercase)
- Quantization creates ±0.13° tolerance - verify decoded angles with `abs(diff) <= 0.13`
