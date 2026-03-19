import os
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
with open(env_path, 'r') as f:
    for line in f:
        line = line.strip()
        if line.startswith('GEMINI_API_KEY='):
            key = line.split('=', 1)[1].strip().strip('"').strip("'")
            print(key[:15] + '...')
            break
