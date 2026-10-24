"""Watch the engaged junction settle. One line per 15 s window; exits READY
after 3 consecutive quiet windows, or NOT_SETTLED after max_windows."""
import json, sys, time, urllib.request
import numpy as np

max_windows = int(sys.argv[1]) if len(sys.argv) > 1 else 20
good = 0
for w in range(max_windows):
    time.sleep(15)
    try:
        s = json.load(urllib.request.urlopen("http://127.0.0.1:8765/samples?n=3000", timeout=10))["samples"]
    except Exception as e:
        print(f"w{w} bridge error {e}", flush=True); continue
    s = [x for x in s if x["is_const_current"]]
    if len(s) < 500:
        print(f"w{w} CC_OFF_OR_NO_DATA n={len(s)}", flush=True); sys.exit(3)
    a = np.array([x["adc"] for x in s], float); z = np.array([x["dac_z"] for x in s], float)
    lnstd = float(np.std(np.log(np.clip(a, 1, None))))
    lost = 100 * float((a <= 16).mean()); sat = 100 * float((a >= 32000).mean())
    zr = float(np.percentile(z, 95) - np.percentile(z, 5)); zm = float(z.mean())
    quiet = lnstd < 0.8 and lost < 2 and sat == 0 and zr < 800
    good = good + 1 if quiet else 0
    print(f"w{w} med={np.median(a):.0f} lnstd={lnstd:.2f} lost%={lost:.1f} sat%={sat:.1f} "
          f"z={zm:.0f} zrange90={zr:.0f} {'quiet' if quiet else 'noisy'} ({good}/3)", flush=True)
    if zm > 44000 or sat > 2:
        print("DANGER z high or saturating", flush=True); sys.exit(4)
    if good >= 3:
        print("READY", flush=True); sys.exit(0)
print("NOT_SETTLED", flush=True); sys.exit(1)
