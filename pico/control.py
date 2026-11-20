"""Browser control page: jog, move, reset position, halt and basic settings.

Lives outside /api/v1 so Alpaca clients and ConformU never see it. The same page answers
the Alpaca setup URLs (/setup and /setup/v1/focuser/0/setup).
"""
try:
    import asyncio
except ImportError:          # pragma: no cover
    import uasyncio as asyncio

from settings import EDITABLE, save_settings, validate_settings

LIVE = ('steps_per_sec', 'reverse', 'hold_when_idle')        # applied without a restart
JOG_STEPS = (-1000, -100, -10, 10, 100, 1000)


def _form(req):
    form = req.form or {}
    return {k: form[k] for k in form}          # Microdot MultiDict -> first values


def _int_field(form, name):
    raw = str(form.get(name, '')).strip()
    digits = raw[1:] if raw[:1] == '-' else raw
    if not digits.isdigit():
        raise ValueError('{} must be a whole number'.format(name))
    return int(raw)


async def _later(fn, delay=0.5):
    await asyncio.sleep(delay)
    fn()


def add_routes(app, stepper, state, ip_getter):
    settings = state.settings

    def temperature():
        try:
            return state.sensor.read()
        except Exception:
            return None

    def status():
        return {'position': stepper.position, 'target': stepper.target,
                'moving': stepper.is_moving, 'connected': state.connected,
                'temperature': temperature(), 'max_step': settings['max_step'],
                'start_position': settings['start_position'], 'ip': ip_getter(),
                'settings': {k: settings[k] for k in EDITABLE}}

    def move(target):
        target = max(0, min(settings['max_step'], target))
        # Without a client holding the focuser, only power the motor for the move itself
        stepper.move_to(target, release=not state.connected)
        return status()

    @app.get('/control/status')
    async def get_status(req):
        return status()

    @app.post('/control/move')
    async def post_move(req):
        try:
            target = _int_field(_form(req), 'position')
        except ValueError as e:
            return str(e), 400
        if not 0 <= target <= settings['max_step']:
            return 'position must be 0..{}'.format(settings['max_step']), 400
        return move(target)

    @app.post('/control/jog')
    async def post_jog(req):
        try:
            steps = _int_field(_form(req), 'steps')
        except ValueError as e:
            return str(e), 400
        return move(stepper.target + steps)

    @app.post('/control/halt')
    async def post_halt(req):
        stepper.halt()
        return status()

    @app.post('/control/reset')
    async def post_reset(req):
        try:
            stepper.set_position(settings['start_position'])
        except ValueError as e:
            return str(e), 400
        return status()

    @app.get('/control/settings')
    async def get_settings(req):
        return {k: settings[k] for k in EDITABLE}

    @app.post('/control/settings')
    async def post_settings(req):
        try:
            values = validate_settings(_form(req))
        except ValueError as e:
            return str(e), 400
        if stepper.is_moving:
            return 'stop the focuser before changing settings', 400
        save_settings(state.settings_path, values)
        stepper.configure(values['steps_per_sec'], values['reverse'], values['hold_when_idle'])
        restart_needed = any(values[k] != settings[k] for k in EDITABLE if k not in LIVE)
        for k in LIVE:
            settings[k] = values[k]
        return {'saved': True, 'restart_needed': restart_needed}

    @app.post('/control/restart')
    async def post_restart(req):
        if state.restart is None:
            return 'restart is not available here', 400
        asyncio.create_task(_later(state.restart))      # answer first, then restart
        return {'restarting': True}

    def page():
        html = (PAGE.replace('@NAME@', settings['name'])
                .replace('@POSITION@', str(stepper.position))
                .replace('@START@', str(settings['start_position']))
                .replace('@JOG@', ''.join('<button onclick="jog({0})">{0:+d}</button>'.format(n)
                                          for n in JOG_STEPS)))
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    @app.get('/setup')
    async def setup(req):
        return page()

    @app.get('/setup/v1/focuser/<int:devnum>/setup')
    async def device_setup(req, devnum):
        return page()


PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>@NAME@</title>
<style>
body{font-family:system-ui,sans-serif;max-width:34rem;margin:1rem auto;padding:0 1rem;
background:#111;color:#ddd}h1{font-size:1.3rem}h2{font-size:1rem;margin-top:1.5rem}
.big{font-size:2.4rem;font-variant-numeric:tabular-nums}button,input{font-size:1rem;
padding:.5rem;margin:.15rem;border-radius:.4rem;border:1px solid #555;background:#222;color:#eee}
button{cursor:pointer}#halt{background:#822;width:100%}#warn{color:#fb4}#msg{color:#8c8}
.err{color:#f77!important}label{display:block;margin:.3rem 0}input[type=number]{width:8rem}
</style></head><body>
<h1>@NAME@</h1>
<div class="big" id="pos">@POSITION@</div>
<div id="info">target - | not moving</div><div id="temp"></div><div id="warn"></div>
<h2>Jog</h2><div>@JOG@</div>
<h2>Move</h2><input type="number" id="target" min="0"> <button onclick="moveTo()">Move</button>
<p><button id="halt" onclick="post('/control/halt')">Halt</button></p>
<p><button onclick="if(confirm('Set the current position to @START@ without moving?'))post('/control/reset')">
Reset position to @START@</button></p>
<h2>Settings</h2>
<form id="set" onsubmit="save(event)">
<label>Name <input name="name" maxlength="40"></label>
<label>Max step <input type="number" name="max_step"></label>
<label>Start position <input type="number" name="start_position"></label>
<label>Steps per second <input type="number" name="steps_per_sec"></label>
<label><input type="checkbox" name="reverse"> Reverse direction</label>
<label><input type="checkbox" name="hold_when_idle"> Hold motor when idle</label>
<button>Save</button> <button type="button" id="rs" hidden onclick="restart()">Restart now</button>
</form><p id="msg"></p>
<script>
const $=id=>document.getElementById(id);let loaded=false;
function show(m,bad){$('msg').textContent=m;$('msg').className=bad?'err':''}
async function post(url,data){const r=await fetch(url,{method:'POST',body:new URLSearchParams(data||{})});
const t=await r.text();if(!r.ok){show(t,true);return null}try{return JSON.parse(t)}catch(e){return t}}
function jog(n){post('/control/jog',{steps:n})}
function moveTo(){post('/control/move',{position:$('target').value})}
async function save(e){e.preventDefault();const f=new FormData($('set'));
const r=await post('/control/settings',f);if(r){show(r.restart_needed?'Saved - restart to apply all changes':'Saved');
$('rs').hidden=!r.restart_needed}}
async function restart(){if(await post('/control/restart'))show('Restarting...')}
async function tick(){try{const s=await (await fetch('/control/status')).json();
$('pos').textContent=s.position;$('info').textContent='target '+s.target+' | '+(s.moving?'moving':'not moving');
$('temp').textContent=s.temperature===null?'':'Temperature '+s.temperature.toFixed(1)+' °C';
$('warn').textContent=s.connected?'NINA connected - moves will disturb autofocus':'';
$('target').max=s.max_step;
if(!loaded){const f=$('set');for(const k in s.settings){const el=f.elements[k];
if(el.type==='checkbox')el.checked=s.settings[k];else el.value=s.settings[k]}loaded=true}
}catch(e){$('info').textContent='connection lost'}}
tick();setInterval(tick,1000);
</script></body></html>"""
