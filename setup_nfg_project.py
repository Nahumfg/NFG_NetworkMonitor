import os

estructura = {
    "NFG_NetworkMonitor": {
        "main.py": "# Punto de entrada principal para NFG Network Monitor\n",
        "README.md": "# NFG Network Monitor\n\nDocumentación inicial.",
        "requirements.txt": "PyQt6>=6.4\nmatplotlib>=3.5\npsutil>=5.9\n",
        "icono_nfg.ico": None,  # archivo vacío si no hay ícono aún
        "logs": {
            "historial.csv": "timestamp,bytes\n"
        }
    }
}

def crear_estructura(ruta, contenido):
    for nombre, valor in contenido.items():
        ruta_absoluta = os.path.join(ruta, nombre)
        if isinstance(valor, dict):
            os.makedirs(ruta_absoluta, exist_ok=True)
            crear_estructura(ruta_absoluta, valor)
        else:
            with open(ruta_absoluta, "w", encoding="utf-8") as f:
                if valor:
                    f.write(valor)
                else:
                    pass  # archivo vacío como icono_nfg.ico

if __name__ == "__main__":
    base = os.getcwd()
    crear_estructura(base, estructura)
    print("✅ Proyecto NFG Network Monitor creado con éxito.")
