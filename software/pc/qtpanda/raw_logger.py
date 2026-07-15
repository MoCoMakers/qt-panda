"""raw_logger — disk capture of RAWD raw ISR-tap blocks (roadmap R1).

The firmware's 'R' frames carry every ISR sample (adc, z, err) at up to
25 kHz.  This module writes each block to disk verbatim, ahead of any GUI
fan-out, and reads them back for analysis.  Qt-free.

File pair per capture:
  <base>.raw  — binary, little-endian block records:
        magic 'R' (1B) | pc_time f64 | seq u16 | count u16
        | t0_millis u32 | dropped_samples u32
        | count * (adc i16, z i32, err i32)   [big-endian, as received]
  <base>.json — sidecar: decimation, sample rate, settings; finalized at stop
        with block/sample/drop totals.

Gap detection: firmware sequence numbers are contiguous mod 65536; any jump
is counted.  The firmware also reports its own cumulative dropped-sample
counter in every block header — both are surfaced, never silent.
"""
import json
import os
import struct
import time

import numpy as np

import session_journal
from serial_reader import RAW_DTYPE

_REC_HEAD = struct.Struct('<BdHHII')  # magic, pc_time, seq, count, t0, dropped
_MAGIC = 0x52


class RawLogger:
    def __init__(self, log_dir="raw"):
        self.log_dir = log_dir
        self._f = None
        self.base_path = None
        self._sidecar = None
        self.n_blocks = 0
        self.n_samples = 0
        self.fw_dropped = 0           # firmware's own cumulative counter
        self.seq_gaps = 0             # missing blocks by sequence number
        self._last_seq = None

    def start(self, meta=None):
        self.stop()
        os.makedirs(self.log_dir, exist_ok=True)
        base = os.path.join(self.log_dir, f"raw_{int(time.time() * 1000)}")
        self.base_path = base
        self._f = open(base + ".raw", "ab")
        self.n_blocks = 0
        self.n_samples = 0
        self.fw_dropped = 0
        self.seq_gaps = 0
        self._last_seq = None
        self._sidecar = {
            "t_start": time.time(),
            "meta": meta or {},
            "sample_layout": "big-endian interleaved (adc i16, z i32, err i32)",
        }
        self._write_sidecar()
        session_journal.record("raw_capture_start", path=base + ".raw")
        return base + ".raw"

    def stop(self):
        if self._f is None:
            return None
        path = self.base_path + ".raw"
        try:
            self._f.close()
        except OSError:
            pass
        self._f = None
        self._sidecar.update({
            "t_end": time.time(),
            "n_blocks": self.n_blocks,
            "n_samples": self.n_samples,
            "fw_dropped_samples": self.fw_dropped,
            "seq_gap_blocks": self.seq_gaps,
        })
        self._write_sidecar()
        session_journal.record("raw_capture_stop", path=path)
        return path

    def is_active(self):
        return self._f is not None

    def status(self):
        return {
            "active": self.is_active(),
            "path": (self.base_path + ".raw") if self.base_path else None,
            "blocks": self.n_blocks,
            "samples": self.n_samples,
            "fw_dropped_samples": self.fw_dropped,
            "seq_gap_blocks": self.seq_gaps,
        }

    def _write_sidecar(self):
        with open(self.base_path + ".json", "w") as f:
            json.dump(self._sidecar, f, indent=2)

    # -- per-block sink (connect to SerialReaderThread.rawBlock) -----------
    def on_block(self, seq, t0, dropped, samples):
        if self._f is None:
            return
        arr = np.asarray(samples)
        self._f.write(_REC_HEAD.pack(_MAGIC, time.time(), seq & 0xFFFF,
                                     len(arr), t0, dropped))
        self._f.write(arr.tobytes())
        self._f.flush()
        self.n_blocks += 1
        self.n_samples += len(arr)
        self.fw_dropped = int(dropped)
        if self._last_seq is not None:
            gap = (seq - self._last_seq - 1) & 0xFFFF
            if gap:
                self.seq_gaps += gap
        self._last_seq = seq


# -- reading back -----------------------------------------------------------
def read_blocks(path):
    """Yield (pc_time, seq, t0_millis, dropped, structured samples) records;
    stops cleanly at a truncated trailing record."""
    with open(path, "rb") as f:
        while True:
            head = f.read(_REC_HEAD.size)
            if len(head) < _REC_HEAD.size:
                return
            magic, t, seq, count, t0, dropped = _REC_HEAD.unpack(head)
            if magic != _MAGIC:
                raise ValueError(f"bad record magic {magic:#x} in {path}")
            payload = f.read(RAW_DTYPE.itemsize * count)
            if len(payload) < RAW_DTYPE.itemsize * count:
                return
            yield t, seq, t0, dropped, np.frombuffer(payload, dtype=RAW_DTYPE)


def to_arrays(path):
    """Concatenate a whole capture: dict of adc (int16), z (int32),
    err (int32) plus block metadata arrays."""
    adc, z, err, t0s, seqs = [], [], [], [], []
    dropped = 0
    for _, seq, t0, drop, samples in read_blocks(path):
        adc.append(samples['adc'].astype(np.int16))
        z.append(samples['z'].astype(np.int32))
        err.append(samples['err'].astype(np.int32))
        t0s.append(t0)
        seqs.append(seq)
        dropped = drop
    if not adc:
        return None
    return {
        "adc": np.concatenate(adc),
        "z": np.concatenate(z),
        "err": np.concatenate(err),
        "block_t0_millis": np.asarray(t0s, np.uint32),
        "block_seq": np.asarray(seqs, np.uint32),
        "fw_dropped_samples": int(dropped),
    }
