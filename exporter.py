#!/usr/bin/env python3
import os, time, requests, xml.etree.ElementTree as ET
from flask import Flask, Response
from urllib.parse import urlparse, urljoin
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)

NS = {'vcloud': 'http://www.vmware.com/vcloud/v1.5'}

# ---------------------------------------------------------------------
# OAuth 2.0 bearer-token cache
# ---------------------------------------------------------------------
_token_cache = {'token': None, 'expires_at': 0}

def get_bearer_token() -> str:
    now = time.time()
    if _token_cache['token'] is None or now >= _token_cache['expires_at'] - 60:
        refresh = os.environ.get('VCD_API_TOKEN')
        if not refresh:
            raise RuntimeError('VCD_API_TOKEN not set')
        parts = urlparse(os.environ['VCD_URL'])
        token_url = f"{parts.scheme}://{parts.netloc}/oauth/provider/token"
        r = requests.post(
            token_url,
            params={'grant_type': 'refresh_token', 'refresh_token': refresh},
            headers={'Accept': 'application/json'},
            verify=False, timeout=(5, 10)
        )
        r.raise_for_status()
        data = r.json()
        _token_cache['token'] = data['access_token']
        _token_cache['expires_at'] = now + int(data.get('expires_in', 3600))
    return _token_cache['token']

# ---------------------------------------------------------------------
# ComputeCapacity fetch
# ---------------------------------------------------------------------
def fetch_compute_capacity(href: str, headers: dict) -> dict:
    r = requests.get(href, headers=headers, verify=False, timeout=(5, 10))
    r.raise_for_status()
    tree = ET.fromstring(r.content)
    cap = tree.find('vcloud:ComputeCapacity', NS)
    cpu = cap.find('vcloud:Cpu', NS) if cap is not None else None
    mem = cap.find('vcloud:Memory', NS) if cap is not None else None
    def intval(el, tag):
        n = el.find(f'vcloud:{tag}', NS) if el is not None else None
        return int(n.text) if n is not None and n.text and n.text.isdigit() else 0
    return {
        'cpu_allocation': intval(cpu, 'Allocation'),
        'cpu_reserved':   intval(cpu, 'Reserved'),
        'cpu_total':      intval(cpu, 'Total'),
        'cpu_used':       intval(cpu, 'Used'),
        'cpu_overhead':   intval(cpu, 'Overhead'),
        'mem_allocation': intval(mem, 'Allocation'),
        'mem_reserved':   intval(mem, 'Reserved'),
        'mem_total':      intval(mem, 'Total'),
        'mem_used':       intval(mem, 'Used'),
        'mem_overhead':   intval(mem, 'Overhead'),
    }

# ---------------------------------------------------------------------
# StorageProfiles fetch
# ---------------------------------------------------------------------
def fetch_storage_profiles(href: str, headers: dict) -> list:
    out = []
    try:
        r = requests.get(href, headers=headers, verify=False, timeout=(5, 10))
        r.raise_for_status()
        tree = ET.fromstring(r.content)
        sec = tree.find('.//vcloud:StorageProfiles', NS)
        if sec is not None:
            for prof in sec.findall('.//vcloud:ProviderVdcStorageProfile', NS):
                name = prof.get('name')
                href_p = prof.get('href')
                if name and href_p:
                    details = fetch_storage_profile_details(href_p, headers)
                    out.append({'name': name, **details})
    except Exception:
        pass
    return out

# ---------------------------------------------------------------------
# StorageProfile details fetch
# ---------------------------------------------------------------------
def fetch_storage_profile_details(profile_href: str, headers: dict) -> dict:
    try:
        r = requests.get(profile_href, headers=headers, verify=False, timeout=(5, 10))
        r.raise_for_status()
        tree = ET.fromstring(r.content)
        def parse(el):
            if el is not None and el.text:
                try: return float(el.text)
                except ValueError: return 0.0
            return 0.0
        return {
            'capacity_total': parse(tree.find('.//vcloud:CapacityTotal', NS)),
            'capacity_used':  parse(tree.find('.//vcloud:CapacityUsed', NS)),
            'iops_capacity':  parse(tree.find('.//vcloud:IopsCapacity', NS)),
            'iops_allocated': parse(tree.find('.//vcloud:IopsAllocated', NS)),
        }
    except Exception:
        return {'capacity_total':0.0, 'capacity_used':0.0, 'iops_capacity':0.0, 'iops_allocated':0.0}

# ---------------------------------------------------------------------
# /metrics endpoint
# ---------------------------------------------------------------------
@app.route('/metrics')
def metrics():
    base_url = os.environ.get('VCD_URL')
    api_ver = os.environ.get('VCD_API_VERSION', '38.0')
    page_size = int(os.environ.get('VCD_PAGE_SIZE', '128'))
    if not base_url:
        return Response('VCD_URL not set', 500)
    try:
        token = get_bearer_token()
    except Exception as e:
        return Response(f'Token error: {e}', 500)
    headers = {'Accept': f'application/*+xml;version={api_ver}', 'Authorization': f'Bearer {token}'}

    # 1. Fetch AdminVdcRecords
    all_vdc_records, cluster_refs = [], {}
    url = base_url
    while url:
        r = requests.get(url, headers=headers, verify=False, timeout=(5, 10))
        if r.status_code != 200:
            return Response(f'Error {r.status_code} on {url}', 500)
        tree = ET.fromstring(r.content)
        for rec in tree.findall('.//vcloud:AdminVdcRecord', NS):
            all_vdc_records.append(rec)
            nm, href = rec.get('providerVdcName'), rec.get('providerVdc')
            if nm and href: cluster_refs[nm] = href
        nxt = tree.find(".//vcloud:Link[@rel='nextPage']", NS)
        url = urljoin(base_url, nxt.get('href')) if nxt is not None else None

    # 2. Fetch providerVdc storage info
    parts = urlparse(base_url)
    prov_url = f"{parts.scheme}://{parts.netloc}/api/query?type=providerVdc&format=records&pageSize={page_size}"
    cluster_storage, p_url = {}, prov_url
    while p_url:
        r = requests.get(p_url, headers=headers, verify=False, timeout=(5, 10))
        r.raise_for_status()
        tree = ET.fromstring(r.content)
        for rec in tree.findall('.//vcloud:VMWProviderVdcRecord', NS):
            nm = rec.get('name')
            cluster_storage[nm] = {
                'storage_alloc': int(rec.get('storageAllocationMB',0)),
                'storage_limit': int(rec.get('storageLimitMB',0)),
                'storage_used':  int(rec.get('storageUsedMB',0)),
            }
            if nm not in cluster_refs and rec.get('href'):
                cluster_refs[nm] = rec.get('href')
        nxt = tree.find(".//vcloud:Link[@rel='nextPage']", NS)
        p_url = urljoin(f"{parts.scheme}://{parts.netloc}", nxt.get('href')) if nxt is not None else None

    # 3. Fetch compute capacity for clusters
    zero = dict(cpu_allocation=0, cpu_reserved=0, cpu_total=0, cpu_used=0, cpu_overhead=0,
                mem_allocation=0, mem_reserved=0, mem_total=0, mem_used=0, mem_overhead=0)
    cluster_caps = {}
    for nm, href in cluster_refs.items():
        try: cluster_caps[nm] = fetch_compute_capacity(href, headers)
        except: cluster_caps[nm] = zero.copy()
    for nm in cluster_storage: cluster_caps.setdefault(nm, zero.copy())

    # 4. Fetch storage profiles per cluster
    cluster_profiles = {nm: fetch_storage_profiles(href, headers) for nm, href in cluster_refs.items()}
    profile_agg = {}
    for profs in cluster_profiles.values():
        for p in profs: profile_agg.setdefault(p['name'], p)

    # 5. Build Prometheus metrics with all HELP/TYPE at top
    lines = [
        # VDC metrics
        '# HELP vcd_vdc_cpu_allocated Allocated CPU (MHz) for VDC',
        '# TYPE vcd_vdc_cpu_allocated gauge',
        '# HELP vcd_vdc_cpu_used Used CPU (MHz) for VDC',
        '# TYPE vcd_vdc_cpu_used gauge',
        '# HELP vcd_vdc_mem_allocated_mb Allocated memory (MB) for VDC',
        '# TYPE vcd_vdc_mem_allocated_mb gauge',
        '# HELP vcd_vdc_mem_used_mb Used memory (MB) for VDC',
        '# TYPE vcd_vdc_mem_used_mb gauge',
        '# HELP vcd_vdc_vm_count Number of VMs in VDC',
        '# TYPE vcd_vdc_vm_count gauge',
        '# HELP vcd_vdc_storage_allocated_mb Storage limit (MB) for VDC',
        '# TYPE vcd_vdc_storage_allocated_mb gauge',
        '# HELP vcd_vdc_storage_used_mb Storage used (MB) for VDC',
        '# TYPE vcd_vdc_storage_used_mb gauge',
        # Cluster metrics
        '# HELP vcd_cluster_cpu_allocated Allocated CPU (MHz) for cluster',
        '# TYPE vcd_cluster_cpu_allocated gauge',
        '# HELP vcd_cluster_cpu_reserved Reserved CPU (MHz) for cluster',
        '# TYPE vcd_cluster_cpu_reserved gauge',
        '# HELP vcd_cluster_cpu_total Total CPU (MHz) for cluster',
        '# TYPE vcd_cluster_cpu_total gauge',
        '# HELP vcd_cluster_cpu_used Used CPU (MHz) for cluster',
        '# TYPE vcd_cluster_cpu_used gauge',
        '# HELP vcd_cluster_cpu_overhead Overhead CPU (MHz) for cluster',
        '# TYPE vcd_cluster_cpu_overhead gauge',
        '# HELP vcd_cluster_mem_allocated_mb Allocated memory (MB) for cluster',
        '# TYPE vcd_cluster_mem_allocated_mb gauge',
        '# HELP vcd_cluster_mem_reserved_mb Reserved memory (MB) for cluster',
        '# TYPE vcd_cluster_mem_reserved_mb gauge',
        '# HELP vcd_cluster_mem_total_mb Total memory (MB) for cluster',
        '# TYPE vcd_cluster_mem_total_mb gauge',
        '# HELP vcd_cluster_mem_used_mb Used memory (MB) for cluster',
        '# TYPE vcd_cluster_mem_used_mb gauge',
        '# HELP vcd_cluster_mem_overhead_mb Overhead memory (MB) for cluster',
        '# TYPE vcd_cluster_mem_overhead_mb gauge',
        '# HELP vcd_cluster_storage_allocated_mb Storage allocation (MB) for cluster',
        '# TYPE vcd_cluster_storage_allocated_mb gauge',
        '# HELP vcd_cluster_storage_limit_mb Storage limit (MB) for cluster',
        '# TYPE vcd_cluster_storage_limit_mb gauge',
        '# HELP vcd_cluster_storage_used_mb Storage used (MB) for cluster',
        '# TYPE vcd_cluster_storage_used_mb gauge',
        # Storage profile metrics
        '# HELP vcd_storage_profile_info Storage profile info',
        '# TYPE vcd_storage_profile_info gauge',
        '# HELP vcd_storage_profile_capacity_total_mb Total capacity (MB) for profile',
        '# TYPE vcd_storage_profile_capacity_total_mb gauge',
        '# HELP vcd_storage_profile_capacity_used_mb Used capacity (MB) for profile',
        '# TYPE vcd_storage_profile_capacity_used_mb gauge',
        '# HELP vcd_storage_profile_iops_capacity IOPS capacity for profile',
        '# TYPE vcd_storage_profile_iops_capacity gauge',
        '# HELP vcd_storage_profile_iops_allocated IOPS allocated for profile',
        '# TYPE vcd_storage_profile_iops_allocated gauge',
    ]
    # VDC metric values
    for rec in all_vdc_records:
        vdc = rec.get('name','unknown').replace('"','\\"')
        org = rec.get('orgName','unknown').replace('"','\\"')
        cl  = rec.get('providerVdcName','unknown').replace('"','\\"')
        lbl = f'vdc="{vdc}",org="{org}",cluster="{cl}"'
        lines += [
            f'vcd_vdc_cpu_allocated{{{lbl}}} {rec.get("cpuAllocationMhz",0)}',
            f'vcd_vdc_cpu_used{{{lbl}}} {rec.get("cpuUsedMhz",0)}',
            f'vcd_vdc_mem_allocated_mb{{{lbl}}} {rec.get("memoryAllocationMB",0)}',
            f'vcd_vdc_mem_used_mb{{{lbl}}} {rec.get("memoryUsedMB",0)}',
            f'vcd_vdc_vm_count{{{lbl}}} {rec.get("numberOfVMs",0)}',
            f'vcd_vdc_storage_allocated_mb{{{lbl}}} {rec.get("storageLimitMB",0)}',
            f'vcd_vdc_storage_used_mb{{{lbl}}} {rec.get("storageUsedMB",0)}',
        ]
    lines.append(f'vcd_vdc_total_records {len(all_vdc_records)}')

    # Cluster metric values
    for nm, cap in cluster_caps.items():
        lbl = f'cluster="{nm}"'
        lines += [
            f'vcd_cluster_cpu_allocated{{{lbl}}} {cap["cpu_allocation"]}',
            f'vcd_cluster_cpu_reserved{{{lbl}}} {cap["cpu_reserved"]}',
            f'vcd_cluster_cpu_total{{{lbl}}} {cap["cpu_total"]}',
            f'vcd_cluster_cpu_used{{{lbl}}} {cap["cpu_used"]}',
            f'vcd_cluster_cpu_overhead{{{lbl}}} {cap["cpu_overhead"]}',
            f'vcd_cluster_mem_allocated_mb{{{lbl}}} {cap["mem_allocation"]}',
            f'vcd_cluster_mem_reserved_mb{{{lbl}}} {cap["mem_reserved"]}',
            f'vcd_cluster_mem_total_mb{{{lbl}}} {cap["mem_total"]}',
            f'vcd_cluster_mem_used_mb{{{lbl}}} {cap["mem_used"]}',
            f'vcd_cluster_mem_overhead_mb{{{lbl}}} {cap["mem_overhead"]}',
        ]
        stor = cluster_storage.get(nm, {'storage_alloc':0,'storage_limit':0,'storage_used':0})
        lines += [
            f'vcd_cluster_storage_allocated_mb{{{lbl}}} {stor["storage_alloc"]}',
            f'vcd_cluster_storage_limit_mb{{{lbl}}} {stor["storage_limit"]}',
            f'vcd_cluster_storage_used_mb{{{lbl}}} {stor["storage_used"]}',
        ]

    # Storage profile metric values
    for name, p in profile_agg.items():
        lbl = f'storage_profile="{name}"'
        lines += [
            f'vcd_storage_profile_info{{{lbl}}} 1',
            f'vcd_storage_profile_capacity_total_mb{{{lbl}}} {p["capacity_total"]:.2f}',
            f'vcd_storage_profile_capacity_used_mb{{{lbl}}} {p["capacity_used"]:.2f}',
            f'vcd_storage_profile_iops_capacity{{{lbl}}} {p["iops_capacity"]}',
            f'vcd_storage_profile_iops_allocated{{{lbl}}} {p["iops_allocated"]}',
        ]

    return Response("\n".join(lines), mimetype='text/plain')

@app.route('/health')
def health():
    return Response('OK', mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('EXPORTER_PORT','8000')), debug=False)
