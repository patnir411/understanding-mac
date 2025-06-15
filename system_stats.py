from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.text import Text
from rich.box import ROUNDED
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.table import Table

import argparse
import json
import logging
import os
import sys
import time
from collections import OrderedDict

import psutil
from dotenv import load_dotenv
from openai import OpenAI
from rich import box
from utils import (
    format_value,
    format_bytes,
    format_time,
    highlight_critical_values,
    format_disk_partitions,
    format_memory_details,
    format_swap_memory_details,
    format_disk_details,
    format_network_connections,
)

try:
    import GPUtil
except Exception:
    GPUtil = None

try:
    from cpuinfo import get_cpu_info
except Exception:
    get_cpu_info = None


# Securely load environment variables
load_dotenv()

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    org = os.environ.get("OPENAI_API_ORG_ID")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, organization=org)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def gather_cpu_stats():
    cpu_stats = OrderedDict()

    # Overall CPU Usage
    cpu_stats['CPU Usage'] = {
        'Overall': psutil.cpu_percent(interval=1),
        'Per CPU': psutil.cpu_percent(interval=1, percpu=True)
    }

    # CPU Times
    cpu_times = psutil.cpu_times()
    cpu_stats['CPU Times'] = {
        'User': cpu_times.user,
        'System': cpu_times.system,
        'Idle': cpu_times.idle,
    }

    # CPU Frequency
    cpu_freq = psutil.cpu_freq()
    cpu_stats['CPU Frequency'] = {
        'Current': cpu_freq.current,
        'Min': cpu_freq.min,
        'Max': cpu_freq.max
    }

    # CPU Counts
    cpu_stats['CPU Counts'] = {
        'Physical': psutil.cpu_count(logical=False),
        'Logical': psutil.cpu_count(logical=True)
    }

    # CPU Load
    load1, load5, load15 = psutil.getloadavg()
    cpu_stats['CPU Load Average'] = {
        '1 min': load1,
        '5 min': load5,
        '15 min': load15
    }

    # Context Switches and Interrupts
    if hasattr(psutil, 'cpu_stats'):
        cpu_stats_info = psutil.cpu_stats()
        cpu_stats['CPU Stats'] = {
            'Context Switches': cpu_stats_info.ctx_switches,
            'Interrupts': cpu_stats_info.interrupts,
            'Soft Interrupts': cpu_stats_info.soft_interrupts,
            'Syscalls': cpu_stats_info.syscalls
        }

    return cpu_stats


def gather_cpu_info_details():
    if get_cpu_info is None:
        return {}
    try:
        info = get_cpu_info()
        return {k: info.get(k) for k in ['brand_raw', 'arch', 'bits', 'count']}
    except Exception as e:
        return {'error': str(e)}

def gather_memory_stats():
    memory_stats = OrderedDict()

    # Virtual Memory
    virtual_memory = psutil.virtual_memory()
    memory_stats['Virtual Memory'] = {
        'Total': virtual_memory.total,
        'Available': virtual_memory.available,
        'Used': virtual_memory.used,
        'Free': virtual_memory.free,
        'Percent': virtual_memory.percent,
        'Active': getattr(virtual_memory, 'active', 'N/A'),
        'Inactive': getattr(virtual_memory, 'inactive', 'N/A'),
        'Buffers': getattr(virtual_memory, 'buffers', 'N/A'),
        'Cached': getattr(virtual_memory, 'cached', 'N/A')
    }

    # Swap Memory
    swap_memory = psutil.swap_memory()
    memory_stats['Swap Memory'] = {
        'Total': swap_memory.total,
        'Used': swap_memory.used,
        'Free': swap_memory.free,
        'Percent': swap_memory.percent,
        'Sin': getattr(swap_memory, 'sin', 'N/A'),
        'Sout': getattr(swap_memory, 'sout', 'N/A')
    }

    return memory_stats


def gather_disk_stats():
    disk_stats = OrderedDict()

    # Disk Usage
    disk_usage = psutil.disk_usage('/')
    disk_stats['Disk Usage'] = {
        'Total': disk_usage.total,
        'Used': disk_usage.used,
        'Free': disk_usage.free,
        'Percent': disk_usage.percent
    }

    # Disk IO
    disk_io = psutil.disk_io_counters()
    disk_stats['Disk IO'] = {
        'Read Count': disk_io.read_count,
        'Write Count': disk_io.write_count,
        'Read Bytes': disk_io.read_bytes,
        'Write Bytes': disk_io.write_bytes,
        'Read Time': disk_io.read_time,
        'Write Time': disk_io.write_time
    }

    # Disk Partitions
    disk_stats['Disk Partitions'] = []
    for partition in psutil.disk_partitions():
        disk_stats['Disk Partitions'].append({
            'Device': partition.device,
            'Mountpoint': partition.mountpoint,
            'FSType': partition.fstype,
            'Opts': partition.opts
        })

    return disk_stats


def gather_network_stats():
    network_stats = OrderedDict()

    # Network IO Counters
    network_stats['Network IO'] = {}
    for iface, stats in psutil.net_io_counters(pernic=True).items():
        network_stats['Network IO'][iface] = {
            'Bytes Sent': stats.bytes_sent,
            'Bytes Received': stats.bytes_recv,
            'Packets Sent': stats.packets_sent,
            'Packets Received': stats.packets_recv,
            'Errors In': stats.errin,
            'Errors Out': stats.errout,
            'Drop In': stats.dropin,
            'Drop Out': stats.dropout
        }

    # Network Interfaces
    network_stats['Network Interfaces'] = {}
    for iface, addrs in psutil.net_if_addrs().items():
        network_stats['Network Interfaces'][iface] = []
        for addr in addrs:
            network_stats['Network Interfaces'][iface].append({
                'Family': str(addr.family),
                'Address': addr.address,
                'Netmask': addr.netmask,
                'Broadcast': getattr(addr, 'broadcast', 'N/A')
            })

    # Network Connections
    network_stats['Network Connections'] = []
    for conn in psutil.net_connections(kind='inet'):
        network_stats['Network Connections'].append({
            'FD': conn.fd,
            'Family': str(conn.family),
            'Type': str(conn.type),
            'Local Address': f"{conn.laddr.ip}:{conn.laddr.port}",
            'Remote Address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else 'N/A',
            'Status': conn.status,
            'PID': conn.pid
        })

    return network_stats


def gather_gpu_stats():
    gpu_stats = []
    if GPUtil is None:
        return gpu_stats
    try:
        for gpu in GPUtil.getGPUs():
            gpu_stats.append(
                {
                    "id": gpu.id,
                    "name": gpu.name,
                    "load": gpu.load * 100,
                    "memory_total": gpu.memoryTotal,
                    "memory_used": gpu.memoryUsed,
                    "memory_free": gpu.memoryFree,
                    "temperature": gpu.temperature,
                }
            )
    except Exception as e:
        gpu_stats = [f"Error getting GPU stats: {e}"]
    return gpu_stats


def gather_sensor_stats():
    sensors = {}
    try:
        temps = psutil.sensors_temperatures(fahrenheit=False)
        sensors["temperatures"] = {k: [t.current for t in v] for k, v in temps.items()}
    except Exception:
        sensors["temperatures"] = "N/A"
    try:
        fans = psutil.sensors_fans()
        sensors["fans"] = {k: [f.current for f in v] for k, v in fans.items()}
    except Exception:
        sensors["fans"] = "N/A"
    return sensors


def gather_network_scan(subnet):
    from scapy.all import ARP, Ether, srp

    results = []
    try:
        arp = ARP(pdst=subnet)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp
        answered = srp(packet, timeout=2, verbose=False)[0]
        for _, received in answered:
            results.append({"ip": received.psrc, "mac": received.hwsrc})
    except Exception as e:
        results = [f"Network scan failed: {e}"]
    return results


def gather_other_stats():
    other_stats = OrderedDict()

    # Processes
    other_stats['Processes'] = {
        'Total': len(psutil.pids()),
        'Details': []
    }
    for proc in psutil.process_iter(['pid', 'name', 'username', 'status']):
        other_stats['Processes']['Details'].append({
            'PID': proc.info['pid'],
            'Name': proc.info['name'],
            'Username': proc.info['username'],
            'Status': proc.info['status']
        })

    # Battery
    battery = psutil.sensors_battery()
    if battery:
        other_stats['Battery'] = {
            'Percent': battery.percent,
            'Seconds Left': battery.secsleft,
            'Power Plugged': battery.power_plugged
        }
    else:
        other_stats['Battery'] = 'No battery information available'

    # Boot Time
    other_stats['Boot Time'] = psutil.boot_time()

    # Users
    other_stats['Users'] = []
    for user in psutil.users():
        other_stats['Users'].append({
            'Name': user.name,
            'Terminal': user.terminal,
            'Host': user.host,
            'Started': user.started,
            'PID': user.pid
        })

    return other_stats


def gather_system_stats(progress):
    tasks = {
        'CPU Stats': progress.add_task("Gathering CPU stats...", total=5),
        'Memory Stats': progress.add_task("Gathering Memory stats...", total=3),
        'Disk Stats': progress.add_task("Gathering Disk stats...", total=4),
        'Network Stats': progress.add_task("Gathering Network stats...", total=3),
        'Sensor Stats': progress.add_task("Gathering Sensor stats...", total=2),
        'GPU Stats': progress.add_task("Gathering GPU stats...", total=2),
        'CPU Info': progress.add_task("Gathering CPU info...", total=1),
        'Other Stats': progress.add_task("Gathering Other stats...", total=4)
    }

    system_stats = OrderedDict()

    try:
        # CPU Stats
        progress.update(tasks['CPU Stats'], advance=1)
        system_stats['CPU Stats'] = gather_cpu_stats()
        progress.update(tasks['CPU Stats'], advance=4)

        # Memory Stats
        progress.update(tasks['Memory Stats'], advance=1)
        system_stats['Memory Stats'] = gather_memory_stats()
        progress.update(tasks['Memory Stats'], advance=2)

        # Disk Stats
        progress.update(tasks['Disk Stats'], advance=1)
        system_stats['Disk Stats'] = gather_disk_stats()
        progress.update(tasks['Disk Stats'], advance=3)

        # Network Stats
        progress.update(tasks['Network Stats'], advance=1)
        system_stats['Network Stats'] = gather_network_stats()
        progress.update(tasks['Network Stats'], advance=2)

        # Sensor Stats
        progress.update(tasks['Sensor Stats'], advance=1)
        system_stats['Sensor Stats'] = gather_sensor_stats()
        progress.update(tasks['Sensor Stats'], advance=1)

        # GPU Stats
        progress.update(tasks['GPU Stats'], advance=1)
        system_stats['GPU Stats'] = gather_gpu_stats()
        progress.update(tasks['GPU Stats'], advance=1)

        # CPU Info
        progress.update(tasks['CPU Info'], advance=1)
        system_stats['CPU Info'] = gather_cpu_info_details()

        # Other Stats
        progress.update(tasks['Other Stats'], advance=1)
        system_stats['Other Stats'] = gather_other_stats()
        progress.update(tasks['Other Stats'], advance=3)

    except Exception as e:
        logging.error(f"Error gathering system stats: {e}")
        system_stats = OrderedDict({"error": f"Error gathering system stats: {e}"})

    return system_stats


def query_gpt(system_stats, user_query="Tell me about my computer."):
    client = get_openai_client()
    if client is None:
        return "OpenAI API key not configured."

    spinner = Spinner("dots", text="Querying GPT...")
    response = ""
    with Live(spinner, refresh_per_second=20, transient=True, vertical_overflow="visible") as live:
        for chunk in client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert systems monitor. Provide useful overall insights about the system and answer any questions the user has. Be brief and concise, only elaborate when asked."
                },
                {
                    "role": "user",
                    "content": str(system_stats)
                },
                {
                    "role": "user",
                    "content": user_query
                }
            ],
            max_tokens=4096,
            stream=True,
        ):
            content = chunk.choices[0].delta.content
            if content is None:
                break
            response += content
            spinner.update(text=Markdown(response))
        spinner.update(text="")
    return response.strip()


def generate_insights(system_stats):
    insights = []
    try:
        cpu_usage = system_stats["CPU Stats"]["CPU Usage"]["Overall"]
        if cpu_usage > 80:
            insights.append(f"High CPU usage detected: {cpu_usage}%")
        mem_percent = system_stats["Memory Stats"]["Virtual Memory"]["Percent"]
        if mem_percent > 80:
            insights.append(f"Memory usage is high at {mem_percent}%")
        disk_percent = system_stats["Disk Stats"]["Disk Usage"]["Percent"]
        if disk_percent > 90:
            insights.append(f"Disk almost full: {disk_percent}% used")
    except Exception:
        pass
    return insights


def create_stats_table(system_stats):
    panels = []
    table = Table(box=box.HORIZONTALS, show_header=False, show_lines=True, border_style="magenta")
    table.add_column("Category", style="bold cyan", width=20)
    table.add_column("Details", style="green")

    for category, stats in system_stats.items():
        category_table = Table(box=box.ROUNDED, show_lines=True, show_header=False)
        category_table.add_column("Metric", style="cyan")
        category_table.add_column("Value")

        for metric, details in stats.items():
            if isinstance(details, dict):
                nested_table = Table(box=box.SIMPLE, show_header=False)
                nested_table.add_column("Sub-Metric", style="dim cyan")
                nested_table.add_column("Value")
                for sub_metric, value in details.items():
                    nested_table.add_row(sub_metric, format_value(value))
                category_table.add_row(metric, nested_table)
            elif isinstance(details, list) and metric in ["Disk Partitions", "Network Connections", "Users", "Network Scan", "GPU Stats"]:
                nested_table = Table(box=box.SIMPLE, show_header=True)
                if details:
                    headers = details[0].keys()
                    for header in headers:
                        nested_table.add_column(header.capitalize(), style="dim cyan")
                    for item in details:
                        nested_table.add_row(*[format_value(item[header]) for header in headers])
                category_table.add_row(metric, nested_table)
            else:
                category_table.add_row(metric, format_value(details))
        table.add_row(category, category_table)

    return table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Advanced system statistics tool")
    parser.add_argument("--query", help="Ask a question about the gathered stats")
    parser.add_argument("--export", help="Write the stats to a JSON file")
    parser.add_argument("--scan", help="Subnet to scan for active hosts")
    args = parser.parse_args()

    console = Console()

    with Progress() as progress:
        system_stats = gather_system_stats(progress)

    if args.scan:
        system_stats["Network Scan"] = gather_network_scan(args.scan)

    insights = generate_insights(system_stats)

    stats_display_table = create_stats_table(system_stats)
    console.print(stats_display_table)

    if insights:
        console.print(Panel("\n".join(insights), title="Insights", style="yellow"))

    if args.export:
        with open(args.export, "w") as f:
            json.dump(system_stats, f, indent=2)

    if args.query:
        response = query_gpt(system_stats, args.query)
        console.print(Markdown(response))
    else:
        while True:
            user_query = input("Ask me a question about your system (exit to quit): ")
            if user_query.lower() == "exit":
                break
            response = query_gpt(system_stats, user_query)
            console.print(Markdown(response))
