from datetime import datetime
import tkinter as tk
from tkinter import ttk
import numpy as np
import stm_control
import time
import csv
import threading
import platform


from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})
# Teensy port detection is provided by stm_control.find_teensy_port()


def save_data_to_file(filename_prefix, data_to_store: list):
    current_time_stamp = datetime.now()
    # getting the timestamp
    ts = int(datetime.timestamp(current_time_stamp)*1000)
    with open(f"{filename_prefix}_{ts}.csv", 'w', newline='') as csvfile:
        # Writing data to a file
        datawriter = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for data in data_to_store:
            datawriter.writerow(data)


class PlotFrame(ttk.Frame):
    def __init__(self, parent, with_toobar=False,  dpi=300.0, width=400, height=400, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.figure = Figure(figsize=(width / dpi*0.8,
                                      height / dpi*0.8), dpi=dpi)

        # Drawing area
        self.canvas = FigureCanvasTkAgg(
            self.figure, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(
            side='top', fill='both', expand=True)

        if with_toobar:
            self.toolbar = NavigationToolbar2Tk(
                self.canvas, self)
            self.toolbar.update()
            self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def add_plot(self, label=None, xlabel=None, ylabel=None,):
        self.plot = self.figure.add_subplot(
            111).plot([0, 1], [0, 0], '-', label=label)[0]
        real_time_plot_ax = self.figure.get_axes()[0]
        real_time_plot_ax.set_autoscalex_on(True)
        real_time_plot_ax.set_autoscaley_on(True)
        real_time_plot_ax.legend(loc='upper right')
        if xlabel:
            real_time_plot_ax.set(xlabel=xlabel)
        if ylabel:
            real_time_plot_ax.set(ylabel=ylabel)

    def add_image(self, image):
        self.image = self.figure.add_subplot(
            111).imshow(image, interpolation='none', norm='linear', origin="lower")

    def set_yscale(self, scale_type='linear', symlog_linthresh=1e-10):
        """Set Y-axis scale to linear or symlog.
        
        Args:
            scale_type: 'linear' or 'symlog'
            symlog_linthresh: threshold for symlog scale (default 1e-10)
        """
        ax = self.figure.get_axes()[0]
        if scale_type == 'symlog':
            ax.set_yscale('symlog', linthresh=symlog_linthresh)
        else:
            ax.set_yscale('linear')
        # Enable autoscaling on Y-axis after changing scale
        ax.set_autoscaley_on(True)
        ax.relim()
        ax.autoscale_view()
        self.canvas.draw()
        self.canvas.flush_events()

    def set_xaxis_range(self, x_min=None, x_max=None):
        """Set X-axis range.
        
        Args:
            x_min: minimum X value (None for auto)
            x_max: maximum X value (None for auto)
        """
        ax = self.figure.get_axes()[0]
        if x_min is not None and x_max is not None:
            ax.set_xlim(x_min, x_max)
            ax.set_autoscalex_on(False)
        else:
            ax.set_autoscalex_on(True)
            ax.relim()
        ax.autoscale_view()
        self.canvas.draw()
        self.canvas.flush_events()

    def update_plot(self, x_data, y_data):
        self.plot.set_xdata(x_data)
        self.plot.set_ydata(y_data)
        ax = self.figure.get_axes()[0]
        # Ensure autoscaling is enabled for both axes
        ax.set_autoscalex_on(True)
        ax.set_autoscaley_on(True)
        ax.relim()
        ax.autoscale_view()
        # We need to draw *and* flush
        self.canvas.draw()
        self.canvas.flush_events()

    def update_image(self, image_data, extend=None):
        self.image.set_data(image_data)
        self.image.autoscale()
        if extend:
            self.image.set_extent(extend)
        # ax = self.figure.get_axes()[0]
        # ax.relim()
        # ax.autoscale_view()
        # We need to draw *and* flush
        self.canvas.draw()
        self.canvas.flush_events()

    def save_figure(self, image_path):
        self.figure.savefig(image_path)


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Init STM
        # STM configs
        self.stm = stm_control.STM()

        self.wm_title("QT-Panda STM")
        self.baseline_size = 500 # changed from 700

        self.image_frame = ttk.Frame(
            self, width=self.baseline_size * 2, height=self.baseline_size * 2)
        self.image_frame.grid(row=0, column=1, padx=10, pady=5)

        # Image frame settings
        self.real_time_current_plot_frame = PlotFrame(
            self.image_frame, dpi=100.0, with_toobar=True, width=self.baseline_size, height=self.baseline_size)
        self.real_time_current_plot_frame.add_plot(
            label="current", xlabel='time(s)', ylabel='adc')
        self.real_time_current_plot_frame.grid(
            row=0, column=0, padx=10, pady=5)

        # Add radio button controls for Y-scale selection (ADC plot)
        self.adc_yscale_var = tk.StringVar(value='linear')
        adc_scale_frame = ttk.LabelFrame(self.image_frame, text="ADC Y-Scale")
        adc_scale_frame.grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        
        linear_radio = ttk.Radiobutton(
            adc_scale_frame, text="Linear", variable=self.adc_yscale_var, 
            value='linear', command=lambda: self.real_time_current_plot_frame.set_yscale('linear'))
        linear_radio.grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        
        symlog_radio = ttk.Radiobutton(
            adc_scale_frame, text="SymLog (±1e-10)", variable=self.adc_yscale_var, 
            value='symlog', command=lambda: self.real_time_current_plot_frame.set_yscale('symlog', symlog_linthresh=1e-10))
        symlog_radio.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        # Add X-axis range controls for ADC plot
        self.adc_xrange_var = tk.StringVar(value='all')
        adc_xrange_frame = ttk.LabelFrame(self.image_frame, text="ADC X-Range")
        adc_xrange_frame.grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
        
        all_radio = ttk.Radiobutton(
            adc_xrange_frame, text="All", variable=self.adc_xrange_var,
            value='all', command=lambda: self.real_time_current_plot_frame.set_xaxis_range(None, None))
        all_radio.grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        
        ttk.Label(adc_xrange_frame, text="Last (s):").grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        
        self.adc_xrange_last_var = tk.StringVar(value="10")
        xrange_entry = ttk.Entry(adc_xrange_frame, textvariable=self.adc_xrange_last_var, width=8)
        xrange_entry.grid(row=0, column=2, padx=2, pady=2, sticky=tk.W)
        
        last_radio = ttk.Radiobutton(
            adc_xrange_frame, text="Range", variable=self.adc_xrange_var,
            value='last', command=self._update_adc_xrange)
        last_radio.grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)
        
        # Bind entry field to update range when text changes
        xrange_entry.bind('<Return>', lambda e: self._update_adc_xrange())

        self.real_time_steps_plot_frame = PlotFrame(
            self.image_frame, dpi=100.0,  with_toobar=True, width=self.baseline_size, height=self.baseline_size)
        self.real_time_steps_plot_frame.add_plot(label="steps")
        self.real_time_steps_plot_frame.grid(
            row=0, column=1, padx=10, pady=5)

        # Image area for iv curve
        self.iv_curve_frame = PlotFrame(
            self.image_frame, dpi=100.0,  with_toobar=True, width=self.baseline_size, height=self.baseline_size)
        self.iv_curve_frame.add_plot(
            label="IVCurve", xlabel="Bias", ylabel="ADC")
        self.iv_curve_frame.grid(row=1, column=1, padx=10, pady=5)

        # Image area for scan image
        # Image frame settings
        self.scan_dacz_frame = PlotFrame(
            self.image_frame, dpi=100.0, with_toobar=True, width=self.baseline_size, height=self.baseline_size)
        init_image = np.random.rand(10, 10)
        self.scan_dacz_frame.add_image(init_image)
        self.scan_dacz_frame.grid(row=0, column=2, padx=10, pady=5)

        self.scan_adc_frame = PlotFrame(
            self.image_frame, dpi=100.0, with_toobar=True, width=self.baseline_size, height=self.baseline_size)
        init_image = np.random.rand(10, 10)
        self.scan_adc_frame.add_image(init_image)
        self.scan_adc_frame.grid(row=1, column=2, padx=10, pady=5)

        self._update_images()

        # Control pannels
        # Create left and right frames for control and display
        row_number = 0
        self.control_frames = ttk.Frame(
            self, width=self.baseline_size, height=self.baseline_size * 2)
        self.control_frames.grid(
            row=row_number, column=0, padx=10, pady=5, sticky=tk.NW)

        button_frame = ttk.Frame(self.control_frames)
        button_frame.grid(row=row_number, column=0, sticky=tk.W)

        class _DAC_Control(tk.Frame):
            def __init__(self, parent, text, default_value, cmd_func, convert_func, *args, **kwargs):
                super().__init__(parent, *args, **kwargs)
                self.cmd_func = cmd_func
                self.convert_func = convert_func
                self.input_string_var = tk.StringVar()
                self.input_string_var.initialize(default_value)
                self.input_entry = tk.Entry(
                    self, textvariable=self.input_string_var, width=15)
                self.input_entry.grid(
                    row=0, column=1, columnspan=1)

                self.display_var = tk.StringVar()
                self._update_display(default_value)

                self.display = tk.Label(self, textvariable=self.display_var)
                self.display.grid(row=0, column=2)
                self.button = ttk.Button(
                    master=self, text=text, command=self.set_value)
                self.button.grid(row=0, column=0)

            def _update_display(self, value):
                self.display_var.set(
                    str(self.convert_func(int(value))))

            def set_value(self):
                target = self.input_string_var.get()
                self.cmd_func(int(target))
                self._update_display(target)

        class _ButtonWithEntry(tk.Frame):
            def __init__(self, parent, text, default_value_list, cmd_func, display_list=None, entry_width=15, *args, **kwargs):
                super().__init__(parent, *args, **kwargs)
                self.input_string_var_list = []
                self.input_entry_list = []
                self.cmd_func = cmd_func
                row_button = 1 if display_list else 0
                for i in range(len(default_value_list)):
                    if display_list and display_list[i]:
                        label = ttk.Label(master=self, text=display_list[i])
                        label.grid(row=0, column=i+1, sticky=tk.W)
                    input_string_var = tk.StringVar()
                    input_string_var.initialize(default_value_list[i])
                    input_entry = tk.Entry(
                        self, textvariable=input_string_var, width=entry_width)
                    input_entry.grid(
                        row=row_button, column=i+1, columnspan=1)
                    self.input_string_var_list.append(input_string_var)
                    self.input_entry_list.append(input_entry)

                button = ttk.Button(
                    master=self, text=text, command=self._set_values)
                button.grid(row=row_button, column=0)

            def _set_values(self):
                values = []
                for i in range(len(self.input_string_var_list)):
                    target = self.input_string_var_list[i].get()
                    values.append(target)
                self.cmd_func(*values)

        class _MultipleButtons(tk.Frame):
            def __init__(self, parent, text_list, func_list, *args, **kwargs):
                super().__init__(parent, *args, **kwargs)
                for i in range(len(text_list)):
                    button = ttk.Button(
                        master=self, text=text_list[i], command=func_list[i])
                    button.grid(row=0, column=i)

        class _ScanControl(tk.Frame):
            def __init__(self, parent, cmd_func, *args, **kwargs):
                super().__init__(parent, *args, **kwargs)
                var_list = []

                def _create_entry(default_value, row, col):
                    input_string_var = tk.StringVar()
                    input_string_var.initialize(default_value)
                    input_entry = tk.Entry(
                        self, textvariable=input_string_var)
                    input_entry.grid(
                        row=row, column=col)
                    return input_string_var

                for row in range(2):
                    start_var = _create_entry("31768", row, 0)
                    end_var = _create_entry("33768", row, 1)
                    interval_var = _create_entry("512", row, 2)
                    var_list += [start_var, end_var, interval_var]
                sample_num_var = _create_entry("10", 2, 1)
                var_list += [sample_num_var]

                def _set_values():
                    values = []
                    for var in var_list:
                        target = int(var.get())
                        values.append(target)
                    cmd_func(*values)
                # Control Button
                button = ttk.Button(
                    master=self, text="Scan", command=_set_values)
                button.grid(row=2, column=0, sticky=tk.W)

        # Try to auto-detect Teensy port; fallback to empty string if not found
        detected_port = stm_control.find_teensy_port()
        open_default = detected_port if detected_port is not None else ""

        # Status variable/label to show detection and open result. We do not
        # auto-open the port; the user must press Open. The Open button will
        # call `_open_cmd` which updates this label on success/failure.
        try:
            if detected_port:
                detect_text = f"Teensy detected"
                detect_fg = 'green'
            else:
                detect_text = "Teensy not detected"
                detect_fg = 'red'
        except Exception:
            detect_text = "Teensy detection error"
            detect_fg = 'red'

        detect_var = tk.StringVar(value=detect_text)
        detect_label = ttk.Label(button_frame, textvariable=detect_var, foreground=detect_fg)

        def _open_cmd(port_str):
            # Called by the Open button (from _ButtonWithEntry). Update label
            # to reflect success/failure.
            try:
                port = port_str if port_str else None
                if not port:
                    detect_var.set("No port specified")
                    detect_label.config(foreground='orange')
                    return
                self.stm.open(port)
                detect_var.set(f"")
                detect_label.config(foreground='green')
            except Exception as e:
                detect_var.set(f"Open failed: {e}")
                detect_label.config(foreground='red')

        open_frame = _ButtonWithEntry(button_frame, "Open", [open_default], _open_cmd)
        open_frame.grid(row=row_number, column=0, pady=5, padx=0, sticky=tk.W)

        # Move Scan control and detection label to the row below the Open
        # control. Use `_ButtonWithEntry` for the Scan button to keep the
        # control styling consistent.

        def _scan_ports():
            try:
                port = stm_control.find_teensy_port()
                if port:
                    detect_var.set(f"Teensy detected, not opened")
                    detect_label.config(foreground='green')
                    # Update the Open entry's first input var if available
                    try:
                        var = open_frame.input_string_var_list[0]
                        try:
                            var.set(port)
                        except Exception:
                            try:
                                var.initialize(port)
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    detect_var.set("Teensy not detected")
                    detect_label.config(foreground='red')
            except Exception as e:
                detect_var.set(f"Scan error: {e}")
                detect_label.config(foreground='red')

        scan_frame = _ButtonWithEntry(button_frame, "Scan Ports", [], _scan_ports, display_list=[detect_label])
        scan_frame.grid(row=row_number+1, column=0, pady=0, padx=0, sticky=tk.W)

        # place the detect label on the same new row on the right side
        detect_label.grid(row=row_number+1, column=1, padx=8, sticky=tk.W)

        # Make layout responsive: allow detection label to expand/wrap on narrow widths
        try:
            button_frame.columnconfigure(0, weight=0)
            button_frame.columnconfigure(1, weight=0)
            button_frame.columnconfigure(2, weight=1)
        except Exception:
            pass

        def _update_wrap(event=None):
            try:
                # Give detect_label a wraplength so it wraps on narrow windows
                total_w = button_frame.winfo_width() or 300
                # reserve ~220px for the Open control + Scan button
                wrap = max(80, total_w - 220)
                detect_label.config(wraplength=wrap)
            except Exception:
                pass

        # Update wrap initially and on resize
        _update_wrap()
        button_frame.bind('<Configure>', _update_wrap)

        row_number += 2

        _stop_rest_clear = _MultipleButtons(button_frame, ["STOP", "Reset", "Clear"], [
                                            self.stm.stop, self.stm.reset, self.stm.clear])
        _stop_rest_clear.grid(row=row_number, column=0,
                              sticky=tk.W)
        row_number += 1

        # Set Bias
        bias_control = _DAC_Control(
            button_frame, "Bias", "33314", self.stm.set_bias, stm_control.STM_Status.dac_to_bias_volts)
        bias_control.grid(row=row_number, column=0,
                          sticky=tk.W, pady=5)
        row_number += 1
        dacz_control = _DAC_Control(
            button_frame, "DACZ", "32768", self.stm.set_dacz, stm_control.STM_Status.dac_to_dacz_volts)
        dacz_control.grid(row=row_number, column=0, pady=5,
                          sticky=tk.W)
        row_number += 1
        dacx_control = _DAC_Control(
            button_frame, "DACX", "32768", self.stm.set_dacx, stm_control.STM_Status.dac_to_dacx_volts)
        dacx_control.grid(row=row_number, column=0, pady=5,
                          sticky=tk.W)
        row_number += 1
        dacy_control = _DAC_Control(
            button_frame, "DACY", "32768", self.stm.set_dacy, stm_control.STM_Status.dac_to_dacy_volts)
        dacy_control.grid(row=row_number, column=0, pady=5,
                          sticky=tk.W)
        row_number += 1
        # Set DACZ

        def _set_all_dac():
            bias_control.set_value()
            time.sleep(0.01)
            dacz_control.set_value()
            time.sleep(0.01)
            dacx_control.set_value()
            time.sleep(0.01)
            dacy_control.set_value()
            time.sleep(0.01)

        # Set All DACs
        set_all_dac_button = ttk.Button(
            master=button_frame, text="SetAllDAC", command=_set_all_dac)
        set_all_dac_button.grid(row=row_number, column=0, pady=5, sticky=tk.W)
        row_number += 1

        # Approach
        # Set Approach
        approach_frame = _ButtonWithEntry(button_frame,  "Approach", [
                                          "500", "1"],  self.stm.approach)
        approach_frame.grid(row=row_number, column=0, pady=5,
                            sticky=tk.W)
        row_number += 1

        # Create a IV Curve Scan control
        iv_curve_frame = _ButtonWithEntry(button_frame,  "PlotIV", [
                                          "31768", "33768", "10"], self._plot_iv_curve)
        iv_curve_frame.grid(row=row_number, column=0, pady=5,
                            sticky=tk.W)
        row_number = row_number + 1

        # Store the IV Curve to a file
        def _save_iv_curve(filename_prefix):
            iv_curve_values = self.stm.get_iv_curve()
            x_value = iv_curve_values[::2]
            y_value = iv_curve_values[1::2]
            save_data_to_file(filename_prefix, zip(x_value, y_value))

        save_curve_frame = _ButtonWithEntry(button_frame,  "Save", [
            "./data/iv_curve_"], _save_iv_curve, entry_width=25)
        save_curve_frame.grid(row=row_number, column=0, pady=5,
                              sticky=tk.W)
        row_number = row_number + 1

        # Const Current Mode
        # Setup PID Values
        row_number += 1
        pid_frame = _ButtonWithEntry(button_frame,  "SetPID", [
            "0.0001", "0.0001", "0.0"], self.stm.set_pid, display_list=["Kp", "Ki", "Kd"])
        pid_frame.grid(row=row_number, column=0, pady=5,
                       sticky=tk.W)
        row_number = row_number + 1
        # Control const current mode
        start_cons_current_frame = _ButtonWithEntry(button_frame,  "ConstCurrentOn", [
            "1000"], self.stm.turn_on_const_current)
        start_cons_current_frame.grid(row=row_number, column=0, pady=5,
                                      sticky=tk.W)
        row_number = row_number + 1
        stop_cons_current_frame = _ButtonWithEntry(
            button_frame,  "ConstCurrentOFF", [], self.stm.turn_off_const_current)
        stop_cons_current_frame.grid(row=row_number, column=0, pady=5,
                                     sticky=tk.W)
        row_number = row_number + 1

        # Scan start button
        def _scan_and_plot(*arg):
            scan_thread = threading.Thread(
                target=self.stm.start_scan, args=arg)
            scan_thread.start()
            print("Updated")

        scan_button_frame = _ScanControl(
            button_frame, _scan_and_plot)
        scan_button_frame.grid(row=row_number, column=0, pady=5,
                               sticky=tk.W)
        row_number = row_number + 1

        # Store the Scan Images to files
        def _save_scan_image(image_path_prefix):
            current_time_stamp = datetime.now()
            # getting the timestamp
            ts = int(datetime.timestamp(current_time_stamp)*1000)
            np.savetxt(f"{image_path_prefix}_adc_{ts}.txt", self.stm.scan_adc)
            np.savetxt(f"{image_path_prefix}_dacz_{ts}.txt",
                       self.stm.scan_dacz)
            self.scan_adc_frame.save_figure(
                f"{image_path_prefix}_adc_{ts}.png")
            self.scan_dacz_frame.save_figure(
                f"{image_path_prefix}_dacz_{ts}.png")

        save_image_frame = _ButtonWithEntry(button_frame,  "Save", [
            "./data/image"], _save_scan_image, entry_width=25)
        save_image_frame.grid(row=row_number, column=0, pady=5,
                              sticky=tk.W)
        row_number = row_number + 1

        # Add command and send
        # Create text widget and specify size.
        cmd_text_box = tk.Text(button_frame, height=1, width=30)
        cmd_text_box.grid(row=row_number, column=0, pady=5)

        def _send_cmd():
            cmd = cmd_text_box.get("1.0", tk.END)
            self.stm.send_cmd(cmd)
        row_number += 1
        send_button = ttk.Button(
            master=button_frame, text="Send", command=_send_cmd)
        send_button.grid(row=row_number, column=0)

        # Area for showing status
        self.status_frame = ttk.Frame(self.control_frames)
        self.status_frame.grid(row=1, column=0)

        self.status_label = ttk.Label(self.status_frame,
                                      text="No Updates", relief=tk.RAISED)
        self.status_label.grid(row=0, column=0)

        self._update_real_time()
        # Default put the windows to be largest.
        # Maximize window based on the operating system
        if platform.system().lower() == "windows":
            self.state('zoomed')
        else: # Assume Linux/maxOS for other cases
            self.attributes('-zoomed', True)

    def _quit(self):
        self.quit()     # stops mainloop
        self.destroy()  # this is necessary on Windows to prevent
        # Fatal Python Error: PyEval_RestoreThread: NULL tstate

    def _reset(self):
        self.stm.reset()

    def _update_adc_xrange(self):
        """Update ADC plot X-axis range based on the selected mode."""
        if self.adc_xrange_var.get() == 'all':
            self.real_time_current_plot_frame.set_xaxis_range(None, None)
        else:  # 'last'
            try:
                last_seconds = float(self.adc_xrange_last_var.get())
                if last_seconds > 0:
                    x_max = 0  # current time is always at 0 in our relative scaling
                    x_min = -last_seconds
                    self.real_time_current_plot_frame.set_xaxis_range(x_min, x_max)
            except ValueError:
                # Invalid input, ignore
                pass

    def _update_real_time(self):
        if not self.stm.busy:
            status = self.stm.get_status()
            plot_x = [hist.time_millis for hist in self.stm.history]
            self.status_label.config(text=status.to_string())
            max_time = max(plot_x)
            plot_x = [(x - max_time) / self.baseline_size *
                      2.0 for x in plot_x]
            plot_adc = [stm_control.STM_Status.adc_to_amp(
                hist.adc) for hist in self.stm.history]
            plot_steps = [hist.steps for hist in self.stm.history]

            self.real_time_current_plot_frame.update_plot(plot_x, plot_adc)
            self.real_time_steps_plot_frame.update_plot(plot_x, plot_steps)
            
            # Apply X-axis range setting to ADC plot
            if self.adc_xrange_var.get() == 'last':
                self._update_adc_xrange()
        self.after(100, self._update_real_time)

    def _update_images(self):
        x_start, x_end, x_resolution, y_start, y_end, y_resolution = self.stm.scan_config
        self.scan_adc_frame.update_image(self.stm.scan_adc, extend=[
            y_start, y_end, x_start, x_end])
        self.scan_dacz_frame.update_image(
            self.stm.scan_dacz, [y_start, y_end, x_start, x_end])
        self.after(100, self._update_images)

    def _plot_iv_curve(self, *args):
        iv_curve_values = self.stm.measure_iv_curve(*args)
        x_value = iv_curve_values[::2]
        y_value = iv_curve_values[1::2]
        current = [stm_control.STM_Status.adc_to_amp(adc) for adc in y_value]
        bias = [stm_control.STM_Status.dac_to_bias_volts(
            dac) for dac in x_value]
        self.iv_curve_frame.update_plot(bias, current)


# If you put root.destroy() here, it will cause an error if the window is
# closed with the window manager.
if __name__ == "__main__":
    app = App()
    app.mainloop()
