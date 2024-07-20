import humanize
from datetime import datetime


# Utility functions for formatting
def format_value(value):
    if isinstance(value, float):
        return f"{value:.2f}"
    elif isinstance(value, int):
        return format_bytes(value) if value > 1024 else str(value)
    elif isinstance(value, list) and len(value) > 5:
        return ", ".join(map(str, value[:5])) + f" ... ({len(value)} items)"
    else:
        return str(value)

def format_bytes(bytes_value):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.2f} PB"

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

def format_disk_details(disk_details):
    formatted_details = [
        f"Total: {humanize.naturalsize(disk_details['total'], binary=True)}",
        f"Used: {humanize.naturalsize(disk_details['used'], binary=True)}",
        f"Free: {humanize.naturalsize(disk_details['free'], binary=True)}",
        f"Percent: {disk_details['percent']}%"
    ]
    return "\n".join(formatted_details)

def format_network_connections(connections):
    formatted_connections = []
    for conn in connections[:10]:
        details = [
            f"FD: {conn['fd']}",
            f"Family: {conn['family'].name}",
            f"Type: {conn['type'].name}",
            f"Laddr: {conn['laddr']}",
            f"Raddr: {conn['raddr']}",
            f"Status: {conn['status']}",
            f"PID: {conn['pid']}"
        ]
        formatted_connections.append(", ".join(details))
    return "\n".join(formatted_connections)