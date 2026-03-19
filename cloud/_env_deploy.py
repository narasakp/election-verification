"""Deploy Cloud Function with correct env vars using YAML file."""
import os
import subprocess
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')

# Read keys from .env
keys = {}
with open(os.path.join(PROJECT_ROOT, '.env'), 'r') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            keys[k.strip()] = v.strip().strip('"').strip("'")

gemini_key = keys.get('GEMINI_API_KEY', '')
print(f"GEMINI_API_KEY: {gemini_key[:15]}...{gemini_key[-5:]} (len={len(gemini_key)})")

# Write env vars YAML file
env_vars = {
    'GEMINI_API_KEY': gemini_key,
    'GCS_BUCKET': 'election69-ocr-results-th',
}
yaml_path = os.path.join(SCRIPT_DIR, '_env_vars.yaml')
with open(yaml_path, 'w') as f:
    yaml.dump(env_vars, f, default_flow_style=False)
print(f"Wrote {yaml_path}")

# Run gcloud deploy
cmd = [
    'gcloud', 'functions', 'deploy', 'ocr-worker',
    '--gen2',
    '--runtime', 'python311',
    '--region', 'asia-southeast1',
    '--source', os.path.join(SCRIPT_DIR, 'function'),
    '--entry-point', 'handle_request',
    '--trigger-http',
    '--allow-unauthenticated',
    '--memory', '512MB',
    '--timeout', '540s',
    '--env-vars-file', yaml_path,
    '--project', 'election-ocr',
]
print(f"\nRunning: {' '.join(cmd[:10])} ...")
result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
print(result.stdout[-2000:] if result.stdout else '')
if result.stderr:
    print(result.stderr[-2000:])
print(f"\nExit code: {result.returncode}")
