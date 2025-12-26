# nec.py Decoder for IR remote control using synchronous code
# Supports NEC and Samsung protocols.
# With thanks to J.E. Tannenbaum for information re Samsung protocol

# For a remote using NEC see https://www.adafruit.com/products/389

# Author: Peter Hinch
# Copyright Peter Hinch 2020-2022 Released under the MIT license

from utime import ticks_us, ticks_diff
from ir_rx import IR_RX

class NEC_ABC(IR_RX):
    def __init__(self, pin, extended, samsung, callback, *args):
        # Block lasts <= 80ms (extended mode) and has 68 edges
        super().__init__(pin, 68, 80, callback, *args)
        self._extended = extended
        self._addr = 0
        self._leader = 2500 if samsung else 4000  # 4.5ms for Samsung else 9ms

    def decode(self, _):
        try:
            if self.edge > 68:
                raise RuntimeError(self.OVERRUN)
            width = ticks_diff(self._times[1], self._times[0])
            if width < self._leader:  # 9ms leading mark for all valid data
                raise RuntimeError(self.BADSTART)
            width = ticks_diff(self._times[2], self._times[1])
            if width > 3000:  # 4.5ms space for normal data
                if self.edge < 68:  # Haven't received the correct number of edges
                    raise RuntimeError(self.BADBLOCK)
                # Time spaces only (marks are always 562.5µs)
                # Space is 1.6875ms (1) or 562.5µs (0)
                # Skip last bit which is always 1
                val = 0
                for edge in range(3, 68 - 2, 2):
                    val >>= 1
                    if ticks_diff(self._times[edge + 1], self._times[edge]) > 1120:
                        val |= 0x80000000
            elif width > 1700: # 2.5ms space for a repeat code. Should have exactly 4 edges.
                raise RuntimeError(self.REPEAT if self.edge == 4 else self.BADREP)  # Treat REPEAT as error.
            else:
                raise RuntimeError(self.BADSTART)
            addr = val & 0xff  # 8 bit addr
            cmd = (val >> 16) & 0xff
            if cmd != (val >> 24) ^ 0xff:
                raise RuntimeError(self.BADDATA)
            if addr != ((val >> 8) ^ 0xff) & 0xff:  # 8 bit addr doesn't match check
                if not self._extended:
                    raise RuntimeError(self.BADADDR)
                addr |= val & 0xff00  # pass assumed 16 bit address to callback
            self._addr = addr
        except RuntimeError as e:
            cmd = e.args[0]
            addr = self._addr if cmd == self.REPEAT else 0  # REPEAT uses last address
        # Set up for new data burst and run user callback
        self.do_callback(cmd, addr, 0, self.REPEAT)

class NEC_8(NEC_ABC):
    def __init__(self, pin, callback, *args):
        super().__init__(pin, False, False, callback, *args)

class NEC_16(NEC_ABC):
    def __init__(self, pin, callback, *args):
        super().__init__(pin, True, False, callback, *args)

class SAMSUNG(NEC_ABC):
    def __init__(self, pin, callback, *args):
        super().__init__(pin, True, True, callback, *args)

class MITSUBISHI(IR_RX):
    """Decoder for Mitsubishi/Some AC remotes that use a ~3.2ms leader
    and 0/1 encoding where marks are ~470us and a space > ~900us means '1'.
    This class is conservative: it checks leader length and ignores short bursts.
    """
    def __init__(self, pin, callback, *args):
        # Allow more edges (some remotes send long frames) and a 120ms block timer
        # Increased nedges to accommodate longer frames without overrun
        super().__init__(pin, 140, 120, callback, *args)

    def decode(self, _):
        vals = []
        try:
            # Protect against too many edges
            if self.edge > self._nedges:
                raise RuntimeError(self.OVERRUN)
            if self.edge < 3:
                raise RuntimeError(self.BADBLOCK)
            leader = ticks_diff(self._times[1], self._times[0])
            # Expect leader mark ~3200us (+/- ~800us)
            if not (2800 < leader < 3600):
                raise RuntimeError(self.BADSTART)

            # Parse bit pairs: mark (short) then space: space > 900 -> 1 else 0
            bits = []
            for edge in range(3, self.edge - 1, 2):
                space = ticks_diff(self._times[edge + 1], self._times[edge])
                bits.append(1 if space > 900 else 0)

            nbits = len(bits)
            if nbits < 32:
                # Too short to be a valid frame
                raise RuntimeError(self.BADDATA)

            # Build byte list (LSB first per byte)
            nbytes = nbits // 8
            for b in range(nbytes):
                v = 0
                for i in range(8):
                    v |= (bits[b * 8 + i] << i)
                vals.append(v)

            # Heuristics: many AC remotes: addr in first 2 bytes, cmd in 3rd
            addr = vals[0] | (vals[1] << 8) if nbytes >= 2 else (vals[0] if nbytes >= 1 else 0)
            cmd = vals[2] if nbytes >= 3 else (vals[1] if nbytes >= 2 else vals[0] if nbytes >= 1 else 0)

        except RuntimeError as e:
            cmd = e.args[0]
            addr = 0

        # Run callback (errors will be routed to error handler)
        self.do_callback(cmd, addr, vals, self.REPEAT)
