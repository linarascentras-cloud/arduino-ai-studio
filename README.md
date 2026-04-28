# 🤖 Arduino AI Studio v3.0

> **Rašyk paprastais žodžiais — gauk veikiantį Arduino kodą**

Arduino AI Studio yra nemokama programa Windows kompiuteriui kuri leidžia kurti Arduino/ESP32 projektus **be programavimo žinių**. Tiesiog aprašyk ką nori padaryti lietuviškai ar angliškai — AI sugeneruos kodą, sukompiliuos ir įkels į tavo boardą automatiškai.

![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Groq](https://img.shields.io/badge/AI-Groq%20Nemokama-orange?style=for-the-badge)

---

## ✨ Funkcijos

- 💬 **Pokalbių sąsaja** — rašyk paprastais žodžiais, gauk kodą
- ⚡ **Groq AI** — nemokamas, greitas (llama-3.3-70b modelis)
- 🔌 **Automatinis board atpažinimas** — CH340, FTDI, CP2102, RP2040
- ⚙️ **Automatinis kompiliavimas** — arduino-cli integracija
- 📤 **Vienu mygtuku įkelti** į Arduino/ESP32
- 🔧 **AI klaidų taisymas** — kompiliacijos klaidos taisomos automatiškai
- 🌙 **Tamsus dizainas** — akims draugiškas
- 🇱🇹 **Lietuviškas UI** — suprantamas visiems

---

## 🔌 Palaikomi boardai

| Board | Auto atpažinimas |
|-------|-----------------|
| Arduino Nano (Old Bootloader / CH340) | ✅ |
| Arduino Nano (New Bootloader) | ✅ |
| Arduino Uno | ✅ |
| Arduino Mega 2560 | ✅ |
| ESP32 / ESP32-C3 / ESP32-S3 | ✅ |
| Raspberry Pi Pico (RP2040) | ✅ |

---

## 🚀 Greitas pradžias

### 1. Reikalavimai
- Windows 10/11
- Python 3.8+ — [python.org](https://www.python.org/downloads/) — **pažymėk "Add to PATH"!**
- arduino-cli.exe — [parsisiųsti čia](https://arduino.github.io/arduino-cli/latest/installation/)

### 2. Parsisiųsti projektą
Spusk žalią mygtuką **Code → Download ZIP** → išpakuok

### 3. arduino-cli.exe
Parsisiųsk `arduino-cli_Windows_64bit.zip` ir padėk `arduino-cli.exe` į `arduino_ai_studio\` aplanką

### 4. Nemokamas Groq API raktas
1. Eik į **[console.groq.com](https://console.groq.com)**
2. Registruokis per Google arba el. paštą — **kortelės nereikia!**
3. Spusk **API Keys → Create API Key**
4. Nukopijuok raktą (prasideda `gsk_...`)

### 5. Paleisti
```
run.bat  ← du kartus spausti
```
Tada programoje: **⚙️ Nustatymai → įvesk Groq raktą → Išsaugoti**

---

## 💡 Naudojimo pavyzdžiai

```
"Noriu LED mirksėjimą ant pin 13 kas pusę sekundės"
"Parašyk temperatūros matavimą su DHT11 davikliu"
"Valdyk servo variklį potenciometru"
"Tetris žaidimas SSD1306 OLED ekrane"
```

---

## 📁 Struktūra

```
arduino_ai_studio/
├── run.bat              ← PALEISTI ČIA
├── launcher.py
├── config.json
├── core/
│   ├── ai_client.py     ← Groq + Ollama AI
│   └── arduino.py       ← Kompiliavimas, board detekcija
├── gui/
│   └── app.py           ← UI
└── tools/               ← Čia padėk arduino-cli.exe
```

---

## 🐛 Dažnos problemos

| Problema | Sprendimas |
|----------|-----------|
| `Python nerastas` | Įdiek Python su "Add to PATH" pažymėtu |
| `model decommissioned` | config.json: `"groq_model": "llama-3.3-70b-versatile"` |
| `Board nerastas` | Spusk "🔍 Rasti automatiškai" |
| `run.bat` rodo `'cho'` | Parsisiųsk run.bat iš naujo iš GitHub |

---

## 📄 Licencija

MIT — naudok laisvai!

---

*Sukurta hobisto iš Lietuvos 🇱🇹 — jei padėjo, palik ⭐ žvaigždutę!*
