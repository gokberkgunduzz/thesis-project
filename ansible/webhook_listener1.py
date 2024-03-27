from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received webhook data:", json.dumps(data, indent=4))

    # Determine which service to restart based on alert name or labels
    for alert in data.get('alerts', []):
        if alert.get('labels', {}).get('alertname') == 'InstanceDown':
            if 'node_exporter' in alert.get('labels', {}).get('job', ''):
                playbook = './playbooks/restart_service.yml'
            elif 'ssh' in alert.get('labels', {}).get('job', ''):
                playbook = './playbooks/restart_ssh_service.yml'
            else:
                continue  # Skip if no matching condition

            # Run the determined playbook
            result = subprocess.run(['ansible-playbook', playbook, '--inventory', './ansible/inventory'], capture_output=True, text=True)
            print("Ansible playbook output:", result.stdout)

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
