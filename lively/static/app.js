/**
 * Lively 2D World Canvas & Client Application
 */

// Application State
const state = {
    world: {
        bounds: { min_x: -1000, max_x: 1000, min_y: -1000, max_y: 1000 },
        squirrel: { x: 0, y: 0, heading: 0, battery: 100, last_thought: "", current_activity: "" },
        objects: [],
        users: []
    },
    user: {
        name: localStorage.getItem("lively_username") || "David",
        x: 20,
        y: 20,
        targetX: 20,
        targetY: 20,
        speed: 6
    },
    camera: {
        x: 0,
        y: 0,
        zoom: 1.0,
        isDragging: false,
        lastMouseX: 0,
        lastMouseY: 0
    },
    keysPressed: {},
    ws: null,
    selectedProject: null,
    squirrelTrail: []
};

// Canvas & DOM Elements
const canvas = document.getElementById("world-canvas");
const ctx = canvas.getContext("2d");
const container = document.getElementById("canvas-container");

// UI Elements
const statSquirrelPos = document.getElementById("stat-squirrel-pos");
const statUserPos = document.getElementById("stat-user-pos");
const statBattery = document.getElementById("stat-battery");
const statGmail = document.getElementById("stat-gmail");
const thoughtText = document.getElementById("thought-text");
const activityText = document.getElementById("activity-text");
const btnWake = document.getElementById("btn-wake");
const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
const sidebar = document.getElementById("sidebar");
const modal = document.getElementById("modal");
const modalBody = document.getElementById("modal-body");
const modalClose = document.getElementById("modal-close");

// Resize canvas
function resizeCanvas() {
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

// Coordinate Transformations
function worldToScreen(wx, wy) {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const sx = cx + (wx - state.camera.x) * state.camera.zoom;
    const sy = cy - (wy - state.camera.y) * state.camera.zoom; // Invert Y for Cartesian coordinates
    return { x: sx, y: sy };
}

function screenToWorld(sx, sy) {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const wx = state.camera.x + (sx - cx) / state.camera.zoom;
    const wy = state.camera.y - (sy - cy) / state.camera.zoom;
    return { x: Math.round(wx), y: Math.round(wy) };
}

// Render Loop
function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const zoom = state.camera.zoom;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    // Draw Grid
    const gridSize = 100;
    const topLeft = screenToWorld(0, 0);
    const bottomRight = screenToWorld(canvas.width, canvas.height);

    const startX = Math.floor(topLeft.x / gridSize) * gridSize;
    const endX = Math.ceil(bottomRight.x / gridSize) * gridSize;
    const startY = Math.floor(bottomRight.y / gridSize) * gridSize;
    const endY = Math.ceil(topLeft.y / gridSize) * gridSize;

    ctx.lineWidth = 1;

    // Subtle grid lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
    for (let x = startX; x <= endX; x += gridSize) {
        const p1 = worldToScreen(x, startY);
        const p2 = worldToScreen(x, endY);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
    }
    for (let y = startY; y <= endY; y += gridSize) {
        const p1 = worldToScreen(startX, y);
        const p2 = worldToScreen(endX, y);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
    }

    // Origin Axes
    const origin = worldToScreen(0, 0);
    ctx.strokeStyle = "rgba(245, 158, 11, 0.2)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(origin.x, 0);
    ctx.lineTo(origin.x, canvas.height);
    ctx.moveTo(0, origin.y);
    ctx.lineTo(canvas.width, origin.y);
    ctx.stroke();

    // World Boundary Box
    const b = state.world.bounds;
    const bTopLeft = worldToScreen(b.min_x, b.max_y);
    const bBottomRight = worldToScreen(b.max_x, b.min_y);
    ctx.strokeStyle = "rgba(245, 158, 11, 0.35)";
    ctx.setLineDash([6, 6]);
    ctx.strokeRect(bTopLeft.x, bTopLeft.y, bBottomRight.x - bTopLeft.x, bBottomRight.y - bTopLeft.y);
    ctx.setLineDash([]);

    // Draw Squirrel Trail
    if (state.squirrelTrail.length > 1) {
        ctx.strokeStyle = "rgba(245, 158, 11, 0.25)";
        ctx.lineWidth = 2 * zoom;
        ctx.beginPath();
        for (let i = 0; i < state.squirrelTrail.length; i++) {
            const p = worldToScreen(state.squirrelTrail[i].x, state.squirrelTrail[i].y);
            if (i === 0) ctx.moveTo(p.x, p.y);
            else ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
    }

    // Draw World Objects
    state.world.objects.forEach(obj => {
        const p = worldToScreen(obj.x, obj.y);

        // Icon based on type
        let icon = "📍";
        if (obj.type === "tree") icon = "🌳";
        else if (obj.type === "cache") icon = "🌰";
        else if (obj.type === "sensor") icon = "📡";
        else if (obj.type === "contraption") icon = "⚙️";
        else if (obj.type === "note") icon = "📝";

        ctx.font = `${20 * zoom}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(icon, p.x, p.y);

        // Name Tag
        ctx.font = `${Math.max(10, 11 * zoom)}px sans-serif`;
        ctx.fillStyle = "#cbd5e1";
        ctx.fillText(obj.name, p.x, p.y + 18 * zoom);
    });

    // Draw Squirrel
    const sq = state.world.squirrel;
    const sqScreen = worldToScreen(sq.x, sq.y);

    // Glowing aura
    const gradient = ctx.createRadialGradient(sqScreen.x, sqScreen.y, 4, sqScreen.x, sqScreen.y, 25 * zoom);
    gradient.addColorStop(0, "rgba(245, 158, 11, 0.4)");
    gradient.addColorStop(1, "rgba(245, 158, 11, 0)");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(sqScreen.x, sqScreen.y, 25 * zoom, 0, Math.PI * 2);
    ctx.fill();

    // Squirrel emoji & badge
    ctx.font = `${26 * zoom}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("🐿️", sqScreen.x, sqScreen.y);

    // Squirrel Name Tag
    ctx.font = `bold ${Math.max(10, 12 * zoom)}px sans-serif`;
    ctx.fillStyle = "#f59e0b";
    ctx.fillText("LIVELY ⚡", sqScreen.x, sqScreen.y - 20 * zoom);

    // Draw Other Users
    state.world.users.forEach(u => {
        const up = worldToScreen(u.x, u.y);
        ctx.font = `${20 * zoom}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText("🤖", up.x, up.y);
        ctx.font = `${10 * zoom}px sans-serif`;
        ctx.fillStyle = "#94a3b8";
        ctx.fillText(u.name, up.x, up.y - 16 * zoom);
    });

    // Draw Your Avatar
    const userScreen = worldToScreen(state.user.x, state.user.y);
    ctx.fillStyle = "rgba(6, 182, 212, 0.3)";
    ctx.beginPath();
    ctx.arc(userScreen.x, userScreen.y, 16 * zoom, 0, Math.PI * 2);
    ctx.fill();

    ctx.font = `${24 * zoom}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("🧑‍🚀", userScreen.x, userScreen.y);

    ctx.font = `bold ${Math.max(10, 11 * zoom)}px sans-serif`;
    ctx.fillStyle = "#38bdf8";
    ctx.fillText(`${state.user.name} (You)`, userScreen.x, userScreen.y - 18 * zoom);

    // Smooth movement towards target
    updateUserMovement();

    requestAnimationFrame(render);
}

// User Movement (Smooth interpolation & Keyboard / Mouse)
function updateUserMovement() {
    let moved = false;
    let step = state.user.speed / state.camera.zoom;

    if (state.keysPressed["w"] || state.keysPressed["ArrowUp"]) {
        state.user.targetY += step;
        moved = true;
    }
    if (state.keysPressed["s"] || state.keysPressed["ArrowDown"]) {
        state.user.targetY -= step;
        moved = true;
    }
    if (state.keysPressed["a"] || state.keysPressed["ArrowLeft"]) {
        state.user.targetX -= step;
        moved = true;
    }
    if (state.keysPressed["d"] || state.keysPressed["ArrowRight"]) {
        state.user.targetX += step;
        moved = true;
    }

    // Clamp to world
    const b = state.world.bounds;
    state.user.targetX = Math.max(b.min_x, Math.min(b.max_x, state.user.targetX));
    state.user.targetY = Math.max(b.min_y, Math.min(b.max_y, state.user.targetY));

    // Smooth lerp
    const dx = state.user.targetX - state.user.x;
    const dy = state.user.targetY - state.user.y;
    const dist = Math.hypot(dx, dy);

    if (dist > 0.5) {
        state.user.x += dx * 0.15;
        state.user.y += dy * 0.15;
        statUserPos.innerText = `(${Math.round(state.user.x)}, ${Math.round(state.user.y)})`;

        // Send to WebSocket
        sendUserPosition();
    }
}

// Send position to WebSocket (throttled)
let lastSend = 0;
function sendUserPosition() {
    const now = Date.now();
    if (now - lastSend > 80 && state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({
            type: "move",
            x: Math.round(state.user.x),
            y: Math.round(state.user.y),
            name: state.user.name
        }));
        lastSend = now;
    }
}

// Canvas Input Listeners
canvas.addEventListener("mousedown", (e) => {
    if (e.button === 0) { // Left click
        const clickWorld = screenToWorld(e.clientX, e.clientY);

        // Check if clicked an object
        const clickedObj = state.world.objects.find(obj => {
            const dist = Math.hypot(obj.x - clickWorld.x, obj.y - clickWorld.y);
            return dist < (30 / state.camera.zoom);
        });

        if (clickedObj) {
            showObjectModal(clickedObj);
            return;
        }

        // Set target destination
        state.user.targetX = clickWorld.x;
        state.user.targetY = clickWorld.y;

        // Auto-fill coordinates in Add Object form
        document.getElementById("obj-x").value = clickWorld.x;
        document.getElementById("obj-y").value = clickWorld.y;
    } else if (e.button === 1 || e.button === 2) { // Middle or right click to pan
        state.camera.isDragging = true;
        state.camera.lastMouseX = e.clientX;
        state.camera.lastMouseY = e.clientY;
    }
});

canvas.addEventListener("mousemove", (e) => {
    if (state.camera.isDragging) {
        const dx = e.clientX - state.camera.lastMouseX;
        const dy = e.clientY - state.camera.lastMouseY;
        state.camera.x -= dx / state.camera.zoom;
        state.camera.y += dy / state.camera.zoom;
        state.camera.lastMouseX = e.clientX;
        state.camera.lastMouseY = e.clientY;
    }
});

window.addEventListener("mouseup", () => {
    state.camera.isDragging = false;
});

canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    state.camera.zoom = Math.max(0.2, Math.min(3.0, state.camera.zoom * zoomFactor));
});

// Keyboard
window.addEventListener("keydown", (e) => {
    if (["input", "textarea"].includes(document.activeElement.tagName.toLowerCase())) return;
    state.keysPressed[e.key.toLowerCase()] = true;
});

window.addEventListener("keyup", (e) => {
    state.keysPressed[e.key.toLowerCase()] = false;
});

// WebSocket Connection
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log("[WS] Connected to Lively world server");
        sendUserPosition();
    };

    state.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error("[WS] Parse error:", e);
        }
    };

    state.ws.onclose = () => {
        console.log("[WS] Disconnected, retrying in 3s...");
        setTimeout(connectWebSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    if (data.type === "welcome") {
        updateWorldState(data.state);
        // Center camera initially near squirrel
        state.camera.x = state.world.squirrel.x;
        state.camera.y = state.world.squirrel.y;
    } else if (data.type === "user_moved") {
        const idx = state.world.users.findIndex(u => u.id === data.user.id);
        if (idx >= 0) state.world.users[idx] = data.user;
        else state.world.users.push(data.user);
    } else if (data.type === "user_left") {
        state.world.users = state.world.users.filter(u => u.id !== data.user_id);
    } else if (data.type === "object_added") {
        state.world.objects.push(data.object);
        renderObjectList();
    } else if (data.type === "object_removed") {
        state.world.objects = state.world.objects.filter(o => o.id !== data.id);
        renderObjectList();
    } else if (data.type === "squirrel_wake") {
        updateWorldState(data.world);
        loadProjects();
        loadMemories();
        showNotification("🐿️ Lively finished a wake cycle!");
    }
}

function updateWorldState(wsState) {
    state.world = wsState;
    const sq = wsState.squirrel;

    statSquirrelPos.innerText = `(${sq.x}, ${sq.y})`;
    statBattery.innerText = `${sq.battery}%`;
    thoughtText.innerText = sq.last_thought || "Observing the digital landscape...";
    activityText.innerText = sq.current_activity || "Exploring";

    // Track trail
    state.squirrelTrail.push({ x: sq.x, y: sq.y });
    if (state.squirrelTrail.length > 50) state.squirrelTrail.shift();

    renderObjectList();
}

// REST API Calls
async function fetchWorld() {
    try {
        const res = await fetch("/api/world");
        const data = await res.json();
        updateWorldState(data);
    } catch (e) {
        console.error("Fetch world error:", e);
    }
}

async function fetchGmailStatus() {
    try {
        const res = await fetch("/auth/gmail/status");
        const data = await res.json();
        if (data.authenticated) {
            statGmail.innerText = "Linked ✅";
            statGmail.className = "val badge ready";
            document.getElementById("gmail-status-text").innerText = "Gmail is authorized! Lively can send you emails.";
            document.getElementById("btn-auth-gmail").innerText = "Reconnect Gmail";
        } else {
            statGmail.innerText = "Unlinked ⚠️";
            statGmail.className = "val badge unlinked";
            document.getElementById("gmail-status-text").innerText = "Not linked. Click below to authorize Gmail sending.";
            document.getElementById("btn-auth-gmail").innerText = "🔗 Connect Gmail Account";
        }
    } catch (e) {
        statGmail.innerText = "Error";
    }
}

async function loadProjects() {
    try {
        const res = await fetch("/api/projects");
        const data = await res.json();
        const list = document.getElementById("project-list");
        list.innerHTML = "";

        if (data.length === 0) {
            list.innerHTML = `<p class="hint">No projects coded yet.</p>`;
            return;
        }

        data.forEach(p => {
            const item = document.createElement("div");
            item.className = "list-item";
            item.innerHTML = `
                <div class="item-info">
                    <div class="item-title">💻 ${p.filename}</div>
                    <div class="item-subtitle">${p.description || "Created by Lively"}</div>
                </div>
                <button class="btn small primary">View Code</button>
            `;
            item.onclick = () => showProjectCode(p);
            list.appendChild(item);
        });
    } catch (e) {
        console.error("Load projects error:", e);
    }
}

function showProjectCode(project) {
    state.selectedProject = project;
    const viewer = document.getElementById("code-viewer");
    viewer.classList.remove("hidden");
    document.getElementById("code-filename").innerText = project.filename;
    document.getElementById("code-content").innerText = project.code;
    document.getElementById("code-output").classList.add("hidden");
}

document.getElementById("btn-run-code").addEventListener("click", async () => {
    if (!state.selectedProject) return;
    const btn = document.getElementById("btn-run-code");
    btn.innerText = "Running...";
    btn.disabled = true;

    try {
        const res = await fetch(`/api/projects/${encodeURIComponent(state.selectedProject.filename)}/run`, {
            method: "POST"
        });
        const out = await res.json();
        const outputBox = document.getElementById("code-output");
        outputBox.classList.remove("hidden");
        document.getElementById("code-stdout").innerText =
            out.stdout || out.stderr || out.error || "Script completed with no output.";
    } catch (e) {
        alert("Error running code: " + e);
    } finally {
        btn.innerText = "▶ Run Script";
        btn.disabled = false;
    }
});

async function loadMemories() {
    try {
        const res = await fetch("/api/memories");
        const data = await res.json();

        document.getElementById("long-term-summary").innerText = data.summary || "No summary yet.";

        const list = document.getElementById("journal-list");
        list.innerHTML = "";

        if (data.journals.length === 0) {
            list.innerHTML = `<p class="hint">No diary entries recorded yet.</p>`;
            return;
        }

        data.journals.forEach(j => {
            const item = document.createElement("div");
            item.className = "list-item";
            item.innerHTML = `
                <div class="item-info">
                    <div class="item-title">📖 ${j.filename}</div>
                    <div class="item-subtitle">${j.preview}</div>
                </div>
            `;
            item.onclick = () => {
                showModal(`<h2>${j.filename}</h2><div class="markdown-body">${escapeHtml(j.content)}</div>`);
            };
            list.appendChild(item);
        });
    } catch (e) {
        console.error("Load memories error:", e);
    }
}

function renderObjectList() {
    const list = document.getElementById("object-list");
    const count = document.getElementById("obj-count");
    count.innerText = state.world.objects.length;
    list.innerHTML = "";

    if (state.world.objects.length === 0) {
        list.innerHTML = `<p class="hint">The world is empty. Place some landmarks!</p>`;
        return;
    }

    state.world.objects.forEach(obj => {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = `
            <div class="item-info">
                <div class="item-title">${obj.name} <small>(${obj.x}, ${obj.y})</small></div>
                <div class="item-subtitle">${obj.description || obj.type}</div>
            </div>
            <button class="btn small" style="color:#ef4444;" title="Delete">✕</button>
        `;
        item.querySelector("button").onclick = async (e) => {
            e.stopPropagation();
            if (confirm(`Remove ${obj.name}?`)) {
                await fetch(`/api/objects/${obj.id}`, { method: "DELETE" });
            }
        };
        item.onclick = () => {
            state.camera.x = obj.x;
            state.camera.y = obj.y;
            showObjectModal(obj);
        };
        list.appendChild(item);
    });
}

// Add Object Form
document.getElementById("form-add-object").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("obj-name").value.trim();
    const x = parseFloat(document.getElementById("obj-x").value);
    const y = parseFloat(document.getElementById("obj-y").value);
    const type = document.getElementById("obj-type").value;
    const desc = document.getElementById("obj-desc").value.trim();

    try {
        const res = await fetch("/api/objects", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, x, y, type, description: desc })
        });
        if (res.ok) {
            document.getElementById("obj-name").value = "";
            document.getElementById("obj-desc").value = "";
        }
    } catch (err) {
        alert("Error adding object: " + err);
    }
});

// Trigger Wake Cycle Button
btnWake.addEventListener("click", async () => {
    btnWake.disabled = true;
    btnWake.innerText = "🐿️ Thinking...";
    try {
        const res = await fetch("/api/squirrel/wake", { method: "POST" });
        const result = await res.json();
        showNotification("🐿️ Lively has awakened and taken action!");
    } catch (e) {
        alert("Error triggering wake: " + e);
    } finally {
        btnWake.disabled = false;
        btnWake.innerText = "⚡ Wake Squirrel";
    }
});

// Connect Gmail Button
document.getElementById("btn-auth-gmail").addEventListener("click", async () => {
    try {
        const res = await fetch("/auth/gmail");
        const data = await res.json();
        if (data.auth_url) {
            window.open(data.auth_url, "_blank");
        } else {
            alert("No auth URL returned: " + JSON.stringify(data));
        }
    } catch (e) {
        alert("Error initiating Gmail auth: " + e);
    }
});

// User name edit
document.getElementById("user-display-name").addEventListener("change", (e) => {
    state.user.name = e.target.value.trim() || "David";
    localStorage.setItem("lively_username", state.user.name);
    sendUserPosition();
});

// Sidebar Tabs
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(btn.dataset.tab).classList.add("active");
    });
});

btnToggleSidebar.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
});

// Modal helpers
function showObjectModal(obj) {
    showModal(`
        <h2>${escapeHtml(obj.name)}</h2>
        <p><b>Type:</b> ${obj.type} | <b>Coords:</b> (${obj.x}, ${obj.y})</p>
        <p><b>Created By:</b> ${obj.created_by}</p>
        <hr style="border:0; border-top:1px solid #334; margin: 12px 0;">
        <p>${escapeHtml(obj.description || "No description provided.")}</p>
    `);
}

function showModal(html) {
    modalBody.innerHTML = html;
    modal.classList.remove("hidden");
}

modalClose.addEventListener("click", () => modal.classList.add("hidden"));
modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
});

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}

function showNotification(msg) {
    const n = document.createElement("div");
    n.innerText = msg;
    n.style.position = "fixed";
    n.style.bottom = "24px";
    n.style.right = "24px";
    n.style.background = "#f59e0b";
    n.style.color = "#000";
    n.style.fontWeight = "bold";
    n.style.padding = "10px 18px";
    n.style.borderRadius = "8px";
    n.style.zIndex = "1000";
    n.style.boxShadow = "0 4px 16px rgba(0,0,0,0.5)";
    document.body.appendChild(n);
    setTimeout(() => n.remove(), 4000);
}

// Initial Boot
fetchWorld();
fetchGmailStatus();
loadProjects();
loadMemories();
connectWebSocket();
requestAnimationFrame(render);
