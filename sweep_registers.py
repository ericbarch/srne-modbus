#!/usr/bin/env python3
"""One-shot sweep: read every Modbus-backed topic once and report what it returns.

Ignores ENABLED_TOPICS and the persisted skip state so every register is tried.
Stop the srne-modbus service first — the serial port can only be opened once.

Usage:  ./venv/bin/python3 sweep_registers.py [--csv out.csv]
"""
import os
import sys
import time
import csv

os.environ["ENABLED_TOPICS"] = ""
os.environ["MODBUS_SKIP_STATE_FILE"] = "/dev/null"
os.environ["DEBUG"] = "false"
os.environ["MODBUS_SKIP_THRESHOLD"] = "999999"

from dotenv import load_dotenv  # noqa: E402
load_dotenv(override=False)

import modbus  # noqa: E402
from mqtt_topic_config import mqtt_config  # noqa: E402

PAUSE = 0.05  # seconds between reads, keeps the bus relaxed
csv_path = None
if "--csv" in sys.argv:
    csv_path = sys.argv[sys.argv.index("--csv") + 1]

rows = []
ok = fail = zero = 0
items = [(n, v) for n, v in mqtt_config.items() if "args" in v and "register" in v["args"]]
print(f"Sweeping {len(items)} registers...\n")
print(f"{'topic':45} {'reg':7} {'type':7} {'result':10} value")
for name, vals in items:
    args = dict(vals["args"])
    args["name"] = ""
    reg = args["register"]
    t0 = time.time()
    try:
        value = vals["value"](**args)
    except Exception as e:
        value = None
    ms = int((time.time() - t0) * 1000)
    if value is None:
        status = "FAIL"
        fail += 1
    elif str(value).strip("0.") in ("", "-") or str(value) in ("0", "0.0", "00:00", "Disabled"):
        status = "zero"
        zero += 1
    else:
        status = "ok"
        ok += 1
    ttype = vals.get("topic_type", "sensor")
    print(f"{name:45} 0x{reg:04X} {ttype:7} {status:4} {ms:4}ms  {value}")
    rows.append((name, f"0x{reg:04X}", ttype, status, ms, value))
    time.sleep(PAUSE)

print(f"\nok={ok}  zero/default={zero}  fail={fail}  total={len(items)}")
print("'zero' means the read succeeded but returned 0/Disabled — may be real or unsupported.")

if csv_path:
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["topic", "register", "type", "status", "ms", "value"])
        w.writerows(rows)
    print(f"Wrote {csv_path}")
