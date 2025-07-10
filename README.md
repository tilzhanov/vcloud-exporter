# ☁️ vCloud Director Exporter for Prometheus

Custom Prometheus exporter to collect resource metrics from **VMware vCloud Director (VCD)** using its REST API. This exporter exposes usage and allocation statistics for clusters and Virtual Data Centers (VDCs) in a format compatible with Prometheus.

---

## <a name="table-of-contents"></a>📚 Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [Running the Exporter](#running-the-exporter)
- [Docker Support](#docker-support)
- [Prometheus Job Configuration](#prometheus-job-configuration)
- [Grafana Dashboard](#grafana-dashboard)
- [Exposed Metrics](#exposed-metrics)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## <a name="features"></a>✅ Features

- Connects to VMware vCloud Director API via OAuth2
- Collects usage & allocation data from:
  - Provider Clusters
  - Virtual Data Centers (VDC)
- Exposes Prometheus-compatible metrics via `/metrics`
- Supports pagination and large VDCs
- Works standalone or in Docker

---

## <a name="requirements"></a>🧰 Requirements

- Python **3.0+**
- Access to vCloud Director API endpoint
- Prometheus for scraping metrics

---

## <a name="installation"></a>📦 Installation

```bash
git clone https://gitlab.com/tilzhanov/vcloud-exporter.git
cd vcloud-exporter
pip install -r requirements.txt
```

---

## <a name="environment-configuration"></a>⚙️ Environment Configuration

1. **Create your environment file**:

```bash
cp vcd_exporter_example vcd_exporter.env
```

2. **Edit `vcd_exporter.env` with your VCD connection details**:

```dotenv
VCD_URL=https://<vcd.example>/api/query?type=adminOrgVdc&pageSize=128&page=1 ###put your address
VCD_API_TOKEN= ###you have to create it from vcloud directory user preferences 
VCLOUD_API_VERSION=  ###depends on vcloud session version. for example 37.0 or 38.0
VCD_VERIFY_SSL=false
VCD_PAGE_SIZE=128
EXPORTER_PORT=8000
```

---

## <a name="running-the-exporter-locally"></a>🚀 Running the Exporter (Locally)

```bash
source vcd_exporter.env
python3 exporter.py
```

Available endpoints:

- Metrics: `http://localhost:8000/metrics`

---

## <a name="docker-support"></a>🐳 Docker Support

### <a name="build-docker-image"></a>Build Docker image:

```bash
docker build -t vcloud-exporter .
```

### <a name="run-with-environment"></a>Run with environment:

```bash
docker run --rm -p 8000:8000 --env-file ./vcd_exporter.env vcloud-exporter
```

---

## <a name="prometheus-job-configuration"></a>📡 Prometheus Job Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'vcloud_exporter'
    metrics_path: /metrics
    scrape_interval: 1m
    scrape_timeout: 30s
    static_configs:
      - targets: ['vcloud-exporter.local:8000']
```

> ⚠️ Replace `vcloud-exporter.local` with your actual hostname or IP.

---

## <a name="grafana-dashboard"></a>📊 Grafana Dashboard

You can create a custom dashboard using metrics such as:

- `vcd_vdc_cpu_allocated`
- `vcd_vdc_memory_used`
- `vcd_cluster_cpu_total`
- `vcd_vdc_vm_count`

For example, use a **Graph panel** to show VDC CPU usage over time:

```text
vcd_vdc_cpu_used{vdc="Tenant1"}
```

If you need a ready-to-import Grafana dashboard JSON, check the `/grafana` directory (if available) or open an issue to request one.

---

## <a name="exposed-metrics"></a>📈 Exposed Metrics

| Metric Name                            | Description                              |
|----------------------------------------|------------------------------------------|
| `vcd_vdc_cpu_allocated`                | CPU allocated to VDC (MHz)               |
| `vcd_vdc_cpu_used`                     | CPU used by VDC (MHz)                    |
| `vcd_vdc_memory_allocated`            | Memory allocated to VDC (MB)             |
| `vcd_vdc_memory_used`                 | Memory used by VDC (MB)                  |
| `vcd_vdc_storage_allocated_mb`        | Storage allocated to VDC (MB)            |
| `vcd_vdc_storage_used_mb`             | Storage used by VDC (MB)                 |
| `vcd_vdc_vm_count`                    | Number of VMs in VDC                     |
| `vcd_cluster_cpu_total`               | Total CPU in cluster (MHz)               |
| `vcd_cluster_cpu_reserved`            | Reserved CPU in cluster (MHz)            |
| `vcd_cluster_cpu_used`                | Used CPU in cluster (MHz)                |
| `vcd_cluster_memory_total`            | Total memory in cluster (MB)             |
| `vcd_cluster_memory_reserved`         | Reserved memory in cluster (MB)          |
| `vcd_cluster_memory_used`             | Used memory in cluster (MB)              |

---

## <a name="troubleshooting"></a>🧯 Troubleshooting

| Problem | Solution |
|--------|----------|
| 🔐 Auth error | Check `VCD_API_TOKEN` |
| 🌐 Empty metrics | Ensure user has access to VDCs and Org is correct |
| 🔒 SSL error | Set `VCLOUD_VERIFY_SSL=false` in env file |
| 🧊 Exporter freezes | Check API rate limits or large VDC page sizes |

Enable debug mode or log prints if needed by editing the script manually.

---

## <a name="contributing"></a>🤝 Contributing

1. Fork this repository
2. Create a feature branch
3. Open a merge request

Feedback, bug reports, and improvements are very welcome.

---

## <a name="license"></a>📄 License

This project is licensed under the [MIT License](./LICENSE).

---

## <a name="author"></a>👤 Author

Maintained by [tilzhanov](https://gitlab.com/tilzhanov) and [Temirlaaan](https://gitlab.com/Temirlaaan)

If you use this exporter — please ⭐️ the project or share feedback!