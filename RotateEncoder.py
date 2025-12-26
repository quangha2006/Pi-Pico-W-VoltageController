import micropython
import utime as time
from machine import Pin

class Rotary:
    ROT_CW = 1
    ROT_CCW = 2
    SW_PRESS = 4
    SW_RELEASE = 8

    # 16-entry lookup table for quadrature transitions
    # index = (old_state<<2) | new_state
    # value = +1 (CW step), -1 (CCW step), 0 (invalid/bounce)
    _TRANS = (
        0, -1, +1, 0,
        +1, 0, 0, -1,
        -1, 0, 0, +1,
        0, +1, -1, 0
    )

    def __init__(self, dt, clk, sw, steps_per_detent=4, irq_debounce_us=200):
        self.dt_pin = Pin(dt, Pin.IN, Pin.PULL_UP)
        self.clk_pin = Pin(clk, Pin.IN, Pin.PULL_UP)
        self.sw_pin = Pin(sw, Pin.IN, Pin.PULL_UP)

        self.handlers = []

        # encoder state
        self._state = (self.dt_pin.value() << 1) | self.clk_pin.value()
        self._acc = 0
        self._steps_per_detent = steps_per_detent  # usually 4; some encoders feel better with 2
        self._irq_debounce_us = irq_debounce_us
        self._last_irq_us = time.ticks_us()

        # button
        self.last_button_status = self.sw_pin.value()
        self._last_btn_0_ms = time.ticks_ms()
        self._last_btn_1_ms = self._last_btn_0_ms

        # IRQ
        trig = Pin.IRQ_FALLING | Pin.IRQ_RISING
        self.dt_pin.irq(handler=self._rotary_irq, trigger=trig)
        self.clk_pin.irq(handler=self._rotary_irq, trigger=trig)
        self.sw_pin.irq(handler=self._switch_irq, trigger=trig)

    def add_handler(self, handler):
        self.handlers.append(handler)

    def _emit(self, evt):
        for h in self.handlers:
            h(evt)

    def call_handlers(self, evt):
        # called via micropython.schedule
        self._emit(evt)

    def _rotary_irq(self, pin):
        # simple time-based debounce to drop the worst bouncing storms
        now = time.ticks_us()
        if time.ticks_diff(now, self._last_irq_us) < self._irq_debounce_us:
            return
        self._last_irq_us = now

        new_state = (self.dt_pin.value() << 1) | self.clk_pin.value()
        if new_state == self._state:
            return

        idx = (self._state << 2) | new_state
        delta = Rotary._TRANS[idx]
        self._state = new_state

        if delta == 0:
            return  # invalid transition -> ignore (usually bounce)

        self._acc += delta

        # Only emit when we got a full detent worth of valid steps
        if self._acc >= self._steps_per_detent:
            self._acc = 0
            try:
                micropython.schedule(self.call_handlers, Rotary.ROT_CW)
            except RuntimeError:
                pass
        elif self._acc <= -self._steps_per_detent:
            self._acc = 0
            try:
                micropython.schedule(self.call_handlers, Rotary.ROT_CCW)
            except RuntimeError:
                pass

    def _switch_irq(self, pin):
        now = time.ticks_ms()
        ticks_diff_0 = time.ticks_diff(now, self._last_btn_0_ms)
        ticks_diff_1 = time.ticks_diff(now, self._last_btn_1_ms)
        v = self.sw_pin.value()

        #  debounce 20–40ms
        print(f'switch button ticks_diff = {ticks_diff_0} {ticks_diff_1} sw_pin_value = {v}')
        if v == 0 and ticks_diff_0 < 20:
            return
        
        if v == 1 and ticks_diff_1 < 20:
            return
        if v == 0:
            self._last_btn_0_ms = now
        if v == 1:
            self._last_btn_1_ms = now

          # pull-up: 0 = pressed
        if v == self.last_button_status:
            return
        
        self.last_button_status = v

        evt = Rotary.SW_PRESS if v == 0 else Rotary.SW_RELEASE
        try:
            micropython.schedule(self.call_handlers, evt)
        except RuntimeError:
            pass