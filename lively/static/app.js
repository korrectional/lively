/**
 * Lively 2D World Canvas & Client Application (Upgraded Visuals & Controls)
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
    avatarType: localStorage.getItem("lively_avatar_type") || "scout",
    myUserId: null,
    camera: {
        x: 0,
        y: 0,
        targetX: 0,
        targetY: 0,
        zoom: 1.0,
        isDragging: false,
        lastMouseX: 0,
        lastMouseY: 0
    },
    keysPressed: {},
    ws: null,
    selectedProject: null,
    squirrelTrail: [],
    particles: []
};

// Canvas & DOM Elements
const canvas = document.getElementById("world-canvas");
const ctx = canvas.getContext("2d");
const container = document.getElementById("canvas-container");
const minimapCanvas = document.getElementById("minimap-canvas");
const minimapCtx = minimapCanvas ? minimapCanvas.getContext("2d") : null;

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

// Spawn ambient floating digital particles
for (let i = 0; i < 40; i++) {
    state.particles.push({
        x: Math.random() * 2000 - 1000,
        y: Math.random() * 2000 - 1000,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        size: Math.random() * 2 + 1,
        alpha: Math.random() * 0.6 + 0.2
    });
}

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
    const sy = cy - (wy - state.camera.y) * state.camera.zoom; // Invert Y
    return { x: sx, y: sy };
}

function screenToWorld(sx, sy) {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const wx = state.camera.x + (sx - cx) / state.camera.zoom;
    const wy = state.camera.y - (sy - cy) / state.camera.zoom;
    return { x: Math.round(wx), y: Math.round(wy) };
}

// Helper: Pill Badge with Text
function drawPillBadge(context, x, y, text, color = "#cbd5e1", bgColor = "rgba(15, 20, 32, 0.85)", borderColor = "rgba(255, 255, 255, 0.12)") {
    context.save();
    context.font = "bold 11px sans-serif";
    const textWidth = context.measureText(text).width;
    const paddingX = 8;
    const paddingY = 4;
    const width = textWidth + paddingX * 2;
    const height = 18;
    const radius = 9;

    const rx = x - width / 2;
    const ry = y - height / 2;

    // Background pill
    context.fillStyle = bgColor;
    context.beginPath();
    context.roundRect(rx, ry, width, height, radius);
    context.fill();

    // Border
    context.strokeStyle = borderColor;
    context.lineWidth = 1;
    context.stroke();

    // Text
    context.fillStyle = color;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, x, y);
    context.restore();
}

// ==========================================
// Clean Emoji Canvas Sprites
// ==========================================

// 1. Robot Squirrel (Pure, clean 🐿️ emoji — cute, natural bobbing, facing direction, crisp emoji rendering, no glow)
function drawSquirrelEmoji(c, x, y, size, heading, time) {
    c.save();
    c.translate(x, y);

    // Subtle grounding shadow (stationary on ground)
    c.fillStyle = "rgba(0, 0, 0, 0.28)";
    c.beginPath();
    c.ellipse(0, size * 0.38, size * 0.38, size * 0.12, 0, 0, Math.PI * 2);
    c.fill();

    // Natural smooth bobbing animation
    const bob = Math.sin(time * 0.004) * 2.5;
    c.translate(0, bob);

    // Direction flip:
    // The standard 🐿️ emoji natively faces LEFT across platforms (Apple, Segoe UI, Noto).
    // If heading is pointing east/right (-90° to +90° or dx >= 0), flip horizontally to face right.
    const norm = ((heading % 360) + 360) % 360;
    const movingLeft = (norm > 90 && norm < 270);
    if (!movingLeft) {
        c.scale(-1, 1);
    }

    // Ensure absolutely no glow/shadow leakage
    c.shadowBlur = 0;
    c.shadowColor = "transparent";

    // Crisp emoji rendering
    c.font = `${Math.round(size)}px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif`;
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText("🐿️", 0, 0);

    c.restore();
}

// 2. World Object Emoji
function drawObjectEmoji(c, x, y, size, obj, time) {
    c.save();
    c.translate(x, y);

    // Ground shadow for spatial depth
    c.fillStyle = "rgba(0, 0, 0, 0.25)";
    c.beginPath();
    c.ellipse(0, size * 0.36, size * 0.4, size * 0.13, 0, 0, Math.PI * 2);
    c.fill();

    // Subtle floating bob
    const bob = Math.sin(time * 0.003 + (obj.x || 0)) * 1.5;
    c.translate(0, bob);

    let emoji = obj.icon || "";
    if (!emoji) {
        if (obj.type === "tree") emoji = "🌲";
        else if (obj.type === "sensor") emoji = "📡";
        else if (obj.type === "cache") emoji = "🌰";
        else if (obj.type === "contraption") emoji = "⚙️";
        else if (obj.type === "note") emoji = "📝";
        else emoji = "📍";
    }

    c.shadowBlur = 0;
    c.shadowColor = "transparent";
    c.font = `${Math.round(size)}px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif`;
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText(emoji, 0, 0);

    c.restore();
}

// 3. Player / Explorer Avatar (Quantum Scout Spaceship & Explorer Models)
function drawPlayer(c, x, y, scale, name, avatarType = "scout", time = 0) {
    c.save();
    c.translate(x, y);
    c.scale(scale, scale);

    const hover = Math.sin((time + (name ? name.charCodeAt(0) * 80 : 0)) * 0.005) * 3;
    c.translate(0, hover);

    if (avatarType === "mech") {
        // --- 1. Cyber Mech Pilot ---
        c.fillStyle = "rgba(0, 0, 0, 0.4)";
        c.beginPath();
        c.ellipse(0, 18, 14, 5, 0, 0, Math.PI * 2);
        c.fill();

        c.strokeStyle = "#475569";
        c.lineWidth = 3.5;
        c.beginPath();
        c.moveTo(-6, 4); c.lineTo(-8, 14); c.lineTo(-11, 16);
        c.moveTo(6, 4); c.lineTo(8, 14); c.lineTo(11, 16);
        c.stroke();

        c.fillStyle = "#1e293b";
        c.strokeStyle = "#0ea5e9";
        c.lineWidth = 1.5;
        c.beginPath();
        c.roundRect(-12, -8, 24, 18, 4);
        c.fill();
        c.stroke();

        c.fillStyle = "#334155";
        c.fillRect(-15, -12, 5, 8);
        c.fillRect(10, -12, 5, 8);

        c.fillStyle = "#06b6d4";
        c.fillRect(-7, -4, 14, 4);

    } else if (avatarType === "nomad") {
        // --- 2. Star Nomad Astronaut ---
        c.fillStyle = "rgba(0, 0, 0, 0.35)";
        c.beginPath();
        c.ellipse(0, 16, 12, 4, 0, 0, Math.PI * 2);
        c.fill();

        c.fillStyle = "#475569";
        c.fillRect(-10, -6, 20, 12);

        c.fillStyle = "#f59e0b";
        c.beginPath();
        c.moveTo(-6, 6); c.lineTo(-4, 12 + Math.random() * 4); c.lineTo(-2, 6);
        c.moveTo(2, 6); c.lineTo(4, 12 + Math.random() * 4); c.lineTo(6, 6);
        c.fill();

        c.fillStyle = "#f1f5f9";
        c.beginPath();
        c.ellipse(0, 0, 8, 11, 0, 0, Math.PI * 2);
        c.fill();

        c.fillStyle = "#0284c7";
        c.beginPath();
        c.arc(0, -9, 7.5, 0, Math.PI * 2);
        c.fill();
        c.fillStyle = "#f59e0b";
        c.beginPath();
        c.ellipse(1, -9, 4.5, 3.5, 0, 0, Math.PI * 2);
        c.fill();

    } else if (avatarType === "cyberfox") {
        // --- 3. Synth Fox ---
        c.fillStyle = "rgba(0, 0, 0, 0.35)";
        c.beginPath();
        c.ellipse(0, 14, 14, 5, 0, 0, Math.PI * 2);
        c.fill();

        c.fillStyle = "#f97316";
        c.beginPath();
        c.ellipse(0, 2, 11, 8, 0, 0, Math.PI * 2);
        c.fill();

        c.fillStyle = "#f8fafc";
        c.beginPath();
        c.ellipse(4, 2, 5, 5, 0, 0, Math.PI * 2);
        c.fill();

        c.fillStyle = "#ea580c";
        c.beginPath();
        c.arc(7, -6, 6, 0, Math.PI * 2);
        c.fill();
        c.beginPath();
        c.moveTo(4, -10); c.lineTo(6, -17); c.lineTo(9, -11);
        c.moveTo(8, -10); c.lineTo(12, -16); c.lineTo(13, -9);
        c.fill();

        c.fillStyle = "#22d3ee";
        c.fillRect(8, -7, 4, 2);

        c.strokeStyle = "#fdba74";
        c.lineWidth = 2.5;
        c.beginPath();
        c.moveTo(-9, 0); c.quadraticCurveTo(-18, -4, -14, -14);
        c.stroke();

    } else if (avatarType === "orb") {
        // --- 4. Holo Orb ---
        c.fillStyle = "rgba(0, 0, 0, 0.3)";
        c.beginPath();
        c.ellipse(0, 20, 10, 4, 0, 0, Math.PI * 2);
        c.fill();

        c.save();
        c.rotate(time * 0.002);
        c.strokeStyle = "#38bdf8";
        c.lineWidth = 1.5;
        c.beginPath();
        c.ellipse(0, 0, 16, 6, 0.4, 0, Math.PI * 2);
        c.stroke();
        c.restore();

        c.save();
        c.rotate(-time * 0.003);
        c.strokeStyle = "#a855f7";
        c.lineWidth = 1.5;
        c.beginPath();
        c.ellipse(0, 0, 12, 5, -0.6, 0, Math.PI * 2);
        c.stroke();
        c.restore();

        c.fillStyle = "#06b6d4";
        c.beginPath();
        c.arc(0, 0, 6, 0, Math.PI * 2);
        c.fill();

    } else {
        // --- 5. Quantum Scout Spaceship (Default — beloved by user!) ---
        c.fillStyle = "rgba(0, 0, 0, 0.4)";
        c.beginPath();
        c.ellipse(0, 18 - hover * 0.5, 16, 5, 0, 0, Math.PI * 2);
        c.fill();

        // Twin Plasma Thruster Trails (flickering cyan)
        const flame = 6 + Math.sin(time * 0.03) * 3;
        c.fillStyle = "#06b6d4";
        c.beginPath();
        c.moveTo(-9, 6); c.lineTo(-6, 6 + flame); c.lineTo(-3, 6);
        c.moveTo(3, 6);  c.lineTo(6, 6 + flame);  c.lineTo(9, 6);
        c.fill();

        // Delta hovercraft chassis
        c.fillStyle = "#0f172a";
        c.strokeStyle = "#0284c7";
        c.lineWidth = 1.8;
        c.beginPath();
        c.moveTo(0, -14);
        c.lineTo(16, 4);
        c.lineTo(9, 8);
        c.lineTo(0, 4);
        c.lineTo(-9, 8);
        c.lineTo(-16, 4);
        c.closePath();
        c.fill();
        c.stroke();

        // Wing stabilizer lights
        c.fillStyle = "#38bdf8";
        c.beginPath();
        c.arc(-13, 2, 2, 0, Math.PI * 2);
        c.arc(13, 2, 2, 0, Math.PI * 2);
        c.fill();

        // Cockpit sensor orb
        c.fillStyle = "#1e293b";
        c.strokeStyle = "#38bdf8";
        c.lineWidth = 1.5;
        c.beginPath();
        c.arc(0, -3, 6.5, 0, Math.PI * 2);
        c.fill();
        c.stroke();

        c.fillStyle = "#38bdf8";
        c.beginPath();
        c.arc(0, -3, 3, 0, Math.PI * 2);
        c.fill();
    }

    c.restore();
}

// ==========================================
// Object Clumping & Radial Layout
// ==========================================
function getObjectVisualOffsets(objects, zoom = 1.0) {
    if (!objects || objects.length === 0) return new Map();
    // If multiple objects share coordinates (within 35m) or are too close, fan them out radially
    const clusters = {};
    const clusterDist = Math.max(35, 40 / Math.max(0.1, zoom));

    objects.forEach(obj => {
        let placed = false;
        for (const k in clusters) {
            const [cx, cy] = k.split(",").map(Number);
            if (Math.hypot(obj.x - cx, obj.y - cy) < clusterDist) {
                clusters[k].push(obj);
                placed = true;
                break;
            }
        }
        if (!placed) {
            const key = `${obj.x},${obj.y}`;
            clusters[key] = [obj];
        }
    });

    const offsets = new Map();
    for (const k in clusters) {
        const group = clusters[k];
        if (group.length === 1) {
            offsets.set(group[0].id, { x: group[0].x, y: group[0].y, isClustered: false });
        } else {
            const count = group.length;
            // Radius in world units, ensuring minimum 45 screen pixels spread
            const radius = Math.max(35, 48 / Math.max(0.2, zoom));
            group.forEach((obj, idx) => {
                const angle = (idx * (Math.PI * 2) / count) - (Math.PI / 2);
                offsets.set(obj.id, {
                    x: obj.x + Math.cos(angle) * radius,
                    y: obj.y + Math.sin(angle) * radius,
                    isClustered: true
                });
            });
        }
    }
    return offsets;
}

// ==========================================
// Main Render Loop
// ==========================================
function render(timestamp) {
    const time = timestamp || performance.now();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const zoom = state.camera.zoom;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    // Smooth camera pan toward target if needed
    if (!state.camera.isDragging && state.camera.targetX !== undefined) {
        state.camera.x += (state.camera.targetX - state.camera.x) * 0.08;
        state.camera.y += (state.camera.targetY - state.camera.y) * 0.08;
    }

    // Draw Grid
    const gridSize = 100;
    const topLeft = screenToWorld(0, 0);
    const bottomRight = screenToWorld(canvas.width, canvas.height);

    const startX = Math.floor(topLeft.x / gridSize) * gridSize;
    const endX = Math.ceil(bottomRight.x / gridSize) * gridSize;
    const startY = Math.floor(bottomRight.y / gridSize) * gridSize;
    const endY = Math.ceil(topLeft.y / gridSize) * gridSize;

    // Dual Grid Lines
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
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
    ctx.strokeStyle = "rgba(245, 158, 11, 0.25)";
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
    ctx.strokeStyle = "rgba(245, 158, 11, 0.4)";
    ctx.setLineDash([8, 8]);
    ctx.strokeRect(bTopLeft.x, bTopLeft.y, bBottomRight.x - bTopLeft.x, bBottomRight.y - bTopLeft.y);
    ctx.setLineDash([]);

    // Ambient Floating Particles
    state.particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < b.min_x) p.x = b.max_x;
        if (p.x > b.max_x) p.x = b.min_x;
        if (p.y < b.min_y) p.y = b.max_y;
        if (p.y > b.max_y) p.y = b.min_y;

        const sp = worldToScreen(p.x, p.y);
        ctx.fillStyle = `rgba(6, 182, 212, ${p.alpha})`;
        ctx.beginPath();
        ctx.arc(sp.x, sp.y, p.size * zoom, 0, Math.PI * 2);
        ctx.fill();
    });

    // Draw Squirrel Trail
    if (state.squirrelTrail.length > 1) {
        ctx.strokeStyle = "rgba(245, 158, 11, 0.35)";
        ctx.lineWidth = 2.5 * zoom;
        ctx.beginPath();
        for (let i = 0; i < state.squirrelTrail.length; i++) {
            const p = worldToScreen(state.squirrelTrail[i].x, state.squirrelTrail[i].y);
            if (i === 0) ctx.moveTo(p.x, p.y);
            else ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
    }

    // Calculate smart offsets for clustered objects
    const objOffsets = getObjectVisualOffsets(state.world.objects, zoom);

    // Draw World Objects
    state.world.objects.forEach(obj => {
        const offset = objOffsets.get(obj.id) || { x: obj.x, y: obj.y };
        const p = worldToScreen(offset.x, offset.y);
        const spriteScale = Math.max(0.6, Math.min(1.8, zoom));

        // Draw connecting leader line if fanned out
        if (offset.isClustered) {
            const originP = worldToScreen(obj.x, obj.y);
            ctx.strokeStyle = "rgba(148, 163, 184, 0.35)";
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 4]);
            ctx.beginPath();
            ctx.moveTo(originP.x, originP.y);
            ctx.lineTo(p.x, p.y);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Render clean emoji object
        drawObjectEmoji(ctx, p.x, p.y, 28 * spriteScale, obj, time);

        // Draw pill label badge (never raw overlapping text!)
        drawPillBadge(ctx, p.x, p.y + 24 * spriteScale, obj.name, "#cbd5e1");
    });

    // Draw Robot Squirrel (Clean 🐿️ emoji — no glow, no text floating on him!)
    const sq = state.world.squirrel;
    const sqScreen = worldToScreen(sq.x, sq.y);
    const sqScale = Math.max(0.7, Math.min(2.0, zoom));
    drawSquirrelEmoji(ctx, sqScreen.x, sqScreen.y, 38 * sqScale, sq.heading, time);

    // Draw Other Users (filter out own ID and name so NEVER duplicate!)
    state.world.users.forEach(u => {
        if (state.myUserId && u.id === state.myUserId) return;
        if (u.name === state.user.name) return;
        const up = worldToScreen(u.x, u.y);
        drawPlayer(ctx, up.x, up.y, Math.max(0.6, Math.min(1.5, zoom)), u.name, u.avatar_type || "scout", time);
        drawPillBadge(ctx, up.x, up.y - 24 * zoom, u.name, "#94a3b8");
    });

    // Draw Your Avatar (Quantum Scout Spaceship intact!)
    const userScreen = worldToScreen(state.user.x, state.user.y);
    const playerScale = Math.max(0.7, Math.min(1.8, zoom));
    drawPlayer(ctx, userScreen.x, userScreen.y, playerScale, state.user.name, state.avatarType, time);
    drawPillBadge(ctx, userScreen.x, userScreen.y - 26 * playerScale, `${state.user.name} (You)`, "#38bdf8", "rgba(15, 23, 42, 0.9)", "rgba(6, 182, 212, 0.4)");

    // Smooth movement towards target
    updateUserMovement();

    // Render Mini-Map
    renderMiniMap();

    requestAnimationFrame(render);
}

// Render Mini-Map
function renderMiniMap() {
    if (!minimapCtx) return;
    const mc = minimapCtx;
    const w = minimapCanvas.width;
    const h = minimapCanvas.height;

    mc.clearRect(0, 0, w, h);
    mc.fillStyle = "#090b10";
    mc.fillRect(0, 0, w, h);

    const b = state.world.bounds;
    const toMapX = (wx) => ((wx - b.min_x) / (b.max_x - b.min_x)) * w;
    const toMapY = (wy) => h - ((wy - b.min_y) / (b.max_y - b.min_y)) * h;

    // Objects
    state.world.objects.forEach(obj => {
        mc.fillStyle = obj.type === "tree" ? "#10b981" : (obj.type === "sensor" ? "#06b6d4" : "#f59e0b");
        mc.beginPath();
        mc.arc(toMapX(obj.x), toMapY(obj.y), 2.5, 0, Math.PI * 2);
        mc.fill();
    });

    // Squirrel (Amber Blip)
    const sq = state.world.squirrel;
    mc.fillStyle = "#f59e0b";
    mc.beginPath();
    mc.arc(toMapX(sq.x), toMapY(sq.y), 4.5, 0, Math.PI * 2);
    mc.fill();

    // User (Cyan Blip)
    mc.fillStyle = "#38bdf8";
    mc.beginPath();
    mc.arc(toMapX(state.user.x), toMapY(state.user.y), 3.5, 0, Math.PI * 2);
    mc.fill();

    // Camera viewport box
    const tl = screenToWorld(0, 0);
    const br = screenToWorld(canvas.width, canvas.height);
    mc.strokeStyle = "rgba(255, 255, 255, 0.25)";
    mc.lineWidth = 1;
    mc.strokeRect(toMapX(tl.x), toMapY(tl.y), toMapX(br.x) - toMapX(tl.x), toMapY(br.y) - toMapY(tl.y));
}

// User Movement (Smooth interpolation & Keyboard / Mouse)
function updateUserMovement() {
    let step = state.user.speed / state.camera.zoom;

    if (state.keysPressed["w"] || state.keysPressed["ArrowUp"]) state.user.targetY += step;
    if (state.keysPressed["s"] || state.keysPressed["ArrowDown"]) state.user.targetY -= step;
    if (state.keysPressed["a"] || state.keysPressed["ArrowLeft"]) state.user.targetX -= step;
    if (state.keysPressed["d"] || state.keysPressed["ArrowRight"]) state.user.targetX += step;

    // Clamp
    const b = state.world.bounds;
    state.user.targetX = Math.max(b.min_x, Math.min(b.max_x, state.user.targetX));
    state.user.targetY = Math.max(b.min_y, Math.min(b.max_y, state.user.targetY));

    // Smooth lerp
    const dx = state.user.targetX - state.user.x;
    const dy = state.user.targetY - state.user.y;
    const dist = Math.hypot(dx, dy);

    if (dist > 0.4) {
        state.user.x += dx * 0.16;
        state.user.y += dy * 0.16;
        statUserPos.innerText = `(${Math.round(state.user.x)}, ${Math.round(state.user.y)})`;
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
            name: state.user.name,
            avatar_type: state.avatarType || "scout"
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
            return dist < (35 / state.camera.zoom);
        });

        if (clickedObj) {
            showObjectModal(clickedObj);
            return;
        }

        // Set target destination for user avatar
        state.user.targetX = clickWorld.x;
        state.user.targetY = clickWorld.y;

        // Auto-fill coordinates in Add Object form
        document.getElementById("obj-x").value = clickWorld.x;
        document.getElementById("obj-y").value = clickWorld.y;
    } else if (e.button === 1 || e.button === 2) { // Middle or right click to pan
        state.camera.isDragging = true;
        state.camera.targetX = undefined; // Cancel auto-pan
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

// Quick Focus Buttons
document.getElementById("btn-focus-squirrel").addEventListener("click", () => {
    state.camera.targetX = state.world.squirrel.x;
    state.camera.targetY = state.world.squirrel.y;
});

document.getElementById("btn-focus-user").addEventListener("click", () => {
    state.camera.targetX = state.user.x;
    state.camera.targetY = state.user.y;
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
        setTimeout(connectWebSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    if (data.type === "welcome") {
        state.myUserId = data.user_id;
        updateWorldState(data.state);
        state.camera.x = state.world.squirrel.x;
        state.camera.y = state.world.squirrel.y;
    } else if (data.type === "user_moved") {
        if (state.myUserId && data.user.id === state.myUserId) return;
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
    } else if (data.type === "project_added") {
        loadProjects();
    } else if (data.type === "schedule_updated") {
        loadSchedule();
    } else if (data.type === "world_reset") {
        updateWorldState(data.world);
        loadProjects();
        loadMemories();
        loadBlogPosts();
        loadThoughtSessions();
        loadIncomingEmails();
        loadSystemInfo();
        showNotification("🌱 World & memories have been reset!");
    } else if (data.type === "squirrel_wake") {
        updateWorldState(data.world);
        loadProjects();
        loadMemories();
        loadBlogPosts();
        loadThoughtSessions();
        loadIncomingEmails();
        loadSystemInfo();
        showNotification("🐿️ Squirrel finished a wake cycle!");
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

// ==========================================
// Gmail Integration (Settings & Testing)
// ==========================================
async function fetchGmailStatus() {
    try {
        const res = await fetch("/api/settings/gmail");
        const data = await res.json();
        const actionsRow = document.getElementById("gmail-actions-row");
        const statusText = document.getElementById("gmail-status-text");

        if (data.authenticated) {
            statGmail.innerText = "Ready ✅";
            statGmail.className = "val badge ready";
            if (statusText) statusText.innerHTML = `Gmail is connected (${data.method}) to <b>${escapeHtml(data.user_email || "your account")}</b>. Squirrel can email you!`;
            if (actionsRow) actionsRow.classList.remove("hidden");
        } else {
            statGmail.innerText = "Setup Needed ⚠️";
            statGmail.className = "val badge unlinked";
            if (statusText) statusText.innerText = "Not connected yet. Follow the step-by-step guide below to connect with a Google App Password.";
            if (actionsRow) actionsRow.classList.add("hidden");
        }
        if (data.user_email && document.getElementById("gmail-user-email")) {
            document.getElementById("gmail-user-email").value = data.user_email;
        }
        if (data.client_id && document.getElementById("gmail-client-id")) {
            document.getElementById("gmail-client-id").value = data.client_id;
        }
    } catch (e) {
        statGmail.innerText = "Error";
    }
}

// Connect with App Password (Direct SMTP Verification)
const formGmailConnect = document.getElementById("form-gmail-connect");
if (formGmailConnect) {
    formGmailConnect.addEventListener("submit", async (e) => {
        e.preventDefault();
        const user_email = document.getElementById("gmail-user-email").value.trim();
        const app_password = document.getElementById("gmail-app-pw").value.trim();
        const msgBox = document.getElementById("gmail-connect-msg");
        const btn = document.getElementById("btn-connect-gmail");

        if (!app_password) {
            alert("Please paste your 16-character App Password.");
            return;
        }

        btn.disabled = true;
        btn.innerText = "Verifying Credentials...";
        msgBox.innerHTML = "<span style='color:#06b6d4;'>Testing connection to smtp.gmail.com:465...</span>";

        try {
            const res = await fetch("/api/settings/gmail/connect", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_email, app_password })
            });
            const out = await res.json();
            if (out.success) {
                msgBox.innerHTML = `<b style="color:#10b981;">✅ Verified! Connected to Gmail as ${escapeHtml(user_email)}.</b>`;
                document.getElementById("gmail-app-pw").value = "";
                fetchGmailStatus();
                showNotification("✉️ Gmail successfully connected!");
            } else {
                msgBox.innerHTML = `<b style="color:#ef4444;">❌ Verification failed:</b> ${escapeHtml(out.error || out.message)}`;
            }
        } catch (err) {
            msgBox.innerHTML = `<b style="color:#ef4444;">❌ Error connecting:</b> ${err}`;
        } finally {
            btn.disabled = false;
            btn.innerText = "🔌 Connect & Verify Gmail Account";
        }
    });
}

// Disconnect Gmail
const btnDisconnectGmail = document.getElementById("btn-disconnect-gmail");
if (btnDisconnectGmail) {
    btnDisconnectGmail.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to disconnect Gmail?")) return;
        try {
            await fetch("/api/settings/gmail/disconnect", { method: "POST" });
            fetchGmailStatus();
            showNotification("Gmail disconnected.");
        } catch (err) {
            alert("Error disconnecting Gmail: " + err);
        }
    });
}

// Method 2: Save OAuth Credentials
const formGmailOAuth = document.getElementById("form-gmail-oauth");
if (formGmailOAuth) {
    formGmailOAuth.addEventListener("submit", async (e) => {
        e.preventDefault();
        const user_email = document.getElementById("gmail-user-email").value.trim();
        const client_id = document.getElementById("gmail-client-id").value.trim();
        const client_secret = document.getElementById("gmail-client-secret").value.trim();

        try {
            await fetch("/api/settings/gmail", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    method: "oauth",
                    user_email,
                    client_id,
                    client_secret
                })
            });
            alert("OAuth credentials saved. Now click 'Open Google Sign-In Link' below!");
            fetchGmailStatus();
        } catch (err) {
            alert("Error saving OAuth credentials: " + err);
        }
    });
}

// Method 2: Open Auth URL
const btnAuthGmail = document.getElementById("btn-auth-gmail");
if (btnAuthGmail) {
    btnAuthGmail.addEventListener("click", async () => {
        try {
            const res = await fetch("/auth/gmail");
            const data = await res.json();
            if (data.success && data.auth_url) {
                window.open(data.auth_url, "_blank");
            } else {
                alert(data.error || "Please enter your Client ID & Secret in Method 2 first.");
            }
        } catch (e) {
            alert("Error initiating Gmail auth: " + e);
        }
    });
}

// Send Test Email
const btnTestEmail = document.getElementById("btn-test-email");
if (btnTestEmail) {
    btnTestEmail.addEventListener("click", async () => {
        const resultBox = document.getElementById("email-test-result");
        btnTestEmail.disabled = true;
        btnTestEmail.innerText = "Sending test email...";
        resultBox.innerText = "";

        try {
            const res = await fetch("/api/test/email", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    subject: "🐿️ Hello from Squirrel the Robot Squirrel!",
                    body: "Greetings David!\n\nThis is a transmission from Squirrel living on your Raspberry Pi! My email sensors are online and functioning perfectly.\n\nCatch you later on the map! 🌰⚡"
                })
            });
            const out = await res.json();
            if (out.success) {
                resultBox.innerHTML = "<b style='color:#10b981;'>✅ Email sent successfully! Check your inbox.</b>";
                fetchGmailStatus();
            } else {
                resultBox.innerHTML = `<b style='color:#ef4444;'>❌ Send failed:</b> ${escapeHtml(out.error)}`;
            }
        } catch (e) {
            resultBox.innerHTML = `<b style='color:#ef4444;'>❌ Error:</b> ${e}`;
        } finally {
            btnTestEmail.disabled = false;
            btnTestEmail.innerText = "📨 Send Test Email";
        }
    });
}

// ==========================================
// GitHub Projects & Code Workshop
// ==========================================
async function loadProjects() {
    try {
        const res = await fetch("/api/projects");
        const repos = await res.json();
        const list = document.getElementById("project-list");
        const countBadge = document.getElementById("repo-count");
        if (countBadge) countBadge.innerText = repos.length;
        if (!list) return;
        list.innerHTML = "";

        if (repos.length === 0) {
            list.innerHTML = `<p class="hint">No repositories created yet.</p>`;
            return;
        }

        repos.forEach(repo => {
            const item = document.createElement("div");
            item.className = "list-item";
            item.innerHTML = `
                <div class="item-info">
                    <div class="item-title">📁 <b>${escapeHtml(repo.name)}</b> <span class="badge ready" style="font-size:0.75rem;">Git (${repo.commit_count || 1})</span></div>
                    <div class="item-subtitle">${escapeHtml(repo.description || "GitHub repository")}</div>
                    <div class="hint" style="font-size:0.78rem; margin-top:3px; color:#94a3b8;">
                        ${repo.file_count || 1} file(s) • Latest: <i>"${escapeHtml(repo.last_commit_msg || 'Initial commit')}"</i>
                    </div>
                </div>
                <button class="btn small primary">Open Repo</button>
            `;
            item.onclick = () => showProjectRepo(repo);
            list.appendChild(item);
        });

        // If a repo is already selected, re-select it
        if (state.selectedRepo) {
            const matched = repos.find(r => r.name === state.selectedRepo.name);
            if (matched) showProjectRepo(matched);
        }
    } catch (e) {
        console.error("Load projects error:", e);
    }
}

async function showProjectRepo(repoSummary) {
    try {
        const res = await fetch(`/api/projects/${encodeURIComponent(repoSummary.name)}`);
        const repo = await res.json();
        state.selectedRepo = repo;

        const viewer = document.getElementById("repo-viewer");
        if (!viewer) return;
        viewer.classList.remove("hidden");

        document.getElementById("repo-title").innerText = `📁 ${repo.name}`;
        document.getElementById("repo-commits-text").innerText = `${repo.commits ? repo.commits.length : 1} commit(s)`;
        const lastMsg = (repo.commits && repo.commits[0]) ? repo.commits[0].message : "Initial commit";
        document.getElementById("repo-last-commit-msg").innerText = `Latest: "${lastMsg}"`;

        // Populate file dropdown
        const select = document.getElementById("repo-file-select");
        select.innerHTML = "";
        const files = repo.files || ["main.py"];
        files.forEach(f => {
            const opt = document.createElement("option");
            opt.value = f;
            opt.innerText = f;
            if (f === "main.py") opt.selected = true;
            select.appendChild(opt);
        });

        // Load primary code
        const defaultFile = select.value || files[0] || "main.py";
        loadRepoFile(repo.name, defaultFile);

        const outputBox = document.getElementById("code-output");
        if (outputBox) outputBox.classList.add("hidden");
    } catch (e) {
        console.error("Error showing repo:", e);
    }
}

async function loadRepoFile(repoName, filePath) {
    try {
        const res = await fetch(`/api/projects/${encodeURIComponent(repoName)}/file?path=${encodeURIComponent(filePath)}`);
        const data = await res.json();
        const codeBox = document.getElementById("code-content");
        if (codeBox) codeBox.innerText = data.content || "# Empty file";
    } catch (e) {
        console.error("Error loading file:", e);
    }
}

// File select change handler
const repoFileSelect = document.getElementById("repo-file-select");
if (repoFileSelect) {
    repoFileSelect.addEventListener("change", (e) => {
        if (state.selectedRepo) {
            loadRepoFile(state.selectedRepo.name, e.target.value);
        }
    });
}

// Run program with AGYC Safety Checker
const btnRunCode = document.getElementById("btn-run-code");
if (btnRunCode) {
    btnRunCode.addEventListener("click", async () => {
        if (!state.selectedRepo) return;
        const entrypoint = document.getElementById("repo-file-select") ? document.getElementById("repo-file-select").value : "main.py";
        btnRunCode.innerText = "🛡️ Inspecting with Safety Guard...";
        btnRunCode.disabled = true;

        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(state.selectedRepo.name)}/run`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ entrypoint, timeout: 15 })
            });
            const out = await res.json();
            const outputBox = document.getElementById("code-output");
            const stdoutBox = document.getElementById("code-stdout");
            outputBox.classList.remove("hidden");

            if (out.blocked) {
                stdoutBox.innerHTML = `<span style="color:#ef4444; font-weight:bold;">🛡️ EXECUTION BLOCKED BY AGYC SAFETY CHECKER:</span>\n${escapeHtml(out.error)}\nThreat Level: Critical | Sandbox Boundary Protected.`;
                showNotification("⚠️ Program blocked by Safety Checker!");
            } else if (out.success) {
                let safetyNote = out.safety_verdict ? `\n[AGYC Safety: Approved - ${out.safety_verdict.reason}]` : "";
                stdoutBox.innerText = (out.stdout || "Program completed with returncode 0.") + safetyNote;
                showNotification(`▶ Program '${entrypoint}' finished successfully!`);
            } else {
                stdoutBox.innerText = out.stderr || out.error || "Program failed with non-zero exit code.";
            }
        } catch (e) {
            alert("Error running code: " + e);
        } finally {
            btnRunCode.innerText = "▶ Run Program (AGYC Guarded)";
            btnRunCode.disabled = false;
        }
    });
}

// Memories
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

// Squirrel Blog Posts
async function loadBlogPosts() {
    const list = document.getElementById("blog-list");
    if (!list) return;
    try {
        const res = await fetch("/api/blog");
        const posts = await res.json();
        list.innerHTML = "";

        if (posts.length === 0) {
            list.innerHTML = `<p class="hint">No blog posts published yet.</p>`;
            return;
        }

        posts.forEach(p => {
            const item = document.createElement("div");
            item.className = "list-item";
            item.innerHTML = `
                <div class="item-info">
                    <div class="item-title">✍️ ${escapeHtml(p.title || p.filename)}</div>
                    <div class="item-subtitle">${escapeHtml(p.preview || "")}</div>
                </div>
            `;
            item.onclick = () => {
                showModal(`<h2>✍️ ${escapeHtml(p.title || p.filename)}</h2><div class="markdown-body" style="white-space:pre-wrap; line-height:1.6;">${escapeHtml(p.content)}</div>`);
            };
            list.appendChild(item);
        });
    } catch (e) {
        console.error("Load blog posts error:", e);
    }
}

// ==========================================
// Mind Logs & Session Transcripts
// ==========================================
async function loadThoughtSessions() {
    const list = document.getElementById("thought-sessions-list");
    const countBadge = document.getElementById("mind-logs-count");
    if (!list) return;
    try {
        const res = await fetch("/api/thoughts");
        const sessions = await res.json();
        if (countBadge) countBadge.innerText = `${sessions.length} Sessions`;
        list.innerHTML = "";

        if (sessions.length === 0) {
            list.innerHTML = `<p class="hint">No mind logs archived yet. Click "Wake & Stream Thought Process" above to log a session!</p>`;
            return;
        }

        sessions.forEach(s => {
            const item = document.createElement("div");
            item.className = "list-item";
            const dateStr = s.timestamp ? new Date(s.timestamp).toLocaleTimeString() : "";
            item.innerHTML = `
                <div class="item-info">
                    <div class="item-title">🧠 <b>Wake Cycle #${s.cycle_number}</b> <small style="color:#f59e0b;">(${dateStr})</small></div>
                    <div class="item-subtitle">"${escapeHtml(s.preview || 'Deliberation recorded.')}"</div>
                    <div class="hint" style="font-size:0.75rem; color:#06b6d4;">${s.action_count || 0} action(s) materialized</div>
                </div>
                <button class="btn small">View Mind Log</button>
            `;
            item.onclick = () => showThoughtSessionModal(s);
            list.appendChild(item);
        });
    } catch (e) {
        console.error("Load thought sessions error:", e);
    }
}

function showThoughtSessionModal(session) {
    let actionsHtml = "";
    if (session.actions && session.actions.length > 0) {
        actionsHtml = "<h4>Materialized Actions:</h4><ul>";
        session.actions.forEach(a => {
            actionsHtml += `<li><b>${escapeHtml(a.action_type)}:</b> <code>${escapeHtml(JSON.stringify(a.parameters))}</code></li>`;
        });
        actionsHtml += "</ul>";
    }

    showModal(`
        <h2>🧠 Squirrel Mind Log — Cycle #${session.cycle_number}</h2>
        <p class="hint" style="color:#94a3b8;">Recorded: ${session.timestamp || 'N/A'}</p>
        <hr style="border:0; border-top:1px solid #334155; margin:12px 0;">
        <h4>Stream of Consciousness (Raw Deliberation):</h4>
        <pre style="background:#090b10; border:1px solid #334155; padding:12px; border-radius:6px; color:#e2e8f0; font-family:monospace; max-height:260px; overflow-y:auto; white-space:pre-wrap;">${escapeHtml(session.raw_monologue || 'No monologue text.')}</pre>
        ${actionsHtml}
    `);
}

// ==========================================
// Two-Way Gmail Inbox (Replies from David)
// ==========================================
async function loadIncomingEmails() {
    const list = document.getElementById("inbox-list");
    if (!list) return;
    try {
        const res = await fetch("/api/email/inbox");
        const emails = await res.json();
        list.innerHTML = "";

        if (emails.length === 0) {
            list.innerHTML = `<p class="hint">No incoming replies recorded yet. Reply to any of Squirrel's emails to talk with him!</p>`;
            return;
        }

        emails.forEach(em => {
            const item = document.createElement("div");
            item.className = "list-item";
            item.innerHTML = `
                <div class="item-info">
                    <div class="item-title">📩 <b>${escapeHtml(em.subject || 'No Subject')}</b></div>
                    <div class="item-subtitle">${escapeHtml(em.body ? em.body.slice(0, 140) + '...' : '')}</div>
                    <div class="hint" style="font-size:0.75rem; color:#94a3b8;">From: ${escapeHtml(em.sender || 'David')} • ${escapeHtml(em.date || '')}</div>
                </div>
            `;
            item.onclick = () => {
                showModal(`
                    <h2>📩 ${escapeHtml(em.subject || 'Incoming Message')}</h2>
                    <p><b>From:</b> ${escapeHtml(em.sender || 'David')} | <b>Date:</b> ${escapeHtml(em.date || '')}</p>
                    <hr style="border:0; border-top:1px solid #334155; margin:12px 0;">
                    <div class="markdown-body" style="white-space:pre-wrap; line-height:1.6;">${escapeHtml(em.body || '')}</div>
                `);
            };
            list.appendChild(item);
        });
    } catch (e) {
        console.error("Load inbox error:", e);
    }
}

const btnCheckInbox = document.getElementById("btn-check-inbox");
if (btnCheckInbox) {
    btnCheckInbox.addEventListener("click", async () => {
        btnCheckInbox.innerText = "Checking IMAP...";
        btnCheckInbox.disabled = true;
        try {
            const res = await fetch("/api/email/check", { method: "POST" });
            const data = await res.json();
            loadIncomingEmails();
            showNotification(`📬 Checked inbox: ${data.count || 0} messages synced!`);
        } catch (e) {
            alert("Error checking email inbox: " + e);
        } finally {
            btnCheckInbox.innerText = "🔄 Check Inbox Now";
            btnCheckInbox.disabled = false;
        }
    });
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
                <div class="item-title">${obj.name} <small style="color:#06b6d4;">(${obj.x}, ${obj.y})</small></div>
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
            state.camera.targetX = obj.x;
            state.camera.targetY = obj.y;
            showObjectModal(obj);
        };
        list.appendChild(item);
    });
}

// Object Icon Picker & Custom Emoji
const iconBtns = document.querySelectorAll(".icon-btn");
const objIconInput = document.getElementById("obj-icon");
const objCustomIconInput = document.getElementById("obj-custom-icon");

if (iconBtns.length > 0 && objIconInput) {
    iconBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            iconBtns.forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            objIconInput.value = btn.dataset.icon;
            if (objCustomIconInput) objCustomIconInput.value = "";
        });
    });
}

if (objCustomIconInput && objIconInput) {
    objCustomIconInput.addEventListener("input", (e) => {
        const val = e.target.value.trim();
        if (val) {
            iconBtns.forEach(b => b.classList.remove("selected"));
            objIconInput.value = val;
        }
    });
}

// Add Object Form
document.getElementById("form-add-object").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("obj-name").value.trim();
    const x = parseFloat(document.getElementById("obj-x").value);
    const y = parseFloat(document.getElementById("obj-y").value);
    const type = document.getElementById("obj-type").value;
    const icon = objIconInput ? objIconInput.value.trim() : "";
    const desc = document.getElementById("obj-desc").value.trim();

    try {
        const res = await fetch("/api/objects", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, x, y, type, icon, description: desc })
        });
        if (res.ok) {
            document.getElementById("obj-name").value = "";
            document.getElementById("obj-desc").value = "";
            showNotification(`📍 Placed "${name}" into the world!`);
        }
    } catch (err) {
        alert("Error adding object: " + err);
    }
});

// ==========================================
// Cognitive Streaming (Watch It Think)
// ==========================================
function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    if (btn) btn.classList.add("active");
    const pane = document.getElementById(tabId);
    if (pane) pane.classList.add("active");
    sidebar.classList.remove("collapsed");
}

function appendConsoleLine(text, type = "system") {
    const box = document.getElementById("thought-console");
    if (!box) return;
    const line = document.createElement("div");
    line.className = `console-line ${type}`;
    line.innerText = text;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

function startThinkingStream() {
    switchTab("tab-brain");
    const badge = document.getElementById("think-status-badge");
    const btnStream = document.getElementById("btn-stream-think");
    const btnTopWake = document.getElementById("btn-wake");

    if (badge) {
        badge.innerText = "Thinking...";
        badge.className = "badge unlinked";
    }
    if (btnStream) btnStream.disabled = true;
    if (btnTopWake) btnTopWake.disabled = true;

    const box = document.getElementById("thought-console");
    if (box) box.innerHTML = "";
    appendConsoleLine(`⚡ Neural core activated at ${new Date().toLocaleTimeString()}`, "system");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const thinkWs = new WebSocket(`${protocol}//${window.location.host}/ws/think`);

    thinkWs.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const stage = data.stage;

            if (stage === "sensory_scan") {
                appendConsoleLine(`[SENSORY] ${data.message}`, "scan");
            } else if (stage === "memory_recall") {
                appendConsoleLine(`[MEMORY] ${data.message}`, "memory");
            } else if (stage === "prompt_ready") {
                appendConsoleLine(`[SYNTHESIS] Context compiled. Input size: ${data.prompt.length} chars`, "prompt");
            } else if (stage === "llm_query") {
                appendConsoleLine(`[NEURAL ENGINE] ${data.message}`, "system");
            } else if (stage === "engine_notice") {
                appendConsoleLine(`[ENGINE NOTICE] ${data.message}`, "prompt");
            } else if (stage === "raw_cognition") {
                appendConsoleLine(`\n--- SQUIRREL MONOLOGUE ---`, "system");
                const lines = data.raw_text.split("\n");
                lines.forEach(l => {
                    if (l.startsWith("THINK:")) appendConsoleLine(l, "thought");
                    else if (l.startsWith("MOVE_TO:") || l.startsWith("BUILD_OBJECT:") || l.startsWith("WRITE_CODE:")) appendConsoleLine(l, "action");
                    else if (l.trim()) appendConsoleLine(l, "system");
                });
                appendConsoleLine(`--- END OF MONOLOGUE ---\n`, "system");
            } else if (stage === "actions_parsed") {
                appendConsoleLine(`[DECISIONS] Materializing ${data.actions.length} action(s):`, "action");
                data.actions.forEach(a => {
                    appendConsoleLine(`  ⚡ ${a.action_type}: ${JSON.stringify(a.parameters)}`, "action");
                });
            } else if (stage === "complete") {
                appendConsoleLine(`\n✅ ${data.message}`, "action");
                showNotification("🐿️ Squirrel finished thinking and acted!");
                if (badge) {
                    badge.innerText = "Completed";
                    badge.className = "badge ready";
                }
                fetchWorld();
                loadProjects();
                loadMemories();
                loadBlogPosts();
                loadThoughtSessions();
                loadIncomingEmails();
            }
        } catch (e) {
            console.error("Think stream error:", e);
        }
    };

    thinkWs.onclose = () => {
        if (btnStream) btnStream.disabled = false;
        if (btnTopWake) btnTopWake.disabled = false;
        if (badge && badge.innerText === "Thinking...") {
            badge.innerText = "Done";
            badge.className = "badge ready";
        }
    };

    thinkWs.onerror = () => {
        appendConsoleLine("❌ WebSocket stream error. Fallback to HTTP...", "error");
        if (btnStream) btnStream.disabled = false;
        if (btnTopWake) btnTopWake.disabled = false;
    };
}

// Trigger Wake Cycle Button (Now connects to thinking stream!)
btnWake.addEventListener("click", () => {
    startThinkingStream();
});

const btnStreamThink = document.getElementById("btn-stream-think");
if (btnStreamThink) {
    btnStreamThink.addEventListener("click", () => {
        startThinkingStream();
    });
}

// User name edit
document.getElementById("user-display-name").addEventListener("change", (e) => {
    state.user.name = e.target.value.trim() || "David";
    localStorage.setItem("lively_username", state.user.name);
    sendUserPosition();
});

// Avatar Appearance Selector
const avatarOptions = document.querySelectorAll(".avatar-option");
if (avatarOptions.length > 0) {
    avatarOptions.forEach(opt => {
        if (opt.dataset.avatar === state.avatarType) {
            opt.classList.add("selected");
        } else {
            opt.classList.remove("selected");
        }
        opt.addEventListener("click", () => {
            avatarOptions.forEach(o => o.classList.remove("selected"));
            opt.classList.add("selected");
            state.avatarType = opt.dataset.avatar;
            localStorage.setItem("lively_avatar_type", state.avatarType);
            sendUserPosition();
            const label = opt.querySelector("b") ? opt.querySelector("b").innerText : state.avatarType;
            showNotification(`🛸 Avatar updated to ${label}!`);
        });
    });
}

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

// ==========================================
// Settings & Run Schedule Cadence
// ==========================================
async function loadSchedule() {
    try {
        const res = await fetch("/api/settings/schedule");
        const data = await res.json();

        const badge = document.getElementById("schedule-badge");
        const nextRun = document.getElementById("schedule-next-run");
        const banner = document.getElementById("schedule-status-banner");
        const select = document.getElementById("schedule-frequency-select");
        const customGroup = document.getElementById("custom-calendar-group");
        const customInput = document.getElementById("schedule-custom-cal");

        if (select) {
            select.value = data.frequency || "paused";
        }

        if (customGroup) {
            if (data.frequency === "custom") {
                customGroup.classList.remove("hidden");
                if (customInput) customInput.value = data.custom_on_calendar || "";
            } else {
                customGroup.classList.add("hidden");
            }
        }

        if (data.active) {
            if (badge) {
                badge.innerText = "Active";
                badge.className = "badge ready";
            }
            if (banner) {
                banner.className = "status-banner active";
            }
            if (nextRun) {
                nextRun.innerText = `Next run: ${data.next_run || "Scheduled"}`;
            }
        } else {
            if (badge) {
                badge.innerText = "Paused";
                badge.className = "badge unlinked";
            }
            if (banner) {
                banner.className = "status-banner paused";
            }
            if (nextRun) {
                nextRun.innerText = "Manual wake only (Timer stopped)";
            }
        }
    } catch (e) {
        console.error("Load schedule error:", e);
    }
}

const scheduleSelect = document.getElementById("schedule-frequency-select");
if (scheduleSelect) {
    scheduleSelect.addEventListener("change", (e) => {
        const customGroup = document.getElementById("custom-calendar-group");
        if (e.target.value === "custom") {
            customGroup.classList.remove("hidden");
        } else {
            customGroup.classList.add("hidden");
        }
    });
}

const formSchedule = document.getElementById("form-schedule");
if (formSchedule) {
    formSchedule.addEventListener("submit", async (e) => {
        e.preventDefault();
        const freq = document.getElementById("schedule-frequency-select").value;
        const customCal = document.getElementById("schedule-custom-cal") ? document.getElementById("schedule-custom-cal").value : "";
        const msgBox = document.getElementById("schedule-msg");
        const btn = document.getElementById("btn-save-schedule");

        btn.disabled = true;
        btn.innerText = "Applying Schedule...";
        msgBox.innerText = "";

        try {
            const res = await fetch("/api/settings/schedule", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ frequency: freq, custom_on_calendar: customCal })
            });
            const out = await res.json();
            msgBox.innerHTML = `<b style="color:#10b981;">✅ Cadence updated: ${out.message || "Saved"}</b>`;
            loadSchedule();
            loadSystemInfo();
            showNotification(`⏰ Lively schedule updated to ${freq}!`);
        } catch (err) {
            msgBox.innerHTML = `<b style="color:#ef4444;">❌ Error: ${err}</b>`;
        } finally {
            btn.disabled = false;
            btn.innerText = "Apply Schedule Cadence";
        }
    });
}

// System Telemetry Info
async function loadSystemInfo() {
    try {
        const res = await fetch("/api/system/info");
        const info = await res.json();

        const hostEl = document.getElementById("info-hostname");
        if (hostEl) hostEl.innerText = info.hostname;

        const tailEl = document.getElementById("info-tailscale");
        if (tailEl) tailEl.innerText = info.tailscale_url;

        const battEl = document.getElementById("info-battery");
        if (battEl) battEl.innerText = `${info.squirrel_battery}%`;

        const cycEl = document.getElementById("info-cycles");
        if (cycEl) cycEl.innerText = `${info.total_cycles} cycles (${info.total_distance.toFixed(1)}m traveled)`;

        const emailEl = document.getElementById("info-email");
        if (emailEl) emailEl.innerText = info.user_email;
    } catch (e) {
        console.error("Load system info error:", e);
    }
}

// Workspace Project Creation Form
const formNewProject = document.getElementById("form-new-project");
if (formNewProject) {
    formNewProject.addEventListener("submit", async (e) => {
        e.preventDefault();
        const repo_name = document.getElementById("proj-new-filename").value.trim();
        const desc = document.getElementById("proj-new-desc").value.trim();
        const code = document.getElementById("proj-new-code").value;

        try {
            const res = await fetch("/api/projects", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_name, description: desc, code, filename: "main.py" })
            });
            if (res.ok) {
                document.getElementById("proj-new-filename").value = "";
                document.getElementById("proj-new-desc").value = "";
                document.getElementById("proj-new-code").value = "";
                loadProjects();
                showNotification(`📁 Repository '${repo_name}' created & committed!`);
            }
        } catch (err) {
            alert("Error creating project repository: " + err);
        }
    });
}

// Settings tab manual wake
const btnSettingsWake = document.getElementById("btn-settings-wake");
if (btnSettingsWake) {
    btnSettingsWake.addEventListener("click", () => {
        startThinkingStream();
    });
}

// World Factory Reset Button
const btnFactoryReset = document.getElementById("btn-factory-reset");
if (btnFactoryReset) {
    btnFactoryReset.addEventListener("click", async () => {
        const confirmMsg = "Are you sure you want to perform a Factory Reset?\n\nThis will:\n- Wipe all custom objects\n- Spawn TreeberryPine at coordinates (45, 45)\n- Return Squirrel to origin (0, 0)\n- Wipe all memory journals & caches\n- Restore starter projects";
        if (!confirm(confirmMsg)) return;

        const msgBox = document.getElementById("reset-msg");
        btnFactoryReset.disabled = true;
        btnFactoryReset.innerText = "Resetting...";

        try {
            const res = await fetch("/api/world/reset", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                msgBox.innerHTML = `<b style="color:#10b981;">✅ Factory reset complete. TreeberryPine restored.</b>`;
                fetchWorld();
                loadProjects();
                loadMemories();
                loadBlogPosts();
                loadThoughtSessions();
                loadIncomingEmails();
                loadSystemInfo();
                showNotification("🌱 Factory reset complete!");
            }
        } catch (err) {
            msgBox.innerHTML = `<b style="color:#ef4444;">❌ Reset failed: ${err}</b>`;
        } finally {
            btnFactoryReset.disabled = false;
            btnFactoryReset.innerText = "⚠️ Factory Reset World & Memories";
        }
    });
}

// Initial Boot
fetchWorld();
fetchGmailStatus();
loadProjects();
loadMemories();
loadBlogPosts();
loadThoughtSessions();
loadIncomingEmails();
loadSchedule();
loadSystemInfo();
connectWebSocket();
requestAnimationFrame(render);
