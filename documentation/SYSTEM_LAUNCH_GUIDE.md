# STM System Launch Guide

## Overview

This guide walks you through the initial setup and verification steps for the Panda STM system. Follow these steps in order to ensure proper hardware connection, communication, and basic functionality before proceeding with measurements.

## Quick Start Summary

Click on any step below to jump to the detailed instructions:

1. [**Step 1: Connect COM Port**](#step-1-connect-com-port) - Establish serial communication between PC and STM controller
2. [**Step 2: Reset and Verify Current Reading**](#step-2-reset-and-verify-current-reading) - Initialize controller and verify current measurements
3. [**Step 3: Set Bias Voltage and Verify with Multimeter**](#step-3-set-bias-voltage-and-verify-with-multimeter) - Set and verify bias voltage output
4. [**Step 4: Run Approach Sequence**](#step-4-run-approach-sequence) - Bring tip close to sample using automated approach
5. [**Step 5: Fine-Tune Position and Test Scans**](#step-5-fine-tune-position-and-test-scans) - Optimize tip position and verify scanning functionality
6. [**Reset Procedure**](#reset-procedure) - How to safely reset the system and recover from issues
7. [**Probe Retraction Techniques**](#probe-retraction-techniques) - Methods for retracting the probe tip (manual rotation or command-based)

## Prerequisites

- STM controller hardware powered on and connected
- USB-to-serial adapter connected (if required)
- PC GUI application (`stm_app.py`) ready to run
- Multimeter or voltmeter for voltage verification (optional but recommended)

## Step-by-Step Setup

### Step 1: Connect COM Port

**Objective:** Establish serial communication between the PC and STM controller.

**Procedure:**
1. Power on the STM controller hardware
2. Connect the controller to your PC via USB (or USB-to-serial adapter)
3. Identify the COM port:
   - **Windows**: Open Device Manager → Ports (COM & LPT) → Note the COM port number (e.g., COM7, COM3)
   - **Linux/Mac**: Check `/dev/tty*` devices or use `dmesg` to identify the port
4. Launch the Panda STM GUI application (`stm_app.py`)
5. In the GUI, locate the **Open** button in the Connection Control section
6. Enter the COM port number in the text field (e.g., "COM7")
7. Click **Open** to establish the connection

**Verification:**
- The status display should update from "No Updates" to show current STM status
- If connection fails, check:
  - Controller is powered on
  - Correct COM port number
  - No other program is using the COM port
  - USB drivers are installed correctly

**Troubleshooting:**
- If the port doesn't appear, check USB connections and drivers
- If connection times out, verify baud rate settings (should be 115200)
- Try closing and reopening the connection if status doesn't update

---

### Step 2: Reset and Verify Current Reading

**Objective:** Reset the STM controller to a known state and verify that current measurements are functioning correctly.

**Procedure:**
1. With the COM port connected, locate the **Reset** button in the Connection Control section
2. Click **Reset** to initialize the STM controller to a default state
3. Wait a few seconds for the reset to complete
4. Observe the **Real-Time Current Plot** (top left plot in the GUI)
5. Check the current values displayed

**Expected Results:**
- Current values should be in the range of approximately **±1×10⁻¹¹ to ±1×10⁻¹² amperes** (±10-100 picoamperes)
- The current reading may fluctuate slightly due to noise
- Values should be close to zero when the tip is far from the sample (no tunneling)

**What to look for:**
- **Good sign**: Current values around ±10⁻¹¹ to ±10⁻¹² A (±10-100 pA) indicate the preamp and ADC are working correctly
- **Bad signs**: 
  - Zero current (0 A) - might indicate connection issues or preamp problems
  - Very large values (>10⁻⁹ A) - might indicate short circuit or measurement error
  - Noisy/unstable readings - might indicate grounding issues or electrical interference

**Verification:**
- The current plot should show a relatively flat line near zero with small fluctuations
- Status display should show ADC values corresponding to these small currents
- If values are outside the expected range, check:
  - Preamp connections
  - Grounding
  - Tip-sample distance (should be far apart initially)

**Important Note:** After resetting, all DAC values (including bias voltage) are cleared. You must **re-click the Bias button** (and any other DAC controls) to restore your desired settings. The reset command initializes the controller to default values, so any previously set voltages will be lost.

**Note:** The current conversion formula is: `current = ADC / 32768 * 10.24 / 100e6` amperes. For very small currents (picoamperes), you're looking at ADC values in the range of approximately 30-300 counts.

---

### Step 3: Set Bias Voltage and Verify with Multimeter

**Important:** If you performed Step 2 (Reset), you must set the bias voltage in this step. After a reset, all DAC values are cleared and need to be set again.

**Objective:** Set a known bias voltage and verify it using a multimeter on exposed test points, confirming the DAC-to-voltage conversion is working correctly.

**Procedure:**
1. Locate the **Bias Control** in the DAC Control section
2. Enter a DAC value in the Bias entry field (DAC range: 0 to 65535, out of 2^16 = 65536 total values)
3. Click the **Bias** button to set the voltage
   - **Note:** If you just performed a reset (Step 2), you must click the Bias button now to restore the bias voltage setting, as reset clears all DAC values
4. Verify the display label shows the converted voltage

**Bias Voltage Testing Progression:**
- **Initial test value**: DAC = **60000** → approximately **-2.493 V**
- **Stepped down to**: DAC = **50000** → approximately **-1.580 V**
- **Further reduced to**: DAC = **45000** → approximately **-1.121 V**
- **Status**: Still testing optimal values - these may be adjusted based on sample characteristics and measurement requirements

**Voltage Calculation:**
The bias voltage conversion formula is:
```
bias_volts = -1.0 * (dac - 32768) / 32768 * 3.0
```

**Tested Values:**

For DAC = 60000 (initial test):
- `bias_volts = -1.0 * (60000 - 32768) / 32768 * 3.0`
- `bias_volts = -1.0 * 27232 / 32768 * 3.0`
- `bias_volts ≈ -2.493 V`

For DAC = 50000 (stepped down):
- `bias_volts = -1.0 * (50000 - 32768) / 32768 * 3.0`
- `bias_volts = -1.0 * 17232 / 32768 * 3.0`
- `bias_volts ≈ -1.580 V`

For DAC = 45000 (further reduced):
- `bias_volts = -1.0 * (45000 - 32768) / 32768 * 3.0`
- `bias_volts = -1.0 * 12232 / 32768 * 3.0`
- `bias_volts ≈ -1.121 V`

**Hardware Verification:**
1. Locate the exposed bias voltage test points on the STM controller board
2. Set your multimeter to DC voltage mode
3. Connect the multimeter probes to the bias voltage test points:
   - **Red probe**: Positive bias output (or tip bias)
   - **Black probe**: Ground/common
4. Read the voltage displayed on the multimeter

**Expected Results:**
- Multimeter should read the voltage corresponding to your selected DAC value
  - DAC = 60000 → approximately **-2.493 V**
  - DAC = 50000 → approximately **-1.580 V**
  - DAC = 45000 → approximately **-1.121 V**
- The sign should be negative (tip negative relative to sample, or sample positive relative to tip)
- Small variations (±0.01-0.02 V) are acceptable due to:
  - DAC resolution limits
  - Voltage reference accuracy
  - Measurement tolerances

**What this verifies:**
- ✅ DAC-to-voltage conversion is working correctly
- ✅ Bias voltage output circuit is functional
- ✅ The displayed voltage matches actual hardware output
- ✅ Polarity is correct (negative bias)

**Troubleshooting:**
- **If voltage doesn't match**: 
  - Check if the bias circuit is properly connected
  - Verify the voltage reference on the controller board
  - Check for loose connections
- **If voltage is zero**: 
  - Verify the Bias command was sent successfully
  - Check status display to confirm bias DAC value matches your input
  - Check for short circuits or disconnected outputs
- **If polarity is wrong**: 
  - Verify probe connections (red to positive, black to ground)
  - Check if the bias circuit has inverted outputs
  - Verify the conversion formula matches your hardware

**Additional Test Points:**
You can test other bias voltages to verify linearity:
- DAC = 32768 → Should give 0.000 V (center point)
- DAC = 60000 → Approximately -2.493 V (initial test value)
- DAC = 50000 → Approximately -1.580 V (stepped down, currently testing)
- DAC = 45000 → Approximately -1.121 V (further reduced, currently testing)
- DAC = 40000 → Should give approximately -0.662 V
- DAC = 25000 → Should give approximately +0.711 V

**Note:** Optimal bias voltage depends on sample characteristics, tip condition, and measurement goals. The values 50000 and 45000 are currently being tested and may be adjusted based on experimental results.

---

### Step 4: Run Approach Sequence

**Objective:** Use the automated approach command to bring the tip close to the sample, monitoring for proper operation and detecting potential tip-sample contact.

**Procedure:**
1. Ensure bias voltage is set (from Step 3)
2. Locate the **Approach** button or command interface in the GUI
3. Run the **Approach** command in the GUI
4. **Observe LED indicators** on the motor controller - they should be moving/blinking to indicate motor activity
5. **Monitor the Current Plot** visual continuously - watch for current changes as the tip approaches
6. Watch for current peaks in the plot

**Expected Behavior:**
- The approach sequence should automatically move the motor forward (toward the sample)
- LED indicators on the motor controller should show activity (blinking or changing states)
- Current should gradually increase as the tip gets closer to the sample
- The approach should **automatically stop** when the current reaches a set threshold (indicating tunneling contact)
- Motor movement should cease when the target current threshold is detected

**What to Watch For:**
- **Normal operation**: Current gradually increases, approach stops automatically at threshold
- **Potential plunge**: If you see a **dramatic, sudden peak** in current (much larger than expected), the probe tip may have plunged into the sample
- **Motor not stopping**: If the current spikes dramatically but the motor continues moving, the automatic stop may have failed

**Critical Safety Actions:**
- **Be prepared to press STOP immediately** if:
  - Current shows a dramatic peak (indicating possible plunge)
  - Motor continues moving after current threshold should have been reached
  - Any unexpected behavior occurs
- Keep your hand near the **STOP** button throughout the approach sequence
- Monitor both the current plot and LED indicators simultaneously

**Troubleshooting:**
- **If approach doesn't start**: Check that bias voltage is set and connection is active
- **If LEDs don't move**: Verify motor controller power and connections
- **If current doesn't change**: Tip may already be too close or too far - try manual motor movement first
- **If plunge occurs**: Immediately press STOP, then follow the Reset Procedure (see below) to back away safely

---

### Step 5: Fine-Tune Position and Test Scans

**Objective:** Optimize tip-sample distance using small step movements, then verify scanning functionality. Iterate on motor movement commands to avoid plunging.

**Procedure:**
1. **After approach completes** (or if you stopped it manually), verify the tip is **not plunged** into the sample:
   - Current should be stable and within expected tunneling range
   - No dramatic spikes or erratic behavior
2. **If tip is too close or plunged**: Use small backward steps to retract:
   - Use command: `MTMV -1` (moves 1 step backward)
   - Monitor current plot - current should decrease as tip moves away
   - Repeat with small increments until current stabilizes
3. **If tip needs to get closer**: Use small forward steps:
   - Use command: `MTMV 1` (moves 1 step forward)
   - Monitor current plot - current should gradually increase
   - Stop if current spikes dramatically
4. **Test small scans** once position is stable:
   - Configure a small scan area (e.g., 10×10 pixels)
   - Start scan and observe the scan plot
   - Verify tip moves smoothly without plunging
5. **Iterate on MTMV command values**:
   - Try different step sizes (1, 2, 5 steps) to find optimal movement
   - Goal: Find step sizes that allow smooth approach without plunging
   - Document successful step sizes for future reference

**Optimizing PID Control Values:**

The system uses PID (Proportional-Integral-Derivative) control for maintaining constant current during scanning. While detailed PID optimization will be covered in future documentation, here are starting concepts:

**Initial PID Values (Starting Point):**
- **Kp (Proportional)**: Start with values around 0.1 to 1.0
  - Controls immediate response to current error
  - Too high: Oscillations and instability
  - Too low: Slow response, poor tracking
- **Ki (Integral)**: Start with values around 0.01 to 0.1
  - Eliminates steady-state error
  - Too high: Can cause overshoot and instability
  - Too low: May not eliminate offset errors
- **Kd (Derivative)**: Start with values around 0.001 to 0.01
  - Reduces overshoot and oscillations
  - Too high: Can amplify noise
  - Too low: May not dampen oscillations effectively

**PID Tuning Strategy:**
1. Start with conservative values (lower gains)
2. Gradually increase Kp until you see oscillations
3. Add Kd to reduce oscillations
4. Add Ki to eliminate steady-state error
5. Fine-tune all three together for optimal performance

**Setting PID Values:**
Use the command: `PIDS Kp Ki Kd` (e.g., `PIDS 0.5 0.05 0.005`)

**What to Monitor:**
- Current stability during scans
- Tip height (Z-axis) variations
- Scan image quality and artifacts
- System response time to current changes

**Expected Results:**
- Tip position should be stable (not plunged)
- Small scans should complete without errors
- Current should remain relatively constant during scanning
- Scan images should show sample features, not noise or artifacts

**Troubleshooting:**
- **If scans show plunging**: Reduce scan speed, increase step size, or adjust PID values
- **If current is unstable**: Adjust PID values (typically reduce Kp, increase Kd)
- **If scans don't start**: Verify tip position is stable and current is in expected range

---

## Reset Procedure

**When to Use:**
- After a tip plunge into the sample
- When system becomes unresponsive
- To return to a known safe state
- After any unexpected behavior

**Complete Reset Steps:**

1. **Power off the motor controller**:
   - Locate the power switch or disconnect power to the motor controller
   - This prevents any automatic movements during reset

2. **Retract the probe tip** (if plunged):
   - **Option A - Command-based (Recommended)**: Use `MTMV -500` or larger negative values to retract significantly (see [Probe Retraction Techniques](#probe-retraction-techniques) section)
   - **Option B - Manual rotation**: Power off motor, then manually rotate the rotor to retract tip (see [Probe Retraction Techniques](#probe-retraction-techniques) section)
   - Move tip to a safe distance (several millimeters away)
   - **Important**: If using manual rotation, motor must be powered off to avoid conflicts

3. **Power on the motor controller**:
   - Restore power to the motor controller
   - Wait for initialization to complete

4. **Reset in GUI**:
   - In the GUI, locate the **Reset** button in the Connection Control section
   - Click **Reset** to initialize the STM controller to default state
   - Wait a few seconds for reset to complete

5. **CRITICAL: Re-apply bias voltage**:
   - **If you press Reset in the GUI, you MUST re-apply the bias voltage**
   - Reset clears all DAC values, including bias voltage
   - Go to **Step 3** and set your bias voltage again
   - Click the **Bias** button to restore your desired voltage setting
   - Verify the voltage is set correctly before proceeding

6. **Verify system state**:
   - Check current readings (should be near zero with tip far from sample)
   - Verify all settings are restored
   - Confirm connection is stable

**Important Notes:**
- **Never skip re-applying bias voltage** after reset - the system will not function correctly without it
- Always manually back away the tip before resetting if a plunge occurred
- Keep motor powered off during manual adjustments to prevent damage
- After reset, you may need to repeat the approach sequence (Step 4) to bring tip close again

---

## Probe Retraction Techniques

When you need to retract the probe tip away from the sample (e.g., after a plunge, before sample changes, or for safety), there are two methods available:

### Method 1: Manual Rotation (Physical)

**When to use:** Quick physical retraction, especially after a plunge or when the system is unresponsive.

**Procedure:**
1. **CRITICAL: Power off the stepper motor controller first**
   - Locate the power switch or disconnect power to the motor controller
   - **Never attempt manual rotation while the motor is powered** - this can damage the motor or cause conflicts
2. Locate the manual adjustment mechanism (rotor) on the STM head
3. Manually rotate the rotor to move the tip **backward/away** from the sample
4. Rotate until the tip is retracted to a safe distance (several millimeters away)
5. Power the motor controller back on before resuming operations

**Advantages:**
- Fast physical retraction
- Works even if system is unresponsive
- No need for GUI connection

**Disadvantages:**
- Requires physical access to the STM head
- Motor must be powered off
- Step count may not be accurately tracked

**Safety:**
- ⚠️ **Always power off the motor before manual rotation**
- Move slowly and carefully
- Ensure tip is fully retracted before powering motor back on

---

### Method 2: Command-Based Retraction (Recommended)

**When to use:** Controlled retraction with accurate step tracking, preferred method for significant retractions.

**Procedure:**
1. Ensure the GUI is connected and communication is active
2. Locate the **Command Text Box** in the Manual Command Interface section
3. For significant retraction (e.g., after a plunge or to return to starting position), use a large negative step value:
   - **Command:** `MTMV -500` (moves motor 500 steps backward/away from sample)
   - For even larger retractions, you can use: `MTMV -1000` or `MTMV -2000`
4. Click **Send** button
5. Monitor the **Real-Time Steps Plot** to verify the step count decreases
6. Monitor the **Real-Time Current Plot** - current should decrease as tip moves away
7. Repeat with additional retraction commands if needed until current is near baseline

**Recommended Retraction Distances:**
- **Small adjustment**: `MTMV -10` to `MTMV -50` steps
- **Moderate retraction**: `MTMV -100` to `MTMV -200` steps
- **Significant retraction** (after plunge or sample change): `MTMV -500` to `MTMV -1000` steps
- **Full retraction** (return to starting position): `MTMV -2000` or more steps

**Advantages:**
- Accurate step tracking
- Can be done while system is running
- No need to power off motor
- Precise control over retraction distance
- Can monitor current and step count in real-time

**Disadvantages:**
- Requires GUI connection
- Takes longer than manual rotation for very large distances

**Safety:**
- Monitor current plot continuously - if current doesn't decrease, tip may be stuck
- Use STOP button if anything unexpected happens
- For very large retractions (1000+ steps), consider breaking into smaller increments (e.g., multiple `MTMV -500` commands)

**Example Workflow for Significant Retraction:**
```
1. MTMV -500  (retract 500 steps)
2. Monitor current plot - wait for current to stabilize
3. If still too close, repeat: MTMV -500
4. Continue until current is near baseline (±10-100 pA)
5. Verify step count has decreased appropriately
```

---

## Post-Setup Verification Checklist

After completing all steps, verify:

- [ ] COM port connection is stable and status updates continuously
- [ ] Current readings are in the expected range (±10⁻¹¹ to ±10⁻¹² A when tip is far)
- [ ] Bias voltage can be set and matches multimeter readings
- [ ] **After any reset, bias voltage (and other DAC settings) have been re-applied by clicking the respective buttons**
- [ ] Approach sequence completes successfully without plunging
- [ ] Tip position is stable and not plunged into sample
- [ ] Small test scans complete without errors
- [ ] Status display shows all parameters updating correctly
- [ ] No error messages or communication timeouts
- [ ] LED indicators on motor controller respond correctly

## Manual Motor Control

### Moving the Motor Backward

If you need to move the step motor backward (away from the sample), you can use the manual command interface:

**Command:** `MTMV -<steps>`

**How to use:**
1. Locate the **Command Text Box** in the Manual Command Interface section
2. Type: `MTMV -<number>` where `<number>` is the number of steps to move backward
   - Example: `MTMV -1` (moves 1 step backward)
   - Example: `MTMV -500` (moves 500 steps backward - for significant retraction)
3. Click **Send** button
4. The motor will move backward by the specified number of steps

**Notes:**
- **MTMV** stands for "Move Motor"
- Negative values move the motor backward (away from sample)
- Positive values move the motor forward (toward sample)
- Example: `MTMV -5` moves 5 steps backward, `MTMV 10` moves 10 steps forward
- Monitor the **Real-Time Steps Plot** to see the step count change
- Use this for fine manual positioning or to back away if you get too close during approach

**Step Size Guidelines:**
- **Fine positioning** (close to sample): `MTMV -1` to `MTMV -10` (small increments)
- **Moderate retraction**: `MTMV -50` to `MTMV -200` (medium increments)
- **Significant retraction** (after plunge or sample change): `MTMV -500` to `MTMV -1000` (large increments)
- See [Probe Retraction Techniques](#probe-retraction-techniques) section for detailed retraction procedures

**When to use:**
- Backing away after getting too close during approach
- Fine manual positioning before starting measurements
- Adjusting tip-sample distance incrementally
- Recovering from a situation where the tip is too close
- Significant retraction after a plunge (use `MTMV -500` or larger)

**Safety:**
- Move slowly (1 step at a time) when close to the sample
- For large retractions, monitor current plot - current should decrease as tip moves away
- Use STOP button if anything unexpected happens
- If current doesn't decrease during retraction, tip may be stuck - stop and investigate

## Next Steps

Once basic setup is verified:

1. **Approach Sequence**: Use the Approach button to bring the tip close to the sample
2. **Manual Motor Control**: Use `MTMV -1` command to move backward if needed
3. **IV Curve Measurement**: Take an IV curve to verify tip-sample contact
4. **Constant Current Mode**: Enable feedback and verify it maintains target current
5. **Test Scan**: Perform a small test scan to verify scanning functionality

## Safety Notes

- Always verify voltages with a multimeter before connecting to sensitive samples
- Start with small bias voltages (< 1V) when first approaching samples
- Monitor current continuously during approach - be ready to STOP if current spikes
- Ensure proper grounding to avoid electrical hazards
- Double-check all connections before applying bias voltages
- **Keep STOP button accessible at all times during approach and scanning**
- **If plunge occurs, immediately press STOP and follow Reset Procedure**

## Technical Reference

### Voltage Ranges
- **Bias Voltage**: -3.0 V to +3.0 V (DAC range: 0 to 65535, center at 32768)
- **Z/X/Y Axes**: -2.5 V to +2.5 V (DAC range: 0 to 65535, center at 32768)

### Current Measurement
- **ADC Range**: 0 to 65535 (16-bit)
- **Current Range**: Approximately -10 nA to +10 nA (depends on preamp gain)
- **Typical Noise Floor**: ±10-100 pA (±10⁻¹¹ to ±10⁻¹⁰ A)

### Conversion Formulas
- **Bias Voltage**: `V_bias = -1.0 * (DAC - 32768) / 32768 * 3.0`
- **Current**: `I = ADC / 32768 * 10.24 / 100e6` (amperes)
- **Z/X/Y Voltage**: `V = (DAC - 32768) / 32768 * 10.0 / 2.0`

