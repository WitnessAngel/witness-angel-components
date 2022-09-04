
import atexit

import RPi.GPIO as GPIO

# We have to disable this remote GPIO.cleanup function, since some E-Paper screens calls it wrongly on sleep #

_real_gpio_cleanup = GPIO.cleanup
atexit.register(_real_gpio_cleanup)  # We cleanup before we leave

def fake_gpio_cleanup(*args, **kwargs):
    print("# SKIPPING WRONG GPIO CLEANUP #")
GPIO.cleanup = fake_gpio_cleanup


GPIO.setmode(GPIO.BCM)  # We use Chip numbering for GPIOs here
GPIO.setwarnings(False)  # Other apps or previous crash might have left GPIOs in weird states;..


def register_button_callback(pin, callback):
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(pin, GPIO.FALLING, callback=callback, bouncetime=1000)

def unregister_button_callbacks(pin):
    GPIO.remove_event_detect(pin)
