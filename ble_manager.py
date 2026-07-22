"""
ELK-BLEDOM BLE Yonetim Modulu
Android (kivy_bleak) icin Bluetooth Low Energy iletisim katmani.
"""

import time
from datetime import datetime
from threading import Lock

from kivy.clock import Clock
from kivy.utils import platform

if platform == "android":
    from jnius import autoclass, cast
    from android.permissions import request_permissions, Permission

    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")
    BluetoothGatt = autoclass("android.bluetooth.BluetoothGatt")
    BluetoothGattCallback = autoclass("android.bluetooth.BluetoothGattCallback")
    BluetoothGattCharacteristic = autoclass(
        "android.bluetooth.BluetoothGattCharacteristic"
    )
    BluetoothGattService = autoclass("android.bluetooth.BluetoothGattService")
    UUID = autoclass("java.util.UUID")
else:
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        BleakClient = None
        BleakScanner = None

WRITE_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"

DEVICE_NAME_PATTERNS = [
    "ELK-BLEDOB", "ELK-BLEDOM", "BLEDOM", "ELK-BLE", "LOTUS", "LED BLE"
]

CMD_POWER_ON = bytes([0x7E, 0x07, 0x04, 0xFF, 0x00, 0x01, 0x02, 0x01, 0xEF])
CMD_POWER_OFF = bytes([0x7E, 0x07, 0x04, 0x00, 0x00, 0x00, 0x02, 0x01, 0xEF])


def cmd_color(r, g, b):
    return bytes([0x7E, 0x07, 0x05, 0x03, r, g, b, 0x10, 0xEF])


def cmd_brightness(level):
    return bytes(
        [0x7E, 0x04, 0x01, max(0, min(100, level)), 0x01, 0xFF, 0xFF, 0x00, 0xEF]
    )


def cmd_mode(mode):
    return bytes(
        [0x7E, 0x07, 0x03, (mode & 0x7F) | 0x80, 0x03, 0xFF, 0xFF, 0x00, 0xEF]
    )


def cmd_speed(speed):
    return bytes(
        [0x7E, 0x04, 0x02, max(0, min(100, speed)), 0xFF, 0xFF, 0xFF, 0x00, 0xEF]
    )


def cmd_time_sync():
    now = datetime.now()
    dow = now.isoweekday()
    return bytes([0x7E, 0x06, 0x83, now.hour, now.minute, now.second, dow, 0x00, 0xEF])


EFFECT_MODES = [
    (0x00, "Kirmizi"),
    (0x01, "Yesil"),
    (0x02, "Mavi"),
    (0x03, "Sari"),
    (0x04, "Cyan"),
    (0x05, "Mor"),
    (0x06, "Beyaz"),
    (0x07, "Kirmizi-Yesil Atlama"),
    (0x08, "Kirmizi-Mavi Atlama"),
    (0x09, "Yesil-Mavi Atlama"),
    (0x0A, "RGB Atlama"),
    (0x0B, "7 Renk Atlama"),
    (0x0C, "Kirmizi Fade"),
    (0x0D, "Yesil Fade"),
    (0x0E, "Mavi Fade"),
    (0x0F, "Kirmizi-Yesil Fade"),
    (0x10, "Kirmizi-Mavi Fade"),
    (0x11, "Yesil-Mavi Fade"),
    (0x12, "RGB Fade"),
    (0x13, "7 Renk Fade"),
    (0x14, "Kirmizi Titresim"),
    (0x15, "Yesil Titresim"),
    (0x16, "Mavi Titresim"),
    (0x17, "7 Renk Titresim"),
    (0x18, "Gokkusagi"),
    (0x19, "Gokkusagi Dalgali"),
    (0x1A, "Renk Degisim"),
]


class AndroidBLEManager:
    """Android icin native BLE yonetici."""

    def __init__(self):
        self.connected = False
        self.gatt = None
        self.write_char = None
        self.device_name = ""
        self._lock = Lock()
        self.on_status = None
        self.on_connect = None
        self.on_disconnect = None

    def request_permissions(self):
        if platform == "android":
            request_permissions(
                [
                    Permission.BLUETOOTH,
                    Permission.BLUETOOTH_SCAN,
                    Permission.BLUETOOTH_CONNECT,
                    Permission.ACCESS_FINE_LOCATION,
                ]
            )

    def _match_device(self, name):
        if not name:
            return False
        u = name.upper()
        return any(p in u for p in DEVICE_NAME_PATTERNS)

    def scan_and_connect(self, callback=None):
        if platform != "android":
            if callback:
                callback(False, "Sadece Android desteklenir")
            return

        self.request_permissions()

        def _do_scan():
            try:
                adapter = BluetoothAdapter.getDefaultAdapter()
                if not adapter or not adapter.isEnabled():
                    Clock.schedule_once(
                        lambda dt: callback(False, "Bluetooth kapali!")
                        if callback
                        else None
                    )
                    return

                adapter.startDiscovery()

                time.sleep(8)

                bonded_devices = adapter.getBondedDevices()
                found_devices = []

                it = bonded_devices.iterator()
                while it.hasNext():
                    device = it.next()
                    name = device.getName()
                    addr = device.getAddress()
                    found_devices.append({"name": name or "Bilinmiyor", "address": addr})

                adapter.cancelDiscovery()

                if callback:
                    Clock.schedule_once(
                        lambda dt: self._connect_to_device(found_devices, callback)
                    )

            except Exception as e:
                if callback:
                    Clock.schedule_once(
                        lambda dt: callback(False, f"Tarama hatasi: {e}")
                    )

        import threading

        threading.Thread(target=_do_scan, daemon=True).start()

    def _connect_to_device(self, devices, callback):
        target = None
        for d in devices:
            if self._match_device(d["name"]):
                target = d
                break

        if not target:
            names = ", ".join(d["name"] for d in devices[:5])
            callback(False, f"Esmlesen cihaz yok. Bulunan: {names}")
            return

        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            device = adapter.getRemoteDevice(target["address"])

            self.gatt = device.connectGatt(
                None, False, GattCallbackManager(self)
            )

            self.device_name = target["name"]
            callback(True, f"Baglandi: {target['name']}")

        except Exception as e:
            callback(False, f"Baglanti hatasi: {e}")

    def send(self, cmd):
        with self._lock:
            if not self.connected or not self.write_char:
                return False

        try:
            self.write_char.setValue(list(cmd))
            self.gatt.writeCharacteristic(self.write_char, list(cmd))
            return True
        except Exception:
            return False

    def disconnect(self):
        try:
            if self.gatt:
                self.gatt.disconnect()
        except Exception:
            pass
        finally:
            self.connected = False
            self.gatt = None
            self.write_char = None


class GattCallbackManager:
    """Android GATT callback."""

    def __init__(self, manager):
        self.manager = manager

    def onConnectionStateChange(self, gatt, status, newState):
        if newState == 2:
            self.manager.connected = True
            gatt.discoverServices()
        else:
            self.manager.connected = False
            if self.manager.on_disconnect:
                Clock.schedule_once(
                    lambda dt: self.manager.on_disconnect(), 0
                )

    def onServicesDiscovered(self, gatt, status):
        if status != 0:
            return

        services = gatt.getServices()
        for i in range(services.size()):
            service = services.get(i)
            chars = service.getCharacteristics()
            for j in range(chars.size()):
                char = chars.get(j)
                uuid_str = char.getUuid().toString()
                if "fff3" in uuid_str.lower():
                    with self.manager._lock:
                        self.manager.write_char = char
                    return

    def onCharacteristicWrite(self, gatt, characteristic, status):
        pass


class DesktopBLEManager:
    """Masaustu icin bleak tabanli BLE yonetici."""

    def __init__(self):
        self.client = None
        self.connected = False
        self.device_name = ""
        self._lock = Lock()
        self.on_status = None
        self.on_connect = None
        self.on_disconnect = None
        self.found_devices = []

    def _match_device(self, name):
        if not name:
            return False
        u = name.upper()
        return any(p in u for p in DEVICE_NAME_PATTERNS)

    def scan_and_connect(self, callback=None):
        import asyncio

        def _work():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ok, msg = loop.run_until_complete(self._async_scan())
                if callback:
                    Clock.schedule_once(lambda dt: callback(ok, msg))
                loop.close()
            except Exception as e:
                if callback:
                    Clock.schedule_once(
                        lambda dt: callback(False, f"Hata: {e}")
                    )

        import threading

        threading.Thread(target=_work, daemon=True).start()

    async def _async_scan(self):
        if not BleakScanner or not BleakClient:
            return False, "bleak kutuphanesi yuklu degil"

        self.found_devices = []

        def on_detect(device, adv):
            e = {"address": device.address, "name": device.name or "Bilinmiyor"}
            if e not in self.found_devices:
                self.found_devices.append(e)

        scanner = BleakScanner(detection_callback=on_detect)
        await scanner.start()
        await asyncio.sleep(8.0)
        await scanner.stop()

        if not self.found_devices:
            return False, "BLE cihazi bulunamadi!"

        target = None
        for d in self.found_devices:
            if self._match_device(d["name"]):
                target = d
                break

        if not target:
            names = ", ".join(d["name"] for d in self.found_devices[:5])
            return False, f"Esmlesen cihaz yok. Bulunan: {names}"

        self.client = BleakClient(target["address"])
        await self.client.connect()
        self.connected = True
        self.device_name = target["name"]

        await asyncio.sleep(1.0)
        try:
            await self.client.write_gatt_char(WRITE_UUID, cmd_time_sync(), response=False)
        except Exception:
            pass

        await asyncio.sleep(0.3)
        try:
            await self.client.write_gatt_char(WRITE_UUID, CMD_POWER_ON, response=False)
        except Exception:
            pass

        await asyncio.sleep(0.3)
        try:
            await self.client.write_gatt_char(
                WRITE_UUID, cmd_color(255, 0, 0), response=False
            )
        except Exception:
            pass

        return True, f"Baglandi: {target['name']}"

    def send(self, cmd):
        if not self.connected or not self.client:
            return False

        import asyncio

        def _send():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.client.write_gatt_char(WRITE_UUID, cmd, response=False)
                )
                loop.close()
            except Exception:
                self.connected = False

        import threading

        threading.Thread(target=_send, daemon=True).start()
        return True

    def disconnect(self):
        import asyncio

        def _disconnect():
            try:
                if self.client and self.connected:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.client.write_gatt_char(
                            WRITE_UUID, CMD_POWER_OFF, response=False
                        )
                    )
                    import time

                    time.sleep(0.2)
                    loop.run_until_complete(self.client.disconnect())
                    loop.close()
            except Exception:
                pass
            finally:
                self.connected = False
                self.client = None

        import threading

        threading.Thread(target=_disconnect, daemon=True).start()


def get_ble_manager():
    if platform == "android":
        return AndroidBLEManager()
    else:
        return DesktopBLEManager()
