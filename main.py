from picozero import pico_temp_sensor, pico_led
from time import sleep
from machine import Pin, PWM
from RotateEncoder import Rotary
from ir_rx.nec import NEC_8
from ir_rx.print_error import print_error
import gc

pico_led.on()

digital_Min = 10535
digital_Max = 63535
digital_step = 1000
increase_step = 100
target_value = 32768
current_value = digital_Min

#duty_cycle = 32768

freq_value = 5000

isOff = False
lastIsOff = False

pwm0 = PWM(Pin(20,mode=Pin.OUT))
pwm0.freq(freq_value)
pwm0.duty_u16(current_value)

run_button = Pin(0, Pin.IN, Pin.PULL_UP)
A_button = Pin(6, Pin.IN, Pin.PULL_DOWN)
B_button = Pin(7, Pin.IN, Pin.PULL_DOWN)
ir_PIN = Pin(16, Pin.IN)
rotary = Rotary(4,5,2)

def rotary_changed(change):
    global target_value
    if change == Rotary.ROT_CW:
        target_value += digital_step
    elif change == Rotary.ROT_CCW:
        target_value -= digital_step
    elif change == Rotary.SW_PRESS:
        print('PRESS')
    elif change == Rotary.SW_RELEASE:
        print('RELEASE')
        
def ir_cb(data, addr, ctrl):
    global target_value
    global isOff
    if data < 0:  # NEC protocol sends repeat codes.
        print("Repeat code.")
    else:
        if data == 25:
            target_value += digital_step
            print("Button A pressed")
        elif data == 24:
            target_value -= digital_step
            print("Button B pressed")
        elif data == 64:
            print("Button Power pressed")
            isOff = not isOff
        else:
            print(f"Data 0x{data:02x} Addr 0x{addr:04x} Ctrl 0x{ctrl:02x}")

rotary.add_handler(rotary_changed)
ir = NEC_8(ir_PIN, ir_cb)
ir.error_function(print_error)

try:
    state = False
    A_button_lastValue = 0
    B_button_lastValue = 0
    while (True):
        if state:
            pico_led.on()
            state = False
        else:
            pico_led.off()
            state = True
        
        #Check button
        if A_button.value() == 1 and A_button_lastValue == 0:
            target_value += digital_step
        
        if B_button.value() == 1 and B_button_lastValue == 0:
            target_value -= digital_step
            
        if current_value != target_value:
            if target_value < digital_Min:
                target_value = digital_Min
            if target_value > digital_Max:
                target_value = digital_Max
            #print(val)
            if current_value < target_value:
                if target_value - current_value < increase_step:
                    current_value = target_value
                else:
                    current_value += increase_step
            elif current_value > target_value:
                if current_value - target_value < increase_step:
                    current_value = target_value
                else:
                    current_value -= increase_step

            #current_value = target_value
            #pwm0.freq(digital_value)
            print(current_value)
            pwm0.duty_u16(current_value)      # set duty cycle, range 0-65535

        if lastIsOff != isOff:
            if isOff:
                pwm0.duty_u16(0)
                print("Off Fan")
            else:
                current_value = digital_Min
                pwm0.duty_u16(current_value)
                print("On Fan")
            lastIsOff = isOff
            
        A_button_lastValue = A_button.value()
        B_button_lastValue = B_button.value()
        #gc.collect()
        sleep(0.033)
        if run_button.value() == 0:
            break
        
except KeyboardInterrupt:
    ir.close()
    machine.reset()

