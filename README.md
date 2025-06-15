# Understanding-Mac

This project provides an advanced system monitoring tool that gathers a wide range of statistics from your machine and optionally leverages OpenAI to answer questions about them.

## Features

- Collects detailed CPU, memory, disk, network, sensor and GPU information
- Optional scanning of a subnet for active hosts
- Generates quick insights highlighting high resource usage
- Interactive CLI for querying the stats with GPT
- Ability to export gathered data to JSON

## Usage

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the tool:
```bash
python system_stats.py --query "How healthy is my system?" --export stats.json --scan 192.168.1.0/24
```

This will display the statistics table, perform a network scan of the specified subnet, save stats to `stats.json` and ask GPT for an overall summary.

Make sure you have `OPENAI_API_KEY` and `OPENAI_API_ORG_ID` set in your environment or a `.env` file if you plan to use the GPT integration.
