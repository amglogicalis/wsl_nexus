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

#### **VÍA INSTALLER.EXE**

1. Ve a la sección **[Releases](https://github.com/amglogicalis/wsl_nexus/releases/latest)**.
2. Descarga el archivo instalador: `WSLNexus_Setup_vX.X.X.exe`.
3. Ejecútalo como **Administrador** (clic derecho → *Ejecutar como administrador*).
4. El asistente de instalación se encargará de:
   - **Activar WSL 2** y Virtual Machine Platform si no están activos en tu equipo (evitando configuraciones manuales).
   - Instalar el programa en la ruta elegida.
   - Crear accesos directos en el Escritorio e Inicio.
   - Registrar la aplicación en "Agregar o quitar programas" para que puedas desinstalarla limpiamente si lo deseas.

#### **VÍA PYTHON**

1. Clonar repo mediante "git clone https://github.com/amglogicalis/wsl_nexus.git"
2. Instalar dependencias (necesitas instalar, si no lo tienes Python:https://www.python.org/downloads/windows/) mediante "python install_deps.py" en un terminal
3. Ejecutar la app mediante "python app.py"

### ⚠️ Aviso de Windows Defender / SmartScreen

Es posible que al ejecutar el instalador, **Windows Defender SmartScreen** muestre una advertencia indicando que el archivo puede ser peligroso. Esto ocurre porque el ejecutable **no está firmado digitalmente** con un certificado de confianza (code signing), lo cual es habitual en software independiente y de código abierto.

**El programa es completamente seguro.** Para continuar con la instalación:
1. Haz clic en **"Más información"** en la ventana de advertencia.
2. Luego pulsa **"Ejecutar de todas formas"** para iniciar el instalador.
3. Asegúrate de ejecutar como **Administrador** para que la instalación se complete correctamente.

> [!IMPORTANT]
> **Reinicio del Sistema**: Si es la primera vez que habilitas WSL en tu ordenador, es muy probable que necesites **reiniciar el ordenador** tras instalar tu primer distribuidor y, tras reiniciar, seguramente volver a instalarlo (o registrarlo) para que se complete la configuración y aparezca en la lista de activos.

> [!WARNING]
> **No ejecutar la aplicación como Administrador**: El programa principal (`app.exe`) **NO** debe ser ejecutado con privilegios de Administrador. Si la ejecutas como Administrador, las distribuciones de WSL se registrarán en el perfil de la cuenta Administrador y no serán visibles desde tu usuario normal, o recibirás errores de "Acceso denegado" (`E_ACCESSDENIED`) al intentar reinstalarlas.

---

## 🔄 ¿Cómo actualizar la aplicación?

Actualizar WSL Desktop Nexus es sumamente fácil y seguro:

1. **Aviso Automático**: La aplicación verifica en segundo plano la existencia de nuevas versiones al iniciar. Si hay una actualización disponible, aparecerá una notificación emergente (Toast) en la esquina inferior derecha.
2. **Descarga**: Haz clic en la notificación. Se abrirá tu navegador predeterminado y te redirigirá a la página de descargas de GitHub para obtener la última versión del instalador (`WSLNexus_Setup_vX.X.X.exe`).
3. **Instalación**:
   - Cierra la aplicación WSL Desktop Nexus si la tienes abierta.
   - Ejecuta el nuevo instalador descargado como **Administrador**.
   - Sigue los pasos del asistente de instalación.
4. **Conservación de datos**: El instalador actualizará los archivos necesarios sobrescribiendo la versión anterior de forma segura. **Todas tus distribuciones de WSL 2 instaladas y sus datos se mantendrán intactos** y no se perderán.

---

## 📄 Propiedad y Licencia

- **Propiedad Intelectual**: Este software y su código fuente son propiedad exclusiva de **AMG Logicalis**.
- **Licencia de uso**: Se concede permiso para descargar, instalar y utilizar libremente los ejecutables e instaladores distribuidos oficialmente. Queda prohibida la redistribución de copias modificadas o su comercialización sin consentimiento expreso por escrito.
