"""Check the error-channel truth: image, #1808 alone beside it, and terrace levels (step heights)."""
import os, sys
import numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import truths as T
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import sweep_player as sp

t, info = T.sep24_error()
h = t.h
print("error-channel truth:", h.shape, f"{t.px:.4f} nm/px", f"rms {h.std():.2f} A", f"p1-p99 span {np.ptp(np.percentile(h, [1, 99])):.2f} A")
hs = ndi.gaussian_filter(h, 2)
cnts, edges = np.histogram(hs, bins=120); cen = (edges[:-1] + edges[1:]) / 2
pk = [i for i in range(2, len(cnts) - 2) if cnts[i] == max(cnts[i - 2:i + 3]) and cnts[i] > cnts.max() * 0.15]
print("terrace levels (A):", np.round(cen[pk], 2), " spacings:", np.round(np.diff(cen[pk]), 2))
D = sp.DayData("2026-Sep-24")
one = -T._rowlev(T._fill(D.image(1808, "e_trace")[0]))
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
ax[0].imshow(one, cmap="inferno", vmin=np.percentile(one, 1), vmax=np.percentile(one, 99)); ax[0].set_title("#1808 alone, -error (peaks bright)")
ax[1].imshow(h, cmap="inferno", vmin=np.percentile(h, 1), vmax=np.percentile(h, 99)); ax[1].set_title(f"truth: #1804-#1812 aligned to #1808 (A), rms {h.std():.2f}")
ax[2].plot(cen, cnts); [ax[2].axvline(cen[i], color="r", ls=":") for i in pk]; ax[2].set_title("height histogram: terrace levels (A)")
for a in ax[:2]: a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); fig.savefig(os.path.join(HERE, "truth_error_check.png"), dpi=65)
