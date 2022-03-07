import concurrent.futures
from threading import Thread

from RpiMotorLib import RpiMotorLib

pan = 0
tilt = 0

panVal = 0
tiltVal = 0

moving = False
panGpioPins = [21, 20, 16, 12]
tiltGpioPins = [8, 25, 24, 23]

# GPIO.add_event_detect(9,GPIO.BOTH,callback=setpospan,bouncetime=10)

# Declare an named instance of class pass a name and motor type
mymotortest = RpiMotorLib.BYJMotor("MyMotorOne", "28BYJ")
tiltmotor = RpiMotorLib.BYJMotor("tiltmotor", "28BYJ")


# call the function pass the parameters
# while (GPIO.input(26)):

def tracker():
    global panVal, moving, tiltVal
    while True:
        absp = abs(panVal)
        abst = abs(tiltVal)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            if (panVal < 0):
                # print("turn Right", panVal)
                executor.submit(turnRight, absp)
                # turnRight(absp)
                # print("turn Right complete", panVal)
            elif (panVal > 0):
                # (print("turn Left", panVal))
                # turnLeft(absp)
                executor.submit(turnLeft, absp)
            panVal = 0

            if (tiltVal < 0):
                # print("tiltup", tiltVal)
                # tiltUp(abst)
                executor.submit(tiltUp, abst)
            elif (tiltVal > 0):
                # (print("tiltDown", panVal))
                # tiltDown(abst)
                executor.submit(tiltDown, abst)
            tiltVal = 0


def turnLeft(steps):
    mymotortest.motor_run(panGpioPins, .002, steps, False, False, "full", .002)


def turnRight(steps):
    mymotortest.motor_run(panGpioPins, .002, steps, True, False, "full", .002)


def tiltUp(steps):
    tiltmotor.motor_run(tiltGpioPins, .002, steps, False, False, "full", .002)


def tiltDown(steps):
    tiltmotor.motor_run(tiltGpioPins, .002, steps, True, False, "full", .002)

Thread(target=tracker).start()

# good practise to cleanup GPIO at some point before exit
# GPIO.cleanup()
# tiltUp(115)
# tiltDown(115)
# turnRight(50)
# turnLeft(50)

