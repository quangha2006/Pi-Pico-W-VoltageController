from picozero import pico_temp_sensor, pico_led
from time import sleep
from machine import Pin, PWM
from RotateEncoder import Rotary


digital_Min = 100
digital_Max = 400
digital_value = 100
duty_cycle = 32768
start_value = 150

pwm0 = PWM(Pin(15,mode=Pin.OUT))
pwm0.freq(start_value)
pwm0.duty_u16(duty_cycle)

run_button = Pin(0, Pin.IN, Pin.PULL_UP)
A_button = Pin(6, Pin.IN, Pin.PULL_DOWN)
B_button = Pin(7, Pin.IN, Pin.PULL_DOWN)
rotary = Rotary(4,5,2)
val = digital_value

def rotary_changed(change):
    global val
    if change == Rotary.ROT_CW:
        val = val + 10
    elif change == Rotary.ROT_CCW:
        val = val - 10
    elif change == Rotary.SW_PRESS:
        print('PRESS')
    elif change == Rotary.SW_RELEASE:
        print('RELEASE')
        
rotary.add_handler(rotary_changed)

try:
    state = False
    A_button_lastValue = 0
    B_button_lastValue = 0
    while (run_button.value() == 0):
        if state:
            pico_led.on()
            state = False
        else:
            pico_led.off()
            state = True
            
        if A_button.value() == 1 and A_button_lastValue == 0:
            print("A pressed down")
            val += 10
        
        if B_button.value() == 1 and B_button_lastValue == 0:
            print("B pressed down")
            val -= 10
            
        if digital_value != val:
            if val < digital_Min:
                val = digital_Min
            if val > digital_Max:
                val = digital_Max
            #print(val)
            digital_value = val
            pwm0.freq(digital_value)
            print(digital_value)
            pwm0.duty_u16(duty_cycle)      # set duty cycle, range 0-65535
            
            
        A_button_lastValue = A_button.value()
        B_button_lastValue = B_button.value()
        sleep(0.033)
        
except KeyboardInterrupt:
    machine.reset()
