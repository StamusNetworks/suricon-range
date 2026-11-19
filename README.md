# Stamus Cyber Range - Suricon 2026

Lab setup, presentation, LLM skillset, etc. Frozen in time to support Suricon 2026 presentation. Note that this is not actively maintained, though should provide good enough starting point for cyber range development.

## Getting started

> **You deploy the lab.** VMs are not provided. Bring up hosts matching
> `ansible/inventory/hosts.ini` (adjust IPs to your network), then apply the
> customization with Ansible.

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make setup
```

### Lab

```bash
cd ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml
cd ..
```

### Configure

```bash
cp .env.example .env
cat ansible/inventory/hosts.ini
cat ansible/inventory/group_vars/*.yml
```

| `.env` | source |
|---|---|
| `TARGET_*`, `TUONI_IP`, `*_URL` hosts | `ansible/inventory/hosts.ini` |
| `TARGET_WS`, `TARGET_DC` domain | `ansible/inventory/group_vars/windows.yml` (`domain_name`) |
| `EXEC_*`, `LATERAL_*` | `ansible/inventory/group_vars/domain_controller.yml` (`domain_users`) |
| `TUONI_USER`, `TUONI_PASS` | `ansible/inventory/group_vars/tuoni.yml` |
| `ARKIME_USER`, `ARKIME_PASS` | `ansible/roles/arkime/defaults/main.yml` (`arkime_users`), `ansible/inventory/group_vars/capture.yml` |
| `ELK_URL` | OpenSearch on the `logserver` host |
| `LLM_*` | optional |

### Run

```bash
jupyter lab presentation.ipynb
```
