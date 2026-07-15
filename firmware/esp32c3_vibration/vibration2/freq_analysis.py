import socket
import threading
import time
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

# Constants
UDP_PORT = 4210
BUFFER_SIZE = 1024
FFT_WINDOW_SECONDS = 1
MAX_LINES = 5000  # Prevent memory overflow
PLOT_UPDATE_INTERVAL = 1  # Plot refresh every 1 second

# Buffers for 3 channels and timestamps
channel_buffers = [deque(maxlen=MAX_LINES) for _ in range(3)]
timestamps = deque(maxlen=MAX_LINES)

def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', UDP_PORT))
    print(f"Listening on UDP port {UDP_PORT}")
    
    while True:
        data, _ = sock.recvfrom(BUFFER_SIZE)
        lines = data.decode('utf-8').split('\n')
        now = time.time()
        for line in lines:
            if not line.strip():
                continue
            try:
                values = list(map(float, line.strip().split(',')))
                if len(values) != 3:
                    continue
                for i in range(3):
                    channel_buffers[i].append(values[i])
                timestamps.append(now)
            except ValueError:
                continue

def calculate_sample_rate():
    now = time.time()
    recent = [t for t in timestamps if now - t <= 1.0]
    return len(recent)

def plot_fft():
    plt.ion()
    fig, axs = plt.subplots(3, 1, figsize=(10, 8))
    lines = [ax.plot([], [])[0] for ax in axs]

    for ax in axs:
        #ax.set_xlim(0, 200)  # Set fixed frequency range to 200 Hz
        #ax.set_ylim(auto=True)  # Let Y-axis auto-scale (handled below)
        ax.set_xlim(1, 200)  # Set fixed frequency range to 200 Hz
        ax.set_ylim(0,10)  # 
        ax.grid(True)

    while True:
        time.sleep(PLOT_UPDATE_INTERVAL)
        sample_rate = calculate_sample_rate()
        print(f"Sample rate: {sample_rate} Hz")

        if sample_rate < 2:
            continue

        n_samples = int(sample_rate * FFT_WINDOW_SECONDS)
        fft_data = []

        for i in range(3):
            data = list(channel_buffers[i])[-n_samples:]
            if len(data) < n_samples:
                fft_data.append(([], []))
                continue
            data = np.array(data) - np.mean(data)
            freqs = np.fft.rfftfreq(n_samples, 1.0 / sample_rate)
            fft_vals = np.abs(np.fft.rfft(data))
            fft_data.append((freqs, fft_vals))

        for i in range(3):
            freqs, fft_vals = fft_data[i]
            if len(freqs) == 0:
                continue
            lines[i].set_xdata(freqs)
            lines[i].set_ydata(fft_vals)
            axs[i].set_xlim(1, 200)  # Re-apply in case autoscale overwrites it
            axs[i].relim()
            axs[i].autoscale_view(scaley=True, scalex=False)
            if(i == 0):
                axs[i].set_title(f"Accelerometer X")
            if(i==1):
                axs[i].set_title(f"Accelerometer Y")
            if(i==2):
                axs[i].set_title(f"Accelerometer Z")


        fig.canvas.draw()
        fig.canvas.flush_events()


# Start threads
listener_thread = threading.Thread(target=udp_listener, daemon=True)
listener_thread.start()

plot_thread = threading.Thread(target=plot_fft, daemon=True)
plot_thread.start()

# Keep main thread alive
while True:
    time.sleep(1)
