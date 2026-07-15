"""RAWD raw-tap: header decode, dtype layout, logger roundtrip, gap counts."""
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import raw_logger
from serial_reader import RAW_DTYPE, decode_raw_header


def _mk_samples(n, seed=0):
    rng = np.random.RandomState(seed)
    arr = np.zeros(n, dtype=RAW_DTYPE)
    arr['adc'] = rng.randint(-32768, 32767, n).astype(np.int16)
    arr['z'] = rng.randint(-524287, 524287, n).astype(np.int32)
    arr['err'] = rng.randint(-2**24, 2**24, n).astype(np.int32)
    return arr


def test_raw_dtype_matches_firmware_layout():
    """10 bytes/sample, big-endian, adc then z then err — as packed by the
    firmware ISR (p[0..1]=adc, p[2..5]=z, p[6..9]=err)."""
    assert RAW_DTYPE.itemsize == 10
    sample = np.zeros(1, dtype=RAW_DTYPE)
    sample['adc'], sample['z'], sample['err'] = -2, 0x01020304, -1
    b = sample.tobytes()
    assert b[0:2] == b'\xff\xfe'                # -2 as >i2
    assert b[2:6] == b'\x01\x02\x03\x04'        # z as >i4
    assert b[6:10] == b'\xff\xff\xff\xff'       # -1 as >i4


def test_decode_raw_header():
    hdr = struct.pack('>HHII', 7, 512, 123456, 42)
    assert decode_raw_header(hdr) == (7, 512, 123456, 42)


def test_logger_roundtrip(tmp_path):
    rl = raw_logger.RawLogger(log_dir=str(tmp_path))
    path = rl.start({"decim": 1})
    sent = []
    for seq in range(5):
        s = _mk_samples(512, seed=seq)
        rl.on_block(seq, 1000 + seq * 20, 0, s)
        sent.append(s)
    rl.stop()

    got = list(raw_logger.read_blocks(path))
    assert len(got) == 5
    for (t, seq, t0, dropped, samples), s in zip(got, sent):
        assert np.array_equal(samples, s)
        assert dropped == 0
    assert rl.n_samples == 5 * 512
    assert rl.seq_gaps == 0

    arrs = raw_logger.to_arrays(path)
    assert arrs["adc"].shape == (2560,)
    assert arrs["adc"].dtype == np.int16
    assert np.array_equal(arrs["z"][:512], sent[0]['z'])


def test_seq_gap_and_fw_drop_accounting(tmp_path):
    rl = raw_logger.RawLogger(log_dir=str(tmp_path))
    rl.start()
    rl.on_block(0, 0, 0, _mk_samples(512))
    rl.on_block(1, 20, 0, _mk_samples(512))
    rl.on_block(4, 80, 137, _mk_samples(512))   # blocks 2,3 missing; fw drops
    rl.stop()
    assert rl.seq_gaps == 2
    assert rl.fw_dropped == 137


def test_seq_gap_across_u16_wrap(tmp_path):
    rl = raw_logger.RawLogger(log_dir=str(tmp_path))
    rl.start()
    rl.on_block(65534, 0, 0, _mk_samples(16))
    rl.on_block(65535, 1, 0, _mk_samples(16))
    rl.on_block(1, 2, 0, _mk_samples(16))       # 0 missing across the wrap
    rl.stop()
    assert rl.seq_gaps == 1


def test_truncated_trailing_block(tmp_path):
    rl = raw_logger.RawLogger(log_dir=str(tmp_path))
    path = rl.start()
    rl.on_block(0, 0, 0, _mk_samples(512))
    rl.on_block(1, 20, 0, _mk_samples(512))
    rl.stop()
    size = os.path.getsize(path)
    with open(path, "r+b") as f:
        f.truncate(size - 100)
    assert len(list(raw_logger.read_blocks(path))) == 1
