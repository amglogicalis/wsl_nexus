# WSL Desktop Nexus

> Gestor de distribuciones WSL con interfaz gráfica premium para Windows.

![Version](https://img.shields.io/github/v/release/amglogicalis/wsl_nexus?style=flat-square&label=versión)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?style=flat-square&logo=windows)
![WSL](https://img.shields.io/badge/WSL-2-orange?style=flat-square&logo=linux)
![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)

---

## ¿Qué es WSL Desktop Nexus?

Es una aplicación de escritorio nativa para Windows que te permite administrar y controlar de forma visual e intuitiva todas tus distribuciones del Subsistema de Windows para Linux (WSL 2).

### Características Principales:
- 📊 **Monitor de Estado**: Inicia, detiene y visualiza tus distribuciones Linux activas con un solo clic.
- 💻 **Consola Interactiva**: Terminales integradas de alto rendimiento con pestañas múltiples.
- 📦 **Importador de Tarballs**: Importa cualquier distribución personalizada (`.tar` o `.tar.gz`) directamente desde la interfaz.
- 🗑️ **Desinstalador Directo**: Elimina de forma segura distribuciones registradas liberando espacio en disco.
- 🔄 **Actualizador Integrado**: Avisos emergentes inteligentes cuando hay nuevas versiones disponibles para descargar.

---

## 🚀 Instalación (Usuarios)

Para instalar y utilizar la aplicación de forma rápida y sencilla:

1. Ve a la sección **[Releases](https://github.com/amglogicalis/wsl_nexus/releases/latest)**.
2. Descarga el archivo instalador: `WSLNexus_Setup_vX.X.X.exe`.
3. Ejecútalo como **Administrador** (clic derecho → *Ejecutar como administrador*).
4. El asistente de instalación se encargará de:
   - **Activar WSL 2** y Virtual Machine Platform si no están activos en tu equipo (evitando configuraciones manuales).
   - Instalar el programa en la ruta elegida.
   - Crear accesos directos en el Escritorio e Inicio.
   - Registrar la aplicación en "Agregar o quitar programas" para que puedas desinstalarla limpiamente si lo deseas.

---

## 🛠️ Desarrollo: Trabajar desde cualquier PC

Si deseas modificar el código o compilar el programa desde otro ordenador con tu misma cuenta de GitHub, sigue estos pasos:

### 1. Clonar el repositorio
Asegúrate de tener instalado Git y tu cuenta configurada:
```powershell
git clone https://github.com/amglogicalis/wsl_nexus.git
cd wsl_nexus
```

### 2. Configurar entorno
Instala Python 3.10+ e Inno Setup 6 (https://jrsoftware.org/isdl.php), luego instala las dependencias de Python:
```powershell
pip install pywebview winpty pyinstaller
```

### 3. Ejecutar en modo desarrollo
```powershell
python app.py
```

### 4. Compilar y publicar actualizaciones
El proceso de compilación del ejecutable `.exe` y empaquetado del instalador está automatizado en un solo script (`build_release.ps1`).

* **Solo compilar localmente** (genera el instalador en `installer_output/`):
  ```powershell
  .\build_release.ps1
  ```

* **Compilar y publicar el release en GitHub**:
  Para subir el release automáticamente a GitHub utilizando tu cuenta, define tu Token de Acceso Personal (PAT) en una variable de entorno antes de ejecutar el script:
  ```powershell
  # Configurar tu token de GitHub
  $env:GITHUB_TOKEN = "tu_github_pat_aquí"

  # Compilar y subir la versión (se subirá el tag y el release con tu cuenta activa)
  .\build_release.ps1 -Version "1.0.0" -UploadRelease
  ```

---

## 📄 Propiedad y Licencia

- **Propiedad Intelectual**: Este software y su código fuente son propiedad exclusiva de **AMG Logicalis**.
- **Licencia de uso**: Se concede permiso para descargar, instalar y utilizar libremente los ejecutables e instaladores distribuidos oficialmente. Queda prohibida la redistribución de copias modificadas o su comercialización sin consentimiento expreso por escrito.
