import psutil
import os
from openai import OpenAI
from rich.console import Console
from rich.table import Table
from rich import box
from datetime import datetime
import humanize
from dotenv import load_dotenv


# Securely load environment variables
load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    organization=os.environ.get("OPENAI_API_ORG_ID"),
)

def gather_system_stats():
    try:
        system_stats = {
            'CPU Usage (per CPU)': psutil.cpu_percent(interval=1, percpu=True),
            'CPU Times': psutil.cpu_times()._asdict(),
            'CPU Frequency': psutil.cpu_freq()._asdict(),
            'CPU Threads': psutil.cpu_count(logical=True),
            'CPU Load Average': psutil.getloadavg(),
            'Processes': len(psutil.pids()),
            'Process Details': [proc.info for proc in psutil.process_iter(['pid', 'name', 'username', 'status'])],
            'Top Processes': gather_top_process_stats(),
            'Memory Usage': psutil.virtual_memory().percent,
            'Memory Details': psutil.virtual_memory()._asdict(),
            'Swap Memory Usage': psutil.swap_memory().percent,
            'Disk Usage': psutil.disk_usage('/').percent,
            'Disk Details': psutil.disk_usage('/')._asdict(),
            'Disk IO': psutil.disk_io_counters()._asdict(),
            'Disk Partitions': [partition._asdict() for partition in psutil.disk_partitions()],
            'Network Stats': {iface: stats._asdict() for iface, stats in psutil.net_io_counters(pernic=True).items()},
            'Network Interfaces': {iface: addrs for iface, addrs in psutil.net_if_addrs().items()},
            'Battery': psutil.sensors_battery()._asdict() if psutil.sensors_battery() else 'No battery information available',
            'Boot Time': psutil.boot_time(),
            'Users': [user._asdict() for user in psutil.users()],
        }
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
    return response.choices[0].message.content.strip()

def create_stats_table(system_stats):
    table = Table(title="System Insights", box=box.ROUNDED)

    table.add_column("Category", style="bold", justify="left")
    table.add_column("Stats", justify="left")

    # Utility functions for formatting
    def format_bytes(bytes):
        return humanize.naturalsize(bytes, binary=True)

    def format_time(timestamp):
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    for category, stats in system_stats.items():
        if isinstance(stats, (list, tuple)):
            if category == "Process Details" or category == "Top Processes":
                # Show a summary of the processes
                summary = [f"{proc['name']} (PID: {proc['pid']})" for proc in stats[:10]]
                stats = ', '.join(summary) + (", ..." if len(stats) > 10 else "")
            else:
                stats = ', '.join(map(str, stats))
        elif isinstance(stats, dict):
            if category == "CPU Times":
                stats = ', '.join(f"{k}: {v:.2f}" for k, v in stats.items())
            elif category == "Memory Details" or category == "Disk Details":
                stats = ', '.join(f"{k}: {format_bytes(v) if 'bytes' in k else v}" for k, v in stats.items())
            elif category == "Disk IO":
                stats = ', '.join(f"{k}: {format_bytes(v) if 'bytes' in k else v}" for k, v in stats.items())
            elif category == "Network Stats":
                stats = ', '.join(f"{iface}: bytes_sent: {format_bytes(details['bytes_sent'])}, bytes_recv: {format_bytes(details['bytes_recv'])}" for iface, details in stats.items())
            elif category == "Battery":
                stats = ', '.join(f"{k}: {v}" for k, v in stats.items())
            else:
                stats = ', '.join(f"{k}: {v}" for k, v in stats.items())
        elif category == "Boot Time":
            stats = format_time(stats)
        else:
            stats = str(stats)
        table.add_row(category, stats)
    return table

if __name__ == "__main__":
    console = Console()
    system_stats = gather_system_stats()
    system_stats_table = create_stats_table(system_stats)
    console.print(system_stats_table)
    while True:
        user_query = input("Ask me a question about your system (exit to quit): ")
        if user_query.lower() == "exit":
            break
        response = query_gpt(system_stats, user_query)
        console.print("[bold cyan]GPT Response:[/bold cyan]", response)
