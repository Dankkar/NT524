# Feedback API And ML/WAF Tuning Loop

Ngay cap nhat: 2026-05-29

Feedback API la thanh phan noi giua `Detect` va `Response`:

```text
WAF block request
-> Filebeat/Logstash day log vao Elasticsearch
-> Feedback API lay blocked payload tu ES
-> operator label legitimate/malicious
-> dataset cap nhat
-> export tuned ModSecurity rules
-> deploy rules lai AWS WAF va OpenStack WAF
```

## Chay API

```bash
python3 scripts/feedback_api.py
```

Mac dinh:

```text
Listen: 0.0.0.0:5005
Dashboard: http://127.0.0.1:5005/
Elasticsearch: http://172.10.10.1:9200/siem-waf-access-*/_search
```

Co the override bang environment:

```bash
FEEDBACK_PORT=5005 \
FEEDBACK_ES_SEARCH_URL='http://172.10.10.1:9200/siem-waf-access-*/_search' \
FEEDBACK_REVIEWER=operator \
FEEDBACK_ML_PYTHON=~/modsec-ai-venv/bin/python \
python3 scripts/feedback_api.py
```

## Dataset Duoc Cap Nhat

Feedback API ghi label vao ca hai dataset path:

```text
data/dataset/
modsec-learn/data/dataset/
```

Ly do:

- `data/dataset/` giu dataset nho/phuc vu lab.
- `modsec-learn/data/dataset/` la dataset ma `scripts/run_training.py` dung khi train model trong `modsec-learn`.

Khi label mot payload:

- label `legitimate` se them payload vao `legitimate_train.json` va xoa khoi `malicious_train.json`.
- label `malicious` se them payload vao `malicious_train.json` va xoa khoi `legitimate_train.json`.
- ghi audit vao `data/feedback/feedback_audit.jsonl`.

## API Endpoints

Health:

```bash
curl -fsS http://127.0.0.1:5005/healthz
```

Lay blocked payload gan day:

```bash
curl -fsS 'http://127.0.0.1:5005/api/blocked?limit=100'
```

Xem dataset status:

```bash
curl -fsS http://127.0.0.1:5005/api/dataset/status
```

Gui feedback:

```bash
curl -fsS -X POST http://127.0.0.1:5005/api/feedback \
  -H 'Content-Type: application/json' \
  -d '{
    "payload": "id=1 OR 1=1",
    "label": "malicious",
    "reviewer": "operator",
    "note": "SQLi test payload"
  }'
```

Export tuned WAF rules tu model da train:

```bash
curl -fsS -X POST http://127.0.0.1:5005/api/export-rules \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "linear_svc_pl4_l1.joblib",
    "threshold": "1e-5"
  }'
```

File output:

```text
ansible/roles/nginx_waf/files/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf
```

Endpoint export uu tien dung `~/modsec-ai-venv/bin/python`, dung voi ghi chu trong file `openstack`. Neu venv nay khong ton tai thi API fallback ve `python3` he thong. Neu chua cai dependencies:

```bash
python3 -m pip install -r modsec-learn/requirements.txt
```

## Workflow Sau Khi Feedback

Sau khi label payload:

```bash
cd modsec-learn
~/modsec-ai-venv/bin/python ../scripts/run_training.py
~/modsec-ai-venv/bin/python ../scripts/export_tuned_rules.py \
  --model linear_svc_pl4_l1.joblib \
  --threshold 1e-5

cd ..
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
/home/deployer/kolla-venv/bin/ansible-playbook \
  -i ansible/inventories/production/hosts.yml \
  ansible/waf.yml \
  --tags update_rules
```

GitHub Actions workflow cu da duoc bo. Ly do: pipeline cu chi deploy AWS WAF, dung path/template cu, va khong phu hop voi OpenStack WAF nam sau private/VPN path. Khi retrain ML, controller local se export rule roi Ansible cap nhat dong thoi AWS WAF va OpenStack WAF bang tag `update_rules`.

Neu thay doi Dockerfile/base WAF image thi moi can build/push image ECR thu cong, sau do chay full `ansible/waf.yml`.

Sau do test lai:

```bash
curl -k -o /dev/null -s -w "%{http_code}\n" \
  "https://app.nt524.io.vn/?id=1%20OR%201=1"
```

## Luu Y Bao Mat

- Feedback API hien phu hop lab noi bo, chua nen expose public Internet.
- Khong ghi raw token, cookie session hay password vao dataset.
- Payload bi block co the chua du lieu nhay cam; can mask neu dua vao bao cao cong khai.
- Operator nen review false positive truoc khi export/deploy rule moi.
