"""Every case dimension, in mm, in the BOARD FRAME.

x: from the board's rear edge (0) towards the motor; y: from the board's top long edge
(0..50, as in KiCad); z: up from the board's top surface. This frame is the PCB's own, so
it is mirror-imaged (KiCad's y points down the screen); parts.to_world() flips y for the
printed parts. Values marked PCB are checked against the committed board in the tests.
"""

CLEAR = 0.3                 # print clearance

# Board v1.0 (ordered, fixed)
BOARD_L, BOARD_W, BOARD_T = 80.0, 50.0, 1.6

# Walls and slots
REAR_WALL = 2.0             # J1 front and J3 nose end flush with its outside (x = -2)
SLOT_DEPTH, SLOT_GAP = 2.0, 0.4
SLOT_Z = (-BOARD_T - SLOT_GAP / 2, SLOT_GAP / 2)        # -1.8 .. 0.2
SLOT_Y = (-SLOT_GAP / 2, BOARD_W + SLOT_GAP / 2)        # slot bottoms: -0.2, 50.2
INNER_Y = (SLOT_Y[0] + SLOT_DEPTH, SLOT_Y[1] - SLOT_DEPTH)   # wall faces 1.8, 48.2
SIDE_WALL = 2.5             # outside the slot bottom
OUTER_Y = (SLOT_Y[0] - SIDE_WALL, SLOT_Y[1] + SIDE_WALL)     # -2.7, 52.7

# Floor: the board slides in from the front over all of it, so its top stays below the
# board's through-hole pins (about 3.5 mm) everywhere; it is thick enough for the nut.
FLOOR_Z = -5.4
GROOVE_D = 1.0              # key groove in the bottom face
NUT_AF, NUT_T = 11.1, 5.6   # 1/4"-20 hex nut: 7/16" across flats, 7/32" thick
NUT_FLOOR = 0.6             # between groove and nut
NUT_POCKET = 6.0            # deeper than the nut (ASME max 5.74) so it never stands proud
NUT_COVER = 0.8             # printed over the nut
BOTTOM_Z = FLOOR_Z - NUT_COVER - NUT_POCKET - NUT_FLOOR - GROOVE_D   # -13.8
NUT_BOTTOM_Z = BOTTOM_Z + GROOVE_D + NUT_FLOOR                  # -12.2
NUT_TOP_Z = NUT_BOTTOM_Z + NUT_POCKET                           # -6.2 (pocket top)
PAUSE_HEIGHT = round(NUT_TOP_Z - BOTTOM_Z, 2)                   # 7.6 mm above the bed
NUT_X, NUT_Y = 100.0, 25.0  # under the motor, near the centre of mass
SCREW_HOLE_D = 6.8          # 1/4" camera screw clearance

# Key (ridge) glued into the groove; runs across the case (along y) in the bracket slot
KEY_W = 6.0
KEY_H = 3.0                 # 1 mm in the groove, 2 mm ridge

# Motor: NEMA 17 up to 48 mm, centred in y, hanging from the front plate
MOTOR_SQUARE = 42.3
MOTOR_HOLE_PITCH = 31.0
MOTOR_BOSS_D, MOTOR_BOSS_H = 22.0, 2.0
MOTOR_MAX_L = 48.0
MOTOR_FACE_X = 134.0
MOTOR_REAR_X = MOTOR_FACE_X - MOTOR_MAX_L       # 86: 6 mm cable gap after the board
MOTOR_Y = BOARD_W / 2
MOTOR_BOTTOM_Z = -0.6
SHAFT_Z = MOTOR_BOTTOM_Z + MOTOR_SQUARE / 2     # 20.55
CONNECTOR_ROOM = 10.0       # the motor's JST PH connector faces up, at its rear end

# Front plate and lid
PLATE_T = 5.0
PLATE_X1 = MOTOR_FACE_X + PLATE_T               # 139
LID_UNDER_Z = MOTOR_BOTTOM_Z + MOTOR_SQUARE + CONNECTOR_ROOM    # 51.7
LID_T = 2.5
LID_TOP_Z = LID_UNDER_Z + LID_T                 # 54.2

OUTER = (-REAR_WALL, OUTER_Y[0], BOTTOM_Z, PLATE_X1, OUTER_Y[1], LID_TOP_Z)

# M3 heat-set inserts and screws
INSERT_D, INSERT_DEPTH = 4.0, 5.0
SCREW_D = 3.4
BOSS_OUT = 2.3              # corner bosses bulge this far outside the side walls
BOSS_Y = (OUTER_Y[0] + 1.1, OUTER_Y[1] - 1.1)   # insert centre lines, -1.6 and 51.6
BOSS_BOTTOM_Z = 40.0
LID_SCREWS = [(3.0, BOSS_Y[0]), (3.0, BOSS_Y[1]),          # (x, y), vertical
              (125.0, BOSS_Y[0]), (125.0, BOSS_Y[1])]
PLATE_SCREWS = [(BOSS_Y[0], 44.0), (BOSS_Y[1], 44.0),      # (y, z), along x
                (4.0, -9.4), (46.0, -9.4)]
BOSS_X = [(-REAR_WALL, 8.0), (120.0, MOTOR_FACE_X)]         # rear and front boss lengths

# Rear wall holes (PCB positions; heights from datasheets)
USB_Y, USB_Z = 13.39, 13.3          # PCB: Pico mid-line; 8.5 socket + 2.5 header + 1.0 PCB + 1.3
USB_HOLE = (10.0, 6.0, 1.5)         # width (y), height (z), corner radius
USB_RECESS = (13.0, 9.0, 1.0)       # outside, for a long plug grip
J1_Y = 29.2                         # PCB: DC-005 pin 1
J1_BODY = (9.0, 10.9)               # width, height
J1_CUT_Y = (J1_Y - J1_BODY[0] / 2 - CLEAR, J1_Y + J1_BODY[0] / 2 + CLEAR)   # 24.4..34.0
J1_CUT_Z = (-SLOT_GAP / 2 - CLEAR, J1_BODY[1] + CLEAR)    # -0.5..11.2: board may sit low in the slot
J3_Y, J3_Z = 40.5, 2.5              # PCB: PJ-320D nose, Ø5, sitting on the board
J3_HOLE_D = 5.8

# Lid openings
POT_X, POT_Y, POT_D = 69.0, 19.0, 8.0          # BTT TMC2209 pot at its VM end
VENT_XS = [64.0 + i * 3.5 for i in range(5)]   # slot centres x 64..78
VENT_W, VENT_Y = 2.0, (3.0, 14.0)
BOARD_STOP_X = (BOARD_L + CLEAR, BOARD_L + CLEAR + 5.0)    # 80.3..85.3: stiff, clear of a 48 mm motor
BOARD_STOP_YS = [(5.0, 20.0), (36.0, 45.0)]                # clear of J2 (y 24.6..31.4)
STOP_SOCKET_D = 2.0         # fin tips sit in sockets in the floor
BOARD_STOP_Z = FLOOR_Z - STOP_SOCKET_D + CLEAR
