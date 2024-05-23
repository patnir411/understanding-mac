from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich.text import Text
from rich.box import ROUNDED
import psutil
import os
import time
from openai import OpenAI
from utils import format_bytes, format_time, highlight_critical_values, format_disk_partitions, format_memory_details, format_swap_memory_details, format_disk_details, format_network_connections
from dotenv import load_dotenv
import logging

# Securely load environment variables
load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    organization=os.environ.get("OPENAI_API_ORG_ID"),
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def gather_cpu_stats():
    return {
        'CPU Usage (per CPU)': psutil.cpu_percent(interval=1, percpu=True),
        'CPU Times': psutil.cpu_times()._asdict(),
        'CPU Frequency': psutil.cpu_freq()._asdict(),
        'CPU Threads': psutil.cpu_count(logical=True),
        'CPU Load Average': psutil.getloadavg(),
    }


def gather_memory_stats():
    return {
        'Memory Usage': psutil.virtual_memory().percent,
        'Memory Details': psutil.virtual_memory()._asdict(),
        'Swap Memory Usage': psutil.swap_memory().percent,
        'Swap Memory Details': psutil.swap_memory()._asdict(),
    }


def gather_disk_stats():
    return {
        'Disk Usage': psutil.disk_usage('/').percent,
        'Disk Details': psutil.disk_usage('/')._asdict(),
        'Disk IO': psutil.disk_io_counters()._asdict(),
        'Disk Partitions': [partition._asdict() for partition in psutil.disk_partitions()],
    }


def gather_network_stats():
    return {
        'Network Stats': {iface: stats._asdict() for iface, stats in psutil.net_io_counters(pernic=True).items()},
        'Network Interfaces': {iface: addrs for iface, addrs in psutil.net_if_addrs().items()},
        'Network Connections': [conn._asdict() for conn in psutil.net_connections(kind='inet')]
    }


def gather_other_stats():
    return {
        'Processes': len(psutil.pids()),
        'Process Details': [proc.info for proc in psutil.process_iter(['pid', 'name', 'username', 'status'])],
        'Battery': psutil.sensors_battery()._asdict() if psutil.sensors_battery() else 'No battery information available',
        'Boot Time': psutil.boot_time(),
        'Users': [user._asdict() for user in psutil.users()],
    }


def gather_system_stats(progress):
    tasks = {
        'CPU Stats': progress.add_task("Gathering CPU stats...", total=5),
        'Memory Stats': progress.add_task("Gathering Memory stats...", total=3),
        'Disk Stats': progress.add_task("Gathering Disk stats...", total=4),
        'Network Stats': progress.add_task("Gathering Network stats...", total=2),
        'Other Stats': progress.add_task("Gathering Other stats...", total=4)
    }

    try:
        progress.update(tasks['CPU Stats'], advance=1)
        cpu_stats = gather_cpu_stats()
        progress.update(tasks['CPU Stats'], advance=4)

        progress.update(tasks['Memory Stats'], advance=1)
        memory_stats = gather_memory_stats()
        progress.update(tasks['Memory Stats'], advance=2)

        progress.update(tasks['Disk Stats'], advance=1)
        disk_stats = gather_disk_stats()
        progress.update(tasks['Disk Stats'], advance=3)

        progress.update(tasks['Network Stats'], advance=1)
        network_stats = gather_network_stats()
        progress.update(tasks['Network Stats'], advance=1)

        progress.update(tasks['Other Stats'], advance=1)
        other_stats = gather_other_stats()
        progress.update(tasks['Other Stats'], advance=3)

        system_stats = {**cpu_stats, **memory_stats, **disk_stats, **network_stats, **other_stats}
    except Exception as e:
        logging.error(f"Error gathering system stats: {e}")
        system_stats = {"error": f"Error gathering system stats: {e}"}

    return system_stats


def query_gpt(system_stats, user_query="Tell me about my computer."):
    with Progress() as progress:
        gpt_task = progress.add_task("[cyan]Querying GPT...", total=5)

        # Step 1: Prepare the query (simulated progress)
        progress.update(gpt_task, advance=1)
        time.sleep(2)  # Simulate preparation time

        # Step 2: Sending the request (simulated progress)
        progress.update(gpt_task, advance=1)
        time.sleep(2)  # Simulate sending time

        # Step 3: Waiting for response (simulated progress)
        progress.update(gpt_task, advance=1)
        time.sleep(2)  # Simulate waiting time

        # Step 4: Receiving the response (simulated progress)
        progress.update(gpt_task, advance=1)
        time.sleep(5)  # Simulate receiving time

        # Step 5: Processing the response (actual query)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert systems monitor. Given the following system statistics, provide a detailed overview of every metric. Evaluate the system's performance and provide possible reasons for any anomalies."
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
        )
        progress.update(gpt_task, advance=1)  # Final update

    return response.choices[0].message.content.strip()


def create_stats_panels(system_stats):
    panels = []

    for category, stats in system_stats.items():
        if isinstance(stats, (list, tuple)):
            if category == "Process Details" or category == "Top Processes":
                summary = [f"{proc['name']} (PID: {proc['pid']})" for proc in stats[:10]]
                stats = ', '.join(summary) + (", ..." if len(stats) > 10 else "")
            elif category == "Disk Partitions":
                stats = format_disk_partitions(stats)
            elif category == "Network Connections":
                stats = format_network_connections(stats)
            else:
                stats = ', '.join(map(str, stats))
        elif isinstance(stats, dict):
            if category == "CPU Times":
                stats = ', '.join(f"{k}: {v:.2f}" for k, v in stats.items())
            elif category == "Memory Details":
                stats = format_memory_details(stats)
            elif category == "Swap Memory Details":
                stats = format_swap_memory_details(stats)
            elif category == "Disk Details":
                stats = format_disk_details(stats)
            elif category == "Disk IO":
                stats = ', '.join(f"{k}: {format_bytes(v) if 'bytes' in k else v}" for k, v in stats.items())
            elif category == "Network Stats":
                formatted_stats = []
                for iface, details in stats.items():
                    formatted_stats.append(f"{iface}: bytes_sent: {format_bytes(details['bytes_sent'])}, bytes_recv: {format_bytes(details['bytes_recv'])}")
                stats = '\n'.join(formatted_stats)
            elif category == "Battery":
                stats = ', '.join(f"{k}: {v}" for k, v in stats.items())
            else:
                stats = ', '.join(f"{k}: {v}" for k, v in stats.items())
        elif category == "Boot Time":
            stats = format_time(stats)
        else:
            stats = highlight_critical_values(category, stats)
        
        panels.append(Panel(Text(str(stats)), title=category, border_style="bold magenta"))

    return Group(*panels)


if __name__ == "__main__":
    console = Console()

    with Progress() as progress:
        system_stats = gather_system_stats(progress)

    system_stats_panels = create_stats_panels(system_stats)
    console.print(system_stats_panels)

    while True:
        user_query = input("Ask me a question about your system (exit to quit): ")
        if user_query.lower() == "exit":
            break
        response = query_gpt(system_stats, user_query)
        console.print("[bold cyan]GPT Response:[/bold cyan]", response)
