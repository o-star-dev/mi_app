from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
import requests
import re
import threading

# 🔑 PEGA TU API KEY AQUI
API_KEY = "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"

# --- CONFIGURACIÓN GENERAL ---
Window.clearcolor = (0.08, 0.08, 0.1, 1)
TAMANO_FUENTE = dp(18)
ANCHO_MENSAJE = dp(300)
RADIO_BORDE = dp(20)


# --- ETIQUETA DE MENSAJE ---
class EtiquetaMensaje(Label):
    def __init__(self, texto, es_usuario=False, **kwargs):
        super().__init__(**kwargs)
        self.text = texto
        self.size_hint = (None, None)
        self.text_size = (ANCHO_MENSAJE, None)
        self.padding = (dp(20), dp(15))
        self.color = (1, 1, 1, 1)
        self.halign = "left"
        self.valign = "middle"
        self.font_size = TAMANO_FUENTE
        
        if es_usuario:
            color_fondo = (0.2, 0.4, 0.8, 1)
            self.pos_hint = {"right": 0.95}
        else:
            color_fondo = (0.35, 0.35, 0.45, 1)
            self.pos_hint = {"left": 0.05}
        
        with self.canvas.before:
            Color(*color_fondo)
            self.fondo = RoundedRectangle(size=self.size, pos=self.pos, radius=[RADIO_BORDE])
        
        self.bind(texture_size=self.actualizar_tamano, size=self.actualizar_fondo)

    def actualizar_tamano(self, *args):
        self.size = (min(self.texture_size[0] + dp(40), ANCHO_MENSAJE), self.texture_size[1] + dp(30))

    def actualizar_fondo(self, *args):
        self.fondo.size = self.size
        self.fondo.pos = self.pos


# --- ÁREA DE MENSAJES ---
class HistorialMensajes(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", spacing=dp(20), padding=[dp(20), dp(20), dp(20), dp(20)])
        self.layout.size_hint_y = None
        self.layout.bind(minimum_height=self.layout.setter("height"))
        self.add_widget(self.layout)
        
        with self.canvas.before:
            Color(0.12, 0.12, 0.15, 1)
            self.fondo = RoundedRectangle(size=self.size, pos=self.pos, radius=[RADIO_BORDE])
        self.bind(size=self.actualizar_fondo, pos=self.actualizar_fondo)

    def actualizar_fondo(self, *args):
        self.fondo.size = self.size
        self.fondo.pos = self.pos

    def agregar_mensaje(self, texto, es_usuario=False):
        lbl = EtiquetaMensaje(texto, es_usuario)
        self.layout.add_widget(lbl)
        self.scroll_y = 0  # Mover scroll al final

    def agregar_indicador_carga(self):
        """Agrega los tres puntos animados"""
        self.indicador = Label(
            text="...",
            font_size=TAMANO_FUENTE,
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(None, None),
            size=(dp(60), dp(50)),
            pos_hint={"left": 0.05}
        )
        with self.indicador.canvas.before:
            Color(0.35, 0.35, 0.45, 1)
            RoundedRectangle(size=self.indicador.size, pos=self.indicador.pos, radius=[RADIO_BORDE])
        self.layout.add_widget(self.indicador)
        self.scroll_y = 0
        
        # Animación de los puntos
        self.contador_puntos = 0
        Clock.schedule_interval(self.animar_puntos, 0.5)

    def animar_puntos(self, dt):
        """Cambia el número de puntos para dar efecto de carga"""
        self.contador_puntos = (self.contador_puntos + 1) % 4
        self.indicador.text = "." * self.contador_puntos if self.contador_puntos !=0 else "..."

    def quitar_indicador_carga(self):
        """Elimina el indicador cuando termina la respuesta"""
        Clock.unschedule(self.animar_puntos)
        self.layout.remove_widget(self.indicador)


# --- APP PRINCIPAL ---
class IAConversacionalApp(App):
    def build(self):
        self.title = "Mi IA Amiga"
        self.historial = []
        self.altura_entrada = dp(80)
        self.ia_respondiendo = False
        
        # Layout principal
        self.layout_principal = BoxLayout(orientation="vertical", spacing=dp(15), padding=dp(15))
        
        # Área de mensajes (solo muestra mensajes enviados)
        self.area_mensajes = HistorialMensajes(size_hint=(1, 1))
        self.layout_principal.add_widget(self.area_mensajes)
        
        # Layout de entrada (donde se escribe – siempre visible abajo)
        self.layout_entrada = BoxLayout(orientation="horizontal", spacing=dp(15), size_hint=(1, None), height=self.altura_entrada)
        
        # Input donde se ve el texto mientras se escribe (sin superposiciones)
        self.input_texto = TextInput(
            hint_text="Escribe tu mensaje...",
            size_hint=(0.75, 1),
            background_color=(0.15, 0.15, 0.2, 1),
            foreground_color=(1, 1, 1, 1),
            multiline=False,
            font_size=TAMANO_FUENTE,
            padding=[dp(20), dp(15)],
            cursor_color=(0.3, 0.6, 0.9, 1)
        )
        # Borde redondeado input
        with self.input_texto.canvas.before:
            Color(0.25, 0.25, 0.3, 1)
            self.borde_input = RoundedRectangle(size=self.input_texto.size, pos=self.input_texto.pos, radius=[RADIO_BORDE])
        self.input_texto.bind(
            size=self.actualizar_borde_input,
            pos=self.actualizar_borde_input,
            on_text_validate=self.enviar_mensaje
        )
        
        # Botón de enviar
        self.btn_enviar = Button(
            text="Enviar",
            size_hint=(0.25, 1),
            background_color=(0.2, 0.6, 0.3, 1),
            color=(1, 1, 1, 1),
            font_size=TAMANO_FUENTE,
            bold=True
        )
        # Borde redondeado botón
        with self.btn_enviar.canvas.before:
            Color(0.2, 0.6, 0.3, 1)
            self.borde_boton = RoundedRectangle(size=self.btn_enviar.size, pos=self.btn_enviar.pos, radius=[RADIO_BORDE])
        self.btn_enviar.bind(
            on_press=self.enviar_mensaje,
            size=self.actualizar_borde_boton,
            pos=self.actualizar_borde_boton
        )
        
        self.layout_entrada.add_widget(self.input_texto)
        self.layout_entrada.add_widget(self.btn_enviar)
        self.layout_principal.add_widget(self.layout_entrada)
        
        # Manejo del teclado
        Window.bind(on_keyboard=self.manejar_teclado, on_resize=self.ajustar_tamano)
        
        # Mensaje de bienvenida
        self.area_mensajes.agregar_mensaje("¡Hola! Soy tu IA amiga 😊 ¿Qué tal tu día?")
        return self.layout_principal

    def manejar_teclado(self, window, key, *args):
        """Ajusta el layout sin superposiciones"""
        if key == 27:  # Tecla de retroceso
            self.layout_entrada.height = self.altura_entrada
            self.area_mensajes.size_hint = (1, 1)
            return True
        elif args[0] == 'textinput' and args[1] == 'focus':
            if args[2]:  # Teclado abierto
                self.layout_entrada.height = self.altura_entrada
                self.area_mensajes.size_hint = (1, 0.7)
                # Mover scroll al final para no tapar mensajes
                self.area_mensajes.scroll_y = 0
            else:  # Teclado cerrado
                self.area_mensajes.size_hint = (1, 1)
        return False

    def ajustar_tamano(self, *args):
        """Ajusta bordes cuando cambia el tamaño de la pantalla"""
        self.actualizar_borde_input()
        self.actualizar_borde_boton()

    def actualizar_borde_input(self, *args):
        """Mantiene el borde del input en su lugar"""
        self.borde_input.size = self.input_texto.size
        self.borde_input.pos = self.input_texto.pos

    def actualizar_borde_boton(self, *args):
        """Mantiene el borde del botón en su lugar"""
        self.borde_boton.size = self.btn_enviar.size
        self.borde_boton.pos = self.btn_enviar.pos

    def limpiar_texto(self, texto):
        texto = re.sub(r"#{1,6}.*", "", texto)
        texto = re.sub(r"\*\*.*?\*\*", "", texto)
        texto = re.sub(r"<.*?>", "", texto)
        texto = re.sub(r"[\n\t]", " ", texto)
        return texto.strip()

    def obtener_respuesta_ia(self, texto_usuario):
        """Obtener respuesta en hilo separado"""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "Mi IA Amiga"
        }

        self.historial.append({"role": "user", "content": texto_usuario})
        data = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [
                {"role": "system", "content": (
                    "Habla SIEMPRE en español. Eres amable, natural y cercana. "
                    "Responde concisamente, sin saltos de línea innecesarios y usa emojis de vez en cuando. "
                    "No repitas mensajes anteriores."
                )}
            ] + self.historial,
            "temperature": 0.7,
            "max_tokens": 150
        }

        try:
            r = requests.post(url, headers=headers, json=data, timeout=20)
            r.raise_for_status()
            respuesta = self.limpiar_texto(r.json()["choices"][0]["message"]["content"])
            self.historial.append({"role": "assistant", "content": respuesta})
        except Exception:
            respuesta = "Perdón, tuve un problema para responder 😅 ¿Podemos intentarlo de nuevo?"
        
        # Mostrar respuesta cuando termine
        Clock.schedule_once(lambda dt: self.mostrar_respuesta(respuesta), 0)

    def enviar_mensaje(self, *args):
        texto = self.input_texto.text.strip()
        if not texto or self.ia_respondiendo:
            return
        
        # Desactivar controles mientras responde
        self.ia_respondiendo = True
        self.btn_enviar.disabled = True
        self.input_texto.disabled = True
        self.input_texto.text = ""  # Limpiar input después de enviar
        
        # Agregar mensaje definitivo del usuario al área de mensajes
        self.area_mensajes.agregar_mensaje(texto, es_usuario=True)
        
        # Mostrar indicador de carga
        self.area_mensajes.agregar_indicador_carga()
        
        # Obtener respuesta en hilo separado
        threading.Thread(target=self.obtener_respuesta_ia, args=(texto,), daemon=True).start()

    def mostrar_respuesta(self, respuesta):
        """Mostrar respuesta y reactivar controles"""
        self.area_mensajes.quitar_indicador_carga()
        self.area_mensajes.agregar_mensaje(respuesta)
        self.ia_respondiendo = False
        self.btn_enviar.disabled = False
        self.input_texto.disabled = False
        self.input_texto.focus = True  # Mantener foco en el input


if __name__ == "__main__":
    IAConversacionalApp().run()
