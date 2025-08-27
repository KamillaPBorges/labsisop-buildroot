#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, os, time, socket, struct
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ----------------------- helpers -----------------------

def _read_first_line(path, default=""):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readline().strip()
    except Exception:
        return default

def _read_all(path, default=""):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return default

def _get_ip_address(ifname: str) -> str or None:
    # ioctl SIOCGIFADDR (0x8915)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(
            struct.pack('256s', ifname.encode('utf-8')[:15])  # ifreq.ifr_name
            and
            struct.unpack('16x4s8x',  # skip name + sa_family
                          fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname.encode('utf-8')[:15])))[0]
        )  # not used (kept for clarity)
    except Exception:
        # implementação portátil (sem fcntl) – tenta via getaddrinfo de bind local
        try:
            # cria UDP e tenta "conectar" para forçar kernel a escolher IP dessa iface
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.01)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

# ----------------------- required fields -----------------------

def get_datetime():
    # ISO 8601 em UTC
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def get_uptime():
    line = _read_first_line("/proc/uptime", "0 0")
    try:
        seconds = float(line.split()[0])
        return int(seconds)
    except Exception:
        return 0

def get_cpu_info():
    cpuinfo = _read_all("/proc/cpuinfo")
    model = "TODO"
    mhz = 0.0
    for line in cpuinfo.splitlines():
        if ":" not in line:
            continue
        k, v = [x.strip() for x in line.split(":", 1)]
        lk = k.lower()
        if lk in ("model name", "hardware", "processor"):
            model = v
        elif lk in ("cpu mhz", "bogomips"):  # bogomips como fallback
            try:
                mhz = float(v)
            except Exception:
                pass

    # % de uso (amostragem curta em /proc/stat)
    def stat_sample():
        s = _read_first_line("/proc/stat")
        parts = s.split()
        if parts and parts[0] == "cpu":
            vals = list(map(int, parts[1:8]))
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
            total = sum(vals)
            return idle, total
        return 0, 0

    idle1, total1 = stat_sample()
    time.sleep(0.2)
    idle2, total2 = stat_sample()
    usage = 0.0
    dt, di = (total2 - total1), (idle2 - idle1)
    if dt > 0:
        usage = 100.0 * (1.0 - (di / dt))

    return {
        "model": model,
        "speed_mhz": round(mhz, 1) if mhz else 0.0,
        "usage_percent": round(usage, 1),
    }

def get_memory_info():
    meminfo = _read_all("/proc/meminfo")
    vals = {}
    for line in meminfo.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            parts = v.strip().split()
            if parts:
                try:
                    vals[k.strip()] = int(parts[0])  # em kB
                except Exception:
                    pass
    total_kb = vals.get("MemTotal", 0)
    avail_kb = vals.get("MemAvailable", vals.get("MemFree", 0))
    used_kb = total_kb - avail_kb if total_kb and avail_kb >= 0 else 0
    return {
        "total_mb": int(total_kb / 1024),
        "used_mb": int(used_kb / 1024),
    }

def get_os_version():
    v = _read_first_line("/proc/version")
    if not v:
        try:
            import platform
            v = platform.platform()
        except Exception:
            v = "unknown"
    return v

def get_process_list():
    procs = []
    try:
        for name in os.listdir("/proc"):
            if not name.isdigit():
                continue
            pid = int(name)
            comm = _read_first_line(f"/proc/{pid}/comm")
            if not comm:
                # fallback: /proc/<pid>/stat segundo campo entre parênteses
                stat = _read_first_line(f"/proc/{pid}/stat")
                if stat:
                    try:
                        start = stat.index('(')
                        end = stat.rindex(')')
                        comm = stat[start+1:end]
                    except Exception:
                        comm = ""
            if comm:
                procs.append({"pid": pid, "name": comm})
        procs.sort(key=lambda x: x["pid"])
        # não precisa listar “todos” — mantém razoável
        return procs[:64]
    except Exception:
        return []

def get_disks():
    items = []
    parts = _read_all("/proc/partitions")
    for line in parts.splitlines()[2:]:
        cols = line.split()
        if len(cols) != 4:
            continue
        name = cols[3]
        # ignora loop/ram/dm para evitar ruído
        if name.startswith(("loop", "ram", "dm-")):
            continue
        try:
            blocks = int(cols[2])  # 1k blocks
            size_mb = int(blocks / 1024)
            items.append({"device": f"/dev/{name}", "size_mb": size_mb})
        except Exception:
            pass
    return items

def get_usb_devices():
    devs = []
    base = "/sys/bus/usb/devices"
    if not os.path.isdir(base):
        return devs
    for d in os.listdir(base):
        path = os.path.join(base, d)
        if not os.path.isdir(path):
            continue
        vid = _read_first_line(os.path.join(path, "idVendor"))
        pid = _read_first_line(os.path.join(path, "idProduct"))
        if not (vid and pid):
            continue
        product = _read_first_line(os.path.join(path, "product")) or "USB device"
        port = d  # nome do nó = “bus-port…”, suficiente como “port”
        devs.append({"port": port, "description": f"{product} ({vid}:{pid})"})
    return devs

def get_network_adapters():
    nets = []
    base = "/sys/class/net"
    if not os.path.isdir(base):
        return nets
    for iface in os.listdir(base):
        if iface == "lo":
            continue
        ip = None
        # tentar via /proc/net/fib_trie -> complexo; vamos por socket ioctl/fallback
        try:
            import fcntl  # stdlib, pode existir no target
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip = socket.inet_ntoa(fcntl.ioctl(
                s.fileno(), 0x8915,  # SIOCGIFADDR
                struct.pack('256s', iface.encode('utf-8')[:15])
            )[20:24])
        except Exception:
            ip = None
        nets.append({"interface": iface, "ip_address": ip or ""})
    return nets

# ----------------------- HTTP server -----------------------

class StatusHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # silencia logs no console do target
        pass

    def do_GET(self):
        if self.path != "/status":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        response = {
            "datetime": get_datetime(),
            "uptime_seconds": get_uptime(),
            "cpu": get_cpu_info(),
            "memory": get_memory_info(),
            "os_version": get_os_version(),
            "processes": get_process_list(),
            "disks": get_disks(),
            "usb_devices": get_usb_devices(),
            "network_adapters": get_network_adapters(),
        }

        data = json.dumps(response, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

def run_server(port=8080):
    print(f"* Servidor disponível em http://0.0.0.0:{port}/status")
    HTTPServer(("0.0.0.0", port), StatusHandler).serve_forever()

if __name__ == "__main__":
    run_server()
