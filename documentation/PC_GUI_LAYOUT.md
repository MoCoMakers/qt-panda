# PC GUI Layout Documentation

## Overview

The Panda STM application provides a graphical user interface for controlling and monitoring the Scanning Tunneling Microscope (STM) system. The GUI is built using Tkinter and Matplotlib, providing real-time visualization and control capabilities.

**Application Title:** "Panda STM"

## Layout Structure

The GUI is organized into two main sections:
- **Left Panel**: Control panel with buttons, input fields, and status display
- **Right Panel**: Visualization area with plots and scan images arranged in a grid

### Grid Layout

The visualization area uses a 3-column, 2-row grid layout (500x500 pixels per cell):

```
Column 0          Column 1          Column 2
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Current     │  │ Steps       │  │ DACZ Scan   │
│ Plot        │  │ Plot        │  │ Image       │
│             │  │             │  │             │
│ (Row 0)     │  │ (Row 0)     │  │ (Row 0)     │
├─────────────┤  ├─────────────┤  ├─────────────┤
│             │  │ IV Curve    │  │ ADC Scan    │
│             │  │ Plot        │  │ Image       │
│             │  │             │  │             │
│ (Row 1)     │  │ (Row 1)     │  │ (Row 1)     │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Visualization Widgets

### Real-Time Current Plot (Row 0, Column 0)

**What it does:**
This plot continuously displays the tunneling current flowing between the STM tip and the sample surface in real-time. Think of it as a live "heartbeat monitor" for your STM - it shows you whether the tip is properly engaged with the sample and how stable the current is.

**Why it's useful:**
When you're approaching the tip to the sample, this plot helps you see when tunneling current starts flowing, indicating the tip is close enough. During scanning or constant current mode, a stable, flat line means the feedback loop is working correctly. If you see sudden spikes or drops, it might indicate tip crashes, contamination, or feedback instability. The plot maintains a rolling history of the last 1000 measurements, so you can see trends over time.

**How it works:**
Every 100 milliseconds, the GUI queries the STM controller for the current status. The ADC (Analog-to-Digital Converter) value is converted from raw counts to actual current in amperes using the formula: `current = ADC / 32768 * 10.24 / 100e6`. The time axis is normalized to show recent history relative to the most recent measurement, making it easy to see what's happening right now.

**What to look for:**
- A steady, constant value means good tip-sample contact
- Gradual changes might indicate drift or thermal effects
- Sudden jumps could signal tip crashes or contamination
- No signal (zero current) means the tip is too far from the sample

### Real-Time Steps Plot (Row 0, Column 1)

**What it does:**
This plot tracks the position of the coarse approach motor (step motor) over time. The step motor is what moves the tip assembly up and down in large increments, typically used for initial approach to the sample before fine positioning with the piezo.

**Why it's useful:**
During the approach sequence, this plot shows you how many steps the motor has taken. You can monitor whether the approach is progressing smoothly or if it's stuck. It's particularly helpful when troubleshooting approach issues - if the step count isn't changing, the motor might not be responding. The plot also helps you understand the relationship between motor steps and tip position, which is important for repeatable positioning.

**How it works:**
Like the current plot, this updates every 100ms from the status data. The step count is a raw integer value from the motor controller, representing the cumulative number of steps taken since the last reset. The plot shows this value over time, giving you a visual record of motor activity.

**What to look for:**
- Increasing values during approach indicate the motor is working
- Constant values mean the motor has stopped (either reached target or encountered an issue)
- Sudden large jumps might indicate skipped steps or motor issues

### IV Curve Plot (Row 1, Column 1)

**What it does:**
This plot displays an I-V (Current-Voltage) spectroscopy measurement, which is one of the fundamental STM measurement techniques. When you click "PlotIV", the system sweeps the bias voltage across a specified range while measuring the tunneling current at each voltage point. The resulting curve reveals electronic properties of the sample at that specific location.

**Why it's useful:**
IV curves are essential for understanding the electronic structure of your sample. They can reveal:
- The work function difference between tip and sample
- Band gaps in semiconductors
- Electronic states and resonances
- Whether you're measuring on an insulator, semiconductor, or conductor
- The quality of tip-sample contact

This is a point spectroscopy technique - it measures at one specific location. You typically position the tip where you want to measure, then take an IV curve to understand the local electronic properties before or after scanning.

**How it works:**
When you press "PlotIV", you specify three parameters: start DAC value, end DAC value, and the number of steps. The system converts these DAC values to actual bias voltages (typically ranging from about -3V to +3V). The STM controller then sweeps the bias voltage from start to end, measuring the current at each step. The measured ADC values are converted to current in amperes, and the plot displays voltage on the X-axis and current on the Y-axis. The measurement takes a few seconds to complete, and the plot updates when finished.

**What to look for:**
- A symmetric curve suggests good tip-sample contact
- Asymmetric curves might indicate tip asymmetry or sample properties
- Sharp features or steps can indicate electronic states or band edges
- The slope gives information about the tunneling barrier

### DACZ Scan Image (Row 0, Column 2)

**What it does:**
This is the **topographic image** - it shows the actual height profile of your sample surface. During scanning in constant current mode, the STM tip follows the surface contours, moving up and down to maintain constant tunneling current. The DACZ values represent these vertical movements of the tip, which directly correspond to the surface topography.

**Why it's useful:**
This is the primary image you'll use to see what your sample looks like. It shows atomic-scale or nanometer-scale features on the surface - individual atoms, steps, defects, or larger structures. The image is displayed as a heatmap or grayscale, where brighter areas typically represent higher features and darker areas represent lower features (though this depends on the color scheme). This is the "picture" of your sample that you'll analyze, publish, or use to understand surface structure.

**How it works:**
During a scan, the tip raster-scans across the surface in a grid pattern. At each point, the feedback system adjusts the Z-axis (vertical) position to keep the current constant. These Z-axis adjustments are recorded as DACZ values. The image updates in real-time as the scan progresses - you'll see it "paint" line by line. The default resolution is 512x512 pixels, but you can adjust this in the scan parameters. The image extent maps directly to your scan area coordinates, so you know exactly what physical area you're imaging.

**What to look for:**
- Atomic resolution features (individual atoms appear as bright spots)
- Surface steps and terraces
- Defects, vacancies, or adsorbates
- Overall surface morphology
- Scan artifacts (lines, streaks) that might indicate drift or feedback issues

### ADC Scan Image (Row 1, Column 2)

**What it does:**
This image shows the tunneling current map across the scanned surface. In constant current mode, this should be relatively uniform since the feedback loop tries to keep current constant. However, variations in this image can reveal important information about the sample's electronic properties.

**The Raster Pattern:**
The tip scans in a **raster pattern** (like a TV screen or inkjet printer):
1. **Forward pass**: Tip moves along the X-axis from left to right (start DAC to end DAC)
2. **Y-step**: Tip steps forward in the Y-direction by one line
3. **Reverse pass**: Tip moves along the X-axis from right to left (end DAC to start DAC)
4. **Y-step**: Tip steps forward again
5. **Repeat**: This back-and-forth pattern continues until the entire area is scanned

At each point in this raster grid, the system records:
- **ADC value**: The tunneling current at that point
- **DACZ value**: The tip height adjustment needed to maintain constant current

The image builds up line by line as the scan progresses - you'll see it "paint" from top to bottom.

**Will it show atoms?**

**In Constant Current Mode (standard STM operation):**
- **DACZ Scan Image**: **YES, this shows atoms!** The DACZ image is the topographic image. As the tip follows surface contours to maintain constant current, the height adjustments (DACZ values) directly map to the surface topography. Individual atoms appear as bright or dark spots depending on whether they're higher or lower than surrounding atoms.
- **ADC Scan Image**: **Usually NO, atoms are NOT visible** in constant current mode. Since the feedback keeps current constant, the ADC values should be relatively uniform across the surface. The ADC image will look mostly flat/featureless if the feedback is working well. However, small variations can occur due to:
  - Electronic differences between atoms (different work functions)
  - Feedback limitations (can't perfectly maintain constant current)
  - Noise

**In Constant Height Mode (less common):**
- **ADC Scan Image**: **YES, can show atoms!** If you scan at a fixed height (constant DACZ), the ADC image directly shows current variations. Higher current = tip closer to surface = atoms appear brighter. Lower current = tip farther = atoms appear darker. This mode reveals electronic structure more directly.

**Why it's useful:**
While the DACZ image shows topography, the ADC image shows electronic properties. If you're scanning in constant current mode, a uniform ADC image confirms the feedback is working correctly. Variations in the ADC image (even with constant current feedback) can indicate:
- Areas with different electronic properties (different work function, band gaps)
- Electronic defects or states
- Tip condition (a contaminated tip might show artifacts)
- Feedback quality (if the image is very non-uniform, the feedback might be struggling)

**How it works:**
As the tip scans across the surface in the raster pattern, the tunneling current (measured as ADC values) is recorded at each point. In constant current mode, the feedback adjusts the tip height to keep this current constant, so ideally all values should be similar. However, real systems show some variation due to noise, feedback limitations, and actual electronic variations in the sample. The image updates in real-time alongside the DACZ image, showing you both the topographic and electronic information simultaneously.

**What to look for:**
- **For atomic resolution**: Look at the **DACZ Scan Image** (top right) - this is where you'll see individual atoms
- **For electronic structure**: Look at the **ADC Scan Image** (bottom right) - variations here reveal electronic properties
- Uniformity in ADC indicates good feedback control
- Variations might reveal electronic structure or defects
- Compare with DACZ image - features that appear in both are likely topographic, features only in ADC are likely electronic
- Artifacts or streaks might indicate scan issues or tip problems

**Summary:**
- **Raster pattern**: Back-and-forth scanning like a TV screen, building the image line by line
- **DACZ image**: Shows atoms and topography (this is your primary atomic-resolution image)
- **ADC image**: In constant current mode, mostly uniform (doesn't show atoms); in constant height mode, can show atoms and electronic structure

## Control Panel Widgets

The left control panel contains the following widgets, arranged vertically:

### Connection Control

#### Open Button

**What it does:**
This button establishes serial communication between your computer and the STM controller hardware. Before you can do anything with the STM, you need to connect to it through a serial port (typically USB-to-serial adapter).

**Why it's useful:**
Without an active connection, all other controls are non-functional. The serial port is how commands are sent to the STM controller and how data is received back. On Windows, serial ports are typically named COM1, COM2, COM3, etc. You need to know which COM port your STM controller is connected to - you can find this in Device Manager or by checking which ports are available.

**How it works:**
Enter the COM port number (like "COM7") in the text field, then click "Open". The system opens a serial connection at 115200 baud rate with a 1-second timeout. Once connected, the STM controller can receive commands and send back status data. If the connection fails (wrong port, device not connected, port already in use), you'll need to troubleshoot the connection before proceeding.

**What to check:**
- Make sure the STM controller is powered on and connected via USB
- Verify the correct COM port number (check Device Manager on Windows)
- Ensure no other program is using that COM port
- Check that drivers for your USB-to-serial adapter are installed

#### STOP, Reset, Clear Buttons

**What they do:**
These three buttons provide emergency and maintenance controls for the STM system:

- **STOP**: Immediately halts whatever operation the STM is currently performing. This is like an emergency stop - it sends a stop command to abort the current task.
- **Reset**: Performs a system reset on the STM controller, reinitializing the hardware to a known state.
- **Clear**: Clears the history buffer in the GUI, wiping the data used for the real-time plots.

**Why they're useful:**
**STOP** is critical for safety - if something goes wrong during approach, scanning, or any operation, you can immediately stop it. This prevents tip crashes, excessive current, or other potentially damaging situations. **Reset** is useful when the controller seems to be in an unknown or error state - it brings everything back to a clean starting point. **Clear** is mainly for housekeeping - if your plots are cluttered with old data, clearing gives you a fresh view.

**How they work:**
Each button sends a specific command to the STM controller over the serial connection. STOP sends "STOP", Reset sends "RSET" (which also clears the history), and Clear just empties the local history buffer without affecting the hardware. These are immediate actions - there's no confirmation dialog, so use them carefully.

**When to use:**
- **STOP**: Use immediately if you see dangerous current spikes, if the tip is approaching too fast, or if any operation seems out of control
- **Reset**: Use if the controller isn't responding, if values seem wrong, or after making significant hardware changes
- **Clear**: Use when you want fresh plots without old data, or when starting a new measurement session

### DAC Control

**Understanding DACs:**
DAC stands for Digital-to-Analog Converter. The STM controller uses DACs to set voltages that control various aspects of the system. The DAC values range from 0 to 65535 (16-bit), with 32768 being the center/midpoint value. Each DAC controls a different physical parameter.

#### Bias Control

**What it does:**
Sets the bias voltage applied between the STM tip and the sample. This voltage is crucial - it determines the direction and energy of electron tunneling. Positive bias means electrons tunnel from sample to tip, negative bias means electrons tunnel from tip to sample.

**Why it's important:**
The bias voltage is fundamental to STM operation. Different bias voltages can reveal different electronic states in your sample. For example, in semiconductors, you might need specific bias voltages to access conduction or valence bands. The bias also affects the tunneling current - higher bias generally means higher current (though this depends on the sample's electronic structure).

**How it works:**
Enter a DAC value in the entry field (default is 33314, which corresponds to a specific bias voltage). The display label shows the converted voltage in volts using the formula: `bias_volts = -1.0 * (dac - 32768) / 32768 * 3.0`. This means the bias range is approximately -3V to +3V, with 32768 being 0V. Click the "Bias" button to send the command to the STM controller.

**Typical usage:**
- Start with small bias voltages (around 0.1-0.5V) for initial approach
- Adjust based on your sample - metals might use 0.1-1V, semiconductors might need higher voltages
- Be careful with high bias voltages as they can cause tip crashes or sample damage

#### DACZ Control

**What it does:**
Controls the Z-axis (vertical) position of the STM tip via the piezo actuator. This is the fine positioning control - it moves the tip up and down in nanometer-scale increments. During scanning, the feedback system automatically adjusts DACZ to maintain constant current, but you can also set it manually.

**Why it's important:**
DACZ is critical for tip-sample distance control. Small changes in DACZ correspond to angstrom-level changes in tip height. This is what allows atomic resolution imaging. The Z-axis piezo has a limited range (typically a few hundred nanometers), so you need to use the coarse approach motor to get close first, then DACZ provides fine control.

**How it works:**
Enter a DAC value (default 32768 is the center position, 0V). The display shows the converted voltage: `volts = (dac - 32768) / 32768 * 10.0 / 2.0`, giving a range of approximately -2.5V to +2.5V. The actual tip movement depends on the piezo's sensitivity. Click "DACZ" to set the value.

**Typical usage:**
- Use for fine positioning after coarse approach
- In constant current mode, the feedback controls this automatically
- Manual control is useful for testing, calibration, or constant-height mode

#### DACX Control

**What it does:**
Controls the X-axis (horizontal) position of the STM tip. This moves the tip left and right across the sample surface. During scanning, this is swept automatically to create the raster pattern, but you can also position it manually.

**Why it's important:**
DACX determines where on the sample you're imaging or measuring. Combined with DACY, it defines the 2D scan area. The X-axis piezo typically has a range of several micrometers, allowing you to scan different regions of your sample.

**How it works:**
Similar to DACZ, enter a DAC value (default 32768 is center). The voltage conversion is the same as DACZ. Click "DACX" to set the position. During scanning, the controller automatically sweeps DACX from the start to end values you specify.

**Typical usage:**
- Set manually to position the tip at a specific location
- Used automatically during scanning to create the raster pattern
- Combine with DACY to define your scan area

#### DACY Control

**What it does:**
Controls the Y-axis position of the STM tip, moving it forward and backward across the sample. Together with DACX, this defines the 2D scan plane.

**Why it's important:**
DACY works in conjunction with DACX to create the 2D scan pattern. The tip scans in lines (X-direction), then steps in the Y-direction to the next line, creating a raster pattern. The Y-axis also has micrometer-scale range.

**How it works:**
Identical to DACX - enter a DAC value and click "DACY" to set it. During scanning, the controller steps DACY between scan lines while sweeping DACX along each line.

**Typical usage:**
- Manual positioning to select scan area
- Automatic stepping during scanning between lines
- Used with DACX to define scan boundaries

#### SetAllDAC Button

**What it does:**
A convenience function that sets all four DAC values (Bias, DACZ, DACX, DACY) in sequence with small delays between each. This ensures all parameters are updated together.

**Why it's useful:**
Instead of clicking each DAC control individually, you can set all the values in their respective entry fields, then click "SetAllDAC" once to apply them all. This is faster and ensures the values are set in a coordinated manner. The 10ms delays between commands give the controller time to process each command before receiving the next.

**How it works:**
The button internally calls `set_value()` on each of the four DAC controls in sequence: Bias, then DACZ, then DACX, then DACY, with 10ms sleep delays between each. Make sure you've entered the desired values in all four entry fields before clicking this button.

**When to use:**
- When you want to set up a complete scanning configuration at once
- When you're repositioning and want to set both position (DACX/DACY) and operating parameters (Bias/DACZ) together
- For convenience when making multiple parameter changes

### Approach Control

#### Approach Button

**What it does:**
Initiates the coarse approach sequence, which moves the tip closer to the sample using the step motor. This is the first step in getting the tip close enough for tunneling to occur. The approach moves the tip assembly in discrete steps until it reaches a target current or position.

**Why it's critical:**
Before you can do any STM measurements, the tip must be close enough to the sample for tunneling current to flow (typically within a few nanometers). The approach sequence automates this process, moving the tip closer step by step while monitoring for tunneling current. Without proper approach, you'll never get close enough for atomic resolution imaging.

**How it works:**
Enter two parameters:
- **Target DAC value**: The target current (in ADC/DAC units) that indicates successful approach. When the measured current reaches this value, the approach stops. Default is 500, which corresponds to a small but measurable tunneling current.
- **Step count**: How many motor steps to take before checking the current again. Default is 1 step at a time for careful approach.

Click "Approach" and the system sends the command to the STM controller. The controller then moves the step motor, checks current, and repeats until either the target current is reached or a maximum number of steps is exceeded. You can monitor progress using the Real-Time Current Plot and Real-Time Steps Plot.

**What to watch:**
- Monitor the current plot - you should see current start to appear as the tip gets close
- Watch the steps plot to see motor activity
- If current suddenly spikes very high, stop immediately - the tip might be crashing
- If no current appears after many steps, the tip might be stuck or the sample might be insulating

**Safety considerations:**
- Start with small step counts (1 step) for careful approach
- Monitor the current plot continuously during approach
- Be ready to hit STOP if current spikes unexpectedly
- If approach fails repeatedly, check tip condition, sample cleanliness, and system alignment

### IV Curve Measurement

#### PlotIV Button

**What it does:**
Performs a current-voltage (I-V) spectroscopy measurement at the current tip position. The system sweeps the bias voltage across a specified range while measuring the tunneling current at each voltage point, then displays the resulting IV curve.

**Why it's essential:**
IV spectroscopy is one of the most important STM measurement techniques. It reveals the electronic structure of your sample at a specific location:
- **Work function**: The energy difference between tip and sample Fermi levels
- **Band gaps**: In semiconductors, the IV curve shows where current drops to near zero
- **Electronic states**: Sharp features indicate discrete energy levels
- **Sample type**: Different materials show characteristic IV curve shapes
- **Tip quality**: A good tip-sample contact produces smooth, reproducible curves

This is a point measurement - it tells you about one specific spot. You typically take IV curves before or after scanning to understand what you're imaging.

**How it works:**
Enter three parameters:
- **Start DAC value**: The starting bias voltage in DAC units (default 31768, approximately -0.5V)
- **End DAC value**: The ending bias voltage in DAC units (default 33768, approximately +0.5V)
- **Step count**: Number of measurement points (default 10)

Click "PlotIV" and the system:
1. Sends the IV measurement command to the STM controller
2. Waits 2 seconds for the measurement to complete
3. Retrieves the measured data (alternating DAC and ADC values)
4. Converts DAC values to bias voltage and ADC values to current
5. Updates the IV Curve plot with the new data

The measurement typically takes a few seconds. During this time, the tip stays at the same position while the bias voltage is swept. Make sure you're positioned where you want to measure before starting.

**Interpreting results:**
- **Symmetric curves**: Usually indicate good tip-sample contact and symmetric electronic structure
- **Asymmetric curves**: May indicate tip asymmetry, sample properties, or contact issues
- **Sharp steps or features**: Can indicate band edges, electronic states, or resonances
- **Current magnitude**: Tells you about the tunneling barrier and tip-sample distance
- **Noise level**: High noise might indicate poor contact or tip issues

#### Save IV Curve Button

**What it does:**
Saves the currently displayed IV curve data to a CSV file for later analysis, publication, or comparison with other measurements.

**Why it's useful:**
IV curves contain valuable electronic structure information that you'll want to analyze in detail, compare with theory, or include in publications. Saving the raw data allows you to:
- Analyze the data in other software (Python, MATLAB, Excel, etc.)
- Compare multiple IV curves from different locations
- Extract quantitative parameters (work function, band gaps, etc.)
- Create publication-quality figures
- Keep records of your measurements

**How it works:**
Enter a file path prefix (default is "./data/iv_curve_"). The system automatically appends a millisecond-precision timestamp to create a unique filename. The CSV file contains two columns: bias voltage (volts) and current (amperes), with one row per measurement point.

**File format:**
The saved CSV file has the format:
```
bias_voltage_1,current_1
bias_voltage_2,current_2
...
```

This makes it easy to import into analysis software or plotting tools.

**Best practices:**
- Use descriptive path prefixes to organize your data (e.g., "./data/sample1_locationA_iv_")
- Save IV curves immediately after measurement while the data is fresh
- Include measurement conditions in your file naming or notes
- Keep the data files with your scan images for complete records

### Constant Current Mode

**Understanding Constant Current Mode:**
Constant current mode is the standard STM imaging mode. The feedback system continuously adjusts the tip height (via DACZ) to keep the tunneling current constant. This allows the tip to follow the surface topography, creating topographic images. The feedback uses a PID (Proportional-Integral-Derivative) controller to achieve smooth, stable control.

#### SetPID Button

**What it does:**
Sets the PID controller parameters that determine how the feedback system responds to current changes. The PID controller is what keeps the current constant by adjusting tip height.

**Why it matters:**
The PID parameters directly affect image quality and stability:
- **Too aggressive** (high gains): The feedback oscillates, creating artifacts in images
- **Too conservative** (low gains): The feedback is slow, causing drift and poor tracking
- **Well-tuned**: Smooth, stable feedback that accurately follows the surface

**How it works:**
Enter three gain values:
- **Kp (Proportional gain)**: Responds to the current error immediately. Higher values make the system respond faster but can cause overshoot. Default: 0.0001
- **Ki (Integral gain)**: Eliminates steady-state error by integrating past errors. Helps maintain the exact target current. Higher values eliminate error faster but can cause oscillation. Default: 0.0001
- **Kd (Derivative gain)**: Dampens oscillations by responding to the rate of change. Helps stabilize the system. Default: 0.0 (often not needed)

Click "SetPID" to send these parameters to the controller. The values are quite small (typically 0.0001 range) because the current and position changes are small.

**Tuning tips:**
- Start with default values
- If images show oscillation or "ringing", reduce Kp and Ki
- If the feedback is slow to respond or drifts, increase Kp and Ki slightly
- Add small Kd (0.00001-0.0001) if you have oscillation issues
- Tune while watching the Real-Time Current Plot - it should be stable and flat

#### ConstCurrentOn Button

**What it does:**
Activates constant current mode, enabling the PID feedback loop that maintains constant tunneling current by adjusting tip height.

**Why it's essential:**
Constant current mode is how you get topographic images. Once enabled, the system automatically adjusts DACZ to keep the current at your target value. This allows the tip to follow surface contours, and the DACZ adjustments become your topographic image data.

**How it works:**
Enter the target ADC value (default 1000) - this is the current you want to maintain, measured in ADC units. Click "ConstCurrentOn" and the feedback system activates. The controller continuously monitors the current and adjusts the tip height to keep it at the target.

**Choosing the target:**
- **Too low** (< 500): May be too close to noise floor, poor signal-to-noise ratio
- **Too high** (> 5000): Tip might be too close, risk of crashes, or too far for atomic resolution
- **Typical range**: 1000-3000 ADC units works well for most samples
- **Adjust based on**: Sample type, desired resolution, tip condition

**What to monitor:**
- Watch the Real-Time Current Plot - it should stabilize near your target value
- If current oscillates wildly, your PID gains might be too high
- If current drifts slowly, PID gains might be too low
- The DACZ Scan Image will start showing topography once scanning begins

#### ConstCurrentOFF Button

**What it does:**
Deactivates constant current mode, disabling the feedback loop. The tip height (DACZ) remains fixed at its current value.

**Why you'd use it:**
- Switching to constant height mode (where you scan at fixed height and measure current variations)
- Manual tip positioning without feedback interference
- Troubleshooting feedback issues
- When you want direct control over tip height

**How it works:**
Simply click "ConstCurrentOFF" - no parameters needed. The feedback immediately stops, and DACZ stays at whatever value it was when you turned it off. The current will likely change as the tip-sample distance changes (due to drift, thermal expansion, etc.) since there's no feedback to maintain it.

**Important notes:**
- Always turn off constant current mode before making large manual DACZ adjustments
- If you turn it off during a scan, the scan will continue but won't follow topography properly
- Remember to turn it back on before starting a new scan if you want topographic images

### Scanning Control

#### Scan Control Panel

**What it does:**
Initiates a 2D raster scan of the sample surface. The tip moves in a grid pattern, measuring current and adjusting height at each point to create topographic and current images of your sample.

**Why it's the core function:**
Scanning is how you create STM images. The tip raster-scans across a defined area, and at each point the system records both the tunneling current (ADC) and the tip height adjustment (DACZ). These measurements form the two images you see: the topographic image (DACZ) and the current map (ADC).

**How it works:**
The scan control has a grid of entry fields organized as follows:

**Row 0 - X-axis parameters:**
- **Start DAC**: Left boundary of scan area in X-direction (default: 31768, center position)
- **End DAC**: Right boundary of scan area in X-direction (default: 33768)
- **Resolution**: Number of points along X-axis (default: 512)

**Row 1 - Y-axis parameters:**
- **Start DAC**: Bottom boundary of scan area in Y-direction (default: 31768)
- **End DAC**: Top boundary of scan area in Y-direction (default: 33768)
- **Resolution**: Number of points along Y-direction (default: 512)

**Row 2 - Sampling:**
- **Sample number**: How many measurements to average at each point (default: 10). More samples = better signal-to-noise but slower scanning.

**Scan process:**
1. Click "Scan" to start
2. The scan runs in a separate thread (so the GUI stays responsive)
3. The tip moves to the starting position
4. It scans line by line: moves along X-axis, steps in Y-direction, repeats
5. At each point, it measures current and adjusts height (if constant current mode is on)
6. Data streams back via serial communication
7. Images update in real-time as data arrives
8. You'll see the images "paint" line by line

**Choosing parameters:**
- **Scan area**: Larger areas show more of your sample but take longer. Start small (100-200 DAC range) for testing
- **Resolution**: Higher resolution (512x512) gives better detail but takes much longer. 256x256 is often sufficient
- **Sampling**: More samples improve quality but slow scanning. 10 is a good default; increase if you have noise issues

**What to watch:**
- Monitor both scan images as they update
- Watch for drift (images shifting or distorting) - might need to reduce scan time
- Check for artifacts (lines, streaks) - could indicate feedback issues or tip problems
- If scan seems stuck, check serial communication and controller status

**Scan time estimate:**
For a 512x512 scan with 10 samples per point, expect several minutes to tens of minutes depending on scan speed settings in the controller.

#### Save Scan Images Button

**What it does:**
Saves the current scan data to files for analysis, publication, or archiving. This creates both image files (PNG) and raw data files (TXT) so you have everything you need.

**Why it's essential:**
Scan images are your primary data - you'll want to analyze them, compare them, include them in publications, and keep records. Saving immediately after a good scan ensures you don't lose the data. The raw data files allow you to reprocess images with different parameters, extract line profiles, or perform quantitative analysis.

**How it works:**
Enter a file path prefix (default: "./data/image"). The system creates four files, all with the same timestamp:
- **`*_adc_*.txt`**: Raw ADC (current) values as a 2D array, one value per scan point
- **`*_dacz_*.txt`**: Raw DACZ (height) values as a 2D array, one value per scan point  
- **`*_adc_*.png`**: PNG image of the ADC scan (current map)
- **`*_dacz_*.png`**: PNG image of the DACZ scan (topographic image)

The timestamp ensures each scan gets a unique filename, preventing accidental overwrites.

**File formats:**
- **TXT files**: Plain text arrays that can be read by Python (numpy.loadtxt), MATLAB, Excel, or any data analysis tool
- **PNG files**: Standard image format viewable in any image viewer and suitable for presentations/publications

**Best practices:**
- Save immediately after completing a good scan
- Use descriptive prefixes (e.g., "./data/sample1_area2_scan_")
- Keep both PNG and TXT files - PNGs for quick viewing, TXTs for analysis
- Organize files by sample, date, or experiment
- Include scan parameters in your file naming or a separate log file
- Don't delete files until you're sure you have backups

**Using the saved data:**
- **PNG files**: Quick viewing, presentations, publications
- **TXT files**: Quantitative analysis, line profiles, Fourier transforms, filtering, reprocessing with different parameters

### Manual Command Interface

#### Command Text Box and Send Button

**What it does:**
Provides a way to send raw commands directly to the STM controller, bypassing the GUI controls. This is useful for advanced operations, debugging, testing, or accessing features not available through the GUI buttons.

**Why it's useful:**
Sometimes you need direct control or want to test specific commands. The manual interface lets you:
- Send custom commands not available in the GUI
- Test controller responses
- Debug communication issues
- Access advanced features
- Script custom operations

**How it works:**
Type your command in the text box (1 line, up to 30 characters). Click "Send" and the command is transmitted directly to the STM controller over the serial connection. The controller processes it and may send back a response (though responses aren't displayed in this simple interface).

**Command examples:**
- `GSTS` - Get status (same as automatic status polling)
- `BIAS 33314` - Set bias (same as Bias button)
- `STOP` - Stop current operation (same as STOP button)
- Custom commands specific to your controller firmware

**Important notes:**
- Commands must match the exact format expected by the controller
- Incorrect commands may be ignored or cause errors
- Use with caution - direct commands bypass safety checks
- Refer to your controller documentation for available commands
- This is mainly for advanced users and debugging

### Status Display

#### Status Label

**What it does:**
Displays a comprehensive, real-time summary of the STM system's current state. This is your "dashboard" showing all the key parameters and operational status at a glance.

**Why it's essential:**
The status display is your primary way to monitor what the STM is doing. It shows:
- **Bias**: Current bias voltage setting
- **Z, X, Y**: Current DAC values for all three axes (tip position)
- **ADC**: Current tunneling current measurement
- **STEPS**: Coarse approach motor position
- **Approaching**: Whether an approach sequence is active
- **ConstCurrent**: Whether constant current feedback is enabled
- **Scan**: Whether a scan is in progress
- **Time**: Timestamp of the status update

**How it works:**
Every 100 milliseconds (when the system isn't busy), the GUI queries the STM controller for status using the `GSTS` command. The controller responds with a comma-separated list of values, which are parsed and formatted into a human-readable string. This string is displayed in the status label, updating continuously.

**What to monitor:**
- **During approach**: Watch STEPS increase and ADC start to show current
- **During scanning**: Watch X and Y values change as the tip moves, and Scan status shows active
- **During IV measurement**: Watch Bias change as voltage is swept
- **For troubleshooting**: All values help diagnose issues - if values aren't changing when they should, there might be a communication or control problem

**Status format:**
The status is displayed as a multi-line text block showing all parameters clearly labeled. If the system is busy or not responding, it may show "No Updates" or the last known status.

**Using the status:**
- Quick check: Glance at status to see current operating mode
- Troubleshooting: Compare displayed values with expected values
- Monitoring: Watch for unexpected changes that might indicate problems
- Verification: Confirm commands were received (values should update after sending commands)

## PlotFrame Widget

All visualization widgets use a custom `PlotFrame` class that wraps matplotlib functionality:

### Features
- **Matplotlib Integration**: Uses `FigureCanvasTkAgg` for embedding plots
- **Toolbar**: Optional matplotlib navigation toolbar (zoom, pan, save, etc.)
- **Plot Support**: Line plots with auto-scaling axes
- **Image Support**: 2D image display with extent mapping
- **Update Methods**: 
  - `update_plot()`: Updates line plot data
  - `update_image()`: Updates image data
  - `save_figure()`: Saves plot/image to file

### Configuration
- **DPI**: 100.0 (for display)
- **Size**: 500x500 pixels (baseline_size)
- **Auto-layout**: Enabled for proper figure sizing

## Data Flow

### Real-Time Updates
1. **Status Polling**: Every 100ms, GUI requests status from STM
2. **History Buffer**: Status updates stored in deque (max 1000 entries)
3. **Plot Updates**: Current and steps plots updated from history
4. **Status Display**: Formatted status string displayed in label

### Scan Updates
1. **Scan Initiation**: User clicks "Scan" with parameters
2. **Thread Execution**: Scan runs in separate thread
3. **Data Reception**: Serial data parsed line-by-line
4. **Image Updates**: Scan arrays updated as data arrives
5. **Display Refresh**: Images redrawn every 100ms

### IV Curve Measurement
1. **User Trigger**: "PlotIV" button pressed
2. **Command Sent**: IV measurement command sent to STM
3. **Wait Period**: 2 second delay for measurement
4. **Data Retrieval**: IV curve data retrieved from STM
5. **Conversion**: DAC/ADC values converted to voltage/current
6. **Plot Update**: IV Curve plot updated with new data

## Window Behavior

- **Initial State**: Window opens maximized (`self.state('zoomed')`)
- **Title**: "Panda STM"
- **Layout**: Fixed grid layout with padding between elements
- **Responsive**: Plots auto-scale based on data range

## Key Conversions

### ADC to Current
```python
current = adc / 32768 * 10.24 / 100e6  # Amperes
```

### DAC to Voltage (Bias)
```python
bias_volts = -1.0 * (dac - 32768) / 32768 * 3.0  # Volts
```

### DAC to Voltage (Z/X/Y axes)
```python
volts = (dac - 32768) / 32768 * 10.0 / 2.0  # Volts
```

## Notes

- All plots include matplotlib toolbars for user interaction (zoom, pan, save)
- Scan operations run in separate threads to prevent GUI freezing
- Status updates are skipped when STM is busy with operations
- Default DAC center value is 32768 (midpoint of 16-bit range)
- All file saves include millisecond-precision timestamps
- The GUI maintains a history buffer of the last 1000 status updates for plotting

