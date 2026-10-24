import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "contour_stack.py"), encoding="utf-8").read().split("# figure: contours, stack height map")[0]
src = src.replace('fig.savefig(os.path.join(OUT, "figC0_fullframes.png"), dpi=80)', 'pass')
g = {"__file__": os.path.join(HERE, "contour_stack.py")}; exec(compile(src, "cs", "exec"), g)
np = g["np"]; ndi = g["ndi"]; PX = g["PX"]
H = g["summary"]["dark"]["height"]; n = len(g["summary"]["dark"]["order"])
yy, xx = np.mgrid[0:H.shape[0], 0:H.shape[1]]
for lev in (2, 4, 6, 8):
    m = H >= lev
    if m.sum() < 5: continue
    lab, k = ndi.label(m); big = lab == (np.bincount(lab.ravel())[1:].argmax() + 1)
    pts = np.c_[yy[big], xx[big]].astype(float); c = pts.mean(0); cov = np.cov((pts - c).T)
    ev, evec = np.linalg.eigh(cov); L = 4 * np.sqrt(ev[::-1]) * PX
    ang = np.degrees(np.arctan2(-evec[0, 1], evec[1, 1]))
    print(f"level >= {lev}/{n}: {big.sum()*PX**2:5.1f} nm2, length {L[0]:.1f} nm x width {L[1]:.1f} nm, "
          f"long axis {ang:+.0f} deg from horizontal, centre (row {c[0]+g['R0']:.0f}, col {c[1]+g['C0_']:.0f}) in #20 coords, pieces {k}")
cy, cx = g["CIRC"][0] - g["R0"], g["CIRC"][1] - g["C0_"]
r = np.hypot((yy - cy) / g["CIRC"][2], (xx - cx) / g["CIRC"][3])
print(f"stack height: circle centre (r<0.35) {H[r < 0.35].mean():.2f}, ring 0.6-1.0 {H[(r > 0.6) & (r < 1.0)].mean():.2f}, outside 1.3-1.8 {H[(r > 1.3) & (r < 1.8)].mean():.2f}")
roi_area = H.size * PX ** 2
areas = g["summary"]["dark"]["areas_nm2"]
print("chance nesting (larger outline's share of the region):", [round(a / roi_area, 2) for a in areas[1:]])
