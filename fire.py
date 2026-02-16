import RPi.GPIO as gpio
from time import sleep

IN1 = 17
IN2 = 22

class fireplace:

    def __init__(self):
        gpio.setmode(gpio.BCM)
        gpio.setup(IN1, gpio.OUT)
        gpio.setup(IN2, gpio.OUT)
        gpio.output(IN1, False)
        gpio.output(IN2, False)

    def on(self, time_seconds=0.2):
        gpio.output(IN1, True)
        gpio.output(IN2, False)
        sleep(time_seconds)
        self.all_off()

    def off(self, time_seconds=0.2):
        gpio.output(IN1, False)
        gpio.output(IN2, True)
        sleep(time_seconds)
        self.all_off()

    def all_off(self):
        gpio.output(IN1, False)
        gpio.output(IN2, False)

    def __dell__(self):
        gpio.cleanup()


if(__name__ == '__main__'):

    # use argparse to see if user wants to turn it on or off
    import argparse
    parser = argparse.ArgumentParser(description="CLI tool to control fireplace solenoid with")
    parser.add_argument("on_off", type=str, help="turn fireplace on or off")

    args = parser.parse_args

    # init fireplace object
    fireplace = fireplace()

    # capture command line args
    args = parser.parse_args()

    if(args.on_off == "on"):
        fireplace.on()
    elif(args.on_off == "off"):
        fireplace.off()
    else:
        print("invalid argument. only 'on' or 'off' is acceptable")
