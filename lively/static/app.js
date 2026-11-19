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
// Procedural Canvas Sprites
// ==========================================

// 1. Robot Squirrel
function drawRobotSquirrel(c, x, y, scale, heading, time) {
    c.save();
    c.translate(x, y);
    c.scale(scale, scale);

    const bob = Math.sin(time * 0.004) * 2;
    c.translate(0, bob);

    // Direction flip (if moving left vs right)
    const facingLeft = (heading > 90 && heading < 270);
    if (facingLeft) c.scale(-1, 1);

    // Radiating energy pulse aura
    const pulse = (Math.sin(time * 0.003) + 1) * 0.5;
    const auraGrad = c.createRadialGradient(0, 0, 5, 0, 0, 38 + pulse * 8);
    auraGrad.addColorStop(0, "rgba(245, 158, 11, 0.35)");
    auraGrad.addColorStop(0.7, "rgba(245, 158, 11, 0.08)");
    auraGrad.addColorStop(1, "rgba(245, 158, 11, 0)");
    c.fillStyle = auraGrad;
    c.beginPath();
    c.arc(0, 0, 42, 0, Math.PI * 2);
    c.fill();

    // Tail: Segmented mechanical tail with glowing cyan joints
    c.save();
    c.translate(-14, 2);
    c.rotate(-0.4 + Math.sin(time * 0.005) * 0.1);

    // Outer tail curve (carbon/titanium segments)
    c.fillStyle = "#475569";
    c.beginPath();
    c.arc(-8, -14, 18, 0, Math.PI * 1.6);
    c.lineWidth = 9;
    c.strokeStyle = "#334155";
    c.stroke();

    // Inner glowing power line
    c.strokeStyle = "#06b6d4";
    c.lineWidth = 2.5;
    c.stroke();

    // Blinking antenna bulb at tip of tail
    const blink = Math.sin(time * 0.008) > 0;
    c.fillStyle = blink ? "#ef4444" : "#f59e0b";
    c.beginPath();
    c.arc(-8, -32, 3.5, 0, Math.PI * 2);
    c.fill();
    c.restore();

    // Squirrel Body: Brushed titanium pear
    const bodyGrad = c.createLinearGradient(-10, -10, 10, 15);
    bodyGrad.addColorStop(0, "#cbd5e1");
    bodyGrad.addColorStop(0.5, "#94a3b8");
    bodyGrad.addColorStop(1, "#64748b");
    c.fillStyle = bodyGrad;
    c.beginPath();
    c.ellipse(0, 2, 12, 16, 0, 0, Math.PI * 2);
    c.fill();
    c.strokeStyle = "#475569";
    c.lineWidth = 1;
    c.stroke();

    // Copper chest plate
    c.fillStyle = "#f59e0b";
    c.beginPath();
    c.ellipse(3, 4, 6, 9, 0.1, 0, Math.PI * 2);
    c.fill();

    // Head
    c.fillStyle = "#e2e8f0";
    c.beginPath();
    c.ellipse(6, -12, 10, 9, 0.2, 0, Math.PI * 2);
    c.fill();

    // Ears
    c.fillStyle = "#94a3b8";
    c.beginPath();
    c.moveTo(2, -18);
    c.lineTo(4, -26);
    c.lineTo(8, -19);
    c.fill();

    // Eye: Glowing cyan visor sensor with blink
    const isBlinking = (Math.sin(time * 0.001) > 0.96);
    c.fillStyle = isBlinking ? "#0891b2" : "#22d3ee";
    c.shadowColor = "#06b6d4";
    c.shadowBlur = isBlinking ? 0 : 8;
    c.beginPath();
    if (isBlinking) {
        c.rect(7, -13, 6, 1.5);
    } else {
        c.ellipse(10, -13, 3.5, 3.5, 0, 0, Math.PI * 2);
    }
    c.fill();
    c.shadowBlur = 0;

    // Nose/snout
    c.fillStyle = "#0f172a";
    c.beginPath();
    c.arc(15, -10, 2, 0, Math.PI * 2);
    c.fill();

    // Paws holding a glowing Cyber Acorn
    c.fillStyle = "#94a3b8";
    c.beginPath();
    c.arc(7, 2, 3, 0, Math.PI * 2);
    c.fill();

    // Golden Cyber Acorn
    c.fillStyle = "#f59e0b";
    c.beginPath();
    c.arc(12, 3, 3.5, 0, Math.PI * 2);
    c.fill();
    c.fillStyle = "#78350f";
    c.fillRect(10, -1, 4, 2);

    c.restore();
}

// 2. Cyber Tree
function drawCyberTree(c, x, y, scale) {
    c.save();
    c.translate(x, y);
    c.scale(scale, scale);

    // Drop shadow
    c.fillStyle = "rgba(0, 0, 0, 0.4)";
    c.beginPath();
    c.ellipse(0, 16, 18, 7, 0, 0, Math.PI * 2);
    c.fill();

    // Trunk
    c.fillStyle = "#334155";
    c.fillRect(-4, 0, 8, 16);

    // Glowing trunk circuit line
    c.strokeStyle = "#10b981";
    c.lineWidth = 1.5;
    c.beginPath();
    c.moveTo(0, 16);
    c.lineTo(0, 2);
    c.lineTo(-3, -2);
    c.stroke();

    // Canopy layers (Pine/Oak hybrid)
    c.fillStyle = "#065f46";
    c.beginPath();
    c.arc(0, 4, 16, 0, Math.PI * 2);
    c.fill();

    c.fillStyle = "#047857";
    c.beginPath();
    c.arc(0, -6, 13, 0, Math.PI * 2);
    c.fill();

    c.fillStyle = "#10b981";
    c.beginPath();
    c.arc(0, -14, 9, 0, Math.PI * 2);
    c.fill();

    // Digital leaf accents
    c.fillStyle = "#6ee7b7";
    c.fillRect(-4, -8, 2, 2);
    c.fillRect(5, -4, 2, 2);
    c.fillRect(1, -16, 2, 2);

    c.restore();
}

// 3. Telemetry Beacon / Sensor
function drawBeacon(c, x, y, scale, time) {
    c.save();
    c.translate(x, y);
    c.scale(scale, scale);

    // Expanding radio wave ripple
    const ripple = (time * 0.002) % 1;
    c.strokeStyle = `rgba(6, 182, 212, ${1 - ripple})`;
    c.lineWidth = 1.5;
    c.beginPath();
    c.arc(0, -12, ripple * 26, 0, Math.PI * 2);
    c.stroke();

    // Base
    c.fillStyle = "#1e293b";
    c.fillRect(-6, 8, 12, 4);

    // Mast
    c.strokeStyle = "#94a3b8";
    c.lineWidth = 2.5;
    c.beginPath();
    c.moveTo(0, 8);
    c.lineTo(0, -12);
    c.stroke();

    // Antenna dish
    c.strokeStyle = "#06b6d4";
    c.lineWidth = 2;
    c.beginPath();
    c.arc(0, -12, 6, Math.PI * 0.8, Math.PI * 2.2);
    c.stroke();

    // Blinking transmitter diode
    c.fillStyle = (Math.sin(time * 0.01) > 0) ? "#ef4444" : "#22d3ee";
    c.beginPath();
    c.arc(0, -16, 2.5, 0, Math.PI * 2);
    c.fill();

    c.restore();
}

// 4. Nut Cache
function drawCache(c, x, y, scale) {
    c.save();
    c.translate(x, y);
    c.scale(scale, scale);

    // Vault box
    c.fillStyle = "#1e293b";
    c.strokeStyle = "#f59e0b";
    c.lineWidth = 1.5;
    c.beginPath();
    c.roundRect(-10, -6, 20, 14, 3);
    c.fill();
    c.stroke();

    // Acorn icon on lid
    c.fillStyle = "#f59e0b";
    c.beginPath();
    c.arc(0, 0, 3.5, 0, Math.PI * 2);
    c.fill();

    // Green status LED
    c.fillStyle = "#10b981";
    c.beginPath();
    c.arc(6, -2, 1.5, 0, Math.PI * 2);
    c.fill();

    c.restore();
}

// 5. Holographic Note
function drawNote(c, x, y, scale, time) {
    c.save();
    c.translate(x, y);
    c.scale(scale, scale);

    const bob = Math.sin(time * 0.003) * 2;
    c.translate(0, bob);

    // Hologram sheet
    c.fillStyle = "rgba(6, 182, 212, 0.25)";
    c.strokeStyle = "#06b6d4";
    c.lineWidth = 1;
    c.beginPath();
    c.roundRect(-8, -11, 16, 22, 2);
    c.fill();
    c.stroke();

    // Scan lines
    c.strokeStyle = "rgba(255, 255, 255, 0.5)";
    c.beginPath();
    c.moveTo(-5, -6); c.lineTo(5, -6);
    c.moveTo(-5, -2); c.lineTo(3, -2);
    c.moveTo(-5, 2);  c.lineTo(4, 2);
    c.moveTo(-5, 6);  c.lineTo(1, 6);
    c.stroke();

    c.restore();
}

// 6. Contraption
function drawContraption(c, x, y, scale, time) {
    c.save();
    c.translate(x, y);
    c.scale(scale, scale);

    // Rotating gear
    c.save();
    c.rotate(time * 0.001);
    c.strokeStyle = "#f59e0b";
    c.lineWidth = 2;
    c.beginPath();
    c.arc(0, 0, 8, 0, Math.PI * 2);
    c.stroke();
    for (let i = 0; i < 6; i++) {
        c.rotate(Math.PI / 3);
        c.strokeRect(-2, -10, 4, 3);
    }
    c.restore();

    // Center jewel
    c.fillStyle = "#06b6d4";
    c.beginPath();
    c.arc(0, 0, 3, 0, Math.PI * 2);
    c.fill();

    c.restore();
}

// 7. Player Avatar
function drawPlayer(c, x, y, scale, name) {
    c.save();
    c.translate(x, y);
    c.scale(scale, scale);

    // Personal light cone / aura
    const light = c.createRadialGradient(0, 0, 4, 0, 0, 24);
    light.addColorStop(0, "rgba(6, 182, 212, 0.3)");
    light.addColorStop(1, "rgba(6, 182, 212, 0)");
    c.fillStyle = light;
    c.beginPath();
    c.arc(0, 0, 24, 0, Math.PI * 2);
    c.fill();

    // Suit Body
    c.fillStyle = "#e2e8f0";
    c.beginPath();
    c.ellipse(0, 2, 9, 11, 0, 0, Math.PI * 2);
    c.fill();
    c.strokeStyle = "#0891b2";
    c.lineWidth = 1;
    c.stroke();

    // Helmet
    c.fillStyle = "#0284c7";
    c.beginPath();
    c.arc(0, -9, 8, 0, Math.PI * 2);
    c.fill();

    // Golden Visor
    c.fillStyle = "#f59e0b";
    c.beginPath();
    c.ellipse(2, -9, 5, 4, 0.1, 0, Math.PI * 2);
    c.fill();

    c.restore();
}

// ==========================================
// Object Clumping & Radial Layout
// ==========================================
function getObjectVisualOffsets(objects) {
    // If multiple objects share coordinates (within 35m), fan them out radially
    const clusters = {};
    const clusterDist = 35;

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
            const radius = 32; // Spread radius in world units
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
    const objOffsets = getObjectVisualOffsets(state.world.objects);

    // Draw World Objects
    state.world.objects.forEach(obj => {
        const offset = objOffsets.get(obj.id) || { x: obj.x, y: obj.y };
        const p = worldToScreen(offset.x, offset.y);
        const spriteScale = Math.max(0.6, Math.min(1.8, zoom));

        // Draw connecting leader line if fanned out
        if (offset.isClustered) {
            const originP = worldToScreen(obj.x, obj.y);
            ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 4]);
            ctx.beginPath();
            ctx.moveTo(originP.x, originP.y);
            ctx.lineTo(p.x, p.y);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Render distinct sprite
        if (obj.type === "tree") {
            drawCyberTree(ctx, p.x, p.y, spriteScale);
        } else if (obj.type === "sensor") {
            drawBeacon(ctx, p.x, p.y, spriteScale, time);
        } else if (obj.type === "cache") {
            drawCache(ctx, p.x, p.y, spriteScale);
        } else if (obj.type === "note") {
            drawNote(ctx, p.x, p.y, spriteScale, time);
        } else if (obj.type === "contraption") {
            drawContraption(ctx, p.x, p.y, spriteScale, time);
        } else {
            // Default Landmark
            ctx.font = `${20 * zoom}px sans-serif`;
            ctx.textAlign = "center";
            ctx.fillText("📍", p.x, p.y);
        }

        // Draw pill label badge (never raw overlapping text!)
        drawPillBadge(ctx, p.x, p.y + 24 * spriteScale, obj.name, "#cbd5e1");
    });

    // Draw Robot Squirrel
    const sq = state.world.squirrel;
    const sqScreen = worldToScreen(sq.x, sq.y);
    const sqScale = Math.max(0.7, Math.min(2.0, zoom));
    drawRobotSquirrel(ctx, sqScreen.x, sqScreen.y, sqScale, sq.heading, time);

    // Squirrel Name Badge
    drawPillBadge(ctx, sqScreen.x, sqScreen.y - 28 * sqScale, "LIVELY ⚡", "#f59e0b", "rgba(24, 27, 36, 0.95)", "rgba(245, 158, 11, 0.4)");

    // Draw Other Users (filter out own ID so NO DUPLICATION!)
    state.world.users.forEach(u => {
        if (state.myUserId && u.id === state.myUserId) return; // Do not draw self twice!
        const up = worldToScreen(u.x, u.y);
        drawPlayer(ctx, up.x, up.y, Math.max(0.6, Math.min(1.5, zoom)), u.name);
        drawPillBadge(ctx, up.x, up.y - 24 * zoom, u.name, "#94a3b8");
    });

    // Draw Your Avatar
    const userScreen = worldToScreen(state.user.x, state.user.y);
    const playerScale = Math.max(0.7, Math.min(1.8, zoom));
    drawPlayer(ctx, userScreen.x, userScreen.y, playerScale, state.user.name);
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

// ==========================================
// Gmail Integration (Settings & Testing)
// ==========================================
async function fetchGmailStatus() {
    try {
        const res = await fetch("/api/settings/gmail");
        const data = await res.json();
        if (data.authenticated) {
            statGmail.innerText = "Ready ✅";
            statGmail.className = "val badge ready";
            document.getElementById("gmail-status-text").innerText = `Gmail is connected (${data.method})! Lively can email you.`;
        } else {
            statGmail.innerText = "Setup Needed ⚠️";
            statGmail.className = "val badge unlinked";
            document.getElementById("gmail-status-text").innerText = "Not connected yet. Choose Method 1 (App Password) or Method 2 (OAuth) below.";
        }
        if (data.user_email) {
            document.getElementById("gmail-user-email").value = data.user_email;
        }
        if (data.client_id) {
            document.getElementById("gmail-client-id").value = data.client_id;
        }
    } catch (e) {
        statGmail.innerText = "Error";
    }
}

// Method 1: Save App Password
document.getElementById("form-gmail-app-pw").addEventListener("submit", async (e) => {
    e.preventDefault();
    const user_email = document.getElementById("gmail-user-email").value.trim();
    const app_password = document.getElementById("gmail-app-pw").value.trim();

    if (!app_password) {
        alert("Please paste your 16-character App Password.");
        return;
    }

    try {
        const res = await fetch("/api/settings/gmail", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                method: "app_password",
                user_email,
                app_password
            })
        });
        const out = await res.json();
        alert("App Password saved successfully!");
        fetchGmailStatus();
    } catch (err) {
        alert("Error saving App Password: " + err);
    }
});

// Method 2: Save OAuth Credentials
document.getElementById("form-gmail-oauth").addEventListener("submit", async (e) => {
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

// Method 2: Open Auth URL
document.getElementById("btn-auth-gmail").addEventListener("click", async () => {
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

// Send Test Email
document.getElementById("btn-test-email").addEventListener("click", async () => {
    const btn = document.getElementById("btn-test-email");
    const resultBox = document.getElementById("email-test-result");
    btn.disabled = true;
    btn.innerText = "Sending test email...";
    resultBox.innerText = "";

    try {
        const res = await fetch("/api/test/email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                subject: "🐿️ Hello from Lively the Robot Squirrel!",
                body: "Greetings David!\n\nThis is a transmission from Lively living on your Raspberry Pi! My email sensors are online and functioning perfectly.\n\nCatch you later on the map! 🌰⚡"
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
        btn.disabled = false;
        btn.innerText = "📨 Send Test Email Now";
    }
});

// Projects & Code Workshop
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
                showNotification("🐿️ Lively finished thinking and acted!");
                if (badge) {
                    badge.innerText = "Completed";
                    badge.className = "badge ready";
                }
                fetchWorld();
                loadProjects();
                loadMemories();
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
