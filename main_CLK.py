from picozero import pico_led
from time import sleep
from machine import Pin, PWM
from RotateEncoder import Rotary
from ir_rx.nec import MITSUBISHI
from ir_rx.print_error import print_error
import utime
from sys import platform
import gc

pico_led.on()

digital_Min = 50
digital_Max = 300
digital_step = 5
increase_step = 1
targetFanFreq = 100 #Start
currentFanFreq = digital_Min
duty_count = 32768
button_step_timeoutMS = 100.0
gc_collect_interval_seconds = 60.0

led_timeout = 0
led_timerMS = 100 #LED ON time after button pressed
data_fileName = "data.csv"

pwm0 = PWM(Pin(20,mode=Pin.OUT))
pwm0.freq(currentFanFreq)
pwm0.duty_u16(duty_count)

Break_Pin = Pin(0, Pin.IN, Pin.PULL_UP)

FanStartStopSignal = Pin(6, Pin.OUT) #Connect GND BLDC
FanSwing_Relay = Pin(7, Pin.OUT) #Rotate Motor
Input_Led = Pin(8, Pin.OUT)
Power_Led = Pin(9, Pin.OUT)

ir_PIN = Pin(16, Pin.IN)
rotary = Rotary(4,5,3,2)
Power_Led.high()

#Init variables
isFanRunning = True
currentIsFanRunning = False
isFanSwing = False
currentIsFanSwing = False
onboardLedOn = True
button_timeout = 0.0

def rotary_changed(change):
    global targetFanFreq
    global isFanRunning
    global led_timeout
    global isFanSwing
    global button_timeout
    if button_timeout > 0.0:
        print(f"Ignore ButtonPreesed button_timeout = {button_timeout}")
        return
    led_timeout = led_timerMS
    if change == Rotary.ROT_CW:
        targetFanFreq += digital_step
        isFanRunning = True
        print(f"CW => {targetFanFreq}")
    elif change == Rotary.ROT_CCW:
        targetFanFreq -= digital_step
        isFanRunning = True
        print(f"CCW => {targetFanFreq}")
    elif change == Rotary.SW_PRESS:
        print('PRESS')
        isFanSwing = not isFanSwing
    elif change == Rotary.SW_RELEASE:
        print('RELEASE')
    button_timeout = button_step_timeoutMS
        
def ir_cb(data, addr, ctrl):
    global targetFanFreq
    global isFanRunning
    global led_timeout
    global isFanSwing
    #print("addr", hex(addr), "cmd", hex(data), "bytes", [hex(x) for x in ctrl])
    button_id = ctrl[6] if ctrl and len(ctrl) > 6 else None
    #print("button id:", hex(button_id) if button_id else None)
    button_map = {0x01: "Power", 0x02: "Increase", 0x05: "Decrease", 0x04: "Swing_ON", 0x03: "Swing_OFF"}
    label = button_map.get(ctrl[6], f"unk_{hex(ctrl[6])}")
    print("button label:", label)
    led_timeout = led_timerMS
    if label == "Increase":
        targetFanFreq += digital_step
        isFanRunning = True
    elif label == "Decrease":
        targetFanFreq -= digital_step
        isFanRunning = True
    elif label == "Swing_ON":
        isFanSwing = True
    elif label == "Swing_OFF":
        isFanSwing = False
    elif label == "Power":
        isFanRunning = not isFanRunning

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

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

rotary.add_handler(rotary_changed)
ir = MITSUBISHI(ir_PIN, ir_cb)
ir.error_function(print_error)

try:
    #init values
    
    savedFanFreq = 0
    total_Time_seconds = 0.0
    
    lastFrameTime = utime.ticks_ms()
    now = lastFrameTime
    frameDeltaTimeMS = 0
    Input_Led.low()
    #Read Data:
    csv_data = read_csv(data_fileName)
    if csv_data:
        print("Data from CSV file: {data_fileName}")
        for row in csv_data:
            values = split_csv_line(row)
            if values[0] == "lastspeed":
                try:
                    savedFanFreq = int(values[1])
                    targetFanFreq = savedFanFreq
                    print(f"lastspeed = {targetFanFreq}")
                except ValueError:
                    print(f"Error while converting '{row}' to interger.")
    else:
        print("Failed to read data from CSV file.")

    while (True):
        now = utime.ticks_ms()
        frameDeltaTimeMS = utime.ticks_diff(now, lastFrameTime)
        lastFrameTime = now
        total_Time_seconds += frameDeltaTimeMS/ 1000.0
        if button_timeout >= 0:
            button_timeout -= frameDeltaTimeMS

        # Update Onboard LED status
        if onboardLedOn:
            pico_led.on()
        else:
            pico_led.off()
        onboardLedOn = not onboardLedOn

        #  Update Fan Speed
        if currentFanFreq != targetFanFreq:
            targetFanFreq = clamp(targetFanFreq, digital_Min, digital_Max)

            if currentFanFreq < targetFanFreq:
                currentFanFreq += increase_step
            elif currentFanFreq > targetFanFreq:
                currentFanFreq -= increase_step

            currentFanFreq = clamp(currentFanFreq, digital_Min, digital_Max)
            print(f'FanSpeed = {currentFanFreq}')
            pwm0.freq(currentFanFreq)
            #pwm0.duty_u16(current_value)      # set duty cycle, range 0-65535

        # Update Fan status
        if currentIsFanRunning != isFanRunning:
            if not isFanRunning:
                pwm0.duty_u16(0)
                FanStartStopSignal.high()
                #Update Swing
                currentIsFanSwing = False
                FanSwing_Relay.high()
                print("Off Fan")
            else:
                FanStartStopSignal.low()
                currentFanFreq = digital_Min
                pwm0.freq(currentFanFreq)
                pwm0.duty_u16(duty_count)
                print("On Fan")
            currentIsFanRunning = isFanRunning

        # Update Swing status
        if currentIsFanSwing != isFanSwing:
            if not isFanSwing:
                FanSwing_Relay.high()
                currentIsFanSwing = isFanSwing
                print("Off fan rotate")
            elif isFanRunning:
                FanSwing_Relay.low()
                print("On fan rotate")
                currentIsFanSwing = isFanSwing

        # Update LED status
        if led_timeout > 0:
            led_timeout -= frameDeltaTimeMS
            Input_Led.high()
        else:
            Input_Led.low()

        if total_Time_seconds > gc_collect_interval_seconds:
            gc.collect()
            total_Time_seconds = 0.0

        if savedFanFreq != targetFanFreq:
            savedFanFreq = targetFanFreq
            data_to_save = f"lastspeed,{targetFanFreq}"
            save_to_csv(data_fileName, data_to_save)

        sleep(0.033)
        
except KeyboardInterrupt:
    ir.close()