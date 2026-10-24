"""Guarded diagnostic scan: KIGA 1.1444, CC engaged, one Y-cycle, then halt."""
import sys, time
import ki_ladder as k

try:
    s = k.status()
    if not s["is_const_current"]:
        raise SystemExit("CC not engaged; refusing")
    k.req("/scan/settings", {**k.SET, "ki": 1.1444})
    k.note("diagnostic scan (post-contact tip check), KIGA 1.1444, 30 nm, 1 Y-cycle, CC on")
    r = k.req("/scan/run", {})
    k.log(f"RUN ok={r.get('ok')} frames={r.get('frames')}")
    k.watch(512 / 10.28 + 3, False)   # scanning guards: sat / Z / lost / CC drop
    k.req("/scan/halt", {})
    k.note("diagnostic scan done, halted (CC stays engaged)")
    k.log("DIAG DONE")
except k.Abort as e:
    k.log(f"DIAG ABORTED: {e}")
    sys.exit(2)
