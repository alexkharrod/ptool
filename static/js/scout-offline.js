/**
 * scout-offline.js
 * Offline buffering for the scouting add form.
 * Stores pending prospects in IndexedDB (photos as Blobs) and
 * syncs them automatically when connectivity is restored.
 */

const SCOUT_DB_NAME    = 'ptool-offline';
const SCOUT_DB_VERSION = 1;
const SCOUT_STORE      = 'pending_scouts';

// ── IndexedDB helpers ──────────────────────────────────────────────────────────

function scoutOpenDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(SCOUT_DB_NAME, SCOUT_DB_VERSION);
        req.onupgradeneeded = e => {
            e.target.result.createObjectStore(SCOUT_STORE, { keyPath: 'id', autoIncrement: true });
        };
        req.onsuccess = e => resolve(e.target.result);
        req.onerror   = e => reject(e.target.error);
    });
}

async function scoutSavePending(fields, imageFile) {
    const db = await scoutOpenDB();
    const record = {
        timestamp: Date.now(),
        fields,
        imageBlob: imageFile || null,
        imageName: imageFile ? imageFile.name : null,
    };
    return new Promise((resolve, reject) => {
        const tx  = db.transaction(SCOUT_STORE, 'readwrite');
        const req = tx.objectStore(SCOUT_STORE).add(record);
        req.onsuccess = e => resolve(e.target.result);
        req.onerror   = e => reject(e.target.error);
    });
}

async function scoutGetPending() {
    const db = await scoutOpenDB();
    return new Promise((resolve, reject) => {
        const req = db.transaction(SCOUT_STORE, 'readonly').objectStore(SCOUT_STORE).getAll();
        req.onsuccess = e => resolve(e.target.result);
        req.onerror   = e => reject(e.target.error);
    });
}

async function scoutRemovePending(id) {
    const db = await scoutOpenDB();
    return new Promise((resolve, reject) => {
        const req = db.transaction(SCOUT_STORE, 'readwrite').objectStore(SCOUT_STORE).delete(id);
        req.onsuccess = () => resolve();
        req.onerror   = e => reject(e.target.error);
    });
}

async function scoutPendingCount() {
    return (await scoutGetPending()).length;
}

// ── CSRF helper ───────────────────────────────────────────────────────────────

function scoutCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
}

// ── Submit one queued record ──────────────────────────────────────────────────

async function scoutSubmitOne(record) {
    const fd = new FormData();
    for (const [k, v] of Object.entries(record.fields)) {
        fd.append(k, v ?? '');
    }
    if (record.imageBlob) {
        fd.append('image', record.imageBlob, record.imageName || 'photo.jpg');
    }

    const resp = await fetch('/scouting/add/', {
        method:  'POST',
        headers: { 'X-CSRFToken': scoutCsrf(), 'X-Async-Submit': '1' },
        body:    fd,
    });

    if (!resp.ok) return false;
    const data = await resp.json();
    return data.ok === true;
}

// ── Sync all pending ──────────────────────────────────────────────────────────

async function scoutSync() {
    if (!navigator.onLine) return 0;
    const pending = await scoutGetPending();
    let synced = 0;
    for (const record of pending) {
        try {
            if (await scoutSubmitOne(record)) {
                await scoutRemovePending(record.id);
                synced++;
            }
        } catch (e) {
            console.warn('[scout-offline] sync failed for id', record.id, e);
        }
    }
    return synced;
}

// ── Banner update (call on any scouting page) ─────────────────────────────────

async function scoutUpdateBanner() {
    const banner = document.getElementById('scout-offline-banner');
    if (!banner) return;
    const count = await scoutPendingCount();
    if (count > 0) {
        banner.style.display = '';
        const el = document.getElementById('scout-pending-count');
        if (el) el.textContent = count;
    } else {
        banner.style.display = 'none';
    }
}
