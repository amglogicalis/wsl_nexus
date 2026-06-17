# WSL Desktop Nexus

> Gestor de distribuciones WSL con interfaz gráfica premium para Windows.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?style=flat-square&logo=windows)
![WSL](https://img.shields.io/badge/WSL-2-orange?style=flat-square&logo=linux)
![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)

---

## ¿Qué es WSL Desktop Nexus?

Una aplicación de escritorio nativa para Windows que te permite **gestionar todas tus distribuciones WSL** desde una interfaz visual moderna, sin necesidad de usar la terminal.

### Funcionalidades principales

- 📋 **Ver distribuciones** instaladas y disponibles en la nube
- ▶️ **Iniciar / Detener** distribuciones con un clic
- 💻 **Terminal interactiva** embebida por cada distribución (con soporte para múltiples pestañas)
- 📦 **Importar distribuciones personalizadas** desde archivos `.tar` / `.tar.gz` con selector visual de archivos
- 🗑️ **Desinstalar** distribuciones con confirmación visual
- 🎨 **4 temas de color** (Cyan, Amber, Emerald, Crimson)
- 🔤 **Tamaño de fuente** de terminal configurable

---

## Requisitos previos

| Requisito | Versión mínima |
|---|---|
| Windows | 10 (build 19041) / 11 |
| Python | 3.10+ |
| WSL | 2 |

### Dependencias Python

```bash
pip install pywebview winpty pyinstaller
```

---

## Cómo ejecutar (modo desarrollo)

```bash
# Clona el repositorio
git clone https://github.com/amglogicalis/wsl_nexus.git
cd wsl_nexus

# Instala las dependencias
pip install pywebview winpty

# Lanza la aplicación
python app.py
```

---

## Cómo compilar el ejecutable `.exe`

```bash
pip install pyinstaller
python -m PyInstaller app.spec --clean
```

El ejecutable se genera en `dist/app.exe`. Cópialo a la carpeta raíz del proyecto o a donde prefieras.

> **Nota:** En equipos corporativos con políticas AppLocker/Antivirus restrictivas, es posible que el `.exe` compilado sea bloqueado. En ese caso, usa siempre `python app.py`.

---

## Estructura del proyecto

```
wsl_nexus/
├── app.py          # Backend Python (pywebview + winpty PTY bridge)
├── index.html      # Interfaz de usuario
├── app.css         # Estilos (glassmorphism, temas, animaciones)
├── app.js          # Lógica frontend (xterm.js, gestión de sesiones)
├── app.ico         # Icono de la aplicación
└── app.spec        # Configuración de PyInstaller
```

---

## Importar distribuciones personalizadas

La app permite importar cualquier distribución Linux empaquetada como `.tar` o `.tar.gz`.

**Formas de obtener un rootfs:**

1. **Exportar una distro existente** (en PowerShell):
   ```powershell
   wsl --export Ubuntu C:\WSL\mi-copia.tar   # (ejemplo)
   ```

2. **Exportar desde Docker** (ejemplo con cualquier imagen):
   ```powershell
   docker export mi-contenedor -o C:\WSL\rootfs.tar   # (ejemplo)
   ```

3. **Descargar desde fuentes oficiales:** Alpine Linux, Ubuntu Cloud Images, etc.

---

## Licencia

© 2025 AMG Logicalis. Todos los derechos reservados.

Este software es de uso interno/propietario. Queda prohibida su redistribución, modificación o uso comercial sin autorización expresa por escrito del autor.
