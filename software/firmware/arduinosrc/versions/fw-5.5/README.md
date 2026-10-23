# FW 5.5 — reconstructed reference build (2026-07-31)

5.4 + SETD floor 5 us (200 kHz capable) + raw ring 4->16 blocks + GSPC abort-on-serial-byte. NOTE: the 5.5.1 exact-dx change is NOT included (that variant had the 2-tick/line X phase walk).

Compiled footprint: FLASH code:58804 / RAM1 311840 - byte-identical to the original build.

Built by layering the documented per-version deltas onto the git
429b9a1 base; see fw-5.3/README.md for the method and era notes.
