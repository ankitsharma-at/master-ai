"""Minimal syntax test without dependencies."""
import sys
import importlib.util

def check_module(filepath):
    """Check if Python file has valid syntax."""
    spec = importlib.util.spec_from_file_location("test", filepath)
    if spec and spec.loader:
        try:
            module = importlib.util.module_from_spec(spec)
            # Don't execute, just load
            with open(filepath) as f:
                code = f.read()
                compile(code, filepath, 'exec')
            return True, None
        except Exception as e:
            return False, str(e)
    return False, "Could not load module"

# Check all Python files
import os
errors = []
count = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['__pycache__', 'venv', '.git']]
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            count += 1
            ok, err = check_module(filepath)
            if not ok:
                errors.append(f"{filepath}: {err}")

print(f"Checked {count} Python files")
if errors:
    print(f"\n❌ {len(errors)} errors found:")
    for err in errors:
        print(f"  {err}")
    sys.exit(1)
else:
    print("\n✅ All Python files have valid syntax!")
    sys.exit(0)
