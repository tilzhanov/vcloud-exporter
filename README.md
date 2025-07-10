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

- OAuth2-based connection to VMware vCloud Director API with automatic bearer-token caching and refresh  
- Collects usage & allocation data from:
  - Provider Clusters
  - Virtual Data Centers (VDC)
- Collects detailed cluster metrics:
  - CPU & memory **allocated**, **reserved**, **used**, **overhead**
  - Storage **allocated**, **limit**, **used**
- Collects storage profile metrics per cluster:
  - Total/used **capacity** (MB)
  - IOPS **capacity** & **allocated**
- Exposes total count of VDC records as `vcd_vdc_total_records`
- Provides `/metrics` endpoint for Prometheus and a `/health` endpoint for liveness checks
- Supports pagination for large VDC and providerVdc queries
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
VCD_API_TOKEN=   # Obtain this API token in vCloud Director: log in, click your username (top right) → “User Preferences” → “API Tokens” (requires System Administrator rights), then create/copy your token
VCD_URL=https://<url>/api/query?type=adminOrgVdc&pageSize=128&page=1
VCD_API_VERSION=   # You can find the API version via Swagger in vCloud Director (Help → API Docs), e.g., 38.0 or 37.0
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

| Metric Name                                 | Description                                         |
|---------------------------------------------|-----------------------------------------------------|
| `vcd_vdc_cpu_allocated`                     | CPU allocated to VDC (MHz)                          |
| `vcd_vdc_cpu_used`                          | CPU used by VDC (MHz)                               |
| `vcd_vdc_mem_allocated_mb`                  | Memory allocated to VDC (MB)                        |
| `vcd_vdc_mem_used_mb`                       | Memory used by VDC (MB)                             |
| `vcd_vdc_vm_count`                          | Number of VMs in VDC                                |
| `vcd_vdc_storage_allocated_mb`              | Storage limit for VDC (MB)                          |
| `vcd_vdc_storage_used_mb`                   | Storage used by VDC (MB)                            |
| `vcd_vdc_total_records`                     | Total number of VDC records retrieved               |
| `vcd_cluster_cpu_allocated`                 | Allocated CPU for cluster (MHz)                     |
| `vcd_cluster_cpu_reserved`                  | Reserved CPU for cluster (MHz)                      |
| `vcd_cluster_cpu_total`                     | Total CPU for cluster (MHz)                         |
| `vcd_cluster_cpu_used`                      | Used CPU for cluster (MHz)                          |
| `vcd_cluster_cpu_overhead`                  | Overhead CPU for cluster (MHz)                      |
| `vcd_cluster_mem_allocated_mb`              | Allocated memory for cluster (MB)                   |
| `vcd_cluster_mem_reserved_mb`               | Reserved memory for cluster (MB)                    |
| `vcd_cluster_mem_total_mb`                  | Total memory for cluster (MB)                       |
| `vcd_cluster_mem_used_mb`                   | Used memory for cluster (MB)                        |
| `vcd_cluster_mem_overhead_mb`               | Overhead memory for cluster (MB)                    |
| `vcd_cluster_storage_allocated_mb`          | Storage allocated for cluster (MB)                  |
| `vcd_cluster_storage_limit_mb`              | Storage limit for cluster (MB)                      |
| `vcd_cluster_storage_used_mb`               | Storage used in cluster (MB)                        |
| `vcd_storage_profile_info`                  | Storage profile info (always 1)                     |
| `vcd_storage_profile_capacity_total_mb`     | Total capacity for storage profile (MB)             |
| `vcd_storage_profile_capacity_used_mb`      | Used capacity for storage profile (MB)              |
| `vcd_storage_profile_iops_capacity`         | IOPS capacity for storage profile                   |
| `vcd_storage_profile_iops_allocated`        | IOPS allocated for storage profile                  |

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

Maintained by [tilzhanov](https://github.com/tilzhanov) and [Temirlaaan](https://github.com/Temirlaaan)

If you use this exporter — please ⭐️ the project or share feedback!
