name: Build Android APK

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 120

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y openjdk-17-jdk autoconf automake build-essential cmake gettext git libltdl-dev libtool libffi-dev libssl-dev pkg-config zip unzip zlib1g-dev

      - name: Install Cython and Buildozer
        run: pip install cython buildozer

      - name: Build APK
        run: |
          cd mobile
          yes | buildozer android debug || true

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: ELK-BLEDOM-LED-Kontrol
          path: mobile/bin/*.apk
          retention-days: 30
