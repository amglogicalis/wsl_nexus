/* -------------------------------------------------------------
   WSL Desktop Nexus - Frontend Application Logic
   ------------------------------------------------------------- */

let allDistros = [];
let activeSessions = {}; // sessionId -> { distroName, term, fitAddon, paneDiv, tabDiv }
let activeSessionId = null;
let pyReady = false;
let resizeTimeout = null;
let currentView = 'distros';
let currentInstallSessionId = null; // PTY session id for the active install/import
let pendingUninstallDistro = null;  // distro name pending uninstall confirmation

// Initialize Lucide icons on load
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initTheme();
    
    // Check if pywebview is already loaded, otherwise wait for event
    if (window.pywebview) {
        onPywebviewReady();
    } else {
        window.addEventListener('pywebviewready', onPywebviewReady);
    }
});

function onPywebviewReady() {
    pyReady = true;
    showToast('Connected to Nexus Backend Engine', 'success');
    
    // Query python and wsl details for settings page
    try {
        pywebview.api.get_system_info().then(info => {
            document.getElementById('info-python-ver').textContent = info.python_version || 'N/A';
            document.getElementById('info-wsl-ver').textContent = info.wsl_version || 'N/A';
        });
    } catch (e) {
        console.error(e);
    }
    
    refreshDistros();
}

// Visual Themes Management
function initTheme() {
    const savedTheme = localStorage.getItem('nexus-theme') || 'cyan';
    setTheme(savedTheme);
}

function setTheme(theme) {
    document.body.className = `theme-${theme}`;
    localStorage.setItem('nexus-theme', theme);
    
    // Update active class on settings buttons
    document.querySelectorAll('.theme-option').forEach(btn => {
        if (btn.getAttribute('data-theme') === theme) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Adjust Terminal Font Size
function adjustFontSize(delta) {
    const input = document.getElementById('setting-font-size');
    let size = parseInt(input.value) + delta;
    size = Math.max(10, Math.min(24, size));
    input.value = size;
    
    // Apply to all active terminals
    for (const sessionId in activeSessions) {
        const session = activeSessions[sessionId];
        if (session && session.term) {
            session.term.options.fontSize = size;
            setTimeout(() => {
                session.fitAddon.fit();
                // Inform backend of new dimensions
                if (pyReady) {
                    pywebview.api.resize_terminal(sessionId, session.term.cols, session.term.rows);
                }
            }, 50);
        }
    }
}

// Navigation View Switching
function switchView(viewName) {
    currentView = viewName;
    
    // Toggle active navigation items
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeNavBtn = document.getElementById(`btn-nav-${viewName}`);
    if (activeNavBtn) activeNavBtn.classList.add('active');
    
    // Toggle view panels
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    const targetPanel = document.getElementById(`view-${viewName}`);
    if (targetPanel) targetPanel.classList.add('active');
    
    // Change view title
    const titleEl = document.getElementById('current-view-title');
    if (viewName === 'distros') {
        titleEl.textContent = 'Distributions';
        document.getElementById('search-box-wrapper').style.display = 'block';
    } else if (viewName === 'terminals') {
        titleEl.textContent = 'Active Terminals';
        document.getElementById('search-box-wrapper').style.display = 'none';
        // Refit active terminal on switch
        setTimeout(fitActiveTerminal, 100);
    } else if (viewName === 'settings') {
        titleEl.textContent = 'Settings';
        document.getElementById('search-box-wrapper').style.display = 'none';
    } else if (viewName === 'installer') {
        titleEl.textContent = 'WSL Cloud Installer';
        document.getElementById('search-box-wrapper').style.display = 'none';
    }
}

// Fetch & Update WSL list
function refreshDistros() {
    if (!pyReady) return;
    
    const refreshIcon = document.getElementById('refresh-icon');
    if (refreshIcon) refreshIcon.classList.add('rotate-spin');
    
    document.getElementById('distros-grid').innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Scanning WSL engine...</p>
        </div>
    `;
    
    pywebview.api.get_wsl_distros().then(distros => {
        allDistros = distros;
        renderDistros(distros);
        updateStats(distros);
        
        if (refreshIcon) {
            setTimeout(() => refreshIcon.classList.remove('rotate-spin'), 600);
        }
    }).catch(err => {
        showToast('Error scanning WSL distros: ' + err, 'danger');
        if (refreshIcon) refreshIcon.classList.remove('rotate-spin');
    });
}

function updateStats(distros) {
    const total = distros.length;
    const running = distros.filter(d => d.state === 'Running').length;
    const defaultDist = distros.find(d => d.is_default);
    
    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-running').textContent = running;
    document.getElementById('stat-default').textContent = defaultDist ? defaultDist.name : 'None';
}

function filterDistros() {
    const query = document.getElementById('search-input').value.toLowerCase().trim();
    if (!query) {
        renderDistros(allDistros);
        return;
    }
    
    const filtered = allDistros.filter(d => 
        d.name.toLowerCase().includes(query) || 
        (d.friendly_name && d.friendly_name.toLowerCase().includes(query))
    );
    renderDistros(filtered);
}

// Helper: SVG templates for distro logos
function getDistroLogo(name) {
    const lowerName = name.toLowerCase();
    
    // Ubuntu
    if (lowerName.includes('ubuntu')) {
        return `<svg viewBox="0 0 24 24" fill="#dd4814"><circle cx="12" cy="12" r="11" fill="none" stroke="#dd4814" stroke-width="2"/><circle cx="12" cy="5" r="2.5"/><circle cx="7" cy="14" r="2.5"/><circle cx="17" cy="14" r="2.5"/></svg>`;
    }
    // Debian
    if (lowerName.includes('debian')) {
        return `<svg viewBox="0 0 24 24" fill="#d70a53"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm0 18c-4.4 0-8-3.6-8-8s3.6-8 8-8 8 3.6 8 8-3.6 8-8 8zm-2-12c1.5 0 2.5 1 2.5 2.5S11.5 11 10 11H8V8h2zm0 5c1.7 0 3 1.3 3 3s-1.3 3-3 3H8v-6h2z"/></svg>`;
    }
    // Kali
    if (lowerName.includes('kali') || lowerName.includes('backtrack')) {
        return `<svg viewBox="0 0 24 24" fill="#1f90ff"><path d="M12 2L2 22h20L12 2zm0 5l6 12H6l6-12z"/></svg>`;
    }
    // openSUSE or SUSE
    if (lowerName.includes('suse') || lowerName.includes('tumbleweed') || lowerName.includes('leap')) {
        return `<svg viewBox="0 0 24 24" fill="#2cbf5e"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm0 3c3.9 0 7 3.1 7 7s-3.1 7-7 7-7-3.1-7-7 3.1-7 7-7z"/></svg>`;
    }
    // Generic linux / other
    return `<svg viewBox="0 0 24 24" fill="var(--accent-color)"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>`;
}

function getDistroClass(name) {
    const lowerName = name.toLowerCase();
    if (lowerName.includes('ubuntu')) return 'card-ubuntu';
    if (lowerName.includes('debian')) return 'card-debian';
    if (lowerName.includes('kali')) return 'card-kali';
    if (lowerName.includes('suse') || lowerName.includes('tumbleweed') || lowerName.includes('leap')) return 'card-suse';
    return 'card-generic';
}

function renderDistros(distros) {
    const grid = document.getElementById('distros-grid');
    if (!distros || distros.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i data-lucide="alert-circle" style="width: 48px; height: 48px; margin-bottom: 16px;"></i>
                <p>No distributions found matching the filters.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    grid.innerHTML = '';
    
    distros.forEach(dist => {
        const card = document.createElement('div');
        card.className = `distro-card ${getDistroClass(dist.name)}`;
        
        let statusText = 'Available';
        let statusClass = 'status-available';
        let mainAction = '';
        let secondaryAction = '';
        let detailsRow = '';
        
        if (dist.installed) {
            statusText = dist.state === 'Running' ? 'Active' : 'Stopped';
            statusClass = dist.state === 'Running' ? 'status-active' : 'status-stopped';
            
            mainAction = `<button class="btn btn-primary" onclick="launchDistroTerminal('${dist.name}')"><i data-lucide="terminal"></i> Terminal</button>`;
            
            if (dist.state === 'Running') {
                secondaryAction = `<button class="btn btn-secondary btn-danger-hover" onclick="stopDistro('${dist.name}')" title="Stop Distribution"><i data-lucide="power"></i> Stop</button>`;
            } else {
                secondaryAction = `<button class="btn btn-secondary" onclick="startDistroSilent('${dist.name}')" title="Start Session"><i data-lucide="play"></i> Start</button>`;
            }
            
            detailsRow = `
                <div class="distro-meta-info">
                    <div class="meta-item"><i data-lucide="cpu"></i> <span>WSL ${dist.version || '2'}</span></div>
                    ${dist.is_default ? '<div class="meta-item text-highlight"><i data-lucide="star"></i> <span>Default</span></div>' : ''}
                </div>
            `;
        } else {
            mainAction = `<button class="btn btn-primary" onclick="installDistro('${dist.name}')"><i data-lucide="download-cloud"></i> Install</button>`;
            detailsRow = `
                <div class="distro-meta-info">
                    <div class="meta-item"><i data-lucide="globe"></i> <span>Cloud Available</span></div>
                </div>
            `;
        }
        
        card.innerHTML = `
            <div class="distro-card-header">
                <div class="distro-card-title">
                    <div class="distro-logo">
                        ${getDistroLogo(dist.name)}
                    </div>
                    <div class="distro-details">
                        <h4>${dist.friendly_name || dist.name}</h4>
                        <span>${dist.name}</span>
                    </div>
                </div>
                <div class="status-pill ${statusClass}">
                    <span class="status-dot"></span>
                    <span>${statusText}</span>
                </div>
            </div>
            ${detailsRow}
            <div class="distro-actions">
                ${mainAction}
                ${secondaryAction}
                ${dist.installed ? `<button class="btn btn-secondary btn-danger-hover" onclick="uninstallDistro('${dist.name}')" title="Uninstall Distribution" style="flex-grow: 0; width: 42px; padding: 10px 0;"><i data-lucide="trash-2" style="width: 16px; height: 16px;"></i></button>` : ''}
            </div>
        `;
        
        grid.appendChild(card);
    });
    
    lucide.createIcons();
}

// Distro operations
function startDistroSilent(distroName) {
    if (!pyReady) return;
    showToast(`Starting ${distroName}...`, 'info');
    pywebview.api.start_distro_silent(distroName).then(success => {
        if (success) {
            showToast(`${distroName} is now running`, 'success');
            refreshDistros();
        } else {
            showToast(`Failed to start ${distroName}`, 'danger');
        }
    });
}

function stopDistro(distroName) {
    if (!pyReady) return;
    showToast(`Stopping ${distroName}...`, 'info');
    pywebview.api.stop_distro(distroName).then(success => {
        if (success) {
            showToast(`${distroName} stopped successfully`, 'success');
            refreshDistros();
        } else {
            showToast(`Failed to stop ${distroName}`, 'danger');
        }
    });
}

// Cloud distribution installer
function installDistro(distroName) {
    if (!pyReady) return;
    
    // Clear installer log console
    const logBox = document.getElementById('installer-log-terminal');
    logBox.textContent = '';
    
    // Setup labels
    document.getElementById('install-distro-name').textContent = `Installing ${distroName}`;
    document.getElementById('install-status-text').textContent = 'Initializing installer task...';
    document.querySelector('.installer-spinner').style.display = 'block';
    
    // Reset and enable interactive input bar
    setInstallerInputEnabled(true);
    document.getElementById('installer-input').value = '';
    document.getElementById('installer-input').placeholder = 'Escribe aquí si el proceso pide datos (usuario, contraseña...)';
    
    // Switch view
    switchView('installer');
    
    // Call Python install api
    pywebview.api.install_distro(distroName).then(res => {
        if (res.started) {
            currentInstallSessionId = res.session_id;
            showToast(`Installation of ${distroName} started`, 'info');
            setTimeout(() => document.getElementById('installer-input').focus(), 300);
        } else {
            showToast(`Could not start installer: ${res.message}`, 'danger');
            document.getElementById('install-status-text').textContent = `Failed to start: ${res.message}`;
            document.querySelector('.installer-spinner').style.display = 'none';
            setInstallerInputEnabled(false);
        }
    });
}

function cancelInstallation() {
    currentInstallSessionId = null;
    setInstallerInputEnabled(false);
    switchView('distros');
    refreshDistros();
}

// Terminal Instances & Sessions Management
function launchDistroTerminal(distroName) {
    switchView('terminals');
    
    // Check if we already have an active terminal for this distro
    for (const sessionId in activeSessions) {
        if (activeSessions[sessionId].distroName === distroName) {
            selectTerminalTab(sessionId);
            return;
        }
    }
    
    // Create new terminal container in pane
    const paneId = `pane-${Date.now()}`;
    const paneDiv = document.createElement('div');
    paneDiv.className = 'terminal-pane';
    paneDiv.id = paneId;
    document.getElementById('terminal-panes-container').appendChild(paneDiv);
    
    // Render clean tabs bar (remove "no terminals" message if there)
    const tabsBar = document.getElementById('terminal-tabs-bar');
    const emptyMsg = tabsBar.querySelector('.no-terminals-msg');
    if (emptyMsg) emptyMsg.remove();
    
    // Create tab button
    const tabId = `tab-${Date.now()}`;
    const tabDiv = document.createElement('div');
    tabDiv.className = 'terminal-tab';
    tabDiv.id = tabId;
    tabDiv.innerHTML = `
        <i data-lucide="terminal" style="width: 14px; height: 14px;"></i>
        <span>${distroName}</span>
        <button class="tab-close-btn" onclick="event.stopPropagation(); closeTerminalTab('${paneId}')">
            <i data-lucide="x"></i>
        </button>
    `;
    
    // Tab click select
    tabDiv.onclick = () => selectTerminalTab(paneId);
    tabsBar.appendChild(tabDiv);
    lucide.createIcons({ props: { style: 'width: 12px; height: 12px;' }, nameList: ['x'] });
    lucide.createIcons();
    
    // Initialize Xterm.js terminal instance
    const fontSizeSetting = parseInt(document.getElementById('setting-font-size').value) || 14;
    const term = new Terminal({
        cursorBlink: true,
        fontFamily: '"JetBrains Mono", Menlo, Monaco, Consolas, monospace',
        fontSize: fontSizeSetting,
        theme: {
            background: '#06080d',
            foreground: '#e2e8f0',
            cursor: '#06b6d4',
            cursorAccent: '#06080d',
            selectionBackground: 'rgba(6, 182, 212, 0.3)',
            black: '#000000',
            red: '#ff5555',
            green: '#50fa7b',
            yellow: '#f1fa8c',
            blue: '#bd93f9',
            magenta: '#ff79c6',
            cyan: '#8be9fd',
            white: '#bfbfbf',
            brightBlack: '#4d4d4d',
            brightRed: '#ff6e67',
            brightGreen: '#5af78e',
            brightYellow: '#f4f99d',
            brightBlue: '#caa9fa',
            brightMagenta: '#ff92d0',
            brightCyan: '#9aedfe',
            brightWhite: '#e6e6e6'
        }
    });
    
    const fitAddon = new window.FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(paneDiv);
    fitAddon.fit();
    
    const cols = term.cols || 80;
    const rows = term.rows || 24;
    
    // Save session in registry before calling backend so callback can access it immediately
    activeSessions[paneId] = {
        distroName: distroName,
        term: term,
        fitAddon: fitAddon,
        paneDiv: paneDiv,
        tabDiv: tabDiv
    };
    
    // Call Python to spawn PTY shell
    pywebview.api.create_terminal_session(distroName, cols, rows).then(res => {
        if (res.success) {
            const actualSessionId = res.session_id;
            
            // Map actual backend session ID to paneId
            activeSessions[paneId].backendSessionId = actualSessionId;
            // Also store lookup reference
            activeSessions[actualSessionId] = activeSessions[paneId];
            
            // Hook up terminal input handler
            term.onData(data => {
                if (pyReady) {
                    pywebview.api.write_terminal_data(actualSessionId, data);
                }
            });
            
            selectTerminalTab(paneId);
            updateTerminalCount();
            
            // Focus terminal input
            setTimeout(() => term.focus(), 100);
            
            refreshDistros(); // Distro state might have updated to "Running"
        } else {
            showToast(`Could not start terminal for ${distroName}: ${res.message}`, 'danger');
            closeTerminalTab(paneId, false);
        }
    });
}

function selectTerminalTab(paneId) {
    activeSessionId = paneId;
    
    // Toggle active classes in UI
    for (const id in activeSessions) {
        const session = activeSessions[id];
        // Ensure we only process key entry, not duplicate mappings
        if (id.startsWith('pane-') && session) {
            if (id === paneId) {
                session.paneDiv.classList.add('active');
                session.tabDiv.classList.add('active');
                
                // Focus active terminal
                setTimeout(() => {
                    session.term.focus();
                    session.fitAddon.fit();
                }, 50);
            } else {
                session.paneDiv.classList.remove('active');
                session.tabDiv.classList.remove('active');
            }
        }
    }
}

function closeTerminalTab(paneId, notifyBackend = true) {
    const session = activeSessions[paneId];
    if (!session) return;
    
    const bId = session.backendSessionId;
    
    // 1. Terminate backend process if needed
    if (notifyBackend && bId && pyReady) {
        pywebview.api.close_terminal_session(bId);
    }
    
    // 2. Dispose front-end components
    try {
        session.term.dispose();
    } catch (e) { console.error(e); }
    session.paneDiv.remove();
    session.tabDiv.remove();
    
    // 3. Clean registries
    delete activeSessions[paneId];
    if (bId) delete activeSessions[bId];
    
    // 4. Update count
    updateTerminalCount();
    
    // 5. Select next tab if active one was closed
    if (activeSessionId === paneId) {
        activeSessionId = null;
        const remainingKeys = Object.keys(activeSessions).filter(k => k.startsWith('pane-'));
        if (remainingKeys.length > 0) {
            selectTerminalTab(remainingKeys[0]);
        } else {
            // Restore empty message
            const tabsBar = document.getElementById('terminal-tabs-bar');
            tabsBar.innerHTML = `<div class="no-terminals-msg">No active terminals open. Start a distro!</div>`;
        }
    }
    
    refreshDistros();
}

function fitActiveTerminal() {
    if (activeSessionId && activeSessions[activeSessionId]) {
        const session = activeSessions[activeSessionId];
        try {
            session.fitAddon.fit();
            const cols = session.term.cols;
            const rows = session.term.rows;
            const bId = session.backendSessionId;
            if (bId && pyReady) {
                pywebview.api.resize_terminal(bId, cols, rows);
            }
        } catch (e) {
            console.error('Fit error:', e);
        }
    }
}

function updateTerminalCount() {
    const count = Object.keys(activeSessions).filter(k => k.startsWith('pane-')).length;
    document.getElementById('terminal-count').textContent = count;
}

// Window resize handler with debounce
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        // Fit all terminals in open tab spaces
        for (const id in activeSessions) {
            const session = activeSessions[id];
            if (id.startsWith('pane-') && session && session.fitAddon) {
                try {
                    session.fitAddon.fit();
                    const cols = session.term.cols;
                    const rows = session.term.rows;
                    const bId = session.backendSessionId;
                    if (bId && pyReady) {
                        pywebview.api.resize_terminal(bId, cols, rows);
                    }
                } catch (e) {
                    console.error(e);
                }
            }
        }
    }, 150);
});

// Notifications/Toast Toast System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'info';
    if (type === 'success') icon = 'check-circle';
    if (type === 'warning') icon = 'alert-triangle';
    if (type === 'danger') icon = 'x-circle';
    
    toast.innerHTML = `
        <i data-lucide="${icon}"></i>
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    container.appendChild(toast);
    lucide.createIcons();
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'none';
        toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 400);
    }, 4000);
}

// Globals exposed to backend Python execution context
window.onTerminalData = function(sessionId, data) {
    const session = activeSessions[sessionId];
    if (session && session.term) {
        session.term.write(data);
    }
};

window.onTerminalExit = function(sessionId) {
    const session = activeSessions[sessionId];
    if (session) {
        showToast(`WSL terminal session for ${session.distroName} terminated`, 'warning');
        closeTerminalTab(session.paneDiv.id, false); // close but don't notify Python since process has exited
    }
};

window.onInstallData = function(distroName, data) {
    const logBox = document.getElementById('installer-log-terminal');
    if (logBox) {
        // Strip ANSI/VT100 escape sequences (e.g. \x1b[0K, \x1b[?25l, \x1b[26G)
        const stripped = data
            .replace(/\x1b\[[0-9;?]*[a-zA-Z]/g, '')   // CSI sequences
            .replace(/\x1b\][^\x07]*\x07/g, '')         // OSC sequences
            .replace(/\x1b[^[\]]/g, '')                  // other lone escapes
            .replace(/\r\r\n/g, '\n')
            .replace(/\r\n/g, '\n')
            .replace(/\r/g, '')                          // discard lone CR (cursor-reset)
            .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, ''); // other control chars
        if (stripped) {
            logBox.textContent += stripped;
            logBox.scrollTop = logBox.scrollHeight;
        }
    }
};

window.onInstallComplete = function(distroName, success, message) {
    const statusText = document.getElementById('install-status-text');
    document.querySelector('.installer-spinner').style.display = 'none';
    
    // Disable input bar when process finishes
    currentInstallSessionId = null;
    setInstallerInputEnabled(false);
    const inputEl = document.getElementById('installer-input');
    if (inputEl) inputEl.placeholder = 'Proceso finalizado.';
    
    if (success) {
        statusText.innerHTML = `<span class="text-success">✓ Instalación completada. Volviendo al inicio...</span>`;
        showToast(`¡${distroName} instalado correctamente! Abriendo lista de distribuciones...`, 'success');
        refreshDistros();
        // Auto-navigate back to distros after short delay so user sees the success message
        setTimeout(() => {
            switchView('distros');
        }, 2500);
    } else {
        statusText.innerHTML = `<span class="text-danger">✕ Installation Failed</span>`;
        showToast(`Failed to install ${distroName}: ${message}`, 'danger');
    }
};

// Import Custom Distro modal handlers
function openImportModal() {
    document.getElementById('import-name').value = '';
    document.getElementById('import-install-dir').value = '';
    document.getElementById('import-tarball').value = '';
    document.getElementById('import-modal').style.display = 'flex';
    document.getElementById('import-name').focus();
}

function closeImportModal() {
    document.getElementById('import-modal').style.display = 'none';
}

function updateDefaultImportPath() {
    const name = document.getElementById('import-name').value.trim();
    const cleanName = name.replace(/[^a-zA-Z0-9_\-]/g, '');
    if (cleanName) {
        document.getElementById('import-install-dir').value = `C:\\WSL\\${cleanName}`;
    } else {
        document.getElementById('import-install-dir').value = '';
    }
}

function submitImportDistro() {
    if (!pyReady) return;
    
    const name = document.getElementById('import-name').value.trim();
    const installDir = document.getElementById('import-install-dir').value.trim();
    const tarballPath = document.getElementById('import-tarball').value.trim();
    
    if (!name || !installDir || !tarballPath) {
        showToast('All fields are required to import a distribution.', 'warning');
        return;
    }
    
    const cleanName = name.replace(/[^a-zA-Z0-9_\-]/g, '');
    if (cleanName !== name) {
        showToast('Distribution name must be alphanumeric with no spaces.', 'warning');
        return;
    }
    
    closeImportModal();
    
    // Setup Installer View
    const logBox = document.getElementById('installer-log-terminal');
    logBox.textContent = '';
    document.getElementById('install-distro-name').textContent = `Importing ${name}`;
    document.getElementById('install-status-text').textContent = 'Extracting and registering distro...';
    document.querySelector('.installer-spinner').style.display = 'block';
    
    // Reset and enable interactive input bar
    setInstallerInputEnabled(true);
    document.getElementById('installer-input').value = '';
    document.getElementById('installer-input').placeholder = 'Escribe aquí si el proceso pide datos (usuario, contraseña...)';
    
    switchView('installer');

    
    pywebview.api.import_custom_distro(name, installDir, tarballPath).then(res => {
        if (res.started) {
            currentInstallSessionId = res.session_id;
            showToast(`Import of ${name} started successfully`, 'info');
            setTimeout(() => document.getElementById('installer-input').focus(), 300);
        } else {
            showToast(`Could not start import: ${res.message}`, 'danger');
            document.getElementById('install-status-text').textContent = `Failed: ${res.message}`;
            document.querySelector('.installer-spinner').style.display = 'none';
            setInstallerInputEnabled(false);
        }
    }).catch(err => {
        showToast(`Error: ${err}`, 'danger');
        document.getElementById('install-status-text').textContent = `Error: ${err}`;
        document.querySelector('.installer-spinner').style.display = 'none';
        setInstallerInputEnabled(false);
    });
}

function uninstallDistro(distroName) {
    if (!pyReady) return;
    openDangerModal(distroName);
}

function openDangerModal(distroName) {
    pendingUninstallDistro = distroName;
    document.getElementById('danger-modal-distro-name').textContent = distroName;
    const overlay = document.getElementById('danger-confirm-modal');
    overlay.style.display = 'flex';
    lucide.createIcons();
}

function closeDangerModal() {
    pendingUninstallDistro = null;
    document.getElementById('danger-confirm-modal').style.display = 'none';
}

function confirmUninstall() {
    if (!pyReady || !pendingUninstallDistro) return;
    const distroName = pendingUninstallDistro;
    closeDangerModal();
    showToast(`Eliminando ${distroName}...`, 'info');
    pywebview.api.unregister_distro(distroName).then(success => {
        if (success) {
            showToast(`¡${distroName} eliminado correctamente!`, 'success');
            refreshDistros();
        } else {
            showToast(`No se pudo eliminar ${distroName}`, 'danger');
        }
    });
}

// Dialog folder & file pickers
function selectFolder() {
    if (!pyReady) return;
    pywebview.api.select_folder_dialog().then(path => {
        if (path) {
            document.getElementById('import-install-dir').value = path;
        }
    });
}

function selectTarball() {
    if (!pyReady) return;
    pywebview.api.select_tarball_dialog().then(path => {
        if (path) {
            document.getElementById('import-tarball').value = path;
            // Also try to autofill the name if name is empty
            const nameInput = document.getElementById('import-name');
            if (nameInput && !nameInput.value.trim()) {
                const parts = path.split(/[/\\]/);
                const file = parts[parts.length - 1];
                const cleanName = file.split('.')[0].replace(/[^a-zA-Z0-9_\-]/g, '');
                nameInput.value = cleanName;
                updateDefaultImportPath();
            }
        }
    });
}

// Help content toggle
function toggleHelpText(event) {
    if (event) event.preventDefault();
    const content = document.getElementById('import-help-content');
    if (content) {
        content.classList.toggle('expanded');
    }
}

// 1-Click Install Preset
function installPreset(presetName) {
    if (!pyReady) return;
    
    closeImportModal();
    
    const name = "Alpine";
    
    // Clear log and switch view
    const logBox = document.getElementById('installer-log-terminal');
    logBox.textContent = '';
    document.getElementById('install-distro-name').textContent = `Downloading & Importing Alpine Linux`;
    document.getElementById('install-status-text').textContent = 'Connecting to mirrors and downloading rootfs...';
    document.querySelector('.installer-spinner').style.display = 'block';
    
    switchView('installer');
    
    pywebview.api.download_and_import_preset(presetName).then(res => {
        if (res.started) {
            showToast(`Preset Alpine installation started`, 'info');
        } else {
            showToast(`Could not start preset install: ${res.message}`, 'danger');
            document.getElementById('install-status-text').textContent = `Failed: ${res.message}`;
            document.querySelector('.installer-spinner').style.display = 'none';
        }
    }).catch(err => {
        showToast(`Error: ${err}`, 'danger');
        document.getElementById('install-status-text').textContent = `Error: ${err}`;
        document.querySelector('.installer-spinner').style.display = 'none';
    });
}

// ─── Installer Interactive Input Bar ──────────────────────────────────────────

function setInstallerInputEnabled(enabled) {
    const bar = document.getElementById('installer-input-bar');
    const input = document.getElementById('installer-input');
    if (!bar || !input) return;
    if (enabled) {
        bar.classList.remove('disabled');
        input.disabled = false;
    } else {
        bar.classList.add('disabled');
        input.disabled = true;
    }
}

function sendInstallerInput() {
    if (!pyReady || !currentInstallSessionId) return;
    const input = document.getElementById('installer-input');
    if (!input) return;
    const text = input.value;
    // Send text + newline (Enter) to PTY
    pywebview.api.write_terminal_data(currentInstallSessionId, text + '\r');
    // Echo the typed text (with mask if password mode) in the log
    const logBox = document.getElementById('installer-log-terminal');
    if (logBox) {
        const isPw = input.type === 'password';
        logBox.textContent += (isPw ? '*'.repeat(text.length) : text) + '\n';
        logBox.scrollTop = logBox.scrollHeight;
    }
    input.value = '';
    input.focus();
}

function onInstallerInputKey(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendInstallerInput();
    }
    // Allow Ctrl+C to send interrupt signal
    if (event.key === 'c' && event.ctrlKey) {
        event.preventDefault();
        if (pyReady && currentInstallSessionId) {
            pywebview.api.write_terminal_data(currentInstallSessionId, '\x03');
        }
    }
}

function toggleInstallerInputType() {
    const input = document.getElementById('installer-input');
    const btn = document.getElementById('installer-pw-toggle');
    if (!input || !btn) return;
    const isPassword = input.type === 'password';
    // Toggle: password -> text (now visible), text -> password (now hidden)
    input.type = isPassword ? 'text' : 'password';
    // Icon shows current state after toggle:
    // - switched to text (visible)  => show 'eye'     (click again to hide)
    // - switched to password (hidden) => show 'eye-off' (click again to show)
    btn.innerHTML = isPassword
        ? '<i data-lucide="eye" style="width:15px;height:15px;"></i>'
        : '<i data-lucide="eye-off" style="width:15px;height:15px;"></i>';
    lucide.createIcons();
    input.focus();
}
