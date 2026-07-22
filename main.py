"""
ELK-BLEDOM Bluetooth LED Serit Kontrol - Mobil Uygulama
Kivy + kivy_bleak ile Android icin BLE LED kontrol.
"""

import os
import sys
import time
import colorsys
import random
import threading
from datetime import datetime

os.environ["KIVY_LOG_LEVEL"] = "warning"

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ColorProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform
from kivy.uix.button import Button
from kivy.metrics import dp

from ble_manager import (
    get_ble_manager,
    cmd_color,
    cmd_brightness,
    cmd_mode,
    cmd_speed,
    CMD_POWER_ON,
    CMD_POWER_OFF,
    EFFECT_MODES,
)

kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elk.kv")
Builder.load_file(kv_path)

QUICK_COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 102, 255),
    (255, 255, 0),
    (170, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
    (255, 136, 0),
    (255, 0, 255),
    (136, 255, 0),
    (0, 255, 136),
    (0, 136, 255),
]


class ElkScreen(BoxLayout):
    current_color = ColorProperty([1, 0, 0.5, 1])
    mode_names = ListProperty([m[1] for m in EFFECT_MODES])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ble = get_ble_manager()
        self.ble.on_disconnect = self._on_device_disconnect
        self.current_r = 255
        self.current_g = 0
        self.current_b = 128
        self.music_active = False
        self._music_thread = None
        self._closing = False
        self._audio_stream = None
        self._log_lines = []

        Clock.schedule_once(self._setup_quick_colors, 0.1)

    def _setup_quick_colors(self, dt):
        grid = self.ids.get("quick_colors")
        if not grid:
            return
        for r, g, b in QUICK_COLORS:
            btn = Button(
                size_hint_y=None,
                height=dp(28),
                size_hint_x=None,
                width=dp(28),
                background_normal="",
                background_color=(r / 255.0, g / 255.0, b / 255.0, 1),
            )
            btn.bind(on_release=lambda inst, rv=r, gv=g, bv=b: self._quick_color(rv, gv, bv))
            grid.add_widget(btn)

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_lines.append(line)
        if len(self._log_lines) > 150:
            self._log_lines = self._log_lines[-100:]
        Clock.schedule_once(lambda dt: self._update_log(), 0)

    def _update_log(self):
        log_box = self.ids.get("log_box")
        if log_box:
            log_box.text = "\n".join(self._log_lines)
            log_box.cursor = (0, len(log_box.text))

    def clear_log(self):
        self._log_lines.clear()
        log_box = self.ids.get("log_box")
        if log_box:
            log_box.text = ""

    def _status(self, text, color="#666666"):
        lbl = self.ids.get("status_label")
        if lbl:
            lbl.text = text

    def _set_enabled(self, enabled):
        state = "normal" if not enabled else "disabled"
        ids = self.ids
        for key in [
            "btn_disconnect", "btn_power_on", "btn_power_off",
            "btn_send_color", "btn_send_brightness", "btn_send_mode",
            "btn_random", "btn_send_speed", "spinner_mode",
        ]:
            w = ids.get(key)
            if w:
                w.disabled = not enabled

    def _on_device_disconnect(self):
        Clock.schedule_once(lambda dt: self._handle_disconnect(), 0)

    def _handle_disconnect(self):
        self._status("Cihaz baglantisi kesildi", "#ef4444")
        self._set_enabled(False)
        self.music_active = False
        self._log("Baglanti kesildi")

    def on_connect(self):
        btn = self.ids.get("btn_connect")
        if btn:
            btn.disabled = True
            btn.text = "Taranıyor..."
        self._status("BLE tarama baslatiliyor...", "#fbbf24")
        self._log("BLE tarama baslatiliyor...")

        self.ble.scan_and_connect(callback=self._connect_done)

    def _connect_done(self, ok, msg):
        btn = self.ids.get("btn_connect")
        if btn:
            btn.disabled = False
            btn.text = "Tara ve Baglan"

        if ok:
            self._status(msg, "#22c55e")
            self._set_enabled(True)
            self._log(msg)
        else:
            self._status(msg, "#ef4444")
            self._log(f"HATA: {msg}")

    def on_disconnect(self):
        self.ble.disconnect()
        self._status("Baglanti kesildi", "#666666")
        self._set_enabled(False)
        self.music_active = False
        self._log("Baglanti kesildi")

    def on_slider_change(self):
        r = int(self.ids.slider_r.value)
        g = int(self.ids.slider_g.value)
        b = int(self.ids.slider_b.value)
        self.current_r, self.current_g, self.current_b = r, g, b
        self.current_color = [r / 255.0, g / 255.0, b / 255.0, 1]

    def _quick_color(self, r, g, b):
        self.ids.slider_r.value = r
        self.ids.slider_g.value = g
        self.ids.slider_b.value = b
        self.current_r, self.current_g, self.current_b = r, g, b
        self.current_color = [r / 255.0, g / 255.0, b / 255.0, 1]
        if self.ble.connected:
            self._log(f"Renk gonder: R={r} G={g} B={b}")
            self.ble.send(cmd_color(r, g, b))

    def send_color(self):
        r, g, b = self.current_r, self.current_g, self.current_b
        self._log(f"Renk gonder: R={r} G={g} B={b}")
        self.ble.send(cmd_color(r, g, b))

    def on_brightness_change(self):
        v = int(self.ids.slider_brightness.value)
        lbl = self.ids.get("lbl_brightness")
        if lbl:
            lbl.text = f"%{v}"

    def send_brightness(self):
        v = int(self.ids.slider_brightness.value)
        self._log(f"Parlaklik gonder: %{v}")
        self.ble.send(cmd_brightness(v))

    def on_speed_change(self):
        v = int(self.ids.slider_speed.value)
        lbl = self.ids.get("lbl_speed")
        if lbl:
            lbl.text = f"%{v}"

    def on_mode_select(self, text):
        if text == "Seciniz...":
            return

    def send_mode(self):
        sel = self.ids.spinner_mode.text
        for mode_val, name in EFFECT_MODES:
            if name == sel:
                self._log(f"Mod gonder: {name} (0x{mode_val:02X})")
                self.ble.send(cmd_mode(mode_val))
                spd = int(self.ids.slider_speed.value)
                self.ble.send(cmd_speed(spd))
                break

    def random_mode(self):
        m = random.choice(EFFECT_MODES)
        self.ids.spinner_mode.text = m[1]
        self._log(f"Rastgele mod: {m[1]}")
        self.ble.send(cmd_mode(m[0]))
        spd = int(self.ids.slider_speed.value)
        self.ble.send(cmd_speed(spd))

    def send_speed(self):
        v = int(self.ids.slider_speed.value)
        self._log(f"Hiz gonder: %{v}")
        self.ble.send(cmd_speed(v))

    def send_power_on(self):
        self._log("Power ON gonderildi")
        self.ble.send(CMD_POWER_ON)

    def send_power_off(self):
        self._log("Power OFF gonderildi")
        self.ble.send(CMD_POWER_OFF)

    def toggle_music(self):
        if not self.ble.connected:
            self._status("Once baglanin!", "#ef4444")
            self._log("HATA: Once Bluetooth baglantisi yapin")
            return

        self.music_active = not self.music_active
        btn = self.ids.get("btn_music")
        lbl = self.ids.get("lbl_auto_status")

        if self.music_active:
            if btn:
                btn.text = ">> Ses ACIK <<"
                btn.background_color = [0.58, 0.2, 0.93, 1]
            if lbl:
                lbl.text = "Ses analiz ediliyor..."
                lbl.color = [0.58, 0.2, 0.93, 1]
            self._status("Ses modu aktif", "#9333ea")
            self._log("Ses duyarli mod baslatildi")
            self._start_music()
        else:
            if btn:
                btn.text = "Ses Duyarli Mod"
                btn.background_color = [0.42, 0.13, 0.66, 1]
            if lbl:
                lbl.text = "Kapali"
                lbl.color = [0.33, 0.33, 0.33, 1]
            self._status("Ses modu kapatildi", "#666666")
            self._log("Ses duyarli mod durduruldu")

    def _start_music(self):
        def _work():
            try:
                if platform == "android":
                    from android.permissions import request_permissions, Permission
                    request_permissions([Permission.RECORD_AUDIO])
                    import audioop
                    import wave

                    sr = 16000
                    chunk = 640

                    from jnius import autoclass
                    AudioFormat = autoclass("android.media.AudioFormat")
                    AudioRecord = autoclass("android.media.AudioRecord")
                    MediaRecorder = autoclass("android.media.MediaRecorder")

                    audio_source = MediaRecorder.AudioSource.MIC
                    channel = AudioFormat.CHANNEL_IN_MONO
                    encoding = AudioFormat.ENCODING_PCM_16BIT

                    recorder = AudioRecord(audio_source, sr, channel, encoding, chunk * 2)
                    recorder.startRecording()

                    smooth = 0
                    while self.music_active:
                        buf = bytearray(chunk * 2)
                        read = recorder.read(buf, 0, chunk * 2)
                        if read > 0:
                            samples = []
                            for i in range(0, min(read, chunk * 2), 2):
                                val = buf[i] | (buf[i + 1] << 8)
                                if val > 32767:
                                    val -= 65536
                                samples.append(val / 32768.0)
                            if samples:
                                rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
                                level = min(255, int(rms * 800))
                                smooth = int(smooth * 0.5 + level * 0.5)
                                smooth = max(0, min(255, smooth))
                                if smooth >= 50:
                                    if smooth < 85:
                                        h, s, v = 0.66, 1.0, smooth / 85.0
                                    elif smooth < 170:
                                        h, s, v = 0.75, 1.0, (smooth - 85) / 85.0
                                    else:
                                        h, s, v = 0.0, 1.0, 1.0
                                    r, g, b = colorsys.hsv_to_rgb(h, s, v)
                                    self.ble.send(
                                        cmd_color(int(r * 255), int(g * 255), int(b * 255))
                                    )
                        time.sleep(0.04)

                    recorder.stop()
                    recorder.release()

                else:
                    try:
                        import sounddevice as sd
                        import numpy as np
                    except ImportError:
                        self._log("HATA: sounddevice/numpy gerekli")
                        return

                    smooth = 0
                    while self.music_active:
                        try:
                            rec = sd.rec(
                                samplerate=16000,
                                channels=1,
                                dtype="float32",
                                frames=640,
                            )
                            sd.wait()
                            if rec is not None and len(rec) > 0:
                                rms = float(np.sqrt(np.mean(rec.astype(np.float32) ** 2)))
                                level = min(255, int(rms * 800))
                                smooth = int(smooth * 0.5 + level * 0.5)
                                smooth = max(0, min(255, smooth))
                                if smooth >= 50:
                                    if smooth < 85:
                                        h, s, v = 0.66, 1.0, smooth / 85.0
                                    elif smooth < 170:
                                        h, s, v = 0.75, 1.0, (smooth - 85) / 85.0
                                    else:
                                        h, s, v = 0.0, 1.0, 1.0
                                    r, g, b = colorsys.hsv_to_rgb(h, s, v)
                                    self.ble.send(
                                        cmd_color(int(r * 255), int(g * 255), int(b * 255))
                                    )
                        except Exception:
                            pass
                        time.sleep(0.04)

            except Exception as e:
                self._log(f"Ses modu hatasi: {e}")

        self._music_thread = threading.Thread(target=_work, daemon=True)
        self._music_thread.start()


class ELKBledomApp(App):
    def build(self):
        if platform == "android":
            Window.size = (Window.width, Window.height)
        else:
            Window.size = (400, 750)

        self.title = "ELK-BLEDOM LED Kontrol"
        return ElkScreen()

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    try:
        ELKBledomApp().run()
    except Exception as e:
        print(f"Uygulama hatasi: {e}")
        import traceback

        traceback.print_exc()
