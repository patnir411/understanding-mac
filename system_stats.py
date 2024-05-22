from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import Progress
from rich.text import Text
import psutil
import os
import time
from openai import OpenAI
from datetime import datetime
import humanize
from dotenv import load_dotenv

# Securely load environment variables
load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    organization=os.environ.get("OPENAI_API_ORG_ID"),
)

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
        cpu_stats = {
            'CPU Usage (per CPU)': psutil.cpu_percent(interval=1, percpu=True),
            'CPU Times': psutil.cpu_times()._asdict(),
            'CPU Frequency': psutil.cpu_freq()._asdict(),
            'CPU Threads': psutil.cpu_count(logical=True),
            'CPU Load Average': psutil.getloadavg(),
        }
        progress.update(tasks['CPU Stats'], advance=4)
        
        progress.update(tasks['Memory Stats'], advance=1)
        memory_stats = {
            'Memory Usage': psutil.virtual_memory().percent,
            'Memory Details': psutil.virtual_memory()._asdict(),
            'Swap Memory Usage': psutil.swap_memory().percent,
            'Swap Memory Details': psutil.swap_memory()._asdict(),
        }
        progress.update(tasks['Memory Stats'], advance=2)
        
        progress.update(tasks['Disk Stats'], advance=1)
        disk_stats = {
            'Disk Usage': psutil.disk_usage('/').percent,
            'Disk Details': psutil.disk_usage('/')._asdict(),
            'Disk IO': psutil.disk_io_counters()._asdict(),
            'Disk Partitions': [partition._asdict() for partition in psutil.disk_partitions()],
        }
        progress.update(tasks['Disk Stats'], advance=3)
        
        progress.update(tasks['Network Stats'], advance=1)
        network_stats = {
            'Network Stats': {iface: stats._asdict() for iface, stats in psutil.net_io_counters(pernic=True).items()},
            'Network Interfaces': {iface: addrs for iface, addrs in psutil.net_if_addrs().items()},
        }
        progress.update(tasks['Network Stats'], advance=1)
        
        progress.update(tasks['Other Stats'], advance=1)
        other_stats = {
            'Processes': len(psutil.pids()),
            'Process Details': [proc.info for proc in psutil.process_iter(['pid', 'name', 'username', 'status'])],
            'Top Processes': gather_top_process_stats(),
            'Battery': psutil.sensors_battery()._asdict() if psutil.sensors_battery() else 'No battery information available',
            'Boot Time': psutil.boot_time(),
            'Users': [user._asdict() for user in psutil.users()],
        }
        progress.update(tasks['Other Stats'], advance=3)
        
        system_stats = {**cpu_stats, **memory_stats, **disk_stats, **network_stats, **other_stats}
    except Exception as e:
        system_stats = {"error": f"Error gathering system stats: {e}"}
    
    return system_stats

def gather_top_process_stats():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'status']):
        try:
            p = psutil.Process(proc.info['pid'])
            proc.info.update({
                'cpu_percent': p.cpu_percent(),
                'memory_percent': p.memory_percent(),
                'memory_info': p.memory_info()._asdict(),
                'num_threads': p.num_threads(),
                'open_files': [f._asdict() for f in p.open_files()],
                'connections': [c._asdict() for c in p.connections()],
                'create_time': p.create_time(),
            })
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    top_processes = sorted(processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:15]
    return top_processes

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

def create_stats_table(system_stats):
    
    table = Table(title="[bold blue]System Insights[/bold blue]", box=box.ROUNDED, padding=(0,1), show_lines=True)

    table.add_column("Category", style="bold magenta", justify="left")
    table.add_column("Stats", justify="left")

    # Utility functions for formatting
    def format_bytes(bytes):
        return humanize.naturalsize(bytes, binary=True)

    def format_time(timestamp):
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    def highlight_critical_values(category, stats):
        if category == "CPU Usage (per CPU)":
            return ', '.join(f"[red]{value}%[/red]" if value > 80 else str(value) for value in stats)
        if category == "Memory Usage" and stats > 80:
            return f"[red]{stats}%[/red]"
        if category == "Swap Memory Usage" and stats > 80:
            return f"[red]{stats}%[/red]"
        if category == "Disk Usage" and stats > 80:
            return f"[red]{stats}%[/red]"
        return stats

    def format_disk_partitions(partitions):
        formatted_partitions = []
        for partition in partitions:
            details = [
                f"Device: {partition['device']}",
                f"Mountpoint: {partition['mountpoint']}",
                f"Filesystem Type: {partition['fstype']}",
                f"Options: {partition['opts']}",
                f"Max File: {partition['maxfile']}",
                f"Max Path: {partition['maxpath']}"
            ]
            formatted_partitions.append("\n".join(details))
        return "\n\n".join(formatted_partitions)

    def format_memory_details(memory):
        details = []
        for key, value in memory.items():
            if "percent" in key:
                formatted_value = f"{value:.2f}%"
                if value > 80:
                    formatted_value = f"[red]{formatted_value}[/red]"
                details.append(f"{key}: {formatted_value}")
            else:
                formatted_value = humanize.naturalsize(value, binary=True)
                details.append(f"{key}: {formatted_value}")
        return "\n".join(details)

    def format_swap_memory_details(swap):
        details = []
        for key, value in swap.items():
            if "percent" in key:
                formatted_value = f"{value:.2f}%"
                if value > 80:
                    formatted_value = f"[red]{formatted_value}[/red]"
                details.append(f"{key}: {formatted_value}")
            else:
                formatted_value = humanize.naturalsize(value, binary=True)
                details.append(f"{key}: {formatted_value}")
        return "\n".join(details)

    for category, stats in system_stats.items():
        if isinstance(stats, (list, tuple)):
            if category == "Process Details" or category == "Top Processes":
                # Show a summary of the processes
                summary = [f"{proc['name']} (PID: {proc['pid']})" for proc in stats[:10]]
                stats = ', '.join(summary) + (", ..." if len(stats) > 10 else "")
            elif category == "Disk Partitions":
                stats = format_disk_partitions(stats)
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
                stats = ', '.join(f"{k}: {format_bytes(v) if 'bytes' in k else v}" for k, v in stats.items())
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
        table.add_row(category, str(stats))
    return table

if __name__ == "__main__":
    console = Console()
    
    with Progress() as progress:
        system_stats = gather_system_stats(progress)
    
    system_stats_table = create_stats_table(system_stats)
    console.print(system_stats_table)
    
    while True:
        user_query = input("Ask me a question about your system (exit to quit): ")
        if user_query.lower() == "exit":
            break
        response = query_gpt(system_stats, user_query)
        console.print("[bold cyan]GPT Response:[/bold cyan]", response)
