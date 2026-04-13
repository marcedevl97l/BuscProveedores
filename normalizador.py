import re

def limpiar(texto):
    if not texto:
        return ""
    texto = str(texto).lower()
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto
