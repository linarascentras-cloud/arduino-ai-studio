"""
Arduino AI Studio - Arduino Valdymas
Kompiliavimas, įkėlimas, board detekcija, bibliotekos
"""
import subprocess
import serial.tools.list_ports
import json
import os
import re
from pathlib import Path

# VID:PID žodynas — board atpažinimui
VID_PID_MAP = {
    # CH340 (daugelis kloninių Nano/Uno)
    ("1A86", "7523"): {"name": "Arduino Nano/Uno (CH340)", "fqbn": "arduino:avr:nano:cpu=atmega328old"},
    ("1A86", "5523"): {"name": "Arduino Nano (CH340)", "fqbn": "arduino:avr:nano:cpu=atmega328old"},
    ("1A86", "7522"): {"name": "Arduino (CH340)", "fqbn": "arduino:avr:uno"},
    # FTDI (originalūs)
    ("0403", "6001"): {"name": "Arduino Uno (FTDI)", "fqbn": "arduino:avr:uno"},
    ("0403", "6010"): {"name": "Arduino (FTDI)", "fqbn": "arduino:avr:uno"},
    # Originalūs Arduino (ATmega16U2)
    ("2341", "0043"): {"name": "Arduino Uno (orig.)", "fqbn": "arduino:avr:uno"},
    ("2341", "0001"): {"name": "Arduino Uno (orig.)", "fqbn": "arduino:avr:uno"},
    ("2341", "0010"): {"name": "Arduino Mega (orig.)", "fqbn": "arduino:avr:mega"},
    ("2341", "003F"): {"name": "Arduino Mega ADK", "fqbn": "arduino:avr:megaADK"},
    ("2341", "003E"): {"name": "Arduino Leonardo (orig.)", "fqbn": "arduino:avr:leonardo"},
    # CP2102 (ESP32 daugelis)
    ("10C4", "EA60"): {"name": "ESP32 (CP2102)", "fqbn": "esp32:esp32:esp32"},
    ("10C4", "EA61"): {"name": "ESP32-S2 (CP2102)", "fqbn": "esp32:esp32:esp32s2"},
    # CH9102 (ESP32-C3, S3)
    ("1A86", "55D4"): {"name": "ESP32-C3/S3 (CH9102)", "fqbn": "esp32:esp32:esp32c3"},
    ("1A86", "55D3"): {"name": "ESP32-S3 (CH9102)", "fqbn": "esp32:esp32:esp32s3"},
    # RP2040
    ("2E8A", "0005"): {"name": "Raspberry Pi Pico (RP2040)", "fqbn": "rp2040:rp2040:rpipico"},
    ("2E8A", "000A"): {"name": "RP2040 (UF2 mode)", "fqbn": "rp2040:rp2040:rpipico"},
    # STM32
    ("0483", "5740"): {"name": "STM32 (CDC)", "fqbn": "STMicroelectronics:stm32:GenF1"},
}

class ArduinoManager:
    def __init__(self, config: dict):
        self.cli = config.get("arduino_cli_path", "arduino-cli")
        self.workspace = Path(config.get("workspace_dir", "workspace/sketch"))
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.config = config

    def _run(self, args: list, timeout=120) -> tuple[bool, str]:
        """Paleisti arduino-cli komandą"""
        try:
            result = subprocess.run(
                [self.cli] + args,
                capture_output=True, text=True,
                timeout=timeout, encoding="utf-8", errors="replace"
            )
            output = result.stdout + result.stderr
            return result.returncode == 0, output
        except FileNotFoundError:
            return False, f"❌ arduino-cli nerastas: {self.cli}\nPatikrink nustatymus!"
        except subprocess.TimeoutExpired:
            return False, "❌ Per ilgai truko (timeout). Bandyk vėl."
        except Exception as e:
            return False, f"❌ Klaida: {e}"

    def detect_boards(self) -> list[dict]:
        """Automatiškai rasti prijungtus boardus per VID:PID"""
        found = []
        ports = serial.tools.list_ports.comports()
        for port in ports:
            vid = f"{port.vid:04X}" if port.vid else None
            pid = f"{port.pid:04X}" if port.pid else None
            board_info = None
            if vid and pid:
                board_info = VID_PID_MAP.get((vid, pid))
            if board_info:
                found.append({
                    "port": port.device,
                    "name": board_info["name"],
                    "fqbn": board_info["fqbn"],
                    "description": port.description or "",
                    "vid": vid, "pid": pid,
                    "auto_detected": True
                })
            elif port.vid:  # Prijungtas bet neatpažintas
                found.append({
                    "port": port.device,
                    "name": f"Neatpažintas ({port.description})",
                    "fqbn": "",
                    "description": port.description or "",
                    "vid": vid or "?", "pid": pid or "?",
                    "auto_detected": False
                })
        return found

    def list_ports(self) -> list[str]:
        """Paprastas COM portų sąrašas"""
        return [p.device for p in serial.tools.list_ports.comports()]

    def save_sketch(self, code: str) -> Path:
        """Išsaugoti .ino failą"""
        sketch_file = self.workspace / "sketch.ino"
        sketch_file.write_text(code, encoding="utf-8")
        return sketch_file

    def compile(self, fqbn: str, on_progress=None) -> tuple[bool, str]:
        """Kompiliuoti sketch'ą"""
        if on_progress:
            on_progress("⚙️ Kompiliuojama...")
        ok, output = self._run(["compile", "--fqbn", fqbn, str(self.workspace)], timeout=120)
        return ok, output

    def upload(self, fqbn: str, port: str, on_progress=None) -> tuple[bool, str]:
        """Įkelti į boardą"""
        if on_progress:
            on_progress(f"📤 Įkeliama į {port}...")
        ok, output = self._run([
            "upload", "--fqbn", fqbn, "--port", port, str(self.workspace)
        ], timeout=60)
        return ok, output

    def compile_and_upload(self, code: str, fqbn: str, port: str,
                           on_progress=None) -> tuple[bool, str]:
        """Pilnas ciklas: išsaugoti → kompiliuoti → įkelti"""
        self.save_sketch(code)
        ok, output = self.compile(fqbn, on_progress)
        if not ok:
            return False, output
        return self.upload(fqbn, port, on_progress)

    def install_core(self, core: str, on_progress=None) -> tuple[bool, str]:
        """Įdiegti core (pvz. arduino:avr)"""
        if on_progress:
            on_progress(f"📦 Diegiamas {core}...")
        ok, output = self._run(["core", "install", core], timeout=300)
        return ok, output

    def check_core_installed(self, core: str) -> bool:
        """Patikrinti ar core įdiegtas"""
        ok, output = self._run(["core", "list"])
        if ok:
            return core in output
        return False

    def install_library(self, lib_name: str, on_progress=None) -> tuple[bool, str]:
        """Įdiegti biblioteką"""
        if on_progress:
            on_progress(f"📚 Diegiama biblioteka: {lib_name}...")
        ok, output = self._run(["lib", "install", lib_name], timeout=120)
        return ok, output

    def extract_missing_libraries(self, error_output: str) -> list[str]:
        """Iš klaidos teksto rasti trūkstamas bibliotekas"""
        libs = []
        patterns = [
            r"fatal error: (\S+\.h): No such file",
            r"No such file or directory.*?['\"](\w+\.h)['\"]",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, error_output):
                header = match.group(1)
                # Konvertuoti .h į bibliotekos pavadinimą
                lib = header.replace(".h", "").replace("_", " ")
                libs.append(lib)
        return list(set(libs))

    def update_index(self, on_progress=None) -> tuple[bool, str]:
        """Atnaujinti board indeksą"""
        if on_progress:
            on_progress("🔄 Atnaujinamas board indeksas...")
        ok, out = self._run(["core", "update-index"], timeout=60)
        return ok, out

    def cli_version(self) -> str:
        """Gauti arduino-cli versiją"""
        ok, output = self._run(["version"])
        if ok:
            return output.strip()
        return "Nerasta"
