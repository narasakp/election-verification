"""Print the gcloud deploy command with full API key from .env"""
import os

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
keys = {}
with open(env_path, 'r') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            keys[k.strip()] = v.strip().strip('"').strip("'")

gemini_key = keys.get('GEMINI_API_KEY', '')
print(f"GEMINI_API_KEY length: {len(gemini_key)}")
print(f"GEMINI_API_KEY preview: {gemini_key[:15]}...{gemini_key[-5:]}")

# Build deploy command
cmd = (
    'gcloud functions deploy ocr-worker'
    ' --gen2 --runtime python311 --region asia-southeast1'
    ' --source cloud/function'
    ' --entry-point handle_request'
    ' --trigger-http --allow-unauthenticated'
    ' --memory 512MB --timeout 540s'
    f' --set-env-vars GEMINI_API_KEY={gemini_key}'
    f' --update-env-vars GCS_BUCKET=election69-ocr-results-th'
    ' --project election-ocr'
)
print(f"\nDeploy command:\n{cmd}")

# Write to temp file for execution
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '_deploy.cmd'), 'w') as f:
    f.write(cmd + '\n')
print("\nSaved to cloud/_deploy.cmd")
