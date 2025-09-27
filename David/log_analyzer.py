#!/usr/bin/env python3
import re, sys, argparse
from collections import Counter, defaultdict
from datetime import datetime

APACHE_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d{3}) (?P<size>\S+)'
)

SIMPLE_RE = re.compile(
    r'(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z) (?P<level>[A-Z]+) (?P<ip>\d+\.\d+\.\d+\.\d+) - (?P<msg>.+)'
)

def parse_ts(s):
    # Apache: 25/Sep/2025:10:15:32 +0000
    try:
        return datetime.strptime(s, "%d/%b/%Y:%H:%M:%S %z")
    except Exception:
        pass
    # Simple ISO with Z suffix (UTC)
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return None

def analyze(path, topn=5):
    by_level = Counter()
    by_ip = Counter()
    by_msg = Counter()
    errors_by_hour = Counter()
    status_counts = Counter()
    total = 0
    slow_lines = []  # (duration_ms, line)

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            total += 1
            line = line.rstrip("\n")
            m = APACHE_RE.search(line)
            if m:
                ip = m.group("ip")
                ts = parse_ts(m.group("ts"))
                # normalize to naive UTC
                if ts and ts.tzinfo is not None:
                    ts = ts.astimezone(__import__('datetime').timezone.utc).replace(tzinfo=None)
                status = int(m.group("status"))
                level = "ERROR" if status >= 500 else ("WARN" if 400 <= status < 500 else "INFO")
                msg = f'HTTP {status} {m.group("method")} {m.group("path")}'
                by_level[level] += 1
                by_ip[ip] += 1
                by_msg[msg] += 1
                status_counts[status] += 1
                if level == "ERROR" and ts:
                    hour = ts.replace(minute=0, second=0, microsecond=0)
                    errors_by_hour[hour] += 1
                continue

            m = SIMPLE_RE.search(line)
            if m:
                ip = m.group("ip")
                ts = parse_ts(m.group("ts"))
                # normalize to naive UTC
                if ts and ts.tzinfo is not None:
                    ts = ts.astimezone(__import__('datetime').timezone.utc).replace(tzinfo=None)
                level = m.group("level")
                msg = m.group("msg")
                by_level[level] += 1
                by_ip[ip] += 1
                by_msg[msg] += 1
                # detect duration_ms=NNN
                dm = re.search(r'duration_ms=(\d+)', msg)
                if dm:
                    slow_lines.append( (int(dm.group(1)), line) )
                if level == "ERROR" and ts:
                    hour = ts.replace(minute=0, second=0, microsecond=0, tzinfo=None)
                    errors_by_hour[hour] += 1
                continue

            # Unknown format: count as OTHER
            by_level["OTHER"] += 1

    report = []
    report.append("=== SUMMARY ===")
    report.append(f"Total lines: {total}")
    report.append("By level: " + ", ".join(f"{k}={v}" for k,v in by_level.most_common()))
    if status_counts:
        report.append("HTTP statuses: " + ", ".join(f"{k}={v}" for k,v in status_counts.most_common()))
    report.append("\n=== Top IPs ===")
    for ip, c in by_ip.most_common(topn):
        report.append(f"{ip}: {c}")
    report.append("\n=== Top messages ===")
    for msg, c in by_msg.most_common(topn):
        report.append(f"{c} × {msg}")
    report.append("\n=== Errors per hour ===")
    for hour, c in sorted(errors_by_hour.items()):
        report.append(f"{hour}: {c}")
    if slow_lines:
        report.append("\n=== Slow lines (by duration_ms) ===")
        for dur, line in sorted(slow_lines, reverse=True)[:topn]:
            report.append(f"{dur} ms | {line}")
    return "\n".join(report)

def main():
    p = argparse.ArgumentParser(description="Simple log analyzer")
    p.add_argument("path", help="Path to log file (txt)")
    p.add_argument("--top", type=int, default=5, help="Top N entries to show (default: 5)")
    args = p.parse_args()
    out = analyze(args.path, topn=args.top)
    print(out)

if __name__ == "__main__":
    main()
