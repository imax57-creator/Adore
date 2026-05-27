import sys
import json
import re
import subprocess
import os

if __name__ == '__main__':
    try:
        data = json.loads(sys.stdin.read())
        fp = data.get('tool_input', {}).get('file_path', '')
        if re.search(r'(app|tests)[/\\].*\.py$', fp):
            project_root = os.path.dirname(os.path.abspath(__file__))
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            subprocess.Popen(['python', 'run_all_tests.py'], cwd=project_root, env=env)
    except Exception:
        pass
