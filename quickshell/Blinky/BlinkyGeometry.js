.pragma library

// Body outlines as a radius per angle (1 = the body radius), drawn as one smooth closed path.

function radiusAt(shape, theta) {
    const c = Math.cos(theta), s = Math.sin(theta);
    switch (shape) {
    case "squircle":
        return 0.9 * Math.pow(Math.pow(Math.abs(c), 4) + Math.pow(Math.abs(s), 4), -0.25);
    case "pebble":
        return 1 + 0.07 * Math.cos(2 * theta + 0.6) + 0.04 * Math.cos(3 * theta + 2);
    case "cloud":
        return 0.93 + 0.08 * Math.abs(Math.cos(3 * theta));
    case "capsule":
        return Math.pow(Math.pow(Math.abs(c), 6) + Math.pow(Math.abs(s / 0.78), 6), -1 / 6);
    default:
        return 1;
    }
}

// Quadratic segments through the midpoints of a sampled polygon: smooth, no corners.
function bodyPath(shape, size, radius) {
    const n = 48, pts = [];
    for (let i = 0; i < n; i++) {
        const a = i / n * 2 * Math.PI, r = radiusAt(shape, a) * radius;
        pts.push([size / 2 + r * Math.cos(a), size / 2 + r * Math.sin(a)]);
    }
    const mid = (p, q) => ((p[0] + q[0]) / 2).toFixed(2) + " " + ((p[1] + q[1]) / 2).toFixed(2);
    let d = "M " + mid(pts[n - 1], pts[0]);
    for (let i = 0; i < n; i++)
        d += " Q " + pts[i][0].toFixed(2) + " " + pts[i][1].toFixed(2) + " " + mid(pts[i], pts[(i + 1) % n]);
    return d + " Z";
}

// A repeatable pseudo-random number in [0, 1) for an integer step and a per-blinky seed.
function noise(step, seed) {
    const x = Math.sin(step * 12.9898 + seed * 78.233) * 43758.5453;
    return x - Math.floor(x);
}

// Number from a string, so every blinky gets its own rhythm.
function seedOf(text) {
    let h = 7;
    for (let i = 0; i < text.length; i++)
        h = (h * 31 + text.charCodeAt(i)) % 9973;
    return h / 9973;
}
