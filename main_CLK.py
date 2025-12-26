from picozero import pico_led
from time import sleep
from machine import Pin, PWM
from RotateEncoder import Rotary
from ir_rx.nec import MITSUBISHI
from ir_rx.print_error import print_error
import utime
from sys import platform
import sys, select, time
#from neopixel import NeoPixel
import gc

pico_led.on()

digital_Min = 50
digital_Max = 300
digital_step = 5
increase_step = 1
target_value = 100 #Start
current_value = digital_Min
duty_count = 32768
button_step_timeoutMS = 100
gc_collect_interval_seconds = 60.0

led_remain_count = 0
led_on_count = 3
data_fileName = "data.csv"

pwm0 = PWM(Pin(20,mode=Pin.OUT))
pwm0.freq(current_value)
pwm0.duty_u16(duty_count)

Break_Pin = Pin(0, Pin.IN, Pin.PULL_UP)

SS_Relay = Pin(6, Pin.OUT) #Connect GND BLDC
RT_Relay = Pin(7, Pin.OUT) #Rotate
Input_Led = Pin(8, Pin.OUT)
Power_Led = Pin(9, Pin.OUT)

ir_PIN = Pin(16, Pin.IN)
rotary = Rotary(4,5,3,2)
Power_Led.high()
#RGB Onboard Led
#led_RGB_onboard = Pin(23, Pin.OUT)
#np = NeoPixel(led_RGB_onboard, 8)
#np[0] = (255, 0, 0) # RGB
#np.write()

def rotary_changed(change):
    global target_value
    global isOff
    global led_remain_count
    global isOffRotate
    global button_timeout
    if button_timeout > 0:
        print(f"Ignore ButtonPreesed button_timeout = {button_timeout}")
        return
    led_remain_count = led_on_count
    if change == Rotary.ROT_CW:
        target_value += digital_step
        if isOff:
            isOff = False
        print(f"CW => {target_value}")
    elif change == Rotary.ROT_CCW:
        target_value -= digital_step
        if isOff:
            isOff = False
        print(f"CCW => {target_value}")
    elif change == Rotary.SW_PRESS:
        print('PRESS')
        isOffRotate = not isOffRotate
    elif change == Rotary.SW_RELEASE:
        print('RELEASE')
    button_timeout = button_step_timeoutMS
        
def ir_cb(data, addr, ctrl):
    global target_value
    global isOff
    global led_remain_count
    global isOffRotate
    #print("addr", hex(addr), "cmd", hex(data), "bytes", [hex(x) for x in ctrl])
    button_id = ctrl[6] if ctrl and len(ctrl) > 6 else None
    #print("button id:", hex(button_id) if button_id else None)
    button_map = {0x01: "Power", 0x02: "Increase", 0x05: "Decrease", 0x04: "Swing_ON", 0x03: "Swing_OFF"}
    label = button_map.get(ctrl[6], f"unk_{hex(ctrl[6])}")
    print("button label:", label)
    led_remain_count = led_on_count
    if label == "Increase":
        target_value += digital_step
        if isOff:
            isOff = False
    elif label == "Decrease":
        target_value -= digital_step
        if isOff:
            isOff = False
    elif label == "Swing_ON":
        isOffRotate = False
    elif label == "Swing_OFF":
        isOffRotate = True
    elif label == "Power":
        isOff = not isOff

def save_to_csv(filename, data):
    try:
        with open(filename, "w") as file:
            file.write(data + "\n")
        print(f"Data appended to {filename} successfully!")
    except Exception as ex:
        print(f"Error writing to {filename}: {ex}")

def read_csv(filename):
    try:
        data = []
        with open(filename, "r") as file:
            for line in file:
                data.append(line.strip())

        return data
    except Exception as ex:
        print(f"Error reading from {filename}: {ex}")
        return None
def split_csv_line(line):
    return [value.strip() for value in line.split(',')]

rotary.add_handler(rotary_changed)
ir = MITSUBISHI(ir_PIN, ir_cb)
ir.error_function(print_error)

try:
    #init values
    led_on = False
    lastSaveValue = 0
    isOff = False
    lastIsOff = True
    isOffRotate = True
    lastIsOffRotate = True
    total_Time_seconds = 0.0
    button_timeout = 0
    SS_Relay.low()
    RT_Relay.high()
    last = utime.ticks_ms()
    now = utime.ticks_ms()
    dt_ms = 0
    Input_Led.low()
    #Read Data:
    csv_data = read_csv(data_fileName)
    if csv_data:
        print("Data from CSV file: {data_fileName}")
        for row in csv_data:
            values = split_csv_line(row)
            if values[0] == "lastspeed":
                try:
                    lastSaveValue = int(values[1])
                    target_value = lastSaveValue
                    print(f"lastspeed = {target_value}")
                except ValueError:
                    print(f"Error while converting '{row}' to interger.")
    else:
        print("Failed to read data from CSV file.")

    while (True):
        now = utime.ticks_ms()
        dt_ms = utime.ticks_diff(now, last)
        last = now
        total_Time_seconds += dt_ms/ 1000.0
        if button_timeout >= 0:
            button_timeout -= dt_ms
        if led_on:
            pico_led.on()
            led_on = False
        else:
            pico_led.off()
            led_on = True
            
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

            print(f'FanSpeed = {current_value}')
            pwm0.freq(current_value)
            #pwm0.duty_u16(current_value)      # set duty cycle, range 0-65535

        if lastIsOff != isOff:
            if isOff:
                pwm0.duty_u16(0)
                SS_Relay.high()
                print("Off Fan by IR")
            else:
                SS_Relay.low()
                current_value = digital_Min
                pwm0.freq(current_value)
                pwm0.duty_u16(duty_count)
                print("On Fan by IR")
            lastIsOff = isOff
        
        if lastIsOffRotate != isOffRotate:
            if isOffRotate:
                RT_Relay.high()
                print("Off fan rotate")
            else:
                RT_Relay.low()
                print("On fan rotate")
            lastIsOffRotate = isOffRotate

        if led_remain_count > 0:
            led_remain_count -= 1
            Input_Led.high()
        else:
            Input_Led.low()

        if total_Time_seconds > gc_collect_interval_seconds:
            gc.collect()
            total_Time_seconds = 0.0

        if lastSaveValue != target_value:
            lastSaveValue = target_value
            data_to_save = f"lastspeed,{target_value}"
            save_to_csv(data_fileName, data_to_save)

        sleep(0.033)
        
except KeyboardInterrupt:
    ir.close()