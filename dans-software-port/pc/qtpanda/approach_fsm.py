"""approach_fsm — guarded auto-approach state machine (Phase 5 v2 logic).

Pure, Qt-free, hardware-free.  Fed the current stream during an approach, it
returns the next *action* the caller should take; the caller (later: stab_runner
v2 / the co-pilot) translates actions into single MTMV/ENGA/retract commands.
The safety envelope the LLM co-pilot (Phase 6) must stay inside.

Interlocks (from the contact-run analysis — the tunneling window is crossed in
<110 ms, so coarse stepping overshoots into contact):
  * **hard retract on rail** — any ADC-railed sample -> RETRACT, terminal.
  * **single-step near the window** — once |I-offset| >= near_sigmas*sigma,
    only one step at a time (never a coarse burst).
  * **engage in-window** — at >= engage_sigmas*sigma, hand off to feedback.

Actions: 'step_in' | 'step_in_single' | 'engage' | 'hold' | 'retract'.
"""


class ApproachFSM:
    APPROACH = "approach"      # far out: coarse stepping allowed
    NEAR = "near"             # close: single steps only
    ENGAGED = "engaged"        # in tunnelling: feedback holds
    RETRACTED = "retracted"    # terminal: hit the rail

    def __init__(self, floor_offset_A, floor_sigma_A,
                 engage_sigmas=3.0, near_sigmas=2.0, rail_adc=32767):
        if floor_sigma_A <= 0:
            raise ValueError("floor_sigma_A must be > 0 (run a baseline first)")
        self.offset = floor_offset_A
        self.sigma = floor_sigma_A
        self.engage_sigmas = engage_sigmas
        self.near_sigmas = near_sigmas
        self.rail = rail_adc
        self.state = self.APPROACH

    def update(self, current_A, adc):
        """Advance on one sample; return the action to take."""
        # Terminal / feedback states first.
        if adc >= self.rail:
            self.state = self.RETRACTED
            return "retract"
        if self.state == self.RETRACTED:
            return "retract"
        if self.state == self.ENGAGED:
            return "hold"

        dev = abs(current_A - self.offset)
        if dev >= self.engage_sigmas * self.sigma:
            self.state = self.ENGAGED
            return "engage"
        if dev >= self.near_sigmas * self.sigma:
            self.state = self.NEAR
            return "step_in_single"      # interlock: one step at a time
        self.state = self.APPROACH
        return "step_in"
