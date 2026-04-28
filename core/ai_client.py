"""
Arduino AI Studio - AI Klientas
Palaiko: Groq (nemokamas, greitas) + Ollama (lokalus)
"""
import requests
import json
import re

ARDUINO_SYSTEM_PROMPT = """Tu esi Arduino/ESP32 programavimo ekspertas.
Tavo tikslas - rašyti TEISINGĄ, VEIKIANTĮ Arduino kodą.

TAISYKLĖS:
1. Visada grąžink TIKTAI kodą be paaiškinimų prieš ar po
2. Kodas turi būti tarp ```cpp ir ``` žymių
3. Visada įtraukk reikiamas bibliotekas (#include)
4. Kodas turi kompiliuotis be klaidų
5. Komentarus rašyk lietuviškai arba angliškai
6. Jei klaida - analizuok ir taisyk, nepaaiškink ilgai

Pavyzdys kaip grąžinti kodą:
```cpp
#include <Arduino.h>

void setup() {
  // ...
}

void loop() {
  // ...
}
```
"""

class AIClient:
    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("ai_provider", "groq")  # "groq" arba "ollama"
        self.groq_key = config.get("groq_api_key", "")
        self.groq_model = config.get("groq_model", "llama-3.1-8b-instant")
        self.ollama_url = config.get("ollama_url", "http://localhost:11434")
        self.ollama_model = config.get("default_model", "llama3.1:8b")
        self.timeout = config.get("ai_timeout", 60)

    def is_groq_configured(self) -> bool:
        return bool(self.groq_key and self.groq_key.startswith("gsk_"))

    def generate(self, prompt: str, on_chunk=None) -> tuple[str, str]:
        """
        Generuoja kodą. Grąžina (kodas, klaida).
        on_chunk(text) - callback kiekvienam žodžiui (streaming)
        """
        if self.provider == "groq" and self.is_groq_configured():
            return self._groq_generate(prompt, on_chunk)
        elif self.provider == "ollama":
            return self._ollama_generate(prompt, on_chunk)
        else:
            return "", "❌ Nenustatytas AI teikėjas. Nustatyk Groq API raktą arba Ollama."

    def _groq_generate(self, prompt: str, on_chunk=None) -> tuple[str, str]:
        """Groq API - greitas ir nemokamas"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": ARDUINO_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": bool(on_chunk),
            "temperature": 0.2,
            "max_tokens": 8000
        }

        try:
            if on_chunk:
                # Streaming
                full_text = ""
                finish_reason = "stop"
                with requests.post(url, headers=headers, json=payload,
                                   stream=True, timeout=self.timeout) as resp:
                    if resp.status_code != 200:
                        err = resp.json().get("error", {}).get("message", resp.text)
                        return "", f"❌ Groq klaida: {err}"
                    for line in resp.iter_lines():
                        if line and line.startswith(b"data: "):
                            data = line[6:]
                            if data == b"[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                token = chunk["choices"][0]["delta"].get("content", "")
                                fr = chunk["choices"][0].get("finish_reason")
                                if fr:
                                    finish_reason = fr
                                if token:
                                    full_text += token
                                    on_chunk(token)
                            except:
                                pass
                if finish_reason == "length":
                    return "", "⚠️ Kodas per ilgas — buvo nukirptas! Bandyk supaprastinti užklausą arba prašyk dalimis (pvz. tik setup() funkciją)."
                return self._extract_code(full_text), ""
            else:
                resp = requests.post(url, headers=headers, json=payload,
                                     timeout=self.timeout)
                if resp.status_code != 200:
                    err = resp.json().get("error", {}).get("message", resp.text)
                    return "", f"❌ Groq klaida: {err}"
                choice = resp.json()["choices"][0]
                if choice.get("finish_reason") == "length":
                    return "", "⚠️ Kodas per ilgas — buvo nukirptas! Bandyk supaprastinti užklausą arba prašyk dalimis."
                text = choice["message"]["content"]
                return self._extract_code(text), ""

        except requests.exceptions.ConnectionError:
            return "", "❌ Interneto ryšys nepasiekiamas. Patikrink WiFi/Ethernet."
        except requests.exceptions.Timeout:
            return "", "❌ Groq per ilgai atsakinėja. Bandyk vėliau."
        except Exception as e:
            return "", f"❌ Klaida: {e}"

    def _ollama_generate(self, prompt: str, on_chunk=None) -> tuple[str, str]:
        """Ollama API - lokalus"""
        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": ARDUINO_SYSTEM_PROMPT + "\n\n" + prompt,
            "stream": bool(on_chunk)
        }
        try:
            if on_chunk:
                full_text = ""
                with requests.post(url, json=payload, stream=True,
                                   timeout=self.timeout) as resp:
                    if resp.status_code != 200:
                        return "", f"❌ Ollama klaida: {resp.status_code}"
                    for line in resp.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                token = chunk.get("response", "")
                                if token:
                                    full_text += token
                                    on_chunk(token)
                                if chunk.get("done"):
                                    break
                            except:
                                pass
                return self._extract_code(full_text), ""
            else:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                if resp.status_code != 200:
                    return "", f"❌ Ollama klaida: {resp.status_code}"
                # Surinkti visas eilutes
                full_text = ""
                for line in resp.text.strip().split("\n"):
                    try:
                        full_text += json.loads(line).get("response", "")
                    except:
                        pass
                return self._extract_code(full_text), ""

        except requests.exceptions.ConnectionError:
            return "", f"❌ Ollama nepasiekiama ({self.ollama_url}). Ar ji paleista?"
        except requests.exceptions.Timeout:
            return "", "❌ Ollama per ilgai atsako. Modelis per sunkus CPU."
        except Exception as e:
            return "", f"❌ Klaida: {e}"

    def _extract_code(self, text: str) -> str:
        """Ištraukia kodą iš markdown bloko"""
        # Ieško ```cpp ... ``` arba ``` ... ```
        patterns = [
            r"```(?:cpp|arduino|c\+\+|ino)?\s*\n?(.*?)```",
            r"```\s*\n?(.*?)```"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        # Jei nėra markdown — grąžina viską
        return text.strip()

    def fix_error(self, code: str, error: str, on_chunk=None) -> tuple[str, str]:
        """Taisyti klaidas - sutrumpinta kad tilptu i Groq limita"""
        # Tik pirmosios klaidos eilutes
        error_lines = error.strip().split("\n")
        short_error = "\n".join(error_lines[:15])

        # Sutrumpinti koda jei per ilgas
        code_lines = code.strip().split("\n")
        if len(code_lines) > 120:
            short_code = "\n".join(code_lines[:120])
            short_code += "\n// ... (sutrumpinta)"
        else:
            short_code = code

        prompt = (
            "Arduino kodo kompiliacijos klaidos. Ištaisyk.\n\n"
            "KLAIDOS:\n" + short_error + "\n\n"
            "KODAS:\n```cpp\n" + short_code + "\n```\n\n"
            "Grazink tik isaisyta koda."
        )
        return self.generate(prompt, on_chunk)

    def get_available_ollama_models(self) -> list[str]:
        """Gauti Ollama modelių sąrašą"""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m["name"] for m in models]
        except:
            pass
        return []
