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
# Removed highlight_critical_values as it's unused.
# The functionality of highlighting critical data is now partly visual (Bars)
# or handled by the 'Insights' panel.

# Removed format_disk_partitions as Disk Partitions are now displayed using a Rich Tree.
# Removed format_memory_details as Memory details are now displayed per metric in a table, with percentages as Bars.
# Removed format_swap_memory_details for the same reason as format_memory_details.
# Removed format_disk_details for the same reason as format_memory_details.
# Removed format_network_connections as Network Connections are now displayed in a Rich Table.