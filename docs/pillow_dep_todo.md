# Pillow Dependency Resolution Action Plan

## Problem Context
The project is experiencing dependency resolution issues when using `uv` to resolve a complex set of dependencies, particularly around:
- **`pillow` vs. `streamlit` version conflicts** (`pillow>=11.1.0` conflicts with `streamlit==1.47.0`'s pinned `pillow<=11.0.0`)
- **Multi-index resolution problems** (PyPI vs. PyTorch's extra index)
- **Python version constraints** (accidental resolution attempts for unsupported Python versions)

The goal is to:
1. **Resolve conflicts** without breaking existing functionality
2. **Ensure reproducibility** across environments (dev, CI, production)
3. **Minimize risk** by validating dependency combinations in a sandbox (`tools/uv_sandbox/`)

## Action Plan

### 1. Upgrade Streamlit to Resolve Pillow Conflict
- [x] Test `streamlit>=1.48.0` in the sandbox (aligned with Pillow 11.1.0+)
- [x] Update sandbox pyproject.toml:
  ```bash
  sed -i 's/streamlit==1.47.0/streamlit>=1.48.0/' tools/uv_sandbox/pyproject.toml
  ```
- [x] Run sandbox validation:
  ```bash
  cd tools/uv_sandbox && ./run.sh | cat
  ```
- [ ] If conflicts persist, test `pillow==11.0.0` temporarily (if security allows)

### 2. Enforce Per-Package Index Mapping (Best Practice)
- [x] Map only `torch` to the `pytorch` index in sandbox `pyproject.toml`
- [x] Remove global extra indexes and unsafe index strategy flags from `run.sh`
- [x] Re-run sandbox to validate

### 3. Strict Python Version Enforcement
- [ ] Ensure all environments use Python 3.12.x
- [ ] Confirm Python version in sandbox:
  ```bash
  .venv/bin/python -V
  ```
- [ ] Update CI/CD workflows to explicitly use 3.12:
  ```bash
  grep "python-version" .github/workflows/*.yml
  ```
- [ ] If Python 3.13 is needed, update `requires-python` to `>=3.12,<3.14` and retest

### 4. Simplify Dependencies
- [ ] Audit and relax overlapping constraints (e.g., `protobuf>=5.26,<7.0` → `protobuf~=5.29.5`)
- [ ] Check for conflicts:
  ```bash
  uv pip check
  ```
- [x] Generate resolved lockfile:
  ```bash
  uv lock
  ```
- [ ] Use `uv pip compile` to generate a minimal reproducible set if needed

## Validation Steps
- [x] Successful resolution of `pillow>=11.1.0` and `streamlit>=1.48.0`
- [x] No warnings from `uv pip check`
- [ ] All tests pass with new dependency set
- [ ] CI/CD pipeline works with resolved dependencies

## Fallback Options
- [ ] Downgrade `pillow` to 11.0.0 if security allows
- [ ] Pin `streamlit` to a specific working version
- [ ] Use `uv pip compile` to generate minimal reproducible set
- [ ] Consider alternative packages if conflicts persist

## Notes
- Keep `protobuf==5.29.5` and `grpcio*==1.63.0` aligned
- Prefer CPU wheels unless CUDA/ROCm needed
- Document any changes in `@uv-sandbox.mdc` rule
