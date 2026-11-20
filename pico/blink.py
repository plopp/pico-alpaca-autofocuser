from machine import Pin
import time

# --- Configuration ---
STEP_PIN_NUM = 16
DIR_PIN_NUM = 20
EN_PIN_NUM = 21  # Optional: Pull LOW to enable driver

# --- Setup ---
step_pin = Pin(STEP_PIN_NUM, Pin.OUT)
dir_pin = Pin(DIR_PIN_NUM, Pin.OUT)
en_pin = Pin(EN_PIN_NUM, Pin.OUT)

# Enable the driver (Active LOW)
en_pin.value(0)


def move_motor(steps, direction, delay_micros):
    """
    steps: integer
    direction: 0 or 1
    delay_micros: speed control (lower is faster)
    """
    dir_pin.value(direction)

    for _ in range(steps):
        step_pin.value(1)
        time.sleep_us(2)  # Minimum pulse width for TMC2209 is ~100ns, 2us is safe
        step_pin.value(0)
        time.sleep_us(delay_micros)


# --- Main Loop ---
print("Starting Step/Dir Demo...")

try:
    while True:
        # Move 1 Revolution (assuming 16 microsteps * 200 steps = 3200)
        print("Moving CW")
        move_motor(3200, 1, 300)  # Fast

        time.sleep(0.5)

        print("Moving CCW")
        move_motor(3200, 0, 800)  # Slow

        time.sleep(0.5)

except KeyboardInterrupt:
    print("Stopped")
    en_pin.value(1)  # Disable motor to prevent heating
