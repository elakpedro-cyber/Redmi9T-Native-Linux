"""Summarize frame-boundary counters; never equate commits with LCD scanout."""
from collections import defaultdict
import json
from pathlib import Path
import re
import sys


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    return values[round((len(values) - 1) * fraction)]


def summarize(log):
    scope = json.loads((log / "run.json").read_text())["scope"] if (log / "run.json").exists() else "offline ARM64/QEMU; software rendering explicitly enabled"
    clock_ticks = 100
    result = {"scope": scope,
              "frame_boundaries": [], "limitations": [
                  "PipeWire queue != encoded RDP frame; cursor-only updates are possible",
                  "Wayland commit != Weston presentation or LCD scanout",
                  "D-Bus dispatch RTT != input-to-photon latency",
                  "Sampled PSS can miss peaks; QEMU processes include emulator memory"]}
    for filename in ("gnome-frames.jsonl", "rdp-frames.jsonl"):
        groups = defaultdict(list)
        path = log / filename
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if event["event"] == "clock_ticks":
                clock_ticks = event["id"]
            if event["event"] != "clock_ticks":
                groups[(event["event"], event["pid"], event["id"])].append(event["ns"])
        for (kind, pid, object_id), timestamps in groups.items():
            timestamps.sort()
            intervals = [(b-a)/1e6 for a, b in zip(timestamps, timestamps[1:])]
            bins = defaultdict(int)
            for timestamp in timestamps:
                bins[timestamp // 1_000_000_000] += 1
            span = (timestamps[-1] - timestamps[0])/1e9
            result["frame_boundaries"].append({"file": filename, "event": kind,
                "pid_namespace": pid, "object_id": object_id, "count": len(timestamps),
                "span_seconds": round(span, 3),
                "observed_updates_per_second": round((len(timestamps)-1)/span, 3) if span else None,
                "max_updates_in_one_second_bin": max(bins.values()),
                "interval_ms_p50": percentile(intervals, .5),
                "interval_ms_p95": percentile(intervals, .95)})
    dispatch = []
    timeline = log / "timeline.jsonl"
    if not timeline.exists():
        timeline = log / "weston-timeline.jsonl"
    if timeline.exists():
        starts = {}
        durations = []
        posted = 0
        for line in timeline.read_text().splitlines():
            event = json.loads(line)
            if "T" not in event:
                continue
            timestamp = event["T"][0]*1000 + event["T"][1]/1e6
            output = event.get("wo")
            if event["N"] == "core_repaint_begin":
                starts[output] = timestamp
            elif event["N"] == "core_repaint_posted" and output in starts:
                durations.append(timestamp-starts.pop(output))
                posted += 1
        result["weston"] = {"repaints_posted": posted,
            "begin_to_posted_ms_p50": percentile(durations, .5),
            "begin_to_posted_ms_p95": percentile(durations, .95),
            "scope": "Software repaint submission; not encoded frame latency or photon timing"}
    input_log = log / "input.log"
    if input_log.exists():
        for line in input_log.read_text(errors="replace").splitlines():
            if line.startswith('{"event":"input_dispatch"') or line.startswith('{"event": "input_dispatch"'):
                event = json.loads(line)
                if event["method"].startswith("Notify"):
                    dispatch.append(event["elapsed_us"]/1000)
    result["input_dispatch"] = {"count": len(dispatch),
        "rtt_ms_p50": percentile(dispatch, .5), "rtt_ms_p95": percentile(dispatch, .95),
        "rtt_ms_max": max(dispatch) if dispatch else None}
    samples = (log / "samples.txt").read_text(errors="replace")
    peak_pss = 0
    previous = {}
    cpu = []
    for sample in samples.split("UPTIME ")[1:]:
        timestamp = float(sample.split()[0])
        peak_pss = max(peak_pss, sum(map(int, re.findall(r"^Pss:\s+(\d+)", sample, re.M))))
        for process in sample.split("PROCESS ")[1:]:
            lines = process.splitlines()
            if len(lines) < 3 or ")" not in lines[2]:
                continue
            pid = int(lines[0])
            fields = lines[2].rsplit(")", 1)[1].split()
            ticks = int(fields[11]) + int(fields[12])
            identity = (pid, int(fields[19]))
            if identity in previous:
                then, old = previous[identity]
                if timestamp > then:
                    cpu.append((ticks-old) / clock_ticks / (timestamp-then) * 100)
            previous[identity] = timestamp, ticks
    copy_log = log / "rdp-copies.jsonl"
    if copy_log.exists():
        copies = defaultdict(list)
        for line in copy_log.read_text().splitlines():
            event = json.loads(line)
            copies[event["event"]].append(event)
        result["rdp_operations"] = {kind: {
            "calls": len(events), "pixels_processed": sum(e["pixels"] for e in events),
            "duration_ms_sum": sum(e["duration_ns"] for e in events)/1e6,
            "duration_ms_p50": percentile([e["duration_ns"]/1e6 for e in events], .5),
            "duration_ms_p95": percentile([e["duration_ns"]/1e6 for e in events], .95),
            "failed_calls": sum(not e["ok"] for e in events),
            "meaning": "rectangle operations, not unique frames; interposed calls only"}
            for kind, events in copies.items()}
    result["resources"] = {"peak_sampled_aggregate_pss_kib": peak_pss,
        "max_single_process_cpu_percent_one_core": round(max(cpu), 2) if cpu else None,
        "cpu_clock_ticks_from_trace": clock_ticks}
    return result


if __name__ == "__main__":
    log = Path(sys.argv[1])
    result = summarize(log)
    (log / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
