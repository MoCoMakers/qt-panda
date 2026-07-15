"""tab_help — plain-language help text for the analysis tabs.

Keyed by the tab's title.  Each entry: what it is, how to use it for value,
and a key-terms glossary (anything a high-schooler might not know).  Kept
Qt-free so it is trivially editable and testable.
"""

HELP = {
    "dI/dV Curve": {
        "what":
            "This measures how much current flows between the tip and the "
            "sample as you change the voltage between them (the 'bias'). "
            "It parks the tip at one spot, sweeps the bias across a range, "
            "and records the current at each step. The blue curve is "
            "current-vs-voltage (I–V); the green curve is its slope "
            "(dI/dV), which is the real prize: it maps the sample's "
            "electronic states.",
        "how":
            "Get a STABLE tunnelling junction first (current in the pico- "
            "to nano-amp range, NOT slammed against the rail). Then set a "
            "narrow bias window around zero — e.g. -0.5 V to +0.5 V — with "
            "a small step like 0.01 V, and press Plot IV. A good curve "
            "bends smoothly; a clipped square-wave means you are in hard "
            "contact and need to retract. Peaks in the green dI/dV curve "
            "reveal energy levels / band edges in the material.",
        "terms": {
            "Bias": "The voltage applied between tip and sample; it drives "
                    "the tunnelling current.",
            "Tunnelling": "A quantum effect where electrons cross the tiny "
                          "vacuum gap between tip and sample without "
                          "touching.",
            "dI/dV": "The slope of the current-voltage curve; proportional "
                     "to the sample's density of electronic states.",
            "Density of states": "How many electron 'slots' exist at each "
                                  "energy — peaks mean lots of available "
                                  "states.",
            "Rail / saturation": "When the current is so large the "
                                  "electronics max out and read a flat "
                                  "ceiling instead of the true value.",
        },
    },
    "dI/dZ Curve": {
        "what":
            "This measures how the current changes as the tip moves "
            "toward or away from the surface (the Z direction). Because "
            "tunnelling current drops off exponentially with distance, "
            "this curve is an extremely sensitive 'am I really tunnelling?' "
            "check and a way to measure the gap's decay constant.",
        "how":
            "With a junction established, sweep Z over a small range and "
            "read the curve. A healthy tunnelling gap gives a steep, smooth "
            "exponential rise as the tip approaches. A flat or jumpy curve "
            "means contact, a broken junction, or noise. The steepness "
            "tells you the barrier height (roughly the work function).",
        "terms": {
            "Z": "The tip-height axis (toward/away from the sample); the "
                 "crash axis, so treat it carefully.",
            "Exponential decay": "The current falls by a fixed FACTOR for "
                                 "each equal step of distance — so tiny "
                                 "height changes cause huge current "
                                 "changes.",
            "Work function": "The energy needed to pull an electron out of "
                             "the surface; sets how fast current decays "
                             "with gap.",
            "Decay constant": "A number describing how quickly current "
                              "shrinks with distance.",
        },
    },
    "grid spectroscopy": {
        "what":
            "This runs a full dI/dV spectrum at EVERY pixel of a grid over "
            "the surface — a 3-D data cube (x, y, and bias). Instead of one "
            "spectrum at one spot, you get a map of the electronic "
            "structure across an area.",
        "how":
            "Pick an area (x/y range and resolution) and a bias range with "
            "a number of points. Keep the grid small at first (say 16x16) — "
            "it takes one spectrum per point, so it is slow. The result "
            "lets you slice the cube at any bias voltage and see how "
            "features light up at different energies.",
        "terms": {
            "Spectroscopy": "Measuring a signal as a function of energy "
                            "(here, bias voltage).",
            "Data cube": "A 3-D dataset: a full spectrum stored at each x,y "
                         "location.",
            "Slice": "A single 2-D image pulled from the cube at one chosen "
                     "bias voltage.",
            "Resolution": "How many pixels across — more pixels = finer "
                          "detail but much longer scans.",
        },
    },
    "Noise Scan": {
        "what":
            "This scans the area while recording the NOISE (variation) of "
            "the signal rather than its average. It is a diagnostic: it "
            "shows where the junction is unstable, where vibration or "
            "electrical pickup is worst, and whether the whole setup is "
            "quiet enough to image.",
        "how":
            "Run it before serious imaging. Uniform low noise = good, "
            "stable conditions. Bright noisy patches or streaks point to "
            "mechanical vibration, a bad ground, or an unstable tip. Use it "
            "to decide if you need better isolation, a fresh tip, or to "
            "check the grounding before spending time on a real scan.",
        "terms": {
            "Noise": "Unwanted random variation in a signal; here, how much "
                     "the current jitters.",
            "Ground / grounding": "A shared electrical reference; a missing "
                                  "ground turns the rig into an antenna and "
                                  "adds huge noise.",
            "Vibration isolation": "Cushioning that keeps floor/building "
                                   "motion from shaking the tip-sample gap.",
        },
    },
    "Calibration": {
        "what":
            "This is where the software's physical units are defined — how "
            "many DAC counts equal a volt, how many nanometres the piezo "
            "moves per volt, and the preamp's current scaling. Get these "
            "right and every 'nm' and 'nA' the app reports is trustworthy.",
        "how":
            "Enter the constants from your hardware (piezo datasheet, "
            "preamp resistor, DAC range). The example readout shows what a "
            "30 nm scan or a 1 nA setpoint converts to, so you can sanity- "
            "check. Approximate values are fine early on — the physical "
            "unit labels are still far more useful than raw counts, and you "
            "can refine calibration over time.",
        "terms": {
            "DAC": "Digital-to-Analog Converter — turns a number into a "
                   "voltage that drives the piezo or bias.",
            "LSB / count": "The smallest step of the DAC; one unit of its "
                           "number.",
            "Piezo": "A crystal that changes size slightly when voltage is "
                     "applied — it moves the tip in x, y, and z.",
            "Preamp": "The amplifier that turns the tiny tunnelling current "
                      "into a measurable voltage.",
            "Setpoint": "The target current the feedback loop tries to "
                        "hold.",
        },
    },
    "Stability": {
        "what":
            "This records the tunnelling current over time and builds a "
            "histogram (a bar chart of how often each current value "
            "occurs). It tells you how steady the junction is: a tight, "
            "tall peak means a rock-solid gap; a wide or wandering "
            "distribution means drift or noise.",
        "how":
            "Press Start with a junction established, let it collect for a "
            "while, then Stop. Read the width of the peak (jitter) and the "
            "drift number. Use it to judge whether the setup is stable "
            "enough to scan, to compare configurations (cage on/off, "
            "different gains), and to catch problems before imaging.",
        "terms": {
            "Histogram": "A bar chart showing how frequently each value "
                         "occurs.",
            "Drift": "Slow, steady wandering of the signal over time — "
                     "usually thermal expansion of the hardware.",
            "Jitter": "Fast random wobble around the average.",
            "Standard deviation": "A single number for how spread-out the "
                                  "values are; smaller = steadier.",
        },
    },
    "Fourier Analysis": {
        "what":
            "This takes the recorded current-over-time and breaks it into "
            "its component frequencies (a Fourier transform / power "
            "spectrum). Every vibration or electrical interference has a "
            "signature frequency, so this chart tells you EXACTLY what is "
            "disturbing the measurement.",
        "how":
            "Record a Stability session, then view this tab. Look for "
            "peaks: 50/60 Hz and its multiples = mains electrical pickup; "
            "a few-Hz bump = building/floor vibration. The Allan-deviation "
            "plot tells you the best averaging time. Use it to target "
            "fixes — grounding for mains peaks, isolation for low-frequency "
            "vibration.",
        "terms": {
            "Frequency": "How many times per second something repeats, in "
                         "hertz (Hz).",
            "Fourier transform": "Math that rewrites a wiggly signal as a "
                                 "sum of pure tones (frequencies).",
            "Power spectrum": "A chart of how much signal energy sits at "
                              "each frequency.",
            "Mains hum": "Electrical pickup at 50 or 60 Hz from wall power.",
            "Allan deviation": "A measure of stability versus averaging "
                               "time; shows the sweet spot for averaging.",
        },
    },
}

# Tabs that do NOT get an Info button.
NO_INFO = {"Main", "Continuous Scan"}
