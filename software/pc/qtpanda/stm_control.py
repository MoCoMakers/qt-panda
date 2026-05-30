import serial

import numpy as np
from dataclasses import dataclass
from collections import deque
import time
import logging
import threading

logger = logging.getLogger("stm")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s  %(message)s",
    datefmt="%H:%M:%S"
)

@dataclass
class STM_Status:
    bias: int = 0
    dac_z: int = 0
    dac_x: int = 0
    dac_y: int = 0
    adc: int = 0
    steps: int = 0
    is_approaching: bool = False
    is_const_current: bool = False
    is_scanning: bool = False
    time_millis: int = 0

    @staticmethod
    def from_list(values):
        return STM_Status(
            bias=values[0],
            dac_z=values[1],
            dac_x=values[2],
            dac_y=values[3],
            adc=values[4],
            steps=values[5],
            is_approaching=bool(values[6]),
            is_const_current=bool(values[7]),
            is_scanning=bool(values[8]),
            time_millis=values[9]
        )

    @staticmethod
    def parse_line(line: str):

        line = line.strip()
        if not line.startswith("STAT:"):
            raise ValueError("Invalid STM status line")

        payload = line[5:]
        parts = payload.split(",")
        if len(parts) != 10:
            raise ValueError(f"Expected 10 fields, got {len(parts)}")

        values = [int(x) for x in parts]

        return STM_Status.from_list(values)



    @staticmethod
    def adc_to_amp(adc: int):
        return 1.0 * adc / 32768 * 10.24 / 100e6

    @staticmethod
    def dac_to_dacz_volts(dac: int):
        return 1.0 * (dac - 32768) / 32768 * 10.0 / 2.0

    @staticmethod
    def dac_to_dacx_volts(dac: int):
        return 1.0 * (dac - 32768) / 32768 * 10.0 / 2.0

    @staticmethod
    def dac_to_dacy_volts(dac: int):
        return 1.0 * (dac - 32768) / 32768 * 10.0 / 2.0

    @staticmethod
    def dac_to_bias_volts(dac: int):
        return -1.0 * (dac - 32768) / 32768 * 3.0

    def to_string(self):
        return """STM Status:
Bias: {} 
Z: {} 
X: {} 
Y: {} 
ADC: {} 
STEPS: {}
Approaching: {}
ConstCurrent: {} 
Scan: {}  
Time: {}""".format(self.bias, self.dac_z, self.dac_x, self.dac_y, self.adc, self.steps, self.is_approaching,  self.is_const_current, self.is_scanning, self.time_millis)


class STM(object):
    def __init__(self, device=None):
        self.is_opened = False
        self.busy = False
        if device:
            self.open(device)

        self.status = STM_Status()
        self.hist_length = 1000
        #self.history = deque()
        self.scan_adc = None
        self.scan_dacz = None
        self.scan_noise = None
        self.receiving = False # is the thread running to listen

        self._cb = None # callback
        #pausing the RX thread:
        self.rx_pause_request = False
        self.rx_paused = False
        self.serial_lock = threading.Lock()


        self.scan_config = [0, 100, 10, 0, 100, 10]
        self.scan_adc = np.ones([512, 512], dtype=np.float32)
        self.scan_dacz = np.ones([512, 512], dtype=np.float32)
        self.scan_noise = np.ones([512, 512], dtype=np.float32)
        self.history = deque(maxlen=self.hist_length)

    def open(self, device): # start the data receive
        self.stm_serial = serial.Serial(device, 921600, timeout=1) # 921600 # 115200
        self.is_opened = True

        threading.Thread(
            target=self.receive_data,
            daemon=True
        ).start()

    def set_done_callback(self, cb):
        self._cb = cb;
        print("callback set")

    def pause_receive_thread(self, timeout=1.0):
        self.rx_pause_request = True
        start = time.time()
        while not self.rx_paused:
            if time.time() - start > timeout:
                raise TimeoutError("Failed to pause receive thread")
            time.sleep(0.001)

    def resume_receive_thread(self):
        self.rx_pause_request = False

    def get_status(self):
        if self.is_opened:
            try:
                self.send_cmd('GSTS')
            except:
                print('no response')
                #return self.history[-1]
                if len(self.history) > 0:
                    return self.history[-1]

                return STM_Status()
        else:
            self.status = STM_Status()
        return self.status

    def reset(self):
        self.send_cmd('RSET')
        self.clear()

    def test(self):
        self.send_cmd('TEST')

    def clear(self):
        self.history = deque(maxlen=self.hist_length)

    def send_cmd(self, cmd):
        if self.is_opened:
            self.stm_serial.write(cmd.encode())
            #logger.info(f"TX  {cmd}")

    def move_motor(self, steps):
        self.send_cmd(f'MTMV {steps}')

    def approach(self, target_dac, steps):
        self.send_cmd(f'APRH {target_dac} {steps}')

    def stop(self):
        self.send_cmd('STOP')


    def start_noise_scan(self,xres,yres,samples,uS):
        print("[CMD] Noise Scan")
        print(f"      xres = {xres}")
        print(f"      yres  = {yres}")
        print(f"      samples  = {samples}")
        print(f"      uS  = {uS}")
        self.send_cmd(f'NOIS {xres} {yres} {samples} {uS}')
        #self.busy = True
        self.scan_noise = np.ones([xres, yres], dtype=np.float32)
        #self.busy = True
        self.scan_config = [0, 65535, xres, 0, 65535, yres]

        return

    def measure_iv_curve(self, dac_start, dac_end, dac_step):
        self.send_cmd(f'IVME {dac_start} {dac_end} {dac_step}')
        # Wait for 0.1s for the STM to response
        time.sleep(1)
        return self.get_iv_curve()

    def get_iv_curve(self):
        bias = []
        current = []
        didv = []
        if self.is_opened:
            self.pause_receive_thread()
            self.send_cmd('IVGE')   # or whatever command triggers send_iv_didv_curve()
            data_str = self.stm_serial.readline().decode().strip()
            logger.info(f"RX  {data_str}")
            data = data_str.split(',')
            if data[0] == "IVD":
                try:
                    N = int(data[1])
                    values = [int(x) for x in data[2:]]

                    # Expect 3 values per point
                    if len(values) == 3 * N:
                        bias = np.array(values[0::3])
                        current = np.array(values[1::3])
                        didv = np.array(values[2::3])
                    else:
                        print("Unexpected IVD data length")

                except Exception as e:
                    print("IVD parse error:", e)

        self.busy = False
        self.resume_receive_thread()
        print("Bias:", bias)
        print("Current:", current)
        print("dIdV:", didv)
        return bias, current, didv

    def measure_dIdZ_curve(self, dac_start, dac_end, dac_step):
        self.send_cmd(f'DIME {dac_start} {dac_end} {dac_step}')
        # Wait for 0.1s for the STM to response
        time.sleep(2)
        return self.get_dIdZ_curve()

    def get_dIdZ_curve(self):
        dIdZ_curve_values = [0, 0]
        if self.is_opened:
            # self.busy = True
            self.pause_receive_thread()
            time.sleep(1)
            self.send_cmd('DIGE')
            data_str = self.stm_serial.readline().decode()
            logger.info(f"RX  {data_str}")
            data = data_str.split(',')
            if data[0] == "DI":
                dIdZ_curve_values = [int(x) for x in data[1:]]
        # self.busy = False
        self.resume_receive_thread()
        print(dIdZ_curve_values)
        return dIdZ_curve_values

    def set_sample_interval(self,value):
        self.send_cmd(f"SINT {value}")
        print(f"SINT {value}")

    def set_scan_mode(self,value):
        self.send_cmd(f"SMOD {value}")
        print(f"SMOD {value}")

    def set_bias(self, value):
        self.send_cmd(f"BIAS {value}")

    def set_dacz(self, value):
        self.send_cmd(f"DACZ {value}")

    def set_dacx(self, value):
        self.send_cmd(f"DACX {value}")

    def set_dacy(self, value):
        self.send_cmd(f"DACY {value}")

    def turn_on_const_current(self, target_adc):
        self.send_cmd(f"CCON {target_adc}")

    def turn_off_const_current(self):
        self.send_cmd(f"CCOF")

    def set_pid(self, Kp, Ki, Kd):
        self.send_cmd(f"PIDS {Kp} {Ki} {Kd}")

    def set_settle(self, x,y,z,bias):
        self.send_cmd(f"SETL {x} {y} {z} {bias}")

    # Receive and parse data
    def _process_full_line_data(self, full_line):
        logger.info(f"RX  {full_line}")
        line = full_line.strip()
        data = line.split(',')
        data_type = data[0]
        # ADC scan line
        if data_type == "A":
            x_i = int(data[1])
            values = [int(x) for x in data[2:]]
            self.scan_adc[x_i, :] = values
            return True
        # Z scan line
        if data_type == "Z":
            x_i = int(data[1])
            values = [int(x) for x in data[2:]]
            self.scan_dacz[x_i, :] = values
            return True
        # Noise scan line
        if data_type == "N":
            x_i = int(data[1])
            values = [int(x) for x in data[2:]]
            self.scan_noise[x_i, :] = values
            return True
        # Status update
        if line.startswith("STAT:"):
            self.status = STM_Status.parse_line(line)
            self.history.append(self.status)
            return True
        # dIdZ curve
        if line.startswith("DI"):
            self.didz_curve_values = [int(x) for x in data[1:]]
            return True        
        # Scan done
        if data_type == "D":            
            self.busy = False            
            if self._cb is not None:
                self._cb()
            return True
        # Unknown packet
        logger.warning(f"Unknown packet: {line}")
        return False

    def receive_data(self):
        """Background serial receive thread."""
        self.receiving = True
        rx_buffer = ""
        logger.info("STM receive thread started")

        while self.receiving:
            try:
                if self.rx_pause_request:
                    self.rx_paused = True

                    while self.rx_pause_request:
                        time.sleep(0.001)

                    self.rx_paused = False

                # Read available bytes
                bytes_waiting = self.stm_serial.in_waiting
                # Prevent CPU spin
                if bytes_waiting == 0: # nothing to read or we're not listening
                    time.sleep(0.001)
                    continue
                # Read and decode incoming data
                incoming = self.stm_serial.read(bytes_waiting)
                incoming_text = incoming.decode(errors='ignore')
                # Append to persistent buffer
                rx_buffer += incoming_text
                # Process all complete lines
                while '\n' in rx_buffer:
                    # Split one line from buffer
                    line, rx_buffer = rx_buffer.split('\n', 1)
                    # Normalize line endings
                    line = line.strip()
                    # Ignore empty lines
                    if not line:
                        continue

                    try:
                        # Parse line
                        self._process_full_line_data(line)
                    except Exception as parse_error:
                        logger.exception(
                            f"STM parse error:\n{line}\n{parse_error}"
                        )

            except serial.SerialException as serial_error:
                logger.exception(
                    f"STM serial exception: {serial_error}"
                )
                self.receiving = False
                self.is_opened = False
                break
            except Exception as thread_error:
                logger.exception(
                    f"STM receive thread exception: {thread_error}"
                )
                time.sleep(0.01)
        logger.info("STM receive thread stopped")

    # start continous scan
    def start_scan_cont(self, x_start, x_end, x_resolution, y_start, y_end, y_resolution, sample_number):
        # self.busy = True
        self.scan_config = [x_start, x_end,
                            x_resolution, y_start, y_end, y_resolution]
        self.send_cmd(
            f"SCCT {x_start} {x_end} {x_resolution} {y_start} {y_end} {y_resolution} {sample_number}")

        # zero out the data to begin
        self.scan_adc = np.ones([x_resolution, y_resolution], dtype=np.float32)
        self.scan_dacz = np.ones([x_resolution, y_resolution], dtype=np.float32)

        #current_line = ''

    # for both the notmal scan and continuous scan, we use the threaded receive function to get and parse the data
    def start_scan(self, x_start, x_end, x_resolution, y_start, y_end, y_resolution, sample_number):
        # self.busy = True
        self.scan_config = [x_start, x_end,
                            x_resolution, y_start, y_end, y_resolution]
        self.send_cmd(
            f"SCST {x_start} {x_end} {x_resolution} {y_start} {y_end} {y_resolution} {sample_number}")

        self.scan_adc = np.ones([x_resolution, y_resolution], dtype=np.float32)
        self.scan_dacz = np.ones([x_resolution, y_resolution], dtype=np.float32)
        return

    def startGridSpectroscopy(self,
                               x_start, x_end, x_resolution,
                               y_start, y_end, y_resolution,
                               bias_start, bias_end,
                               bias_points, mode, progress_callback=None):

        if not self.is_opened:
            return None

        self.busy = True
        self.pause_receive_thread()

        # ---- Send command to firmware ----
        self.send_cmd(
            f'GSPC {x_start} {x_end} {x_resolution} '
            f'{y_start} {y_end} {y_resolution} '
            f'{bias_start} {bias_end} {bias_points} {mode}'
        )

        # ---- Allocate 3D data cube ----
        # grid_data[x, y, bias]
        grid_data = np.zeros(
            (x_resolution, y_resolution, bias_points),
            dtype=np.uint16
        )

        total_pixels = x_resolution * y_resolution
        received_pixels = 0

        print("Receiving grid spectroscopy data...")

        while received_pixels < total_pixels:

            # ---- Wait for sync bytes 'P','X' ----
            while True:
                byte = self.stm_serial.read(1)
                if byte == b'P':
                    second = self.stm_serial.read(1)
                    if second == b'X':
                        break

            # ---- Read header (remaining 7 bytes) ----
            header = self.stm_serial.read(7)

            x_i = int.from_bytes(header[0:2], 'little')
            y_i = int.from_bytes(header[2:4], 'little')
            pts = int.from_bytes(header[4:6], 'little')
            rx_mode = header[6]

            # ---- Safety checks ----
            if pts != bias_points:
                print("Bias point mismatch!")
                break

            # ---- Read spectral data ----
            data_bytes = self.stm_serial.read(2 * pts)

            spectrum = np.frombuffer(data_bytes, dtype=np.uint16)

            # ---- Store ----
            if x_i < x_resolution and y_i < y_resolution:
                grid_data[x_i, y_i, :] = spectrum

            received_pixels += 1

            if received_pixels % 100 == 0:
                print(f"{received_pixels}/{total_pixels} pixels received")
                if progress_callback:
                    progress = int((received_pixels / total_pixels) * 100)
                    progress_callback(progress)

        self.busy = False
        self.resume_receive_thread()

        print("Grid Spectroscopy Complete")

        return grid_data
