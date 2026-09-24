"""Record each authorized cloud mutation before executing it, then its outcome.

Do not pass credentials/secrets as arguments or print them from child commands.
Use for this deployment's gcloud and SSH/SCP operations only.
"""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / 'cloud-activities'
directory.mkdir(exist_ok=True)
purpose, *command = sys.argv[1:]
if not command:
    raise SystemExit('usage: log_action.py PURPOSE COMMAND [ARGS...]')
now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
record = directory / (stamp + '.md')
result_path = directory / (stamp + '.result.txt')
header = f'''# GCP activity: {purpose}

- Started: {now.isoformat()}
- Project: `bigdatainpractice1`
- Acting cloud account: `thaimcpagent@gmail.com`; remote OS identity when SSH: `thaimcpagent_gmail_com` / sudo root.
- Region / zone: `asia-southeast1` / `asia-southeast1-c` (`student3-research-rag`).
- Authorization: user explicitly requested on 2026-09-24 to check and run student3-research-rag cloned from the student1 machine image, matching student1 services and HTTPS.
- Deployment scope and before state: [student3 scope](student3-20260924.md).
- HTTPS authorization: user requested HTTPS on student3 matching the existing student1 classroom service; same public no-login application design disclosed in the existing deployment.
- Firewall/IAM/billing-account upgrades: not authorized by this operation; do not modify.
- Intended action: {purpose}
- Command (JSON argv; no secrets):

```json
{json.dumps(command, ensure_ascii=False, indent=2)}
```

- Status: STARTED; not yet verified.
'''
record.write_text(header)
print(f'ACTIVITY_RECORD={record}', flush=True)
try:
    with result_path.open('w') as output:
        process = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
    status = 'COMMAND SUCCEEDED; inspect evidence before claiming readiness' if process.returncode == 0 else 'FAILED / MAY BE PARTIAL; inspect actual cloud state'
    with record.open('a') as out:
        out.write(f'\n- Finished: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n- Exit code: {process.returncode}\n- Outcome: {status}\n- Evidence: [{result_path.name}]({result_path.name})\n')
    output_text = result_path.read_text()
    print(output_text[-6000:], end='')
    if len(output_text) > 6000:
        print('\nFull output preserved in ' + str(result_path))
    raise SystemExit(process.returncode)
except BaseException as exc:
    if not isinstance(exc, SystemExit):
        with record.open('a') as out:
            out.write(f'\n- Execution interrupted/error: {type(exc).__name__}: {exc}; actual cloud state must be checked.\n')
    raise
