"""
OPTIMIZADOR DE ESPACIO — Mac Mini M4
======================================
Mueve archivos grandes a iCloud para liberar espacio local.
Nunca borra nada: solo mueve a iCloud donde sigue accesible.

Seguro: solo toca archivos que tú ya tienes en carpetas de usuario.
Nunca toca: aplicaciones, sistema, código fuente, credenciales.

Autor: Santiago Jiménez
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

HOME        = Path.home()
ICLOUD      = HOME / "Library/Mobile Documents/com~apple~CloudDocs"
ICLOUD_ARCH = ICLOUD / "Archivos_Mac"   # Carpeta destino en iCloud

# Archivos grandes de estas carpetas se mueven a iCloud
CARPETAS_ORIGEN = [
    HOME / "Movies",
    HOME / "Downloads/Vídeos",
    HOME / "Downloads/Audio",
    HOME / "Downloads/Comprimidos",
    HOME / "Documents",
]

# Umbral: mover archivos mayores de X MB
UMBRAL_MB = 50

# Nunca mover estos tipos (código, credenciales, apps)
EXTENSIONES_PROTEGIDAS = {
    ".py", ".js", ".ts", ".html", ".css", ".json", ".sh",
    ".plist", ".app", ".pkg", ".dmg", ".gitignore",
    ".env", ".key", ".pem", ".cert",
}

# Nunca mover carpetas de proyectos
CARPETAS_PROTEGIDAS = {
    str(HOME / "Projects"),
    str(HOME / "Library"),
    str(ICLOUD),
}


def esta_protegido(ruta: Path) -> bool:
    ruta_str = str(ruta.resolve())
    for p in CARPETAS_PROTEGIDAS:
        if ruta_str.startswith(p):
            return True
    if ruta.suffix.lower() in EXTENSIONES_PROTEGIDAS:
        return True
    return False


def tamaño_legible(b: float) -> str:
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def espacio_libre() -> int:
    return shutil.disk_usage(HOME).free


def escanear_candidatos() -> List[Tuple[Path, int]]:
    candidatos = []
    umbral_bytes = UMBRAL_MB * 1024 * 1024

    for carpeta in CARPETAS_ORIGEN:
        if not carpeta.exists():
            continue
        try:
            for archivo in carpeta.rglob("*"):
                if not archivo.is_file():
                    continue
                if archivo.name.startswith("."):
                    continue
                if esta_protegido(archivo):
                    continue
                try:
                    tam = archivo.stat().st_size
                    if tam >= umbral_bytes:
                        candidatos.append((archivo, tam))
                except OSError:
                    pass
        except PermissionError:
            pass

    return sorted(candidatos, key=lambda x: x[1], reverse=True)


def mover_a_icloud(archivo: Path, simular: bool = False) -> Tuple[bool, int]:
    try:
        ruta_relativa = None
        for carpeta in CARPETAS_ORIGEN:
            try:
                ruta_relativa = archivo.relative_to(carpeta)
                nombre_base   = carpeta.name
                break
            except ValueError:
                pass

        if ruta_relativa is None:
            return False, 0

        destino_dir = ICLOUD_ARCH / nombre_base / ruta_relativa.parent
        destino     = destino_dir / archivo.name

        # Evitar sobreescribir
        contador = 1
        while destino.exists():
            destino = destino_dir / f"{archivo.stem}_{contador}{archivo.suffix}"
            contador += 1

        tam = archivo.stat().st_size

        if not simular:
            destino_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(archivo), str(destino))

        return True, tam

    except Exception as e:
        print(f"     Error: {e}")
        return False, 0


def main() -> None:
    simular = "--simular" in sys.argv
    ahora   = datetime.now().strftime("%d/%m/%Y %H:%M")

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║      OPTIMIZADOR DE ESPACIO — iCloud             ║")
    print(f"║      {ahora:<45}║")
    print("╚══════════════════════════════════════════════════╝\n")

    libre_antes = espacio_libre()
    print(f"Espacio libre ahora: {tamaño_legible(libre_antes)}\n")

    if not ICLOUD.exists():
        print("✗ iCloud Drive no encontrado. Activa iCloud Drive en Ajustes del Sistema.")
        return

    print(f"Buscando archivos mayores de {UMBRAL_MB} MB...\n")
    candidatos = escanear_candidatos()

    if not candidatos:
        print("✓ No hay archivos grandes para mover. El disco está optimizado.\n")
        return

    total_tam = sum(t for _, t in candidatos)
    print(f"  Encontrados: {len(candidatos)} archivos ({tamaño_legible(total_tam)})\n")
    print("─" * 56)

    if simular:
        for archivo, tam in candidatos[:20]:
            print(f"  ~ {archivo.name[:45]:<45} {tamaño_legible(tam):>8}")
        print(f"\n  Total a liberar: {tamaño_legible(total_tam)}")
        print("\n  Para ejecutar: python3 optimizar_espacio.py\n")
        return

    liberado    = 0
    movidos     = 0
    errores     = 0

    for archivo, tam in candidatos:
        exito, bytes_lib = mover_a_icloud(archivo, simular)
        if exito:
            print(f"  ✓ {archivo.name[:50]:<50} {tamaño_legible(tam):>8}")
            liberado += bytes_lib
            movidos  += 1
        else:
            errores += 1

    libre_despues = espacio_libre()

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  RESULTADO                                       ║")
    print("╠══════════════════════════════════════════════════╣")
    print(f"║  Archivos movidos a iCloud: {movidos:<22}║")
    print(f"║  Espacio liberado:  {tamaño_legible(liberado):<29}║")
    print(f"║  Espacio libre ahora: {tamaño_legible(libre_despues):<27}║")
    print("╚══════════════════════════════════════════════════╝")
    print("\n✅ Los archivos siguen en iCloud, accesibles siempre.\n")


if __name__ == "__main__":
    main()
