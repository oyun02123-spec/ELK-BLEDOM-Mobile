[app]

title = ELK-BLEDOM LED Kontrol
package.name = elkbledom
package.domain = com.elkbledom

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = assets/*,images/*,fonts/*

version = 1.0.0
version.filename = %(source.dir)s/main.py

requirements = python3,
    kivy==2.3.0,
    pillow,
    pyjnius,
    android,

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

android.permissions = BLUETOOTH,
    BLUETOOTH_ADMIN,
    BLUETOOTH_SCAN,
    BLUETOOTH_CONNECT,
    ACCESS_FINE_LOCATION,
    RECORD_AUDIO

android.arch = arm64-v8a
android.archs = arm64-v8a, armeabi-v7a

android.release_artifact = apk

# BLE icin gerekli
android.uses_permission = android.permission.BLUETOOTH,
    android.permission.BLUETOOTH_ADMIN,
    android.permission.BLUETOOTH_SCAN,
    android.permission.BLUETOOTH_CONNECT,
    android.permission.ACCESS_FINE_LOCATION,
    android.permission.RECORD_AUDIO

# Kivy ayarlari
log_level = 2
warn_on_root = 0

# Uygulama simgesi (varsa)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# Build surucu modu
# p4a.branch = develop

[buildozer]
warn_on_root = 0
check_app_requirements = 0
