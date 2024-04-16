from flask import Flask, request, jsonify
import subprocess
import json
import re

app = Flask(__name__)

# Helper function to extract the offending IP address from the alert's annotations
def extract_ip_address(alert):
    # The IP should be part of the alert's annotations set by Prometheus alert rule
    annotations = alert.get('annotations', {})
    description = annotations.get('description', '')
    # This regex extracts the first found IP address from the description
    match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', description)
    return match.group(0) if match else None

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received webhook data:", json.dumps(data, indent=4))

    for alert in data.get('alerts', []):
        if alert.get('status') == 'firing':
            labels = alert.get('labels', {})
            instance = labels.get('instance')
            alertname = labels.get('alertname')

            # Define the playbook variable beforehand
            playbook = None

            # Check for different alert types and set the corresponding playbook
            if 'InstanceDown' == alertname:
                playbook = 'restart_service.yml'
            elif 'SSHServiceDown' == alertname:
                playbook = 'restart_ssh_service.yml'
            elif 'HTTPServiceDown' == alertname:
                playbook = 'restart_http_service.yml'
            elif 'HighNumberOfFailedSSHLogins' == alertname:
                # This is the new condition we're handling
                ip_address = extract_ip_address(alert)
                if ip_address:
                    playbook = 'block_ip.yml'
                else:
                    print("No IP address found in alert for HighNumberOfFailedSSHLogins")
                    continue  # Skip if no IP address is found

            # If a playbook is set, then run it
            if playbook:
                extra_vars = f'instance={instance}'
                if 'block_ip.yml' == playbook:
                    # If we're blocking an IP, we need to pass it as an extra var
                    extra_vars = f'ip_address={ip_address}'

                result = subprocess.run(
                    [
                        'ansible-playbook',
                        f'./playbooks/{playbook}',
                        '--inventory',
                        './inventory',
                        '-e',
                        extra_vars
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
