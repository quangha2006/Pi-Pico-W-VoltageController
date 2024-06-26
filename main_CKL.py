from picozero import pico_led
from time import sleep
from machine import Pin, PWM
from RotateEncoder import Rotary
from ir_rx.nec import NEC_8
from ir_rx.print_error import print_error
#from neopixel import NeoPixel
import gc

pico_led.on()

digital_Min = 50
digital_Max = 300
digital_step = 10
increase_step = 1
target_value = 100 #Start
current_value = digital_Min
duty_count = 32768

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
rotary = Rotary(4,5,3)
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
    if change == Rotary.ROT_CW:
        target_value += digital_step
        led_remain_count = led_on_count
    elif change == Rotary.ROT_CCW:
        target_value -= digital_step
        led_remain_count = led_on_count
    elif change == Rotary.SW_PRESS:
        print('PRESS')
        #isOff = not isOff
        isOffRotate = not isOffRotate
        led_remain_count = led_on_count
    elif change == Rotary.SW_RELEASE:
        print('RELEASE')
        
def ir_cb(data, addr, ctrl):
    global target_value
    global isOff
    global led_remain_count
    if data < 0:  # NEC protocol sends repeat codes.
        print("Repeat code.")
    else:
        if data == 25:
            target_value += digital_step
            led_remain_count = led_on_count
            print("Button A pressed")
        elif data == 24:
            target_value -= digital_step
            led_remain_count = led_on_count
            print("Button B pressed")
        elif data == 64:
            print("Button Power pressed")
            led_remain_count = led_on_count
            isOff = not isOff
        else:
            print(f"Data 0x{data:02x} Addr 0x{addr:04x} Ctrl 0x{ctrl:02x}")

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
                data.append(line.strip())  # Loại bỏ ký tự xuống dòng

        return data
    except Exception as ex:
        print(f"Error reading from {filename}: {ex}")
        return None
def split_csv_line(line):
    return [value.strip() for value in line.split(',')]

rotary.add_handler(rotary_changed)
ir = NEC_8(ir_PIN, ir_cb)
ir.error_function(print_error)

try:
    #init values
    led_on = False
    lastSaveValue = 0
    isOff = False
    lastIsOff = True
    isOffRotate = True
    lastIsOffRotate = True
    total_Time = 0.0
    SS_Relay.low()
    RT_Relay.high()
    
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
        total_Time += 0.033
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

            print(current_value)
            pwm0.freq(current_value)
            #pwm0.duty_u16(current_value)      # set duty cycle, range 0-65535

        if lastIsOff != isOff:
            if isOff:
                pwm0.duty_u16(0)
                SS_Relay.high()
                print("Off Fan")
            else:
                SS_Relay.low()
                current_value = digital_Min
                pwm0.freq(current_value)
                pwm0.duty_u16(duty_count)
                print("On Fan")
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

        if total_Time > 5.0:
            gc.collect()
            total_Time = 0.0

        if lastSaveValue != target_value:
            lastSaveValue = target_value
            data_to_save = f"lastspeed,{target_value}"
            save_to_csv(data_fileName, data_to_save)

        sleep(0.033)
        if Break_Pin.value() == 0:
            break
        
except KeyboardInterrupt:
    ir.close()
    machine.reset()


