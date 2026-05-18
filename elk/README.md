# Local SIEM Stack

Docker Compose stack for the hybrid SIEM lab.

- Elasticsearch listens on `172.10.10.1:9200` so Logstash on the OpenStack VPN node can write to it through the laptop AIO provider bridge.
- Kibana listens on `127.0.0.1:5601`.
- Logstash does not run in this compose stack. It is deployed by Ansible on the OpenStack VPN node.

Run:

```bash
sudo sysctl -w vm.max_map_count=262144
sudo docker compose up -d --remove-orphans
```

Logstash writes Filebeat events to daily indices named `siem-hybrid-YYYY.MM.dd`.
