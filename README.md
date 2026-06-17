# WSL Desktop Nexus

> Gestor de distribuciones WSL con interfaz gráfica premium para Windows.

![Version](https://img.shields.io/github/v/release/amglogicalis/wsl_nexus?style=flat-square&label=versión)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?style=flat-square&logo=windows)
![WSL](https://img.shields.io/badge/WSL-2-orange?style=flat-square&logo=linux)
![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)

---

## ¿Qué es WSL Desktop Nexus?

Una aplicación de escritorio nativa para Windows que te permite **gestionar todas tus distribuciones WSL** desde una interfaz visual moderna, sin necesidad de usar la terminal.

### Funcionalidades principales

- 📋 **Ver** distribuciones instaladas y disponibles en la nube
- ▶️ **Iniciar / Detener** distribuciones con un clic
- 💻 **Terminal interactiva** embebida por cada distribución (pestañas múltiples)
- 📦 **Importar distribuciones personalizadas** desde `.tar` / `.tar.gz` con selector de archivos
- 🗑️ **Desinstalar** distribuciones con confirmación visual
- 🔔 **Notificación automática** de nuevas versiones disponibles
- 🎨 **4 temas de color** (Cyan, Amber, Emerald, Crimson)

---

## 🚀 Instalación para usuarios finales

### Método recomendado: Installer

1. Ve a la sección **[Releases](https://github.com/amglogicalis/wsl_nexus/releases/latest)**
2. Descarga `WSLNexus_Setup_vX.X.X.exe`
3. Ejecútalo **como Administrador** (clic derecho → Ejecutar como administrador)
4. El installer:
   - Activa WSL automáticamente si no está habilitado
   - Instala la app en la carpeta elegida
   - Crea accesos directos opcionales en el escritorio y menú de inicio
   - Registra el desinstalador en "Agregar o quitar programas"

> **Nota en equipos corporativos:** Si el antivirus o AppLocker bloquea el `.exe`, usa el método de desarrollo (ver abajo).

---

## 🛠️ Requisitos para desarrollo

| Herramienta | Versión mínima | Descarga |
|---|---|---|
| Windows | 10 build 19041 / 11 | — |
| Python | 3.10+ | https://python.org |
| Git | Cualquiera | https://git-scm.com |
| Inno Setup | 6.x | https://jrsoftware.org/isdl.php |

### Instalar dependencias Python

```powershell
pip install pywebview winpty pyinstaller
```

---

## 💻 Ejecutar en modo desarrollo

```powershell
git clone https://github.com/amglogicalis/wsl_nexus.git
cd wsl_nexus
pip install pywebview winpty
python app.py
```

---

## 📦 Compilar y publicar un Release

Todo el proceso se automatiza con un solo script:

### 1. Instalar Inno Setup 6

Descarga e instala desde: **https://jrsoftware.org/isdl.php**

### 2. Ejecutar el script de build

```powershell
# Solo compilar (sin subir a GitHub)
.\build_release.ps1

# Compilar + subir release a GitHub automáticamente
.\build_release.ps1 -Version "1.1.0" -UploadRelease -GitHubToken "ghp_TU_TOKEN"
```

El script hará automáticamente:
1. ✅ Verifica que Python, PyInstaller e Inno Setup estén instalados
2. ⚙️ Compila `app.exe` con PyInstaller
3. 📦 Compila `WSLNexus_Setup_vX.X.X.exe` con Inno Setup
4. 🏷️ Crea el tag git `vX.X.X` (si `-UploadRelease`)
5. 🚀 Sube el installer como asset al release de GitHub (si `-UploadRelease`)

El installer final se genera en: `installer_output\WSLNexus_Setup_vX.X.X.exe`

---

## 🔄 Flujo de trabajo para nuevas versiones

```
1. Hacer cambios en el código
2. Actualizar archivo VERSION  →  echo "1.2.0" > VERSION
3. Commit y push del código    →  git add -A && git commit -m "feat: ..." && git push
4. Compilar y publicar release →  .\build_release.ps1 -Version "1.2.0" -UploadRelease -GitHubToken "ghp_..."
```

Los usuarios con la app instalada verán una **notificación automática** en la interfaz cuando haya una nueva versión disponible (requiere conexión a internet).

---

## 📂 Estructura del proyecto

```
wsl_nexus/
├── app.py              # Backend Python (pywebview + PTY bridge WSL)
├── index.html          # Interfaz de usuario
├── app.css             # Estilos (glassmorphism, 4 temas, animaciones)
├── app.js              # Lógica frontend (xterm.js, update checker)
├── app.ico             # Icono de la aplicación
├── app.spec            # Configuración de PyInstaller
├── installer.iss       # Script del instalador (Inno Setup 6)
├── check_prereqs.ps1   # Activa WSL/WSL2 (ejecutado por el installer)
├── build_release.ps1   # Script de build y publicación automatizada
├── VERSION             # Versión actual (ej: 1.0.0)
├── LICENSE.txt         # Licencia
├── .gitignore          # Exclusiones de git
└── README.md           # Este archivo
```

---

## Importar distribuciones personalizadas

La app permite importar cualquier distribución Linux empaquetada como `.tar` o `.tar.gz`.

**¿Cómo obtener un rootfs?**

1. **Exportar una distro existente** (en PowerShell — sustituye `Ubuntu` por tu distro):
   ```powershell
   wsl --export Ubuntu C:\WSL\mi-copia.tar   # (ejemplo)
   ```

2. **Exportar desde Docker** (sustituye `mi-contenedor` por el nombre real):
   ```powershell
   docker export mi-contenedor -o C:\WSL\rootfs.tar   # (ejemplo)
   ```

3. **Descargar desde fuentes oficiales:** Alpine Linux, Ubuntu Cloud Images, etc. ofrecen archivos `.tar.gz` directamente descargables sin necesidad de escribir ningún comando.

---

## Licencia

© 2025 AMG Logicalis. Todos los derechos reservados.

Este software es de uso interno/propietario. Queda prohibida su redistribución, modificación o uso comercial sin autorización expresa por escrito del autor.
