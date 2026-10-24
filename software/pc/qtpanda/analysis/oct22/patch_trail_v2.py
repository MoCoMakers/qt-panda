import os
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(HERE, "live_trail_frame.py"), encoding="utf-8").read()
for a, b in (('RAW = {i: g["IMG"][i][0] for i in SEGS}', 'RAW = {i: -g["IMG"][i][0] for i in SEGS}                    # V2: peaks bright (-error)'),
             ("error channel, 30 nm", "−error (peaks bright), 30 nm"),
             ('"live_trail2.gif"', '"live_trail_v2.gif"'),
             ('"live_trail2_check.png"', '"live_trail_v2_check.png"')):
    assert s.count(a) == 1, a
    s = s.replace(a, b)
open(os.path.join(HERE, "live_trail_frame_v2.py"), "w", encoding="utf-8").write(s)
