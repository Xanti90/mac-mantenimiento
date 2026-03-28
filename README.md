# Mac Mantenimiento 🛠️

Herramientas de mantenimiento y optimización para macOS.

## Scripts disponibles

| Script | Descripción |
|--------|-------------|
| `limpiador/limpiar_mac.py` | Limpiador inteligente de caché, temporales y basura |

## Uso del limpiador

```bash
# Solo escanear (no borra nada, modo seguro)
python3 limpiador/limpiar_mac.py

# Escanear y limpiar
python3 limpiador/limpiar_mac.py --limpiar

# Modo automático: solo limpia si hay más de 2 GB de basura
python3 limpiador/limpiar_mac.py --auto
```

## Zonas que limpia

- Caché de aplicaciones (`~/Library/Caches`)
- Caché del sistema (`/Library/Caches`)
- Logs de usuario y sistema
- Archivos temporales del sistema
- Caché de portadas de iTunes / Apple Music
- Archivos `.DS_Store`
- Papelera
- Caché de Homebrew

## Zonas PROTEGIDAS (nunca se tocan)

- `~/Downloads` — descargas organizadas
- `~/Documents` — documentos
- `~/Desktop` — escritorio
- `~/Pictures` — fotos
- `~/Movies` — vídeos
- `~/Music` — biblioteca de Apple Music / iTunes
- `iCloud Drive` — archivos en la nube
- Preferencias, Keychains y datos de aplicaciones

## Automatización

Se ejecuta automáticamente:
- **Cada domingo a las 10:00 AM**
- **Al arrancar el Mac** (si no se ejecutó hoy)
- Solo actúa si hay más de **2 GB** de basura acumulada

Los logs se guardan en `logs/limpieza.log`.

---
Mantenido por Santiago Jiménez
