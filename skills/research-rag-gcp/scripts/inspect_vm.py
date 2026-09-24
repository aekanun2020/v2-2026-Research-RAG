"""Read-only inventory for one explicitly selected Research-RAG GCP VM.

Uses argv arrays. No SSH, cloud mutation, raw metadata or credential output.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'configuration', 'zone', 'vm'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.project == 'quixotic-elf-492100-g5':
        p.error('Prohibited project; no command executed.')
    for name in ('project', 'configuration', 'zone', 'vm'):
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', getattr(a, name)):
            p.error('Invalid selector: ' + name)
    # Fail before cloud reads if a new report cannot be created. No overwrite.
    with a.output.open('x', encoding='utf-8') as out:
        report = {'checked_at': datetime.now(timezone.utc).isoformat(),
                  'project': a.project, 'configuration': a.configuration,
                  'zone': a.zone, 'vm': a.vm, 'mode': 'read-only',
                  'status': 'started', 'actions': []}
        def save():
            out.seek(0)
            out.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            out.truncate()
            out.flush()
        def gcloud(*args):
            cmd = ['gcloud', '--quiet', '--project=' + a.project,
                   '--configuration=' + a.configuration, *args, '--format=json']
            report['actions'].append(cmd)
            save()
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=60)
            if result.returncode:
                # No arbitrary raw CLI output in artifacts; preserve read command.
                raise RuntimeError('gcloud read exited ' + str(result.returncode)
                                   + '; inspect last recorded read command directly')
            return json.loads(result.stdout)
        code = 0
        try:
            config = gcloud('config', 'list', 'account')
            report['acting_account'] = config.get('core', {}).get('account')
            if not report['acting_account']:
                raise RuntimeError('No acting account resolved; stop before VM inspection')
            vm = gcloud('compute', 'instances', 'describe', a.vm, '--zone=' + a.zone)
            report['instance'] = {k: vm.get(k) for k in (
                'name', 'id', 'status', 'zone', 'machineType', 'creationTimestamp',
                'sourceMachineImage', 'guestAccelerators')}
            report['instance']['tags'] = vm.get('tags', {}).get('items', [])
            report['instance']['service_accounts'] = [
                s.get('email') for s in vm.get('serviceAccounts', [])]
            report['instance']['login_metadata'] = [
                item for item in vm.get('metadata', {}).get('items', [])
                if item.get('key') in ('enable-oslogin', 'enable-oslogin-2fa',
                                       'block-project-ssh-keys')]
            report['instance']['disks'] = [
                {k: d.get(k) for k in ('source', 'deviceName', 'diskSizeGb',
                                       'boot', 'autoDelete', 'mode')}
                for d in vm.get('disks', [])]
            report['instance']['interfaces'] = [
                {'networkIP': n.get('networkIP'), 'network': n.get('network'),
                 'external_ipv4': [c.get('natIP') for c in n.get('accessConfigs', [])
                                   if c.get('natIP')]}
                for n in vm.get('networkInterfaces', [])]
            if vm.get('guestAccelerators'):
                raise RuntimeError('Prohibited accelerator present; no workload actions allowed')
            ips = {ip for n in report['instance']['interfaces'] for ip in n['external_ipv4']}
            addresses = gcloud('compute', 'addresses', 'list')
            report['matching_reservations'] = [
                {k: x.get(k) for k in ('name', 'address', 'status', 'region', 'users')}
                for x in addresses if x.get('address') in ips]
            report['ip_reservation_note'] = (
                'Matching reservations observed; verify users/attachment before mutation'
                if report['matching_reservations'] else
                'No matching reservation found; do not assume a stable IP')
            report['status'] = 'inspected'
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            report['status'] = 'failed'
            report['error'] = str(exc)
            code = 1
        finally:
            report['finished_at'] = datetime.now(timezone.utc).isoformat()
            save()
        print(json.dumps({'status': report['status'], 'report': str(a.output)}))
        return code


if __name__ == '__main__':
    sys.exit(main())
