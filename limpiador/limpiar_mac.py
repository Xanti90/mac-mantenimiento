
"""
LIMPIADOR INTELIGENTE DE MAC
==============================
Elimina archivos de caché, temporales y basura acumulada.
Nunca toca documentos, descargas organizadas, música, fotos ni iCloud.

Modos de uso:
  python3 limpiar_mac.py            → Escanea y muestra qué limpiaría (seguro)
  python3 limpiar_mac.py --limpiar  → Escanea y limpia
  python3 limpiar_mac.py --auto     → Solo limpia si hay más de 2 GB de basura (para automatización)

Autor: Santiago Jiménez
"""

import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Tuple

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────

# Umbral para el modo --auto: solo limpia si hay más basura que esto
UMBRAL_AUTO_GB = 2.0

# Directorio de logs
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "limpieza.log"

HOME = Path.home()

# ── Zonas a limpiar (SOLO caché y temporales, regenerables automáticamente) ──
ZONAS_LIMPIEZA = [
    {
        "nombre":      "Caché de aplicaciones",
        "ruta":        HOME / "Library/Caches",
        "tipo":        "directorio_contenido",
        "descripcion": "Archivos temporales que las apps regeneran solas",
    },
    {
        "nombre":      "Caché del sistema",
        "ruta":        Path("/Library/Caches"),
        "tipo":        "directorio_contenido",
        "descripcion": "Caché del sistema macOS",
    },
    {
        "nombre":      "Logs de usuario",
        "ruta":        HOME / "Library/Logs",
        "tipo":        "directorio_contenido",
        "descripcion": "Registros de actividad de aplicaciones",
    },
    {
        "nombre":      "Logs del sistema",
        "ruta":        Path("/Library/Logs"),
        "tipo":        "directorio_contenido",
        "descripcion": "Registros del sistema operativo",
    },
    {
        "nombre":      "Archivos temporales del sistema",
        "ruta":        Path("/private/tmp"),
        "tipo":        "directorio_contenido",
        "descripcion": "Archivos temporales del sistema",
    },
    {
        "nombre":      "Caché de iTunes / Apple Music",
        "ruta":        HOME / "Music/iTunes/Album Artwork/Cache",
        "tipo":        "directorio_contenido",
        "descripcion": "Miniaturas de álbumes (se regeneran al abrir Music)",
    },
    {
        "nombre":      "Caché de Xcode",
        "ruta":        HOME / "Library/Developer/Xcode/DerivedData",
        "tipo":        "directorio_contenido",
        "descripcion": "Proyectos compilados de Xcode",
    },
    {
        "nombre":      "Archivos .DS_Store",
        "ruta":        HOME,
        "tipo":        "ds_store",
        "descripcion": "Archivos ocultos de macOS sin utilidad",
    },
]

# ── Zonas BLINDADAS: nunca se tocan ──
ZONAS_PROTEGIDAS = [
    HOME / "Downloads",
    HOME / "Documents",
    HOME / "Desktop",
    HOME / "Pictures",
    HOME / "Movies",
    HOME / "Music/iTunes/iTunes Library.itl",
    HOME / "Music/iTunes/iTunes Music",
    HOME / "Music/Music",
    HOME / "Library/Mobile Documents",        # iCloud Drive
    HOME / "Library/Application Support",
    HOME / "Library/Keychains",
    HOME / "Library/Preferences",
]


# ─────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────

def tamaño_legible(bytes_: int) -> str:
    for unidad in ["B", "KB", "MB", "GB"]:
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unidad}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


def tamaño_carpeta(ruta: Path) -> int:
    """Calcula el tamaño total de una carpeta en bytes."""
    total = 0
    try:
        for item in ruta.rglob("*"):
            try:
                if item.is_file() and not item.is_symlink():
                    total += item.stat().st_size
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass
    return total


def esta_protegida(ruta: Path) -> bool:
    """Comprueba si una ruta está dentro de una zona blindada."""
    ruta_abs = ruta.resolve()
    for protegida in ZONAS_PROTEGIDAS:
        try:
            ruta_abs.relative_to(protegida.resolve())
            return True
        except ValueError:
            pass
    return False


def espacio_disco() -> tuple[int, int]:
    """Devuelve (usado, total) en bytes."""
    stat = shutil.disk_usage(HOME)
    return stat.used, stat.total


def escribir_log(mensaje: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {mensaje}\n")


# ─────────────────────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────────────────────

def escanear() -> list[dict]:
    """Escanea las zonas y devuelve una lista con lo que hay que limpiar."""
    resultados = []

    for zona in ZONAS_LIMPIEZA:
        ruta = zona["ruta"]

        if not ruta.exists():
            continue

        if esta_protegida(ruta):
            continue

        if zona["tipo"] == "directorio_contenido":
            bytes_zona = tamaño_carpeta(ruta)
            if bytes_zona > 0:
                resultados.append({
                    "nombre":      zona["nombre"],
                    "ruta":        ruta,
                    "tipo":        zona["tipo"],
                    "descripcion": zona["descripcion"],
                    "bytes":       bytes_zona,
                })

        elif zona["tipo"] == "ds_store":
            archivos = list(ruta.rglob(".DS_Store"))
            # Filtrar los que estén en zonas protegidas
            archivos = [a for a in archivos if not esta_protegida(a)]
            bytes_zona = sum(a.stat().st_size for a in archivos if a.exists())
            if archivos:
                resultados.append({
                    "nombre":      zona["nombre"],
                    "ruta":        ruta,
                    "tipo":        zona["tipo"],
                    "descripcion": zona["descripcion"],
                    "bytes":       bytes_zona,
                    "archivos":    archivos,
                })

    return resultados


# ─────────────────────────────────────────────────────────────
# LIMPIEZA
# ─────────────────────────────────────────────────────────────

def limpiar_zona(zona: dict) -> int:
    """Limpia una zona y devuelve los bytes liberados."""
    ruta = zona["ruta"]
    liberados = 0

    try:
        if zona["tipo"] == "directorio_contenido":
            for item in ruta.iterdir():
                if esta_protegida(item):
                    continue
                try:
                    tamaño = tamaño_carpeta(item) if item.is_dir() else item.stat().st_size
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    liberados += tamaño
                except (PermissionError, OSError):
                    pass

        elif zona["tipo"] == "ds_store":
            for archivo in zona.get("archivos", []):
                try:
                    tamaño = archivo.stat().st_size
                    archivo.unlink(missing_ok=True)
                    liberados += tamaño
                except (PermissionError, OSError):
                    pass

    except (PermissionError, OSError):
        pass

    return liberados


def limpiar_homebrew() -> int:
    """Limpia la caché de descargas de Homebrew."""
    try:
        resultado = subprocess.run(
            ["/opt/homebrew/bin/brew", "cleanup", "--prune=0", "-s"],
            capture_output=True, text=True, timeout=60
        )
        # Intentar leer cuánto liberó del output
        for linea in resultado.stdout.splitlines():
            if "freed" in linea.lower() or "liberado" in linea.lower():
                pass
        # Calcular tamaño del cache antes de limpiar
        cache_brew = Path(os.environ.get("HOME", "")) / "Library/Caches/Homebrew"
        return 0  # brew cleanup no reporta bytes fácilmente, se incluye en caché general
    except Exception:
        return 0


def vaciar_papelera() -> int:
    """Vacía la papelera y devuelve bytes liberados."""
    papelera = HOME / ".Trash"
    bytes_antes = tamaño_carpeta(papelera)
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Finder" to empty trash'],
            capture_output=True, timeout=30
        )
    except Exception:
        # Fallback manual
        for item in papelera.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
            except (PermissionError, OSError):
                pass
    return bytes_antes


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    modo_limpiar = "--limpiar" in sys.argv
    modo_auto    = "--auto"    in sys.argv

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║      LIMPIADOR INTELIGENTE DE MAC                ║")
    print(f"║      {ahora:<45}║")
    print("╚══════════════════════════════════════════════════╝\n")

    # ── Estado del disco ──
    usado, total = espacio_disco()
    libre = total - usado
    porcentaje_usado = (usado / total) * 100
    print(f"💾 Disco:  {tamaño_legible(total)} total")
    print(f"   Usado:  {tamaño_legible(usado)} ({porcentaje_usado:.1f}%)")
    print(f"   Libre:  {tamaño_legible(libre)}\n")

    # ── Escaneo ──
    print("🔍 Escaneando zonas seguras...\n")
    zonas = escanear()

    # Papelera
    bytes_papelera = tamaño_carpeta(HOME / ".Trash")

    total_bytes = sum(z["bytes"] for z in zonas) + bytes_papelera
    total_gb    = total_bytes / (1024 ** 3)

    if not zonas and bytes_papelera == 0:
        print("✅ El Mac está limpio, no hay nada que eliminar.\n")
        escribir_log("Escaneo completado — nada que limpiar")
        return

    # ── Mostrar lo encontrado ──
    print("─" * 52)
    print(f"  {'ZONA':<35} {'TAMAÑO':>10}")
    print("─" * 52)
    for zona in zonas:
        print(f"  📁 {zona['nombre']:<33} {tamaño_legible(zona['bytes']):>10}")
        print(f"     {zona['descripcion']}")
    if bytes_papelera > 0:
        print(f"  🗑️  Papelera                          {tamaño_legible(bytes_papelera):>10}")
    print("─" * 52)
    print(f"  {'TOTAL RECUPERABLE':<35} {tamaño_legible(total_bytes):>10}")
    print("─" * 52)

    # ── Lógica de modo ──
    if modo_auto:
        if total_gb < UMBRAL_AUTO_GB:
            print(f"\n💡 Modo automático: {total_gb:.2f} GB < {UMBRAL_AUTO_GB} GB de umbral.")
            print("   No es necesario limpiar todavía. ¡El Mac va bien!\n")
            escribir_log(f"Auto: {tamaño_legible(total_bytes)} de basura — por debajo del umbral, sin limpiar")
            return
        else:
            print(f"\n⚡ Modo automático: {total_gb:.2f} GB supera el umbral. Limpiando...\n")
            modo_limpiar = True

    if not modo_limpiar:
        print(f"\n👆 Modo escaneo (sin borrar nada).")
        print(f"   Para limpiar ejecuta: python3 limpiar_mac.py --limpiar\n")
        return

    # ── Limpieza ──
    print("\n🧹 Limpiando...\n")
    total_liberado = 0

    for zona in zonas:
        liberados = limpiar_zona(zona)
        total_liberado += liberados
        print(f"  ✓  {zona['nombre']:<35} {tamaño_legible(liberados):>10}")

    # Papelera
    if bytes_papelera > 0:
        liberados_papelera = vaciar_papelera()
        total_liberado += liberados_papelera
        print(f"  ✓  Papelera vaciada                   {tamaño_legible(liberados_papelera):>10}")

    # Homebrew
    limpiar_homebrew()

    # ── Resultado final ──
    usado_nuevo, _ = espacio_disco()
    libre_nuevo = total - usado_nuevo

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  RESULTADO                                       ║")
    print("╠══════════════════════════════════════════════════╣")
    print(f"║  🧹 Espacio liberado:  {tamaño_legible(total_liberado):<27}║")
    print(f"║  💾 Espacio libre ahora: {tamaño_legible(libre_nuevo):<25}║")
    print("╚══════════════════════════════════════════════════╝")
    print("\n✅ ¡Mac limpio y optimizado!\n")

    escribir_log(
        f"Limpieza completada — liberado: {tamaño_legible(total_liberado)} | "
        f"libre ahora: {tamaño_legible(libre_nuevo)}"
    )


if __name__ == "__main__":
    main()
