"""ASCOM Alpaca Focuser (IFocuserV4) on Microdot.

create_app() wires every Alpaca route to a Stepper. Rules that matter for
ConformU: GET parameter names are case-insensitive, PUT form names are
case-sensitive; malformed requests get HTTP 400; ASCOM errors are HTTP 200
with ErrorNumber/ErrorMessage.
"""
import time

from microdot import Microdot

import control
from state import FocuserState
from temperature import TemperatureStale, TemperatureUnavailable

NOT_IMPLEMENTED = 0x400
INVALID_VALUE = 0x401
NOT_CONNECTED = 0x407
INVALID_OPERATION = 0x40B
DRIVER_ERROR = 0x500

INTERFACE_VERSION = 4
DRIVER_VERSION = '1.0'
DESCRIPTION = 'Pico 2 W stepper focuser'
DRIVER_INFO = 'MicroPython Alpaca focuser for Raspberry Pi Pico 2 W + TMC2209'
MANUFACTURER = 'Pico Alpaca Focuser'

# Members that work without being connected
_NO_CONNECTION_NEEDED = ('connected', 'connecting', 'connect', 'disconnect',
                         'name', 'description', 'driverinfo', 'driverversion',
                         'interfaceversion', 'supportedactions')


class AlpacaError(Exception):
    def __init__(self, number, message):
        super().__init__(message)
        self.number = number
        self.message = message


class BadRequest(Exception):
    pass


def utc_iso():
    t = time.gmtime()
    return '{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z'.format(*t[:6])


class _Params:
    """Request parameters with Alpaca's case rules."""

    def __init__(self, req):
        self.is_get = req.method in ('GET', 'HEAD')
        source = req.args if self.is_get else (req.form or {})
        self._values = {}
        for key in source:
            self._values[key.lower() if self.is_get else key] = source[key]

    def get(self, name, default=None):
        return self._values.get(name.lower() if self.is_get else name, default)

    def required(self, name):
        value = self.get(name)
        if value is None or value == '':
            raise BadRequest('Missing or misspelled parameter "{}"'.format(name))
        return value

    def required_bool(self, name):
        value = self.required(name).lower()
        if value not in ('true', 'false'):
            raise BadRequest('Parameter "{}" is not a boolean'.format(name))
        return value == 'true'

    def required_int(self, name):
        value = self.required(name)
        digits = value[1:] if value[:1] == '-' else value
        if not digits.isdigit():
            raise BadRequest('Parameter "{}" is not an integer'.format(name))
        return int(value)

    def uint(self, name):
        value = self.get(name)
        if value is None or value == '':
            return 0
        if not value.isdigit():
            raise BadRequest('Parameter "{}" must be an unsigned integer'.format(name))
        return int(value)


def create_app(stepper, settings, unique_id, ip_getter=lambda: '', state=None):
    app = Microdot()
    state = state or FocuserState(settings)

    def require_connected():
        if not state.connected:
            raise AlpacaError(NOT_CONNECTED, 'Focuser is not connected')

    def set_connected(value):
        if value:
            stepper.hold()
        else:
            stepper.disable()
        state.connected = value

    # ---- GET members: return the Value ----
    def not_implemented(name):
        def handler(p):
            raise AlpacaError(NOT_IMPLEMENTED, '{} is not implemented'.format(name))
        return handler

    def get_temperature(p):
        if state.sensor is None:
            raise AlpacaError(NOT_IMPLEMENTED, 'No temperature sensor')
        try:
            return state.sensor.read()
        except TemperatureUnavailable as e:
            raise AlpacaError(NOT_IMPLEMENTED, str(e))
        except TemperatureStale as e:
            raise AlpacaError(DRIVER_ERROR, str(e))

    def device_state(p):
        items = [{'Name': 'IsMoving', 'Value': stepper.is_moving},
                 {'Name': 'Position', 'Value': stepper.position}]
        try:
            items.append({'Name': 'Temperature', 'Value': state.sensor.read()})
        except Exception:
            pass                        # no sensor or no fresh reading: leave it out
        items.append({'Name': 'TimeStamp', 'Value': utc_iso()})
        return items

    get_members = {
        'connected': lambda p: state.connected,
        'connecting': lambda p: False,
        'name': lambda p: settings['name'],
        'description': lambda p: DESCRIPTION,
        'driverinfo': lambda p: DRIVER_INFO,
        'driverversion': lambda p: DRIVER_VERSION,
        'interfaceversion': lambda p: INTERFACE_VERSION,
        'supportedactions': lambda p: [],
        'absolute': lambda p: True,
        'ismoving': lambda p: stepper.is_moving,
        'maxincrement': lambda p: settings['max_increment'],
        'maxstep': lambda p: settings['max_step'],
        'position': lambda p: stepper.position,
        'stepsize': not_implemented('StepSize'),
        'tempcompavailable': lambda p: False,
        'tempcomp': lambda p: False,
        'temperature': get_temperature,
        'devicestate': device_state,
    }

    # ---- PUT members: act, return nothing ----
    def put_connected(p):
        set_connected(p.required_bool('Connected'))

    def put_action(p):
        p.required('Action')
        raise AlpacaError(NOT_IMPLEMENTED, 'Action is not implemented')

    def put_command(p):
        p.required('Command')
        p.required_bool('Raw')
        raise AlpacaError(NOT_IMPLEMENTED, 'Command methods are not implemented')

    def put_move(p):
        position = p.required_int('Position')
        if position < 0 or position > settings['max_step']:
            raise AlpacaError(INVALID_VALUE, 'Position {} is outside 0..{}'.format(
                position, settings['max_step']))
        stepper.move_to(position)

    def put_tempcomp(p):
        if p.required_bool('TempComp'):
            raise AlpacaError(NOT_IMPLEMENTED, 'Temperature compensation is not available')

    put_members = {
        'move': put_move,
        'halt': lambda p: stepper.halt(),
        'tempcomp': put_tempcomp,
        'connected': put_connected,
        'connect': lambda p: set_connected(True),
        'disconnect': lambda p: set_connected(False),
        'action': put_action,
        'commandblind': put_command,
        'commandbool': put_command,
        'commandstring': put_command,
    }

    def respond(req, devnum, member, members, has_value):
        if devnum != 0:
            return 'Device number {} does not exist'.format(devnum), 400
        handler = members.get(member)
        if handler is None:
            return 'Unknown member "{}"'.format(member), 404
        try:
            p = _Params(req)
            p.uint('ClientID')
            client_txn = p.uint('ClientTransactionID')
        except BadRequest as e:
            return str(e), 400
        body = {'ClientTransactionID': client_txn,
                'ServerTransactionID': state.next_txn(),
                'ErrorNumber': 0, 'ErrorMessage': ''}
        try:
            if member not in _NO_CONNECTION_NEEDED:
                require_connected()
            value = handler(p)
            if has_value:
                body['Value'] = value
        except BadRequest as e:
            return str(e), 400
        except AlpacaError as e:
            body['ErrorNumber'] = e.number
            body['ErrorMessage'] = e.message
        except Exception as e:
            body['ErrorNumber'] = DRIVER_ERROR
            body['ErrorMessage'] = 'Driver error: {}'.format(e)
        return body

    @app.get('/api/v1/focuser/<int:devnum>/<member>')
    async def device_get(req, devnum, member):
        return respond(req, devnum, member, get_members, True)

    @app.put('/api/v1/focuser/<int:devnum>/<member>')
    async def device_put(req, devnum, member):
        return respond(req, devnum, member, put_members, False)

    # ---- Management API ----
    def management(req, value):
        try:
            client_txn = _Params(req).uint('ClientTransactionID')
        except BadRequest as e:
            return str(e), 400
        return {'Value': value, 'ClientTransactionID': client_txn,
                'ServerTransactionID': state.next_txn(),
                'ErrorNumber': 0, 'ErrorMessage': ''}

    @app.get('/management/apiversions')
    async def api_versions(req):
        return management(req, [1])

    @app.get('/management/v1/description')
    async def server_description(req):
        return management(req, {'ServerName': settings['name'],
                                'Manufacturer': MANUFACTURER,
                                'ManufacturerVersion': DRIVER_VERSION,
                                'Location': settings['location']})

    @app.get('/management/v1/configureddevices')
    async def configured_devices(req):
        return management(req, [{'DeviceName': settings['name'],
                                 'DeviceType': 'Focuser',
                                 'DeviceNumber': 0,
                                 'UniqueID': unique_id}])

    # ---- Control page (also the Alpaca setup pages) ----
    control.add_routes(app, stepper, state, ip_getter)

    return app
