import yaml
import glob
import sys

files = glob.glob(".github/workflows/*.yml")
has_error = False

for file in files:
    try:
        with open(file, 'r') as f:
            yaml.safe_load(f)
        print(f"✅ {file} is valid YAML")
    except Exception as e:
        print(f"❌ {file} has invalid YAML: {e}")
        has_error = True

if has_error:
    sys.exit(1)
