from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received webhook data:", json.dumps(data, indent=4))

    for alert in data.get('alerts', []):
        if alert.get('status') == 'firing':
            labels = alert.get('labels', {})
            instance = labels.get('instance')
            alertname = labels.get('alertname')

            if 'InstanceDown' == alertname:
                playbook = 'restart_service.yml'
            elif 'SSHServiceDown' == alertname:
                playbook = 'restart_ssh_service.yml'
            elif 'HTTPServiceDown' == alertname:
                playbook = 'restart_http_service.yml'
            else:
                continue  # Skip if no matching condition

            result = subprocess.run(
                [
                    'ansible-playbook',
                    f'./playbooks/{playbook}',
                    '--inventory',
                    './inventory',
                    '-e',
                    f'instance={instance}'
                ],
                capture_output=True,
                text=True
            )
            print("Ansible playbook output:", result.stdout)

            if result.returncode != 0:
                print("Ansible playbook error:", result.stderr)
                return jsonify({'status': 'error', 'message': result.stderr}), 500

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
