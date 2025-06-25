from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, ProgressBar
from rich.text import Text
from rich.box import ROUNDED
# from rich.bar import Bar # No longer used
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.tree import Tree
from rich.table import Table
from rich.theme import Theme # Moved here for global scope

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
    # highlight_critical_values, # Removed, no longer used
    # format_disk_partitions,    # Removed, no longer used
    # format_memory_details,     # Removed, no longer used
    # format_swap_memory_details,# Removed, no longer used
    # format_disk_details,       # Removed, no longer used
    # format_network_connections,# Removed, no longer used
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


from rich.layout import Layout


def create_panel_for_category(category_name: str, category_data: OrderedDict) -> Panel:
    """Creates a Rich Panel for a single category of stats."""
    # Using theme styles for table and panel elements
    category_table = Table(box=box.ROUNDED, show_lines=True, show_header=False, title_style="panel.title", border_style="panel.border")
    category_table.add_column("Metric", style="table.header", no_wrap=True)
    category_table.add_column("Value", style="table.cell")

    for metric, details in category_data.items():
        # --- Direct ProgressBar Rendering ---
        if metric == "Overall" and category_name == "CPU Stats" and isinstance(details, (float, int)):
            # ProgressBar: value is 'completed', total is 'total'. width=None for auto.
            progress_bar = ProgressBar(completed=details, total=100, width=None, style="progress.background", complete_style="bar.complete", finished_style="bar.finished")
            category_table.add_row(metric, progress_bar)
        # --- Tree Rendering ---
        elif metric == "Disk Partitions" and isinstance(details, list) and details:
            tree = Tree(f"[table.header]{metric}[/]", guide_style="rule.line")
            for partition in details:
                if isinstance(partition, dict):
                    node_label = format_value(partition.get('Device', 'N/A'))
                    node = tree.add(Text(node_label, style="info"))
                    node.add(f"Mount: {format_value(partition.get('Mountpoint'))}")
                    node.add(f"Type: {format_value(partition.get('FSType'))}")
                    node.add(f"Opts: {format_value(partition.get('Opts'))}")
                else:
                    tree.add(Text(str(partition), style="warning"))
            category_table.add_row(Text(metric, style="table.header"), tree) # Add metric name separately if tree is the value
        elif metric == "Network Interfaces" and isinstance(details, dict) and details: # details is a dict of ifaces
            tree = Tree(f"[table.header]{metric}[/]", guide_style="rule.line")
            for iface_name, addr_list in details.items(): # details is the dict of interfaces
                iface_node = tree.add(Text(iface_name, style="info"))
                if isinstance(addr_list, list):
                    for addr_info in addr_list:
                        if isinstance(addr_info, dict):
                            addr_label = f"{format_value(addr_info.get('Family'))}: {format_value(addr_info.get('Address'))}"
                            addr_node = iface_node.add(Text(addr_label))
                            addr_node.add(f"Netmask: {format_value(addr_info.get('Netmask'))}")
                            addr_node.add(f"Broadcast: {format_value(addr_info.get('Broadcast'))}")
                        else:
                            iface_node.add(Text(str(addr_info), style="warning"))
                else:
                     iface_node.add(Text(f"Unexpected data: {addr_list}", style="warning"))
            category_table.add_row(Text(metric, style="table.header"), tree)
        # --- Nested Dictionary Handling (potentially with Bars) ---
        elif isinstance(details, dict):
            # Special handling for Memory Stats to correctly place bars
            if category_name == "Memory Stats" and (metric == "Virtual Memory" or metric == "Swap Memory"):
                sub_table = Table(box=box.SIMPLE, show_header=False, border_style="panel.border")
                sub_table.add_column("Sub-Metric", style="info")
                sub_table.add_column("Value", style="table.cell")
                for sub_metric, value in details.items():
                    if sub_metric == "Percent" and isinstance(value, (float, int)):
                        progress_bar = ProgressBar(completed=value, total=100, width=None, style="progress.background", complete_style="bar.complete", finished_style="bar.finished")
                        sub_table.add_row(sub_metric, progress_bar)
                    else:
                        sub_table.add_row(sub_metric, format_value(value))
                category_table.add_row(metric, sub_table)
            # Special handling for Disk Usage Percent Bar
            elif category_name == "Disk Stats" and metric == "Disk Usage":
                sub_table = Table(box=box.SIMPLE, show_header=False, border_style="panel.border")
                sub_table.add_column("Sub-Metric", style="info")
                sub_table.add_column("Value", style="table.cell")
                for sub_metric, value in details.items():
                    if sub_metric == "Percent" and isinstance(value, (float, int)):
                        progress_bar = ProgressBar(completed=value, total=100, width=None, style="progress.background", complete_style="bar.complete", finished_style="bar.finished")
                        sub_table.add_row(sub_metric, progress_bar)
                    else:
                        sub_table.add_row(sub_metric, format_value(value))
                category_table.add_row(metric, sub_table)
            else: # Generic nested dictionary
                sub_table = Table(box=box.SIMPLE, show_header=False, border_style="panel.border")
                sub_table.add_column("Sub-Metric", style="info")
                sub_table.add_column("Value", style="table.cell")
                for sub_metric, value in details.items():
                    sub_table.add_row(sub_metric, format_value(value))
                category_table.add_row(metric, sub_table)
        # --- List Handling (fallback to Table) ---
        elif isinstance(details, list):
            # Handles Users, Network Connections, GPU Stats (success/error list), Processes['Details']
            list_table = Table(box=box.SIMPLE, show_header=True, border_style="panel.border")
            if details:
                if all(isinstance(item, dict) for item in details):
                    headers = details[0].keys() # Assumes all dicts have same keys
                    for header in headers:
                        list_table.add_column(header.capitalize(), style="info")
                    for item in details:
                        list_table.add_row(*[format_value(item.get(header, "N/A")) for header in headers])
                elif all(isinstance(item, str) for item in details): # For GPU error messages as list of str
                    list_table.show_header = False # No headers for simple list of strings
                    for item_str in details:
                        list_table.add_row(Text(item_str, style="warning"))
                else: # Mixed or other non-dict list content
                     category_table.add_row(metric, Text(f"List: {str(details)[:100]}...", style="italic warning")) # Truncate
                     continue # Skip adding this list_table if format is too weird
            else:
                list_table.add_row(Text("No data available.", style="italic info"))
            category_table.add_row(metric, list_table)
        # --- Simple Key-Value Fallback ---
        else:
            category_table.add_row(metric, format_value(details))

    # Panel title uses a specific color, border uses theme's panel.border
    return Panel(category_table, title=f"[{custom_theme.styles['panel.title']}]{category_name}[/]", border_style="panel.border", expand=True)


def create_system_layout(system_stats: OrderedDict, current_theme: Theme) -> Layout:
    """Creates the layout for displaying system statistics."""
    layout = Layout(name="root")

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=5)
    )

    layout["main"].split_row(
        Layout(name="left_column"),
        Layout(name="right_column"),
    )

    layout["left_column"].split_column(
        Layout(name="cpu_mem", ratio=2),
        Layout(name="disk_net", ratio=3)
    )
    layout["cpu_mem"].split_row(Layout(name="cpu"), Layout(name="memory"))
    layout["disk_net"].split_row(Layout(name="disk"), Layout(name="network"))

    layout["right_column"].split_column(
        Layout(name="sensors_gpu", ratio=1),
        Layout(name="other", ratio=2)
    )
    layout["sensors_gpu"].split_row(Layout(name="sensors"), Layout(name="gpu"))
    layout["other"].split_row(Layout(name="cpu_info"), Layout(name="misc"))

    # Populate layout with panels, passing the theme
    if "CPU Stats" in system_stats:
        layout["cpu"].update(create_panel_for_category("CPU Stats", system_stats["CPU Stats"]))
    if "Memory Stats" in system_stats:
        layout["memory"].update(create_panel_for_category("Memory Stats", system_stats["Memory Stats"]))
    if "Disk Stats" in system_stats:
        layout["disk"].update(create_panel_for_category("Disk Stats", system_stats["Disk Stats"]))
    if "Network Stats" in system_stats:
        layout["network"].update(create_panel_for_category("Network Stats", system_stats["Network Stats"]))
    if "Sensor Stats" in system_stats:
        layout["sensors"].update(create_panel_for_category("Sensor Stats", system_stats["Sensor Stats"]))
    if "GPU Stats" in system_stats:
        gpu_data = {"GPU Details": system_stats["GPU Stats"]} if system_stats["GPU Stats"] else {"GPU Details": ["Not available or error"]}
        layout["gpu"].update(create_panel_for_category("GPU Stats", gpu_data))
    if "CPU Info" in system_stats:
        layout["cpu_info"].update(create_panel_for_category("CPU Info", system_stats["CPU Info"]))
    if "Other Stats" in system_stats:
        layout["misc"].update(create_panel_for_category("Other System Stats", system_stats["Other Stats"]))

    # Header and Footer using theme styles
    layout["header"].update(Panel(Text("System Monitor Dashboard", justify="center", style="title"), border_style="panel.border", expand=True))
    layout["footer"].update(Panel(Text("Insights and GPT query will appear here.", justify="center", style="info"), title="[panel.title]Status[/]",border_style="panel.border", expand=True))

    return layout


if __name__ == "__main__":
    # from rich.theme import Theme # Moved to global imports at the top

    parser = argparse.ArgumentParser(description="Advanced system statistics tool")
    parser.add_argument("--query", help="Ask a question about the gathered stats")
    parser.add_argument("--export", help="Write the stats to a JSON file")
    parser.add_argument("--scan", help="Subnet to scan for active hosts")
    args = parser.parse_args()

    # Define a custom theme
    custom_theme = Theme({
        "info": "dim cyan",
        "warning": "magenta",
        "danger": "bold red",
        "title": "bold white on blue", # For main title/header
        "panel.title": "bold white",   # For panel titles
        "panel.border": "dim blue",    # For panel borders
        "table.header": "bold cyan",
        "table.cell": "green",
        "table.footer": "dim cyan",
        "bar.complete": "green",      # Style for completed part of ProgressBar
        "bar.finished": "dim green",   # Style for ProgressBar when 100%
        "progress.background": "dim blue", # Style for the trough/background of ProgressBar
        "progress.description": "white",
        "progress.percentage": "blue",
        "markdown.code": "bold yellow",
        "markdown.strong": "bold",
        "markdown.em": "italic",
        "repr.number": "blue",
        "repr.str": "green",
        "repr.bool_true": "bold green",
        "repr.bool_false": "bold red",
        "repr.none": "dim white",
        "log.level.warning": "yellow",
        "log.level.error": "red",
        "log.message": "white",
        "rule.line": "dim blue",
        "text.highlight": "bold yellow on dark_magenta" # Example for highlighted text
    })

    console = Console(theme=custom_theme)

    with Progress(console=console) as progress: # Pass console to Progress as well
        system_stats = gather_system_stats(progress)

    if args.scan:
        scan_results = gather_network_scan(args.scan)
        # Ensure "Other Stats" exists and add "Network Scan" to it for display
        if "Other Stats" not in system_stats:
            system_stats["Other Stats"] = OrderedDict()
        elif not isinstance(system_stats["Other Stats"], OrderedDict) and system_stats["Other Stats"] is not None : # If it exists but is not a dict (e.g. error string)
             system_stats["Other Stats"] = OrderedDict([("previous_error", system_stats["Other Stats"])]) # Preserve previous error

        # If "Other Stats" was None or some non-dict error from gather_other_stats
        if system_stats.get("Other Stats") is None or not isinstance(system_stats.get("Other Stats"), OrderedDict):
            system_stats["Other Stats"] = OrderedDict()

        system_stats["Other Stats"]["Network Scan"] = scan_results


    insights = generate_insights(system_stats)

    # Create the main layout, passing the theme
    main_layout = create_system_layout(system_stats, custom_theme)

    # Update footer with insights if any, using theme styles
    insights_title = f"[{custom_theme.styles['panel.title']}]Insights[/]"
    insights_border_style = "warning" # Use warning color for insights border
    if insights:
        main_layout["footer"].update(Panel(Text("\n".join(insights), justify="center", style="warning"), title=insights_title, border_style=insights_border_style, expand=True))
    else:
        main_layout["footer"].update(Panel(Text("No critical insights to display.", justify="center", style="info"), title=insights_title, border_style="panel.border", expand=True))


    if args.export:
        with open(args.export, "w") as f:
            json.dump(system_stats, f, indent=2)
        console.print(f"Stats exported to {args.export}", style="info") # Use theme style


    # Use Live to display the layout and handle updates
    with Live(main_layout, console=console, screen=True, refresh_per_second=1, vertical_overflow="visible") as live:
        gpt_query_title = f"[{custom_theme.styles['panel.title']}]GPT Query[/]"
        gpt_response_title = f"[{custom_theme.styles['panel.title']}]GPT Response[/]"

        if args.query:
            time.sleep(0.5)

            gpt_panel_content = Panel("Querying GPT...", title=gpt_query_title, border_style="panel.border", expand=True)
            insights_panel_for_footer = Panel(
                Text("\n".join(insights) if insights else "No critical insights.", justify="center", style="warning" if insights else "info"),
                title=insights_title,
                border_style=insights_border_style if insights else "panel.border", expand=True
            )
            main_layout["footer"].split_row(
                Layout(insights_panel_for_footer, name="insights_footer", ratio=1),
                Layout(gpt_panel_content, name="gpt_footer", ratio=1)
            )
            live.update(main_layout)

            response = query_gpt(system_stats, args.query)

            gpt_response_panel = Panel(Markdown(response), title=gpt_response_title, border_style="info", expand=True) # Use info for successful response
            main_layout["gpt_footer"].update(gpt_response_panel)
            live.update(main_layout)

            try:
                while True: time.sleep(1)
            except KeyboardInterrupt:
                console.print("\nExiting...", style="info")

        else:
            try:
                is_footer_split = False # State variable for interactive mode footer
                while True:
                    # Panel for prompting user input (will be placed in gpt_footer or used to create it)
                    gpt_prompt_panel = Panel(Text("Enter your query below. Type 'exit' to quit.", justify="center", style="info"), title=gpt_query_title, border_style="panel.border", expand=True)

                    insights_panel_for_footer = Panel(
                        Text("\n".join(insights) if insights else "No critical insights.", justify="center", style="warning" if insights else "info"),
                        title=insights_title,
                        border_style=insights_border_style if insights else "panel.border", expand=True
                    )

                    footer_section_layout = main_layout["footer"]

                    if not is_footer_split:
                        footer_section_layout.split_row(
                            Layout(insights_panel_for_footer, name="insights_footer", ratio=1),
                            Layout(gpt_prompt_panel, name="gpt_footer", ratio=1) # gpt_footer gets the prompt panel
                        )
                        is_footer_split = True
                    else:
                        # Footer is already split, just update the gpt_footer part with the prompt panel
                        footer_section_layout["gpt_footer"].update(gpt_prompt_panel)

                    live.update(main_layout) # Show prompt area

                    live.stop()
                    user_query = console.input(Text("Ask me a question about your system (exit to quit): ", style="info"))
                    live.start()

                    if user_query.lower() == "exit":
                        break

                    gpt_panel_content_querying = Panel("Querying GPT...", title=gpt_query_title, border_style="panel.border", expand=True)
                    main_layout["gpt_footer"].update(gpt_panel_content_querying)
                    live.update(main_layout)

                    response = query_gpt(system_stats, user_query)
                    gpt_response_panel = Panel(Markdown(response), title=gpt_response_title, border_style="info", expand=True)
                    main_layout["gpt_footer"].update(gpt_response_panel)
                    live.update(main_layout)

            except KeyboardInterrupt:
                console.print("\nExiting...", style="info")
            finally:
                live.stop()
                console.print("Exited interactive mode.", style="info")
