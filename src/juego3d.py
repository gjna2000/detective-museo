# =====================================================================
#  EL ROBO DE LA COPA DE ORO - juego 3D con Ursina (versión 4)
#  El cerebro es Prolog: antes de abrir este juego ejecuta  swipl servidor.pl
# =====================================================================
import io, json, math, os, queue, struct, subprocess, sys, tempfile, textwrap, threading
import urllib.parse, urllib.request, wave
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

URL = 'http://127.0.0.1:8080/api/'
AQUI = os.path.dirname(os.path.abspath(__file__))
SONIDO = True
PASOS_SONIDO = False          # sonido de pasos desactivado (ponlo en True para activarlo)
COLORES = {'director': '#7a4fb5', 'guardia': '#2f6fb0', 'restauradora': '#c2557a',
           'guia': '#2f9a7a', 'donante': '#c9a227', 'conserje': '#7b8a96'}
# Cada personaje trabaja en su lugar: (x, z, segundos de pausa, trabajo)
RUTAS = {
    'director': [(-17, 5.5, 7, 'firmar', -17, 7.4), (-13, 8, 3, 'leer', -21, 5), (-15, 1.5, 3, 'pensar', -15, 9)],
    'guardia': [(-3, -3, 2, 'vigilar'), (3, 6, 2, 'vigilar'), (-2, 8.5, 1, 'vigilar'), (-2, 12.5, 3, 'vigilar'),
                (2, 16, 2, 'vigilar'), (-2, 12.5, 1, 'vigilar'), (-2, 8.5, 1, 'vigilar')],
    'restauradora': [(11, 18.5, 8, 'pintar', 11, 20), (13.5, 14, 4, 'examinar', 14.8, 12.5), (11, 12, 3, 'examinar', 7.8, 12.5)],
    'guia': [(-6, -2, 5, 'señalar', 0, 2), (6, 2, 5, 'señalar', 0, 2), (0, 6, 4, 'señalar', 0, 2), (-6, 6, 3, 'señalar', 0, 2)],
    'donante': [(-6, 14, 6, 'admirar', -8.5, 14), (-5, 18, 5, 'admirar', -8.5, 19), (1, 17, 5, 'admirar', 4.5, 19), (1, 13, 4, 'admirar', 0, 22)],
    'conserje': [(7, 6, 4, 'barrer'), (7, 0, 4, 'barrer'), (-7, -3, 4, 'barrer'), (-7, 5, 4, 'barrer')]}
PREGUNTAS = [('Dónde estaba', '¿Dónde estabas a las 8?'), ('Coartada', '¿Quién puede confirmar tu coartada?'),
             ('Uniforme', '¿Llevabas uniforme?'), ('Qué vio', '¿Viste algo raro?'),
             ('Motivos', '¿Tenías algún motivo?'), ('Huella', '¿Tocaste la vitrina?'),
             ('Llaves', '¿Qué llaves tienes?')]
SONIDOS = {'pista': [(660, .1), (880, .15)], 'error': [(160, .35)], 'puerta': [(180, .12), (120, .18)],
           'gana': [(523, .2), (659, .2), (784, .2), (1047, .4)], 'pierde': [(392, .3), (330, .3), (262, .3), (196, .5)]}

SONIDOS['desliza'] = [(220, .06), (160, .14)]


def crear_pasos():                    # pasos: un golpe sordo de ruido filtrado
    import random
    for nombre, grave in (('paso1', .55), ('paso2', .4)):
        ruta = os.path.join(AQUI, f'sfx_{nombre}.wav')
        if os.path.exists(ruta):
            continue
        n, prev = int(22050 * .12), 0.0
        with wave.open(ruta, 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
            for i in range(n):
                prev = prev * (1 - grave) + random.uniform(-1, 1) * grave
                w.writeframes(struct.pack('<h', max(-32000, min(32000, int(26000 * prev * (1 - i / n) ** 2)))))


# ---------------------------------------------------------------- Prolog (HTTP)
CONEXION = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(ruta, **params):
    url = URL + ruta + ('?' + urllib.parse.urlencode(params) if params else '')
    try:
        with CONEXION.open(url, timeout=5) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print('ERROR al consultar Prolog:', url, '->', e)
        return None


# ---------------------------------------------------------------- voz (Windows) y micrófono
WIN = sys.platform.startswith('win')
SIN_VENTANA = 0x08000000
PS_VOZ = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$v = @($s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'es*' } | ForEach-Object { $_.VoiceInfo.Name }); "
          "if ($v.Count -gt 0) { $s.SelectVoice($v[[int]$env:TTS_VOZ % $v.Count]) }; "
          "$s.Rate = [int]$env:TTS_RATE; $s.Speak((Get-Content -Raw -Encoding UTF8 $env:TTS_FILE))")
voz_proc = None
cola_mic = queue.Queue()


def decir_en_voz_alta(texto, i):
    global voz_proc
    if not (SONIDO and WIN):
        return
    try:
        if voz_proc and voz_proc.poll() is None:
            voz_proc.kill()
        ruta = os.path.join(tempfile.gettempdir(), 'detective_voz.txt')
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(texto)
        env = dict(os.environ, TTS_FILE=ruta, TTS_VOZ=str(i), TTS_RATE=str(i % 3 - 1))
        voz_proc = subprocess.Popen(['powershell', '-NoProfile', '-Command', PS_VOZ], env=env, creationflags=SIN_VENTANA)
    except Exception as e:
        print('ERROR de voz:', e)


def revisar_voces():
    if not WIN:
        return
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command',
                            "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer)"
                            ".GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name + ' (' + $_.VoiceInfo.Culture.Name + ')' }"],
                           capture_output=True, text=True, timeout=25, creationflags=SIN_VENTANA)
        es = [l for l in r.stdout.splitlines() if '(es' in l.lower()]
        print('Voces en español:', es if es else 'NINGUNA -> instálalas en Configuración > Hora e idioma > Voz')
    except Exception as e:
        print('ERROR revisando voces:', e)


def hilo_mic():                       # graba 5 s con sounddevice y lo pasa a texto (necesita internet)
    try:
        import sounddevice as sd
        import speech_recognition as sr
        fs = 16000
        datos = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(fs); w.writeframes(datos.tobytes())
        buf.seek(0)
        r = sr.Recognizer()
        with sr.AudioFile(buf) as f:
            audio = r.record(f)
        cola_mic.put((True, r.recognize_google(audio, language='es-CO')))
    except ImportError:
        cola_mic.put((False, 'Falta instalar:  pip install sounddevice SpeechRecognition'))
    except Exception as e:
        print('ERROR de micrófono:', type(e).__name__, e)
        cola_mic.put((False, 'No te entendí. Habla más cerca y claro, o escribe la pregunta.'))


def crear_wavs():
    for nombre, notas in SONIDOS.items():
        ruta = os.path.join(AQUI, f'sfx_{nombre}.wav')
        if os.path.exists(ruta):
            continue
        with wave.open(ruta, 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
            for f, d in notas:
                n = int(22050 * d)
                for i in range(n):
                    w.writeframes(struct.pack('<h', int(9000 * math.sin(2 * math.pi * f * i / 22050) * (1 - i / n))))


# ---------------------------------------------------------------- arranque
crear_wavs()
crear_pasos()
threading.Thread(target=revisar_voces, daemon=True).start()
app = Ursina(title='El robo de la Copa de Oro')
window.color = color.hex('#0b1410')
for contador in ('fps_counter', 'entity_counter', 'collider_counter'):   # oculta los números de depuración
    if hasattr(window, contador):
        getattr(window, contador).enabled = False
sfx = {}
for k in list(SONIDOS) + ['paso1', 'paso2']:
    try:
        sfx[k] = Audio(f'sfx_{k}.wav', autoplay=False)
    except Exception:
        pass
try:
    sfx['pasoN'] = Audio('sfx_paso2.wav', autoplay=False)
except Exception:
    pass

datos = api('personas')
if not datos:
    Text('No se pudo conectar con Prolog.\n\nEn otra terminal ejecuta:\n   cd src\n   swipl servidor.pl\n\nLuego abre este juego de nuevo.',
         origin=(0, 0), scale=1.6, color=color.orange)
    app.run()
    raise SystemExit

try:
    from ursina.shaders import basic_lighting_shader as SH
except Exception:
    SH = None


def Obj(**k):
    if SH:
        k.setdefault('shader', SH)
    return Entity(**k)


def hex_(c):
    return color.hex(c)


if SH:
    DirectionalLight(shadows=False, rotation=(50, -30, 0))
    AmbientLight(color=Color(.55, .55, .6, 1))


# ---------------------------------------------------------------- el museo
ALTO = 3.2


def muro(x1, z1, x2, z2, c='#cfc6ae'):
    Obj(model='cube', position=((x1 + x2) / 2, ALTO / 2, (z1 + z2) / 2), color=hex_(c), collider='box',
        scale=(abs(x2 - x1) or .4, ALTO, abs(z2 - z1) or .4))


def etiqueta(texto, pos, esc=14, col=color.white, padre=None):
    return Text(texto, parent=padre or scene, position=pos, scale=esc * .5, origin=(0, 0), billboard=True, color=col)


def caja(pos, esc, c, colision=False):
    return Obj(model='cube', position=pos, scale=esc, color=hex_(c) if isinstance(c, str) else c,
               collider='box' if colision else None)


def torno(perfil, seg=18):            # sólido de revolución: jarrones, copas, cuerpos...
    v, n = [], []
    for (r1, y1), (r2, y2) in zip(perfil, perfil[1:]):
        nr, ny = y2 - y1, -(r2 - r1)
        L = math.hypot(nr, ny) or 1
        for j in range(seg):
            a, b = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
            P = lambda r, y, t: Vec3(r * math.cos(t), y, r * math.sin(t))
            v += [P(r1, y1, a), P(r2, y2, a), P(r2, y2, b), P(r1, y1, a), P(r2, y2, b), P(r1, y1, b)]
            n += [Vec3(nr / L * math.cos((a + b) / 2), ny / L, nr / L * math.sin((a + b) / 2))] * 6
    return Mesh(vertices=v, normals=n, mode='triangle')


def forma(perfil, pos, c, esc=1, **kw):
    return Obj(model=torno(perfil), position=pos, scale=esc, color=hex_(c) if isinstance(c, str) else c, double_sided=True, **kw)


COPA = [(0, 0), (.38, 0), (.38, .1), (.12, .2), (.1, .6), (.36, 1.0), (.44, 1.3), (.3, 1.3), (0, 1.2)]
AMFORA = [(0, 0), (.22, 0), (.4, .3), (.46, .6), (.34, .95), (.16, 1.15), (.2, 1.25), (.3, 1.3), (0, 1.3)]
COLUMNA = [(0, 0), (.55, 0), (.55, .2), (.38, .28), (.38, 2.95), (.55, 3.05), (.55, 3.2), (0, 3.2)]
TOGA = [(0, 0), (.62, 0), (.55, .5), (.42, 1.0), (.48, 1.3), (.3, 1.5), (.14, 1.6), (0, 1.6)]


def copa_dorada(x, y, z): forma(COPA, (x, y, z), '#d4a62a', .5)
def anfora(x, y, z, c='#a5623a'): forma(AMFORA, (x, y, z), c, .6)
def busto(x, y, z):
    forma([(0, 0), (.3, 0), (.3, .15), (.2, .3), (.28, .55), (0, .6)], (x, y, z), '#cfc8b4', .8)
    Obj(model='sphere', position=(x, y + .85, z), scale=.32, color=hex_('#cfc8b4'))


def cuadro(x, y, z, rot, w, h, cielo, suelo):            # el cuadro mira hacia donde apunta rot
    m = Entity(position=(x, y, z), rotation_y=rot)
    Obj(parent=m, model='cube', scale=(w + .24, h + .24, .1), color=hex_('#4a3220'))
    Obj(parent=m, model='cube', position=(0, 0, .04), scale=(w, h, .05), color=hex_(cielo))
    Obj(parent=m, model='cube', position=(0, -h / 3, .07), scale=(w, h / 3, .03), color=hex_(suelo))
    Obj(parent=m, model='sphere', position=(w / 5, h / 6, .07), scale=(h / 4, h / 4, .03), color=hex_('#f2c94c'))


def vitrina(x, z, objeto=None):
    caja((x, .5, z), (1.4, 1, 1.4), '#2a3036', True)
    caja((x, 1.55, z), (1.4, 1.1, 1.4), Color(.6, .85, 1, .22))
    if objeto:
        objeto(x, 1.0, z)


Obj(model='plane', scale=(48, 1, 38), position=(0, 0, 4), color=hex_('#1b2024'), collider='box')
SALAS = [('Entrada', 0, -9, 12, 6, '#1f4a47'), ('Atrio', 0, 2, 20, 16, '#3d4a52'),
         ('Oficina del director', -16, 4, 12, 12, '#5a3d2b'), ('Sala de interrogatorio', 16, 4, 12, 12, '#5a2530'),
         ('Sala de trofeos', -2, 16, 16, 12, '#46505a'), ('Bodega y taller', 11, 16, 10, 12, '#4a463d')]
for nombre, cx, cz, w, d, c in SALAS:
    Obj(model='plane', scale=(w, 1, d), position=(cx, .03, cz), color=hex_(c))
    etiqueta(nombre, (cx, 2.8, cz), 12, color.yellow)
MUROS = [(-6, -12, 6, -12), (-6, -12, -6, -6), (6, -12, 6, -6), (-10, -6, -2, -6), (2, -6, 10, -6),
         (-10, -6, -10, 2), (-10, 5, -10, 22), (10, -6, 10, 2), (10, 5, 10, 10),
         (-22, -2, -10, -2), (10, -2, 22, -2), (-22, -2, -22, 10), (22, -2, 22, 10),
         (-22, 10, -4, 10), (0, 10, 22, 10), (-10, 22, 16, 22), (6, 10, 6, 14), (6, 17, 6, 22), (16, 10, 16, 22)]
for m in MUROS:
    muro(*m)

# atrio: estatua, columnas, ánforas y cuadros
caja((0, .4, 2), (2.6, .8, 2.6), '#8a8f94', True)
forma(TOGA, (0, .8, 2), '#b08d4a')
Obj(model='sphere', position=(0, 2.62, 2), scale=.42, color=hex_('#b08d4a'))
etiqueta('El Fundador - bronce, 1887', (0, 3.15, 2), 6)
for x, z in [(-8, -4), (8, -4), (-8, 8), (8, 8)]:
    forma(COLUMNA, (x, 0, z), '#cfc8b4', collider='box')
for x in (-5, 5):
    caja((x, .5, 8.3), (.9, 1, .9), '#8a8f94', True)
    anfora(x, 1, 8.3)
cuadro(-9.72, 2, -3, 90, 2.4, 1.6, '#7ab7d4', '#4f7a3a'); cuadro(-9.72, 2, 7.5, 90, 2.4, 1.6, '#e8a96b', '#6b4a2e')
cuadro(9.72, 2, -3, -90, 2.4, 1.6, '#9bb7a0', '#3a5a4a'); cuadro(9.72, 2, 7.5, -90, 2.4, 1.6, '#c98a9b', '#5a3d5a')
# entrada
caja((0, .55, -9.6), (4, 1.1, 1), '#6b4a2e', True)
etiqueta('Recepción', (0, 1.6, -9.6), 8)
etiqueta('MUSEO REGIONAL - Bienvenidos', (0, 2.5, -11.6), 8, color.gold)
caja((-4, .3, -10.8), (3, .6, .8), '#5a3d2b'); caja((4, .3, -10.8), (3, .6, .8), '#5a3d2b')
# sala de trofeos
vitrina(-8.5, 14, copa_dorada); vitrina(-8.5, 19, busto); vitrina(4.5, 19, anfora); vitrina(-2, 20)
etiqueta('Vitrina de la Copa de Oro (vacía)', (-2, 2.5, 20), 7)
cuadro(-7, 2.1, 21.72, 180, 2.4, 1.6, '#e0c27a', '#7a4a2a'); cuadro(3, 2.1, 21.72, 180, 2.4, 1.6, '#8fa6c9', '#3a4a6a')
cuadro(-9.72, 2.1, 16.5, 90, 2, 1.4, '#a8c98f', '#4a6a3a')
# oficina
caja((-17, .5, 7.4), (3, 1, 1.4), '#6b4a2e', True); caja((-17, 1.03, 7.4), (.8, .05, .5), '#f0ead8')
caja((-21.3, 1.2, 3), (.8, 2.4, 4), '#4a3220', True)
Obj(model='sphere', position=(-16, 1.3, 7.4), scale=.5, color=hex_('#3a78b0'))
cuadro(-21.72, 2.1, 8, 90, 2, 1.4, '#c9a8d8', '#5a3d5a')
# bodega y taller
caja((11, .5, 21.2), (4, 1, 1), '#7a6a50', True)
caja((10.5, .95, 19.9), (.06, 1.9, .06), '#7b5a3a'); caja((11.5, .95, 19.9), (.06, 1.9, .06), '#7b5a3a')
caja((11, 1.35, 19.85), (1.1, 1, .05), '#e8dcc0'); caja((11, 1.3, 19.82), (.5, .4, .03), '#c2557a'); caja((11.25, 1.55, 19.82), (.3, .25, .03), '#3a78b0')
caja((7.5, .5, 21), (1.2, 1, 1.2), '#7b5a3a', True); caja((14.8, .5, 21), (1.2, 1, 1.2), '#7b5a3a', True)
caja((7.8, .5, 12.5), (1.2, 1, 1.2), '#7b5a3a', True); anfora(7.8, 1, 12.5, '#8a5a3a')
caja((14.8, .5, 12.5), (1.2, 1, 1.2), '#7b5a3a', True); anfora(14.8, 1, 12.5, '#b0704a')
# sala de interrogatorio
caja((16, .5, 4.2), (3.2, 1, 1.3), '#6b4a2e', True)
caja((16, .25, 6.6), (.9, .5, .9), '#3a2a1c')
Obj(model='sphere', position=(16, 2.7, 4.2), scale=.35, color=color.yellow)
caja((16, 1.4, 9.7), (6, 2, .1), Color(.6, .85, 1, .35))
caja((20.5, .5, .6), (2, 1, 1.2), '#d8d2c0', True); caja((20.5, 1.2, .6), (.4, .5, .4), '#222222')
etiqueta('Laboratorio', (20.5, 2.3, .6), 8)
POS_VITRINA, POS_LAB, ASIENTO = Vec3(-2, 0, 18.8), Vec3(20.5, 0, 2.2), Vec3(16, -.28, 6.6)


# ---------------------------------------------------------------- avatares 3D que trabajan
ESTILO = {'director': ('#2b2f4a', '#b3342a', '#b8b8b8', '#e0b48f'), 'guardia': ('#1f3f6b', '#c9a227', '#2b2118', '#d9a679'),
          'restauradora': ('#8a3a5a', '#ecd9b0', '#3a2418', '#e8bf9c'), 'guia': ('#2f7a5a', '#e8e8e8', '#6b4a2e', '#e0b48f'),
          'donante': ('#6a4a8a', '#d8c27a', '#4b3b2a', '#f0c8a8'), 'conserje': ('#6e7a84', '#c9a227', '#2b2b2b', '#c99a73')}
BRAZO = [(0, 0), (.07, 0), (.09, .08), (.085, .5), (.1, .58), (0, .6)]
PIERNA = [(0, 0), (.1, 0), (.12, .1), (.11, .5), (.14, .85), (0, .87)]
TORSO = [(0, .85), (.2, .85), (.25, .98), (.22, 1.22), (.27, 1.5), (.24, 1.62), (.1, 1.7), (0, 1.7)]


class Persona(Entity):
    def __init__(self, id, nombre, cargo):
        self.ruta = RUTAS.get(id, [(0, -9, 5, None)])
        self.casa = Vec3(self.ruta[0][0], 0, self.ruta[0][1])
        super().__init__(position=self.casa)
        self.id, self.nombre, self.cargo = id, nombre, cargo
        self.modo, self.base, self.fase, self.i, self.llego, self.espera = 'quieto', 0, len(nombre), 0, False, 0
        self.camina, self.trabajo, self.habla_hasta = False, None, 0
        traje, detalle, pelo, tez = [hex_(c) for c in ESTILO.get(id, ESTILO['conserje'])]
        oscuro = traje.tint(-.25)
        forma(TORSO, (0, 0, 0), traje, (1.25, 1, .8), parent=self)
        forma([(0, 0), (.08, 0), (.08, .14), (0, .14)], (0, 1.68, 0), tez, parent=self)
        Obj(parent=self, model='sphere', position=(0, 1.96, 0), scale=(.46, .52, .48), color=tez)
        Obj(parent=self, model='sphere', position=(0, 2.03, -.02), scale=(.49, .4, .52), color=pelo)
        Obj(parent=self, model='sphere', position=(0, 1.93, .235), scale=.07, color=tez.tint(-.08))
        for dx in (-.11, .11):
            Obj(parent=self, model='sphere', position=(dx, 1.99, .21), scale=(.1, .075, .05), color=color.white)
            Obj(parent=self, model='sphere', position=(dx, 1.99, .235), scale=.045, color=color.black)
            Obj(parent=self, model='sphere', position=(dx * 2.1, 1.95, 0), scale=.1, color=tez)
            Obj(parent=self, model='cube', position=(dx, 2.07, .22), scale=(.12, .02, .02), color=pelo)
        self.boca = Obj(parent=self, model='cube', position=(0, 1.84, .22), scale=(.12, .03, .03), color=hex_('#6b2b2b'))

        def miembro(x, y, perfil, col, mano=None):          # pivote en el hombro o la cadera
            piv = Entity(parent=self, position=(x, y, 0))
            forma(perfil, (0, -perfil[-1][1], 0), col, parent=piv)
            if mano:
                Obj(parent=piv, model='sphere', position=(0, -perfil[-1][1] - .03, 0), scale=.11, color=mano)
            else:
                Obj(parent=piv, model='sphere', position=(0, -.82, .06), scale=(.2, .12, .34), color=color.black)
            return piv
        self.pi, self.pd = miembro(-.12, .87, PIERNA, oscuro), miembro(.12, .87, PIERNA, oscuro)
        self.bi, self.bd = miembro(-.38, 1.55, BRAZO, traje, tez), miembro(.38, 1.55, BRAZO, traje, tez)
        if id == 'director':
            Obj(parent=self, model='cube', position=(0, 1.38, .2), scale=(.07, .34, .03), color=detalle)
            Obj(parent=self.bi, model='cube', position=(0, -.62, -.1), scale=(.3, .4, .03), color=color.white)
        elif id == 'guardia':
            forma([(0, 0), (.26, 0), (.26, .1), (.2, .16), (0, .16)], (0, 2.2, 0), traje, parent=self)
            Obj(parent=self, model='sphere', position=(.13, 1.45, .2), scale=.07, color=detalle)
            Obj(parent=self.bi, model='cube', position=(0, -.66, -.08), scale=(.07, .3, .07), color=color.black)
        elif id == 'restauradora':
            Obj(parent=self, model='sphere', position=(.05, 2.2, 0), scale=(.5, .14, .5), color=oscuro)
            Obj(parent=self, model='cube', position=(0, 1.1, .2), scale=(.42, .6, .03), color=detalle)
            Obj(parent=self.bd, model='cube', position=(0, -.72, -.1), scale=(.04, .3, .04), color=hex_('#c2557a'))
        elif id == 'guia':
            Obj(parent=self, model='sphere', position=(0, 1.62, 0), scale=(.46, .1, .4), color=detalle)
            Obj(parent=self.bd, model='cube', position=(0, -.9, 0), scale=(.04, .9, .04), color=color.black)
            Obj(parent=self.bd, model='cube', position=(.18, -.55, 0), scale=(.34, .22, .02), color=color.red)
        elif id == 'donante':
            forma([(0, 0), (.4, 0), (.42, .02), (.2, .07), (.2, .2), (0, .2)], (0, 2.16, 0), oscuro, parent=self)
            Obj(parent=self, model='sphere', position=(0, 1.62, .18), scale=.07, color=detalle)
            Obj(parent=self.bi, model='cube', position=(0, -.66, -.1), scale=(.3, .24, .12), color=hex_('#7a2a24'))
        else:
            forma([(0, 0), (.24, 0), (.24, .1), (.18, .14), (0, .14)], (0, 2.18, 0), oscuro, parent=self)
            Obj(parent=self, model='cube', position=(0, 1.2, .2), scale=(.4, .5, .03), color=oscuro)
            Obj(parent=self.bd, model='cube', position=(0, -.9, -.3), scale=(.06, 1.5, .06), color=hex_('#8a6a3a'))
            Obj(parent=self.bd, model='cube', position=(0, -1.62, -.3), scale=(.36, .12, .12), color=hex_('#c9a227'))
        etiqueta(f"{nombre.split()[0]}\n{cargo}", (0, 2.75, 0), 8, color.white, self)

    def rutina(self, dt):                                   # recorre su ruta y hace su oficio
        x, z, pausa, trabajo, *mira = self.ruta[self.i]
        d = Vec3(x - self.x, 0, z - self.z)
        L = d.length()
        if L > .2:
            self.position += d / L * 1.4 * dt
            self.rotation_y = math.degrees(math.atan2(d.x, d.z))
            self.camina, self.trabajo = True, None
        else:
            if not self.llego:
                self.llego, self.espera = True, pausa
            if len(mira) == 2:
                self.rotation_y = math.degrees(math.atan2(mira[0] - self.x, mira[1] - self.z))
            self.camina, self.trabajo = False, trabajo
            self.espera -= dt
            if self.espera <= 0:
                self.i, self.llego = (self.i + 1) % len(self.ruta), False

    def animar(self, t):
        a = math.sin(t * 6) * 35 if self.camina else 0
        self.pi.rotation_x, self.pd.rotation_x, self.bi.rotation_x, self.bd.rotation_x = a, -a, -a, a
        s, tr = math.sin(t * 5), self.trabajo
        if not self.camina:
            if tr in ('pintar', 'firmar'):
                self.bd.rotation_x = -55 + s * 18
            elif tr == 'barrer':
                self.bd.rotation_x, self.bi.rotation_x = -45 + s * 14, -45 - s * 14
            elif tr == 'señalar':
                self.bd.rotation_x = -95 + math.sin(t * 2) * 12
            elif tr == 'examinar':
                self.bd.rotation_x = -60 + s * 8
            elif tr in ('admirar', 'leer', 'pensar'):
                self.bi.rotation_x = -45
            else:
                self.bi.rotation_x, self.bd.rotation_x = s * 4, -s * 4
        if time.time() < self.habla_hasta:                 # habla: mueve la boca y gesticula
            self.boca.scale_y = .03 + abs(math.sin(t * 18)) * .08
            self.bd.rotation_x = min(self.bd.rotation_x, -30 + math.sin(t * 4) * 22)
        else:
            self.boca.scale_y = .03
        self.y = self.base + (abs(math.sin(t * 6)) * .06 if self.camina else math.sin(t * 2 + self.fase) * .02)


personas = [Persona(d['id'], d['nombre'], d['cargo']) for d in datos]
nombre_de = {p.id: p.nombre for p in personas}

# ---------------------------------------------------------------- jugador e interfaz
jugador = FirstPersonController(position=(0, 1.5, -9), speed=6)
notas, rastro = [], []
intentos, panel, actual, buffer, conf, fin_juego, escena_ok, objetivo = 3, False, None, '', False, False, False, None

hud = Text('', parent=camera.ui, position=(.5, .47), color=color.gold)
aviso_t = Text('', parent=camera.ui, position=(0, .42), origin=(0, 0), color=color.white)
prompt = Text('', parent=camera.ui, position=(0, -.4), origin=(0, 0), color=color.yellow, scale=1.2)
Text('WASD mover · Mouse mirar · E interactuar · Tab cuaderno · M plano · Esc cerrar', parent=camera.ui,
     position=(-.88, -.46), scale=.8, color=color.light_gray)

cuad = Entity(parent=camera.ui, enabled=False)
Entity(parent=cuad, model='quad', scale=(.62, .95), position=(-.55, 0), color=Color(.92, .87, .75, .95), z=1)
Text('CUADERNO DEL DETECTIVE', parent=cuad, position=(-.84, .43), color=hex_('#b3342a'), scale=1)
t_cuad = Text('', parent=cuad, position=(-.84, .38), color=hex_('#2b2218'), scale=.85)

ui = Entity(parent=camera.ui, enabled=False)


class Sub:                             # subtítulo con sombra (se lee sin recuadro de fondo)
    def __init__(self, x, y, col, esc=1.05):
        self.s = Text('', parent=ui, position=(x + .0025, y - .0025, .01), color=color.black, scale=esc)
        self.t = Text('', parent=ui, position=(x, y), color=col, scale=esc)

    @property
    def text(self):
        return self.t.text

    @text.setter
    def text(self, v):
        self.t.text = self.s.text = v

    @property
    def enabled(self):
        return self.t.enabled

    @enabled.setter
    def enabled(self, v):
        self.t.enabled = self.s.enabled = v


t_nombre = Sub(-.6, -.14, color.gold, 1.3)
t_resp = Sub(-.6, -.19, color.white, 1.1)
t_entrada = Sub(-.6, -.31, color.cyan, 1.05)
t_pista = Sub(-.6, -.31, color.light_gray, .9)


def boton(texto, x, y, fn, w=.2, col=hex_('#1c3b30')):
    return Button(text=texto, parent=ui, scale=(w, .045), position=(x, y), color=Color(col.r, col.g, col.b, .8), on_click=fn)


def nota(t):
    if t not in notas:
        notas.append(t)
        sonar('pista')
        t_cuad.text = '\n'.join(textwrap.fill('- ' + n, 38) for n in notas[-11:])


def sonar(k):
    if SONIDO and k in sfx:
        sfx[k].play()


def hablar(texto, n):
    n.habla_hasta = time.time() + max(2, len(texto) * .065)
    decir_en_voz_alta(texto, personas.index(n))


def aviso(t, seg=4):
    aviso_t.text = t
    invoke(setattr, aviso_t, 'text', '', delay=seg)


def mostrar(titulo, texto, n=None):
    t_nombre.text = titulo
    t_resp.text = textwrap.fill(texto, 78)
    if n:
        hablar(texto, n)


def mirar_a(n):                                             # la cámara se gira hacia el sospechoso
    if hasattr(jugador, 'camera_pivot'):
        jugador.rotation_y = math.degrees(math.atan2(n.x - jugador.x, n.z - jugador.z))
        jugador.camera_pivot.rotation_x = 6


def abrir(n):
    global panel, actual, buffer, conf
    panel, actual, buffer, conf = True, n, '', False
    jugador.enabled, mouse.locked, ui.enabled, mini.enabled = False, False, True, False
    sala = n.modo == 'sentado'
    for w in W_PREG:
        w.enabled = sala
    b_llevar.enabled = n.modo == 'quieto'
    b_soltar.enabled = n.modo != 'quieto'
    t_entrada.text = '> _' if sala else ''
    b_acusar.text = 'Acusar'
    mirar_a(n)
    mostrar(n.nombre, f'Soy {n.nombre}, {n.cargo[0].lower() + n.cargo[1:]}. ¿Qué se le ofrece, detective?', n)
    t_pista.enabled = not sala
    t_pista.text = '' if sala else 'Para interrogarlo, llévalo a la sala de interrogatorio.'



def abrir_texto(titulo, texto):
    global panel, actual
    panel, actual = True, None
    jugador.enabled, mouse.locked, ui.enabled, mini.enabled = False, False, True, False
    for w in W_PREG + [b_llevar, b_soltar, t_pista]:
        w.enabled = False
    mostrar(titulo, texto)


def cerrar():
    global panel, actual, conf
    panel, actual, conf = False, None, False
    ui.enabled = False
    if not fin_juego:
        jugador.enabled, mouse.locked, mini.enabled = True, True, mapa_on


def preguntar(n, texto):
    d = api('preguntar', persona=n.id, texto=texto)
    if not d:
        return mostrar(n.nombre, 'Sin conexión con Prolog. ¿Sigue abierto servidor.pl?')
    nota(f"{n.nombre.split()[0]}: {d['respuesta']}")
    mostrar(n.nombre, d['respuesta'], n)


def enviar():
    global buffer
    if actual and buffer.strip():
        preguntar(actual, buffer)
    buffer = ''
    t_entrada.text = '> _'


def usar_mic():
    t_entrada.text = '> HABLA AHORA (5 segundos)…'
    aviso('Micrófono activo: habla ahora', 5)
    threading.Thread(target=hilo_mic, daemon=True).start()


def llevar():
    n = actual
    for m in personas:
        if m is not n and m.modo != 'quieto':
            soltar(m, False)
    n.modo, n.position = 'sigue', jugador.position - Vec3(0, jugador.y, 0)
    cerrar()
    sonar('puerta')
    aviso(f'{n.nombre} te acompaña. Llévalo a la sala de interrogatorio.')


def soltar(n=None, cierra=True):
    n = n or actual
    n.modo, n.position, n.base, n.rotation_y, n.i, n.llego = 'quieto', n.casa, 0, 0, 0, False
    if cierra:
        cerrar()
        aviso(f'{n.nombre} vuelve a su trabajo.')


def acusar():
    global conf, intentos
    n = actual
    if not conf:
        conf = True
        b_acusar.text = '¿Seguro? Otra vez'
        return
    conf, b_acusar.text = False, 'Acusar'
    d = api('acusar', persona=n.id)
    if not d:
        return mostrar(n.nombre, 'Sin conexión con Prolog.')
    if d['correcto']:
        return final(True, d)
    intentos -= 1
    sonar('error')
    hud.text = f'Acusaciones: {intentos}'
    if intentos <= 0:
        return final(False, d)
    mostrar('Acusación fallida', f"{n.nombre} no es el culpable. {d['mensaje']} Te quedan {intentos}.")


def final(gano, d):
    global fin_juego
    fin_juego = True
    cerrar()
    jugador.enabled, mouse.locked = False, False
    sonar('gana' if gano else 'pierde')
    p = Entity(parent=camera.ui, z=-2)
    Entity(parent=p, model='quad', scale=(2, 1.2), color=Color(0, 0, 0, .95), z=1)
    Text('¡CASO RESUELTO!' if gano else 'EL CULPABLE ESCAPÓ', parent=p, origin=(0, 0), position=(0, .4),
         scale=2.4, color=color.gold if gano else color.red)
    quien = nombre_de.get(d['culpable'], d['culpable'])
    Text(textwrap.fill(f'El culpable era {quien}. Pruebas:', 70) + '\n' + '\n'.join('- ' + r for r in d['razones']),
         parent=p, position=(-.6, .3), color=color.white)
    Text('Ranking de sospecha\n' + '\n'.join(f"{nombre_de.get(r['persona'], r['persona'])}: {'#' * r['puntaje']} {r['puntaje']}"
                                            for r in d['ranking']), parent=p, position=(-.6, -.05), color=color.orange)
    Button(text='Salir', parent=p, scale=(.2, .06), position=(0, -.45), on_click=application.quit)


def accion_vitrina():
    global escena_ok
    d = api('escena')
    if not d:
        return abrir_texto('Escena', 'Sin conexión con Prolog.')
    escena_ok = True
    for t in d['pistas']:
        nota(t)
    abrir_texto('Escena del robo', ' '.join(d['pistas']))


def accion_lab():
    if not escena_ok:
        return abrir_texto('Laboratorio', 'Primero examina la vitrina de la copa para tomar una muestra de la huella.')
    d = api('huella')
    q = ' y '.join(nombre_de.get(c, c) for c in d['coincidencias'])
    nota(f'La huella coincide con: {q}.')
    abrir_texto('Laboratorio', f"La huella coincide con {q}. {d['aviso']}")


OBJETOS = [(POS_VITRINA, 'examinar la vitrina de la copa', accion_vitrina), (POS_LAB, 'analizar la huella', accion_lab)]

W_PREG = [boton(t, -.675 + i * .225, -.37, lambda q=q: actual and preguntar(actual, q), .21) for i, (t, q) in enumerate(PREGUNTAS)]
b_mic = boton('Micrófono', -.62, -.43, usar_mic, .28, hex_('#3a3a6a'))
b_env = boton('Preguntar', -.31, -.43, enviar, .28, hex_('#27503f'))
b_acusar = boton('Acusar', 0, -.43, acusar, .28, hex_('#7a2a24'))
b_llevar = boton('Llevar a la sala de interrogatorio', -.3, -.43, llevar, .55, hex_('#27503f'))
b_soltar = boton('Soltar', .31, -.43, lambda: soltar(), .28)
boton('Cerrar', .62, -.43, cerrar, .28)
W_PREG += [b_mic, b_env, b_acusar, t_entrada]
hud.text = f'Acusaciones: {intentos}'
# (la misión se avisa al pulsar JUGAR)


# ---------------------------------------------------------------- plano, puertas y pasos
mapa_on, t_paso, t_npc, paso_alt = True, 0, 0, 0
ESC_M, CENT = .5 / 44, (0, 5)


def a_mapa(x, z):
    return ((x - CENT[0]) * ESC_M, (z - CENT[1]) * ESC_M)


mini = Entity(parent=camera.ui, position=(.62, .235))
Entity(parent=mini, model='quad', scale=(.52, 34 * ESC_M + .03), color=Color(0, 0, 0, .65), z=1)
Text('PLANO DEL MUSEO  (M)', parent=mini, position=(0, 34 * ESC_M / 2 + .026), origin=(0, 0), scale=.6, color=color.gold)
for (nombre, cx, cz, w, d, c), corto in zip(SALAS, ['Entrada', 'Atrio', 'Oficina', 'Interrogatorio', 'Trofeos', 'Bodega']):
    px, py = a_mapa(cx, cz)
    Entity(parent=mini, model='quad', position=(px, py), scale=(w * ESC_M + .004, d * ESC_M + .004), color=hex_('#d9cfae'), z=.6)
    Entity(parent=mini, model='quad', position=(px, py), scale=(w * ESC_M - .001, d * ESC_M - .001), color=hex_(c), z=.5)
    Text(corto, parent=mini, position=(px, py), origin=(0, 0), scale=.5, color=color.white, z=-.05)
pt_j = Entity(parent=mini, model='circle', scale=.018, color=color.yellow, z=-.1)
pt_dir = Entity(parent=mini, model='circle', scale=.009, color=color.orange, z=-.2)
pts = {n.id: Entity(parent=mini, model='circle', scale=.012, color=hex_(COLORES.get(n.id, '#888888')), z=-.1) for n in personas}


class Puerta:                          # puerta corrediza: se abre sola cuando alguien se acerca
    def __init__(self, x, z, eje, ancho, sentido):
        self.cerrada = Vec3(x, ALTO / 2, z)
        self.abierta = self.cerrada + (Vec3(sentido * ancho, 0, 0) if eje == 'x' else Vec3(0, 0, sentido * ancho))
        esc = (ancho, ALTO, .25) if eje == 'x' else (.25, ALTO, ancho)
        self.hoja = Obj(model='cube', position=self.cerrada, scale=esc, color=hex_('#7a5a34'), collider='box')
        self.abierto = False

    def actualizar(self, cerca, se_oye):
        if cerca != self.abierto:
            self.abierto = cerca
            self.hoja.collider = None if cerca else 'box'
            if se_oye:
                sonar('desliza')
        self.hoja.position = lerp(self.hoja.position, self.abierta if cerca else self.cerrada, min(1, 7 * time.dt))


PUERTAS = [Puerta(0, -6, 'x', 4, 1), Puerta(-10, 3.5, 'z', 3, 1), Puerta(10, 3.5, 'z', 3, -1),
           Puerta(-2, 10, 'x', 4, -1), Puerta(6, 15.5, 'z', 3, 1)]


# ---------------------------------------------------------------- lógica del juego
def en_sala(p):
    return 10.5 < p.x < 21.5 and 0 < p.z < 9.5


def sentar(n):
    n.modo, n.base, n.rotation_y, n.camina, n.trabajo = 'sentado', -.28, 180, False, None
    n.position = ASIENTO
    sonar('puerta')
    aviso(f'{n.nombre} se sienta. Acércate a la mesa y pulsa E.')


def update():
    global objetivo, t_paso, t_npc, paso_alt
    if fin_juego or en_menu:
        return
    p = Vec3(jugador.x, 0, jugador.z)
    if not rastro or distance_xz(p, rastro[-1]) > .4:
        rastro.append(p)
        del rastro[:-200]
    for pu in PUERTAS:                                          # puertas corredizas
        pu.actualizar(any(distance_xz(pu.cerrada, q) < 3.3 for q in [p] + [n.position for n in personas]),
                      distance_xz(pu.cerrada, p) < 10)
    x, y = a_mapa(p.x, p.z)                                      # plano del museo
    pt_j.position = (x, y)
    ang = math.radians(jugador.rotation_y)
    pt_dir.position = (x + math.sin(ang) * .017, y + math.cos(ang) * .017)
    for n in personas:
        pts[n.id].position = a_mapa(n.x, n.z)
    t_paso, t_npc = t_paso - time.dt, t_npc - time.dt            # pasos
    if PASOS_SONIDO and jugador.enabled and any(held_keys[k] for k in ('w', 'a', 's', 'd')) and t_paso <= 0:
        sonar('paso1' if paso_alt else 'paso2')
        paso_alt, t_paso = paso_alt ^ 1, .42
    if PASOS_SONIDO and t_npc <= 0:
        d = min([distance_xz(n.position, p) for n in personas if n.camina] or [99])
        if d < 12 and 'pasoN' in sfx:
            sfx['pasoN'].volume = .5 * (1 - d / 12)
            sonar('pasoN')
        t_npc = .55
    for n in personas:
        if n.modo == 'sigue':
            if en_sala(p):
                sentar(n)
            else:
                antes = Vec3(n.position)
                n.position = lerp(n.position, rastro[max(0, len(rastro) - 9)], min(1, 8 * time.dt))
                n.rotation_y = math.degrees(math.atan2(p.x - n.x, p.z - n.z))
                n.camina, n.trabajo = distance_xz(antes, n.position) > .01, None
        elif n.modo == 'quieto':
            if distance_xz(n.position, p) < 3 or actual is n:        # se detiene a atenderte
                n.camina, n.trabajo = False, None
                n.rotation_y = math.degrees(math.atan2(p.x - n.x, p.z - n.z))
            else:
                n.rutina(time.dt)
        n.animar(time.time())
    while not cola_mic.empty():
        ok, texto = cola_mic.get()
        if panel and actual and actual.modo == 'sentado':
            t_entrada.text = '> _'
            if ok:
                preguntar(actual, texto)
            else:
                mostrar(actual.nombre, texto)
    objetivo = None
    mejor = 4
    for n in personas:
        d = distance_xz(n.position, p)
        if d < (5 if n.modo == 'sentado' else mejor):
            if d < mejor or n.modo == 'sentado':
                mejor, objetivo = min(d, mejor), ('n', n)
    for o in OBJETOS:
        d = distance_xz(o[0], p)
        if d < mejor:
            mejor, objetivo = d, ('o', o)
    prompt.text = '' if panel or not objetivo else 'E: ' + (
        f'hablar con {objetivo[1].nombre}' if objetivo[0] == 'n' else objetivo[1][1])


def input(key):
    global buffer, mapa_on
    if fin_juego or en_menu:
        return
    if panel:
        if key == 'escape':
            cerrar()
        elif actual and actual.modo == 'sentado':
            if key == 'enter':
                enviar()
                return
            elif key == 'backspace':
                buffer = buffer[:-1]
            elif key == 'space':
                buffer += ' '
            else:
                k = key.replace('shift ', '')
                if len(k) == 1 and k.isalnum() and len(buffer) < 90:
                    buffer += k
            t_entrada.text = '> ' + buffer + '_'
        return
    if key == 'e' and objetivo:
        abrir(objetivo[1]) if objetivo[0] == 'n' else objetivo[1][2]()
    elif key == 'escape':
        abrir_menu(False)
    elif key == 'tab':
        cuad.enabled = not cuad.enabled
    elif key == 'm':
        mapa_on = not mapa_on
        mini.enabled = mapa_on


# ---------------------------------------------------------------- menú principal y de pausa
en_menu, mision_dada = True, False
if hasattr(jugador, 'cursor'):                                  # mira discreta
    jugador.cursor.color, jugador.cursor.scale = Color(1, 1, 1, .7), .006
menu = Entity(parent=camera.ui, z=-3)
Entity(parent=menu, model='quad', scale=(2, 1.2), color=Color(.02, .06, .045, .86), z=1)
for yy in (.33, -.2):
    Entity(parent=menu, model='quad', scale=(1.0, .004), position=(0, yy), color=hex_('#c79a3b'), z=.5)
Text('EL ROBO DE LA', parent=menu, origin=(0, 0), position=(0, .27), scale=1.8, color=color.light_gray)
Text('COPA DE ORO', parent=menu, origin=(0, 0), position=(0, .19), scale=3.6, color=color.gold)
Text('Un juego de detectives con Prolog', parent=menu, origin=(0, 0), position=(0, .09), scale=1.2, color=color.light_gray)
b_jugar = Button(text='JUGAR', parent=menu, scale=(.34, .075), position=(0, -.03), color=hex_('#27503f'))
b_salir = Button(text='SALIR', parent=menu, scale=(.34, .075), position=(0, -.13), color=hex_('#7a2a24'), on_click=application.quit)
Text('WASD moverte  ·  E hablar  ·  Tab cuaderno  ·  M plano  ·  Esc pausa', parent=menu, origin=(0, 0),
     position=(0, -.27), scale=.9, color=color.light_gray)


def abrir_menu(inicio):
    global en_menu
    en_menu = True
    menu.enabled = True
    b_jugar.text = 'JUGAR' if inicio else 'CONTINUAR'
    jugador.enabled, mouse.locked, mini.enabled, cuad.enabled = False, False, False, False
    for e in (hud, prompt, aviso_t):
        e.enabled = False


def empezar():
    global en_menu, mision_dada
    en_menu = False
    menu.enabled = False
    jugador.enabled, mouse.locked, mini.enabled = True, True, mapa_on
    for e in (hud, prompt, aviso_t):
        e.enabled = True
    if not mision_dada:
        mision_dada = True
        aviso('Misión: examina la vitrina, lleva a los 6 a la SALA DE INTERROGATORIO (puerta este del atrio) y acusa al culpable.', 9)


b_jugar.on_click = empezar
abrir_menu(True)
app.run()
