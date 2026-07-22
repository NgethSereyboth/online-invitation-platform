const $ = s => document.querySelector(s),
    $$ = s => [...document.querySelectorAll(s)];
const editorParams = new URLSearchParams(location.search), templateEditId = editorParams.get('templateEdit');
const activeInviteId = localStorage.getItem('sovan-active-invite') || 'demo-wedding';
const draftKey = `sovan-invite-draft-v3:${activeInviteId}`,
    publishKey = `sovan-invite-published-v3:${activeInviteId}`,
    historyKey = `sovan-invite-history-v3:${activeInviteId}`,
    rsvpKey = `sovan-invite-rsvps-v3:${activeInviteId}`;
let selected = null,
    selectedObjects = new Set(),
    saveTimer, serverSaveTimer, historyTimer, lastLocalFingerprint = '', historyApplying = false, undoStack = [], redoStack = [],
    serverInvite = inviteStore.read(`sovan-server-invite:${activeInviteId}`);
const savedGroupsKey = 'sovan-reusable-element-groups-v1';
const savedPageTemplatesKey = 'sovan-reusable-page-templates-v1';
const savedBlockTemplatesKey = 'sovan-reusable-content-blocks-v1';
const savedFullTemplatesKey = 'sovan-full-invitation-templates-v1';
const objectClipboardKey = 'sovan-object-clipboard-v1';
let activeCanvasId = 'hero', accountPageTemplates = [], accountBlockTemplates = [], accountSavedGroups = [];
let editorZoom = Math.max(.35, Math.min(2, Number(localStorage.getItem('sovan-editor-zoom') || 1))), panMode = false, spacePan = false;
async function api(path, options = {}) {
    let token = localStorage.getItem('sovan-auth-token'),
        r = await fetch(path, {
            headers: {
                'Content-Type': 'application/json',
                ...(token ? {
                    Authorization: `Bearer ${token}`
                } : {}),
                ...(options.headers || {})
            },
            ...options
        });
    if (!r.ok) throw Error((await r.json().catch(() => ({}))).error || 'Server request failed');
    return r.json()
}
async function connectServer() {
    try {
        await api('/api/health');
        if (!serverInvite) {
            try {
                serverInvite = await api('/api/invitations/' + encodeURIComponent(activeInviteId));
                state = migrateDocument(serverInvite.document || state);
                inviteStore.write(draftKey, state);
                undoStack = [];
                redoStack = [];
                apply();
                pushHistory(capture())
            } catch (error) {
                if (localStorage.getItem('sovan-auth-token')) throw error;
                let names = state?.fields?.names || 'our invitation';
                serverInvite = await api('/api/invitations', {
                    method: 'POST',
                    body: JSON.stringify({
                        slug: names.replace(/&/g, ' and '),
                        document: state
                    })
                })
            }
            inviteStore.write(`sovan-server-invite:${activeInviteId}`, serverInvite)
        }
        $('#serverState').textContent = 'Server connected';
        renderAssets();
        loadAccountPageTemplates();
        loadAccountComponents();
        setupTemplateEditMode();
        setupPublishingSettings();
    } catch (error) {
        $('#serverState').textContent = error.message === 'Invitation not found' ? 'Server invitation unavailable' : 'Local mode'
    }
}
async function saveServerDraft(document = state) {
    if (!serverInvite) return;
    try {
        await api('/api/invitations/' + serverInvite.id, {
            method: 'PUT',
            body: JSON.stringify({ document })
        });
        $('#serverState').textContent = 'Server connected'
    } catch {
        $('#serverState').textContent = 'Offline — saved locally'
    }
}
const initial = {
    fields: {
        names: 'Sophea & Dara',
        namesKm: 'សុភា & ដារ៉ា',
        date: '2026-12-27',
        time: '16:00',
        venue: 'The Riverside Ballroom, Phnom Penh',
        venueKm: 'សាលពិធីមង្គលការ រាជធានីភ្នំពេញ',
        message: 'Together with our families, we warmly invite you to celebrate our wedding.',
        messageKm: 'ជាមួយនឹងក្រុមគ្រួសាររបស់យើង យើងខ្ញុំសូមគោរពអញ្ជើញលោកអ្នកចូលរួមអបអរសាទរពិធីមង្គលការរបស់យើង។'
    },
    settings: {
        rsvpEnabled: true,
        wishesEnabled: false,
        scheduleEnabled: true,
        venueEnabled: true,
        galleryEnabled: true,
        videoEnabled: false,
        countdownEnabled: true,
        musicEnabled: false,
        openingEnabled: true,
        contactEnabled: true
    },
    languageMode: 'both',
    contactPhone: '',
    contactTelegram: '',
    rsvpFields: [],
    dateFormat: 'both',
    khmerDate: '',
    countdownTitle: 'Counting down to our celebration',
    countdownTitleKm: 'រាប់ថយក្រោយទៅកាន់ថ្ងៃដ៏ពិសេសរបស់យើង',
    theme: 'rose',
    openingStyle: 'soft',
    galleryStyle: 'grid',
    galleryOrder: [],
    sectionOrder: ['gallery', 'video', 'countdown', 'schedule', 'custom', 'venue', 'contact', 'wishes', 'rsvp'],
    sectionAnimations: {
        hero: { preset: 'fade-up', duration: 900 },
        gallery: { preset: 'fade-up', duration: 900 },
        video: { preset: 'soft-zoom', duration: 900 },
        countdown: { preset: 'soft-zoom', duration: 900 },
        schedule: { preset: 'fade-up', duration: 900 },
        custom: { preset: 'fade-up', duration: 900 },
        venue: { preset: 'fade-up', duration: 900 },
        contact: { preset: 'fade-up', duration: 900 },
        rsvp: { preset: 'fade-up', duration: 900 },
        wishes: { preset: 'fade-up', duration: 900 }
    },
    sectionLayouts: {
        countdown: 'cards',
        schedule: 'timeline',
        custom: 'cards',
        venue: 'cards'
    },
    sectionStyles: Object.fromEntries(['gallery','video','countdown','schedule','custom','venue','contact','wishes','rsvp'].map(name => [name, {
        backgroundEnabled: false, background: '#ffffff', textColorEnabled: false, textColor: '#342c26', radius: 0,
        backgroundImageEnabled: false, backgroundImage: '', backgroundSize: 'cover', backgroundOverlay: 0
    }])) ,
    palettePreset: 'template',
    palette: { background: '#fff8f2', surface: '#ffffff', text: '#342c26', heading: '#9d4555' },
    schedule: [{
        time: '4:00 PM',
        title: 'Guest arrival',
        titleKm: 'ទទួលភ្ញៀវ'
    }, {
        time: '5:00 PM',
        title: 'Wedding ceremony',
        titleKm: 'ពិធីមង្គលការ'
    }, {
        time: '6:30 PM',
        title: 'Dinner reception',
        titleKm: 'ពិសាអាហារពេលល្ងាច'
    }],
    venues: [],
    customBlocks: [],
    designPages: [],
    masterPageStyle: { enabled:false, background:'#fffaf6', backgroundImage:'', backgroundSize:'cover', backgroundOverlay:0 },
    backgroundEffects: { mode:'none', start:'#fff8f2', end:'#ead8d0', angle:135, texture:'none', textureOpacity:18 },
    music: null,
    video: null,
    mapUrl: '',
    accent: '#9d4555',
    objects: {}
};

function youtubeId(value) {
    try {
        let u = new URL(value),
            host = u.hostname.replace(/^www\./, '').toLowerCase(),
            id = host === 'youtu.be' ? u.pathname.split('/')[1] : ['youtube.com', 'music.youtube.com', 'm.youtube.com'].includes(host) ? u.searchParams.get('v') || u.pathname.match(/^\/(?:embed|shorts)\/([^/?]+)/)?.[1] : '';
        return /^[\w-]{11}$/.test(id || '') ? id : ''
    } catch {
        return ''
    }
}

function khmerDateFor(date, time = '00:00') {
    try {
        if (!window.momentkh || !date) return '';
        let [y, m, d] = date.split('-').map(Number), [h, min] = time.split(':').map(Number);
        return momentkh.format(momentkh.fromGregorian(y, m, d, h || 0, min || 0))
    } catch {
        return ''
    }
}

function gregorianLabel(fields) {
    let date = new Date(fields.date + 'T00:00:00');
    return isNaN(date) ? fields.date : date.toLocaleDateString(undefined, {
        dateStyle: 'long'
    })
}
function migrateDocument(documentData) {
    const doc = clone(documentData || initial);
    doc.fields = { ...(doc.fields || {}) };
    const hadKhmer = Boolean(doc.fields.namesKm || doc.fields.messageKm);
    if (doc.fields.namesKm == null) doc.fields.namesKm = '';
    if (doc.fields.messageKm == null) doc.fields.messageKm = '';
    if (doc.fields.venueKm == null) doc.fields.venueKm = '';
    if (!doc.languageMode) doc.languageMode = hadKhmer ? 'both' : 'en';
    if (doc.contactPhone == null) doc.contactPhone = '';
    if (doc.contactTelegram == null) doc.contactTelegram = '';
    if (!Array.isArray(doc.rsvpFields)) doc.rsvpFields = [];
    doc.settings = { ...(doc.settings || {}), contactEnabled: doc.settings?.contactEnabled !== false, videoEnabled: doc.settings?.videoEnabled === true };
    if (!doc.video || typeof doc.video !== 'object') doc.video = null;
    if (!Array.isArray(doc.galleryOrder)) doc.galleryOrder = [];
    if (!Array.isArray(doc.customBlocks)) doc.customBlocks = [];
    if (!Array.isArray(doc.designPages)) doc.designPages = [];
    doc.designPages = doc.designPages.filter(page => page && typeof page === 'object').map((page,index) => ({
        id: String(page.id || `page-${Date.now()}-${index}`),
        name: String(page.name || `Visual Page ${index+1}`),
        preset: String(page.preset || 'custom'),
        enabled: page.enabled !== false,
        background: /^#[0-9a-f]{6}$/i.test(page.background||'') ? page.background : '#fffaf6',
        backgroundImage: String(page.backgroundImage || ''),
        backgroundSize: page.backgroundSize === 'contain' ? 'contain' : 'cover',
        backgroundOverlay: Math.max(0, Math.min(80, Number(page.backgroundOverlay || 0))),
        useMasterBackground: page.useMasterBackground === true,
        animation: { preset: page.animation?.preset || 'fade-up', duration: Number(page.animation?.duration || 900) },
        transition: { preset: ['none','soft','overlap','sweep'].includes(page.transition?.preset) ? page.transition.preset : 'soft', duration: Math.max(200, Math.min(2000, Number(page.transition?.duration || 600))) },
        objects: page.objects && typeof page.objects === 'object' && !Array.isArray(page.objects) ? page.objects : {}
    }));
    doc.masterPageStyle = { ...clone(initial.masterPageStyle), ...(doc.masterPageStyle || {}) };
    doc.masterPageStyle.enabled = doc.masterPageStyle.enabled === true;
    doc.masterPageStyle.backgroundSize = doc.masterPageStyle.backgroundSize === 'contain' ? 'contain' : 'cover';
    doc.masterPageStyle.backgroundOverlay = Math.max(0, Math.min(80, Number(doc.masterPageStyle.backgroundOverlay || 0)));
    doc.backgroundEffects = { ...clone(initial.backgroundEffects), ...(doc.backgroundEffects || {}) };
    doc.backgroundEffects.mode = ['none','solid','gradient'].includes(doc.backgroundEffects.mode) ? doc.backgroundEffects.mode : 'none';
    doc.backgroundEffects.texture = ['none','paper','dots','grid','soft-grain'].includes(doc.backgroundEffects.texture) ? doc.backgroundEffects.texture : 'none';
    doc.backgroundEffects.angle = Math.max(0, Math.min(360, Number(doc.backgroundEffects.angle || 135)));
    doc.backgroundEffects.textureOpacity = Math.max(0, Math.min(60, Number(doc.backgroundEffects.textureOpacity ?? 18)));
    if (!Array.isArray(doc.schedule)) doc.schedule = clone(initial.schedule);
    doc.schedule = doc.schedule.map(item => ({ ...item, titleKm: item.titleKm || '' }));
    if (!Array.isArray(doc.venues)) doc.venues = [];
    doc.venues = doc.venues.map(item => ({ ...item, nameKm: item.nameKm || '', addressKm: item.addressKm || '' }));
    if (doc.countdownTitleKm == null) doc.countdownTitleKm = '';
    if (!Array.isArray(doc.sectionOrder)) doc.sectionOrder = clone(initial.sectionOrder);
    doc.sectionAnimations = { ...clone(initial.sectionAnimations), ...(doc.sectionAnimations || {}) };
    doc.sectionLayouts = { ...clone(initial.sectionLayouts), ...(doc.sectionLayouts || {}) };
    doc.sectionStyles = { ...clone(initial.sectionStyles), ...(doc.sectionStyles || {}) };
    Object.keys(initial.sectionStyles).forEach(name => { doc.sectionStyles[name] = { ...initial.sectionStyles[name], ...(doc.sectionStyles?.[name] || {}) } });
    if (!doc.palettePreset) doc.palettePreset = 'template';
    doc.palette = { ...clone(initial.palette), ...(doc.palette || {}) };
    if (!doc.sectionOrder.includes('video')) {
        const galleryIndex = doc.sectionOrder.indexOf('gallery');
        doc.sectionOrder.splice(galleryIndex >= 0 ? galleryIndex + 1 : 0, 0, 'video')
    }
    if (!doc.sectionOrder.includes('custom')) {
        const venueIndex = doc.sectionOrder.indexOf('venue');
        doc.sectionOrder.splice(venueIndex >= 0 ? venueIndex : doc.sectionOrder.length, 0, 'custom')
    }
    if (!doc.sectionOrder.includes('contact')) {
        const rsvpIndex = doc.sectionOrder.indexOf('rsvp');
        doc.sectionOrder.splice(rsvpIndex >= 0 ? rsvpIndex : doc.sectionOrder.length, 0, 'contact')
    }
    return doc
}
let state = migrateDocument(inviteStore.read(draftKey, inviteStore.read('sovan-invite-draft-v3', initial)));

function clone(value) { return typeof structuredClone === 'function' ? structuredClone(value) : JSON.parse(JSON.stringify(value)); }
function updateHistoryButtons() {
    $('#undoBtn').disabled = undoStack.length < 2;
    $('#redoBtn').disabled = redoStack.length === 0;
}
function pushHistory(documentState) {
    if (historyApplying) return;
    const snap = clone(documentState), serialized = JSON.stringify(snap);
    if (undoStack.length && JSON.stringify(undoStack[undoStack.length - 1]) === serialized) return;
    undoStack.push(snap);
    if (undoStack.length > 50) undoStack.shift();
    redoStack = [];
    updateHistoryButtons();
}
function restoreHistory(documentState) {
    historyApplying = true;
    state = clone(documentState);
    inviteStore.write(draftKey, state);
    apply();
    historyApplying = false;
    $('#saveState').textContent = 'Restored';
    updateHistoryButtons();
}
function undo() {
    if (undoStack.length < 2) return;
    redoStack.push(undoStack.pop());
    restoreHistory(undoStack[undoStack.length - 1]);
}
function redo() {
    if (!redoStack.length) return;
    const next = redoStack.pop();
    undoStack.push(clone(next));
    restoreHistory(next);
}

function capture() {
    const editingPage = activeCanvasId !== 'hero' ? (state.designPages || []).find(page => `page:${page.id}` === activeCanvasId) : null;
    const heroObjectsBeforePageCapture = editingPage ? state.objects : null;
    const heroGalleryOrderBeforePageCapture = editingPage ? state.galleryOrder : null;
    if (editingPage) state.objects = editingPage.objects || {};
    state.fields = {
        names: $('#names').value,
        namesKm: $('#namesKm').value,
        date: $('#date').value,
        time: $('#time').value,
        venue: $('#venue').value,
        venueKm: $('#venueKm').value,
        message: $('#message').value,
        messageKm: $('#messageKm').value
    };
    state.settings = {
        ...(state.settings || {}),
        rsvpEnabled: $('#rsvpEnabled').checked,
        wishesEnabled: $('#wishesEnabled')?.checked === true,
        scheduleEnabled: $('#scheduleEnabled').checked,
        venueEnabled: $('#venueEnabled').checked,
        galleryEnabled: $('#galleryEnabled').checked,
        videoEnabled: $('#videoEnabled')?.checked === true,
        countdownEnabled: $('#countdownEnabled').checked,
        musicEnabled: $('#musicEnabled').checked,
        openingEnabled: $('#openingEnabled').checked,
        contactEnabled: $('#contactEnabled').checked
    };
    state.languageMode = $('#languageMode').value;
    state.contactPhone = $('#contactPhone').value.trim();
    state.contactTelegram = $('#contactTelegram').value.trim();
    state.dateFormat = $('#dateFormat').value;
    state.khmerDate = khmerDateFor(state.fields.date, state.fields.time);
    state.countdownTitle = $('#countdownTitle').value.trim();
    state.countdownTitleKm = $('#countdownTitleKm').value.trim();
    state.theme = $('#designTheme').value;
    state.openingStyle = $('#openingStyle').value;
    state.galleryStyle = $('#galleryStyle').value;
    let fixedSections = ['gallery', 'video', 'countdown', 'schedule', 'custom', 'venue', 'contact', 'wishes', 'rsvp'],
        pageSections = (state.designPages || []).map(page => `page:${page.id}`),
        allowed = [...fixedSections, ...pageSections],
        chosen = $('#sectionOrder').value.split(/\r?\n|,/).map(x => x.trim()).filter((x, i, a) => allowed.includes(x) && a.indexOf(x) === i);
    state.sectionOrder = [...chosen, ...allowed.filter(x => !chosen.includes(x))];
    const scheduleEn = $('#scheduleText').value.split(/\r?\n/).map(line => {
        let [time, ...title] = line.split('|');
        return { time: (time || '').trim(), title: title.join('|').trim() }
    });
    const scheduleKm = $('#scheduleTextKm').value.split(/\r?\n/).map(line => {
        let [time, ...title] = line.split('|');
        return { time: (time || '').trim(), titleKm: title.join('|').trim() }
    });
    state.schedule = scheduleEn.map((item, index) => ({ ...item, titleKm: scheduleKm[index]?.titleKm || '' })).filter(x => x.time || x.title || x.titleKm);
    const venuesEn = $('#venuesText').value.split(/\r?\n/).map(line => {
        let [name, address, ...url] = line.split('|');
        return { name: (name || '').trim(), address: (address || '').trim(), mapUrl: url.join('|').trim() }
    });
    const venuesKm = $('#venuesTextKm').value.split(/\r?\n/).map(line => {
        let [nameKm, addressKm] = line.split('|');
        return { nameKm: (nameKm || '').trim(), addressKm: (addressKm || '').trim() }
    });
    state.venues = venuesEn.map((item, index) => ({ ...item, nameKm: venuesKm[index]?.nameKm || '', addressKm: venuesKm[index]?.addressKm || '' })).filter(x => x.name || x.address || x.nameKm || x.addressKm);
    state.mapUrl = $('#mapUrl').value.trim();
    state.youtubeUrl = $('#youtubeUrl').value.trim();
    state.youtubeId = youtubeId(state.youtubeUrl);
    state.accent = $('#accent').value;
    state.palettePreset = $('#palettePreset').value;
    state.palette = { background: $('#paletteBackground').value, surface: $('#paletteSurface').value, text: $('#paletteText').value, heading: $('#paletteHeading').value };
    state.backgroundEffects = {
        mode: $('#stage').dataset.backgroundMode || state.backgroundEffects?.mode || 'none',
        start: $('#stage').dataset.backgroundStart || state.backgroundEffects?.start || '#fff8f2',
        end: $('#stage').dataset.backgroundEnd || state.backgroundEffects?.end || '#ead8d0',
        angle: Number($('#stage').dataset.backgroundAngle || state.backgroundEffects?.angle || 135),
        texture: $('#stage').dataset.backgroundTexture || state.backgroundEffects?.texture || 'none',
        textureOpacity: Number($('#stage').dataset.backgroundTextureOpacity || state.backgroundEffects?.textureOpacity || 18)
    };
    state.masterPageStyle = {
        enabled: $('#masterPageEnabled')?.checked === true,
        background: $('#masterPageBackground')?.value || '#fffaf6',
        backgroundImage: $('#masterPageImage')?.value.trim() || '',
        backgroundSize: $('#masterPageSize')?.value === 'contain' ? 'contain' : 'cover',
        backgroundOverlay: Number($('#masterPageOverlay')?.value || 0)
    };
    state.sectionLayouts = {
        countdown: $('#countdownLayout').value,
        schedule: $('#scheduleLayout').value,
        custom: $('#customLayout').value,
        venue: $('#venueLayout').value
    };
    state.sectionAnimations = state.sectionAnimations || {};
    $$('#sectionAnimationsManager [data-section-animation]').forEach(row => {
        const name = row.dataset.sectionAnimation;
        state.sectionAnimations[name] = {
            preset: row.querySelector('select').value,
            duration: Number(row.querySelector('input[type="range"]').value || 900)
        }
    });
    state.sectionStyles = state.sectionStyles || {};
    $$('#sectionStylesManager [data-section-style]').forEach(row => {
        const name = row.dataset.sectionStyle;
        state.sectionStyles[name] = {
            backgroundEnabled: row.querySelector('[data-style-background-enabled]').checked,
            background: row.querySelector('[data-style-background]').value,
            textColorEnabled: row.querySelector('[data-style-text-enabled]').checked,
            textColor: row.querySelector('[data-style-text]').value,
            radius: Number(row.querySelector('[data-style-radius]').value || 0),
            backgroundImageEnabled: row.querySelector('[data-style-image-enabled]').checked,
            backgroundImage: row.querySelector('[data-style-image]').value.trim(),
            backgroundSize: row.querySelector('[data-style-image-size]').value,
            backgroundOverlay: Number(row.querySelector('[data-style-overlay]').value || 0)
        }
    });
    const existingOrder = Array.isArray(state.galleryOrder) ? state.galleryOrder : [];
    const imageIds = [];
    $$('.object').forEach((o, index) => {
        const img = o.querySelector('img');
        state.objects[o.dataset.id] = {
            left: o.style.left,
            top: o.style.top,
            width: o.style.width,
            height: o.style.height,
            font: o.dataset.font || '',
            color: o.dataset.color || '',
            fontSize: Number(o.dataset.fontSize || 0),
            textAlign: o.dataset.textAlign || 'center',
            textVerticalAlign: o.dataset.textVerticalAlign || 'middle',
            textPadding: Number(o.dataset.textPadding ?? 8),
            fontWeight: o.dataset.fontWeight || '400',
            fontStyle: o.dataset.fontStyle || 'normal',
            letterSpacing: Number(o.dataset.letterSpacing || 0),
            lineHeight: Number(o.dataset.lineHeight || 1.35),
            fillColor: o.dataset.fillColor || '#d9a6ad',
            shapeKind: o.dataset.shapeKind || 'rectangle',
            opacity: Number(o.dataset.opacity || 1),
            borderWidth: Number(o.dataset.borderWidth || 0),
            borderColor: o.dataset.borderColor || '#ffffff',
            borderRadius: Number(o.dataset.borderRadius || 0),
            shadowBlur: Number(o.dataset.shadowBlur || 0),
            shadowColor: o.dataset.shadowColor || '#000000',
            backgroundEnabled: o.dataset.backgroundEnabled === 'true',
            backgroundColor: o.dataset.backgroundColor || '#ffffff',
            backgroundOpacity: Number(o.dataset.backgroundOpacity ?? 100),
            blendMode: o.dataset.blendMode || 'normal',
            fillMode: o.dataset.fillMode || 'solid',
            gradientStart: o.dataset.gradientStart || '#d9a6ad',
            gradientEnd: o.dataset.gradientEnd || '#9d4555',
            gradientAngle: Number(o.dataset.gradientAngle || 135),
            textGradientEnabled: o.dataset.textGradientEnabled === 'true',
            textGradientStart: o.dataset.textGradientStart || '#9d4555',
            textGradientEnd: o.dataset.textGradientEnd || '#b58a3a',
            textGradientAngle: Number(o.dataset.textGradientAngle || 90),
            textStrokeWidth: Number(o.dataset.textStrokeWidth || 0),
            textStrokeColor: o.dataset.textStrokeColor || '#ffffff',
            textShadowBlur: Number(o.dataset.textShadowBlur || 0),
            textShadowColor: o.dataset.textShadowColor || '#000000',
            textTransform: o.dataset.textTransform || 'none',
            animation: o.dataset.animation || 'fade-up',
            duration: o.dataset.duration || '900',
            animationDelay: Number(o.dataset.animationDelay || 0),
            html: o.querySelector('.content')?.innerHTML,
            src: img?.src,
            originalSrc: o.dataset.originalSrc || '',
            alt: o.dataset.alt || img?.alt || '',
            caption: o.dataset.caption || '',
            locked: o.dataset.locked === 'true',
            visible: o.dataset.visible !== 'false',
            layerName: o.dataset.layerName || '',
            rotation: Number(o.dataset.rotation || 0),
            imageFit: o.dataset.imageFit || 'cover',
            imagePositionX: Number(o.dataset.imagePositionX || 50),
            imagePositionY: Number(o.dataset.imagePositionY || 50),
            imageMask: o.dataset.imageMask || 'none',
            imageFrame: o.dataset.imageFrame || 'none',
            imageBrightness: Number(o.dataset.imageBrightness || 100),
            imageContrast: Number(o.dataset.imageContrast || 100),
            imageSaturation: Number(o.dataset.imageSaturation || 100),
            imageGrayscale: Number(o.dataset.imageGrayscale || 0),
            imageSepia: Number(o.dataset.imageSepia || 0),
            imageBlur: Number(o.dataset.imageBlur || 0),
            imageHue: Number(o.dataset.imageHue || 0),
            imageFlipX: o.dataset.imageFlipX === 'true',
            imageFlipY: o.dataset.imageFlipY === 'true',
            showInHero: o.dataset.showInHero !== 'false',
            showInGallery: o.dataset.showInGallery !== 'false',
            groupId: o.dataset.groupId || '',
            zIndex: Number(o.style.zIndex || index + 1),
            type: o.dataset.objectType || (o.classList.contains('image-object') ? 'image' : 'text')
        };
        if (o.classList.contains('image-object')) imageIds.push(o.dataset.id);
    });
    state.galleryOrder = [...existingOrder.filter(id => imageIds.includes(id)), ...imageIds.filter(id => !existingOrder.includes(id))];
    Object.keys(state.objects).forEach(id => {
        if (!document.querySelector(`[data-id="${CSS.escape(id)}"]`)) delete state.objects[id];
    });
    if (editingPage) {
        editingPage.objects = clone(state.objects);
        state.objects = heroObjectsBeforePageCapture || {};
        state.galleryOrder = heroGalleryOrderBeforePageCapture || [];
    }
    return state
}

function save() {
    capture();
    $('#saveState').textContent = 'Saving…';
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
        const serialized = JSON.stringify(state);
        if (serialized === lastLocalFingerprint) {
            $('#saveState').textContent = 'Saved';
            return
        }
        lastLocalFingerprint = serialized;
        const snapshot = structuredClone(state);
        inviteStore.write(draftKey, snapshot);
        clearTimeout(historyTimer);
        historyTimer = setTimeout(() => pushHistory(snapshot), 260);
        $('#saveState').textContent = 'Saved';
        const activeManagerEditor = document.activeElement?.closest?.('.custom-block-editor,.gallery-item-editor,.section-animation-row,.section-style-row,.design-page-editor,.ei-builder-card');
        if (activeManagerEditor) renderLayers();
        else renderEditorManagers();
        clearTimeout(serverSaveTimer);
        serverSaveTimer = setTimeout(() => {
            const run = () => saveServerDraft(snapshot);
            if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 1800 });
            else run()
        }, 850)
    }, 220)
}

function apply() {
    selected = null;
    selectedObjects.clear();
    Object.entries(state.fields || {}).forEach(([k, v]) => {
        if ($('#' + k)) $('#' + k).value = v
    });
    $('#languageMode').value = state.languageMode || 'both';
    $('#contactPhone').value = state.contactPhone || '';
    $('#contactTelegram').value = state.contactTelegram || '';
    $('#contactEnabled').checked = state.settings?.contactEnabled !== false;
    if ($('#videoEnabled')) $('#videoEnabled').checked = state.settings?.videoEnabled === true;
    if ($('#videoState')) $('#videoState').textContent = state.video?.name ? `Selected: ${state.video.name}` : 'No featured video selected.';
    if ($('#wishesEnabled')) $('#wishesEnabled').checked = state.settings?.wishesEnabled === true;
    $('#countdownTitle').value = state.countdownTitle || '';
    $('#countdownTitleKm').value = state.countdownTitleKm || '';
    $('#scheduleText').value = (state.schedule || []).map(item => `${item.time || ''} | ${item.title || ''}`).join('\n');
    $('#scheduleTextKm').value = (state.schedule || []).map(item => `${item.time || ''} | ${item.titleKm || ''}`).join('\n');
    $('#venuesText').value = (state.venues || []).map(item => `${item.name || ''} | ${item.address || ''} | ${item.mapUrl || ''}`).join('\n');
    $('#venuesTextKm').value = (state.venues || []).map(item => `${item.nameKm || ''} | ${item.addressKm || ''}`).join('\n');
    document.documentElement.style.setProperty('--accent', state.accent || '#9d4555');
    $('#accent').value = state.accent || '#9d4555';
    $('#palettePreset').value = state.palettePreset || 'template';
    $('#paletteBackground').value = state.palette?.background || initial.palette.background;
    $('#paletteSurface').value = state.palette?.surface || initial.palette.surface;
    $('#paletteText').value = state.palette?.text || initial.palette.text;
    $('#paletteHeading').value = state.palette?.heading || state.accent || initial.palette.heading;
    if ($('#masterPageEnabled')) $('#masterPageEnabled').checked = state.masterPageStyle?.enabled === true;
    if ($('#masterPageBackground')) $('#masterPageBackground').value = state.masterPageStyle?.background || '#fffaf6';
    if ($('#masterPageImage')) $('#masterPageImage').value = state.masterPageStyle?.backgroundImage || '';
    if ($('#masterPageSize')) $('#masterPageSize').value = state.masterPageStyle?.backgroundSize || 'cover';
    if ($('#masterPageOverlay')) $('#masterPageOverlay').value = state.masterPageStyle?.backgroundOverlay || 0;
    if ($('#masterPageOverlayValue')) $('#masterPageOverlayValue').textContent = `${state.masterPageStyle?.backgroundOverlay || 0}%`;
    $('#countdownLayout').value = state.sectionLayouts?.countdown || 'cards';
    $('#scheduleLayout').value = state.sectionLayouts?.schedule || 'timeline';
    $('#customLayout').value = state.sectionLayouts?.custom || 'cards';
    $('#venueLayout').value = state.sectionLayouts?.venue || 'cards';
    $('#stage').className = `stage theme-${state.theme||'rose'}${state.palettePreset && state.palettePreset !== 'template' ? ' palette-custom' : ''}`;
    applyPaletteToEditor();
    applyBackgroundEffectsToEditor();
    const activePage = activeCanvasId === 'hero' ? null : (state.designPages || []).find(page => `page:${page.id}` === activeCanvasId);
    if (activeCanvasId !== 'hero' && !activePage) activeCanvasId = 'hero';
    const canvasObjects = activeCanvasId === 'hero' ? (state.objects || {}) : (activePage?.objects || {});
    const hasSavedObjects = canvasObjects && Object.keys(canvasObjects).length;
    if (hasSavedObjects) {
        $$('.object').forEach(o => {
            if (!canvasObjects[o.dataset.id]) o.remove();
        });
    }
    Object.entries(canvasObjects || {}).forEach(([id, d], index) => {
        let o = document.querySelector(`[data-id="${CSS.escape(id)}"]`);
        if (!o) {
            o = createObject(id, d.type);
            $('#stage').append(o)
        }
        ['left', 'top', 'width', 'height'].forEach(k => { if (d[k]) o.style[k] = d[k] });
        o.style.zIndex = String(d.zIndex || index + 1);
        o.dataset.font = d.font || '';
        o.dataset.color = d.color || '';
        o.dataset.objectType = d.type || (o.classList.contains('image-object') ? 'image' : 'text');
        o.dataset.fontSize = String(d.fontSize || 0);
        o.dataset.textAlign = d.textAlign || 'center';
        o.dataset.fontWeight = d.fontWeight || '400';
        o.dataset.fontStyle = d.fontStyle || 'normal';
        o.dataset.letterSpacing = String(d.letterSpacing || 0);
        o.dataset.lineHeight = String(d.lineHeight || 1.35);
        o.dataset.fillColor = d.fillColor || '#d9a6ad';
        o.dataset.shapeKind = d.shapeKind || 'rectangle';
        o.dataset.opacity = String(d.opacity ?? 1);
        o.dataset.borderWidth = String(d.borderWidth || 0);
        o.dataset.borderColor = d.borderColor || '#ffffff';
        o.dataset.borderRadius = String(d.borderRadius || 0);
        o.dataset.shadowBlur = String(d.shadowBlur || 0);
        o.dataset.shadowColor = d.shadowColor || '#000000';
        o.dataset.backgroundEnabled = d.backgroundEnabled ? 'true' : 'false';
        o.dataset.backgroundColor = d.backgroundColor || '#ffffff';
        o.dataset.backgroundOpacity = String(d.backgroundOpacity ?? 100);
        o.dataset.blendMode = d.blendMode || 'normal';
        o.dataset.fillMode = d.fillMode || 'solid';
        o.dataset.gradientStart = d.gradientStart || '#d9a6ad';
        o.dataset.gradientEnd = d.gradientEnd || '#9d4555';
        o.dataset.gradientAngle = String(d.gradientAngle ?? 135);
        o.dataset.textGradientEnabled = d.textGradientEnabled ? 'true' : 'false';
        o.dataset.textGradientStart = d.textGradientStart || '#9d4555';
        o.dataset.textGradientEnd = d.textGradientEnd || '#b58a3a';
        o.dataset.textGradientAngle = String(d.textGradientAngle ?? 90);
        o.dataset.textStrokeWidth = String(d.textStrokeWidth ?? 0);
        o.dataset.textStrokeColor = d.textStrokeColor || '#ffffff';
        o.dataset.textShadowBlur = String(d.textShadowBlur ?? 0);
        o.dataset.textShadowColor = d.textShadowColor || '#000000';
        o.dataset.textTransform = d.textTransform || 'none';
        o.dataset.textVerticalAlign = ['top','middle','bottom'].includes(d.textVerticalAlign) ? d.textVerticalAlign : 'middle';
        o.dataset.textPadding = String(d.textPadding ?? 8);
        o.dataset.animation = d.animation || 'fade-up';
        o.dataset.duration = d.duration || '900';
        o.dataset.animationDelay = String(d.animationDelay ?? 0);
        o.dataset.caption = d.caption || '';
        o.dataset.alt = d.alt || '';
        o.dataset.locked = d.locked ? 'true' : 'false';
        o.dataset.visible = d.visible === false ? 'false' : 'true';
        o.dataset.layerName = d.layerName || '';
        o.dataset.rotation = String(d.rotation || 0);
        o.dataset.originalSrc = d.originalSrc || '';
        o.dataset.imageFit = d.imageFit || 'cover';
        o.dataset.imagePositionX = String(d.imagePositionX ?? 50);
        o.dataset.imagePositionY = String(d.imagePositionY ?? 50);
        o.dataset.imageMask = d.imageMask || 'none';
        o.dataset.imageFrame = d.imageFrame || 'none';
        o.dataset.imageBrightness = String(d.imageBrightness ?? 100);
        o.dataset.imageContrast = String(d.imageContrast ?? 100);
        o.dataset.imageSaturation = String(d.imageSaturation ?? 100);
        o.dataset.imageGrayscale = String(d.imageGrayscale ?? 0);
        o.dataset.imageSepia = String(d.imageSepia ?? 0);
        o.dataset.imageBlur = String(d.imageBlur ?? 0);
        o.dataset.imageHue = String(d.imageHue ?? 0);
        o.dataset.imageFlipX = d.imageFlipX === true ? 'true' : 'false';
        o.dataset.imageFlipY = d.imageFlipY === true ? 'true' : 'false';
        o.dataset.showInHero = d.showInHero === false ? 'false' : 'true';
        o.dataset.showInGallery = d.showInGallery === false ? 'false' : 'true';
        o.dataset.groupId = d.groupId || '';
        o.style.transform = `rotate(${Number(d.rotation || 0)}deg)`;
        applyObjectVisualStyle(o);
        o.classList.toggle('locked', !!d.locked);
        if (o.querySelector('.content')) {
            o.querySelector('.content').innerHTML = d.html || '';
            o.querySelector('.content').style.fontFamily = d.font || '';
            o.querySelector('.content').style.color = d.color || '';
            o.querySelector('.content').style.fontSize = d.fontSize ? `${d.fontSize}px` : '';
            o.querySelector('.content').style.textAlign = d.textAlign || 'center';
            o.querySelector('.content').style.justifyContent = d.textAlign === 'left' ? 'flex-start' : d.textAlign === 'right' ? 'flex-end' : 'center';
            o.querySelector('.content').style.fontWeight = d.fontWeight || '400';
            o.querySelector('.content').style.fontStyle = d.fontStyle || 'normal';
            o.querySelector('.content').style.letterSpacing = `${Number(d.letterSpacing || 0)}px`;
            o.querySelector('.content').style.lineHeight = String(Number(d.lineHeight || 1.35))
        }
        if (o.querySelector('img') && d.src) {
            o.querySelector('img').src = d.src;
            o.querySelector('img').alt = d.alt || 'Invitation image';
            o.querySelector('img').style.objectFit = d.imageFit || 'cover';
            o.querySelector('img').style.objectPosition = `${d.imagePositionX ?? 50}% ${d.imagePositionY ?? 50}%`;
            o.querySelector('img').style.filter = imageFilterStyle(d)
        }
    });
    syncFields(false);
    refreshPublish();
    renderEditorManagers();
    updateCanvasContextUI();
    window.dispatchEvent(new CustomEvent('einvite:state-applied',{detail:{state}}))
}

function createObject(id, type) {
    let o = document.createElement('div');
    const normalizedType = ['text','image','shape','decoration'].includes(type) ? type : 'text';
    o.className = `object ${normalizedType}-object`;
    o.dataset.id = id;
    o.dataset.objectType = normalizedType;
    o.dataset.locked = 'false';
    o.dataset.visible = 'true';
    o.dataset.layerName = '';
    o.dataset.caption = '';
    o.dataset.alt = '';
    o.dataset.rotation = '0';
    o.dataset.imageFit = 'cover';
    o.dataset.imagePositionX = '50';
    o.dataset.imagePositionY = '50';
    o.dataset.imageMask = 'none';
    o.dataset.imageFrame = 'none';
    o.dataset.imageBrightness = '100';
    o.dataset.imageContrast = '100';
    o.dataset.imageSaturation = '100';
    o.dataset.imageGrayscale = '0';
    o.dataset.imageSepia = '0';
    o.dataset.imageBlur = '0';
    o.dataset.imageHue = '0';
    o.dataset.imageFlipX = 'false';
    o.dataset.imageFlipY = 'false';
    o.dataset.showInHero = 'true';
    o.dataset.showInGallery = normalizedType === 'image' && id !== 'hero' ? 'true' : 'false';
    o.dataset.groupId = '';
    o.dataset.fontSize = (normalizedType === 'text' || normalizedType === 'decoration') ? '28' : '0';
    o.dataset.textAlign = 'center';
    o.dataset.textVerticalAlign = 'middle';
    o.dataset.textPadding = '8';
    o.dataset.fontWeight = '400';
    o.dataset.fontStyle = 'normal';
    o.dataset.letterSpacing = '0';
    o.dataset.lineHeight = '1.35';
    o.dataset.fillColor = '#d9a6ad';
    o.dataset.shapeKind = 'rectangle';
    o.dataset.opacity = '1';
    o.dataset.borderWidth = '0';
    o.dataset.borderColor = '#ffffff';
    o.dataset.borderRadius = '0';
    o.dataset.shadowBlur = '0';
    o.dataset.shadowColor = '#000000';
    o.dataset.backgroundEnabled = 'false';
    o.dataset.backgroundColor = '#ffffff';
    o.dataset.backgroundOpacity = '100';
    o.dataset.blendMode = 'normal';
    o.dataset.fillMode = 'solid';
    o.dataset.gradientStart = '#d9a6ad';
    o.dataset.gradientEnd = '#9d4555';
    o.dataset.gradientAngle = '135';
    o.dataset.textGradientEnabled = 'false';
    o.dataset.textGradientStart = '#9d4555';
    o.dataset.textGradientEnd = '#b58a3a';
    o.dataset.textGradientAngle = '90';
    o.dataset.textStrokeWidth = '0';
    o.dataset.textStrokeColor = '#ffffff';
    o.dataset.textShadowBlur = '0';
    o.dataset.textShadowColor = '#000000';
    o.dataset.textTransform = 'none';
    o.dataset.animationDelay = '0';
    o.style.cssText = `left:20%;top:40%;width:60%;height:100px;z-index:${nextZIndex()}`;
    if (normalizedType === 'image') o.innerHTML = '<img alt="Uploaded invitation image"><i class="resize-handle"></i><span class="rotate-handle" title="Rotate"></span>';
    else if (normalizedType === 'shape') o.innerHTML = '<div class="shape-surface" aria-hidden="true"></div><i class="resize-handle"></i><span class="rotate-handle" title="Rotate"></span>';
    else o.innerHTML = '<div class="content">New text</div><i class="resize-handle"></i><span class="rotate-handle" title="Rotate"></span>';
    applyObjectVisualStyle(o);
    wireObject(o);
    return o
}

function nextZIndex() {
    return Math.max(0, ...$$('.object').map(o => Number(o.style.zIndex || 0))) + 1
}

function refreshKhmerDate() {
    let value = khmerDateFor($('#date').value, $('#time').value);
    $('#khmerDatePreview').textContent = value || 'Khmer calendar conversion is unavailable. Check your connection and reload.';
    return value
}

function syncFields(shouldSave = true) {
    const mode = $('#languageMode').value || 'both';
    const names = mode === 'km' ? ($('#namesKm').value || $('#names').value) : $('#names').value;
    const message = mode === 'km' ? ($('#messageKm').value || $('#message').value) : $('#message').value;
    const title = $('[data-id="title"] .content');
    const subtitle = $('[data-id="subtitle"] .content');
    if (title) {
        title.textContent = names;
        title.classList.toggle('khmer-text', mode === 'km')
    }
    if (subtitle) {
        subtitle.textContent = message;
        subtitle.classList.toggle('khmer-text', mode === 'km')
    }
    let dt = new Date($('#date').value + 'T00:00:00');
    let label = isNaN(dt) ? $('#date').value : dt.toLocaleDateString(undefined, {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        }),
        time = $('#time').value;
    const details = $('[data-id="details"] .content');
    const venueLabel = mode === 'km' ? ($('#venueKm').value || $('#venue').value) : $('#venue').value;
    if (details) {
        details.innerHTML = `${label}${time?` · ${time}`:''}<br>${venueLabel}`;
        details.classList.toggle('khmer-text', mode === 'km')
    }
    refreshKhmerDate();
    if (shouldSave) save()
}

['names', 'namesKm', 'date', 'time', 'venue', 'venueKm', 'message', 'messageKm'].forEach(id => $('#' + id).addEventListener('input', syncFields));
['scheduleText', 'scheduleTextKm', 'mapUrl', 'venuesText', 'venuesTextKm', 'sectionOrder', 'youtubeUrl', 'countdownTitle', 'countdownTitleKm', 'contactPhone', 'contactTelegram'].forEach(id => $('#' + id).addEventListener('input', save));
['scheduleLayout','venueLayout','customLayout','countdownLayout'].forEach(id => $('#' + id).addEventListener('change', save));
['rsvpEnabled', 'scheduleEnabled', 'venueEnabled', 'galleryEnabled', 'videoEnabled', 'countdownEnabled', 'musicEnabled', 'openingEnabled', 'openingStyle', 'dateFormat', 'contactEnabled'].forEach(id => $('#' + id)?.addEventListener('change', save));
$('#languageMode').addEventListener('change', () => syncFields());
$('#invitationPreset').addEventListener('change', e => {
    let presets = {
            pure: [false, false, true, false],
            rsvp: [true, false, true, false],
            full: [true, true, true, true]
        },
        p = presets[e.target.value];
    if (!p) return;
    ['rsvpEnabled', 'scheduleEnabled', 'venueEnabled', 'galleryEnabled'].forEach((id, i) => $('#' + id).checked = p[i]);
    save()
});
$('#designTheme').addEventListener('change', e => {
    let accents = {
        rose: '#9d4555',
        gold: '#a87616',
        emerald: '#1f7158',
        midnight: '#8065c7'
    };
    $('#accent').value = accents[e.target.value];
    document.documentElement.style.setProperty('--accent', accents[e.target.value]);
    $('#stage').className = `stage theme-${e.target.value}${$('#palettePreset').value !== 'template' ? ' palette-custom' : ''}`;
    if ($('#palettePreset').value === 'template') applyPaletteToEditor();
    save()
});
$('#accent').addEventListener('input', e => {
    document.documentElement.style.setProperty('--accent', e.target.value);
    if ($('#palettePreset').value !== 'template') $('#paletteHeading').value = $('#paletteHeading').value || e.target.value;
    save()
});
function applyPalettePreset(name) {
    if (name === 'template') { applyPaletteToEditor(); return save() }
    const preset = palettePresets[name];
    if (preset) {
        $('#paletteBackground').value=preset.background; $('#paletteSurface').value=preset.surface; $('#paletteText').value=preset.text; $('#paletteHeading').value=preset.heading; $('#accent').value=preset.accent;
        document.documentElement.style.setProperty('--accent',preset.accent)
    }
    state.palettePreset = name; state.palette = { background:$('#paletteBackground').value, surface:$('#paletteSurface').value, text:$('#paletteText').value, heading:$('#paletteHeading').value }; state.accent=$('#accent').value;
    applyPaletteToEditor(); save()
}
$('#palettePreset').onchange = e => applyPalettePreset(e.target.value);
['paletteBackground','paletteSurface','paletteText','paletteHeading'].forEach(id => $('#'+id).oninput = () => { $('#palettePreset').value='custom'; state.palettePreset='custom'; state.palette={background:$('#paletteBackground').value,surface:$('#paletteSurface').value,text:$('#paletteText').value,heading:$('#paletteHeading').value}; applyPaletteToEditor(); save() });
$('#galleryStyle').value = state.galleryStyle || 'grid';
$('#galleryStyle').addEventListener('change', save);

function orderedPhotos(documentData = state) {
    const objects = documentData?.objects || {};
    const photos = Object.entries(objects).filter(([, o]) => o.type === 'image' && o.src && o.showInGallery !== false);
    const order = Array.isArray(documentData?.galleryOrder) ? documentData.galleryOrder : [];
    return photos.sort(([aId, a], [bId, b]) => {
        const ai = order.indexOf(aId), bi = order.indexOf(bId);
        if (ai >= 0 || bi >= 0) return (ai < 0 ? 9999 : ai) - (bi < 0 ? 9999 : bi);
        return Number(a.zIndex || 0) - Number(b.zIndex || 0)
    }).map(([id, photo]) => ({ id, ...photo }))
}

function animationName(preset) {
    const animations = {
        'fade-up': 'fadeUp',
        'soft-zoom': 'softZoom',
        'slide-left': 'slideLeft',
        'blur-in': 'blurIn',
        'bounce-in': 'bounceIn',
        'flip-in': 'flipIn',
        float: 'float',
        none: ''
    };
    return Object.prototype.hasOwnProperty.call(animations, preset) ? animations[preset] : 'fadeUp'
}

function renderEditorManagers() {
    renderLayers();
    renderGalleryManager();
    renderCustomBlocksManager();
    renderRsvpFieldsManager();
    renderSavedBlockTemplates();
    renderDesignPagesManager();
    renderPageNavigator();
    renderSavedPageTemplates();
    renderSectionAnimationsManager();
    renderSectionStylesManager();
    updateCanvasContextUI()
}

function renderSectionAnimationsManager() {
    const panel = $('#sectionAnimationsManager');
    if (!panel) return;
    const labels = {
        hero: 'Artistic hero', gallery: 'Gallery', video: 'Featured video', countdown: 'Countdown',
        schedule: 'Schedule', custom: 'Custom blocks', venue: 'Venue',
        contact: 'Contact', wishes: 'Guest wishes', rsvp: 'RSVP'
    };
    panel.innerHTML = '';
    Object.entries(labels).forEach(([name, label]) => {
        const value = state.sectionAnimations?.[name] || initial.sectionAnimations[name];
        const row = document.createElement('div');
        row.className = 'section-animation-row';
        row.dataset.sectionAnimation = name;
        row.innerHTML = `<strong>${label}</strong><select>
            <option value="fade-up">Fade up</option><option value="soft-zoom">Soft zoom</option>
            <option value="slide-left">Slide left</option><option value="blur-in">Blur reveal</option>
            <option value="bounce-in">Elegant bounce</option><option value="flip-in">Card flip</option>
            <option value="float">Gentle float</option><option value="none">None</option>
        </select><label>Duration <input type="range" min="300" max="3000" step="100"></label>`;
        row.querySelector('select').value = value.preset || 'fade-up';
        row.querySelector('input').value = value.duration || 900;
        row.querySelector('select').onchange = save;
        row.querySelector('input').oninput = save;
        panel.append(row)
    })
}

function renderSectionStylesManager() {
    const panel = $('#sectionStylesManager');
    if (!panel) return;
    const labels = { gallery:'Gallery', video:'Featured video', countdown:'Countdown', schedule:'Schedule', custom:'Custom blocks', venue:'Venue', contact:'Contact', wishes:'Guest wishes', rsvp:'RSVP' };
    panel.innerHTML = '';
    Object.entries(labels).forEach(([name,label]) => {
        const value = state.sectionStyles?.[name] || initial.sectionStyles[name];
        const row = document.createElement('div');
        row.className = 'section-style-row';
        row.dataset.sectionStyle = name;
        row.innerHTML = `<strong>${label}</strong>
          <label class="toggle-row compact"><span>Background</span><input data-style-background-enabled type="checkbox" ${value.backgroundEnabled?'checked':''}></label>
          <input data-style-background type="color" value="${value.background||'#ffffff'}" aria-label="${label} background color">
          <label class="toggle-row compact"><span>Text color</span><input data-style-text-enabled type="checkbox" ${value.textColorEnabled?'checked':''}></label>
          <input data-style-text type="color" value="${value.textColor||'#342c26'}" aria-label="${label} text color">
          <label>Corner radius <span>${Number(value.radius||0)}px</span><input data-style-radius type="range" min="0" max="60" step="1" value="${Number(value.radius||0)}"></label>
          <label class="toggle-row compact section-image-toggle"><span>Background image</span><input data-style-image-enabled type="checkbox" ${value.backgroundImageEnabled?'checked':''}></label>
          <input data-style-image type="text" value="${safeHtml(value.backgroundImage||'')}" placeholder="Image URL or uploaded asset URL" aria-label="${label} background image">
          <div class="mini-actions section-image-actions"><button type="button" data-pick-section-image>Choose material</button><button type="button" data-use-selected-image>Use selected image</button><button type="button" data-clear-section-image>Clear</button></div>
          <label>Image fit<select data-style-image-size><option value="cover">Cover</option><option value="contain">Contain</option></select></label>
          <label>Dark overlay <span data-overlay-value>${Number(value.backgroundOverlay||0)}%</span><input data-style-overlay type="range" min="0" max="80" step="1" value="${Number(value.backgroundOverlay||0)}"></label>`;
        row.querySelector('[data-style-image-size]').value = value.backgroundSize || 'cover';
        row.querySelectorAll('input,select').forEach(input => input.addEventListener('input', () => {
          const radiusSpan=row.querySelector('label:has([data-style-radius]) span'); if(radiusSpan) radiusSpan.textContent=`${row.querySelector('[data-style-radius]').value}px`;
          const overlaySpan=row.querySelector('[data-overlay-value]'); if(overlaySpan) overlaySpan.textContent=`${row.querySelector('[data-style-overlay]').value}%`; save()
        }));
        row.querySelector('[data-pick-section-image]').onclick = () => openMaterialPicker(`${label} background`, url => { row.querySelector('[data-style-image]').value=url; row.querySelector('[data-style-image-enabled]').checked=true; save() });
        row.querySelector('[data-use-selected-image]').onclick = () => {
          const imageObject = selected?.dataset.objectType === 'image' ? selected : currentSelection().find(item => item.dataset.objectType === 'image');
          const src = imageObject?.querySelector('img')?.src;
          if (!src) return alert('Select an image object first.');
          row.querySelector('[data-style-image]').value = src; row.querySelector('[data-style-image-enabled]').checked = true; save()
        };
        row.querySelector('[data-clear-section-image]').onclick = () => { row.querySelector('[data-style-image]').value=''; row.querySelector('[data-style-image-enabled]').checked=false; save() };
        panel.append(row)
    })
}

function renderLayers() {
    const panel = $('#layersPanel');
    if (!panel) return;
    const objects = $$('.object').slice().sort((a, b) => Number(b.style.zIndex || 0) - Number(a.style.zIndex || 0));
    const previousQuery = panel.querySelector('[data-layer-search]')?.value || '';
    panel.innerHTML = `<div class="layer-tools"><input data-layer-search type="search" placeholder="Search layers…" value="${safeHtml(previousQuery)}"><button type="button" data-layer-select-all title="Select all layers">All</button></div><div class="layer-list"></div>`;
    const list=panel.querySelector('.layer-list'),search=panel.querySelector('[data-layer-search]');
    const renderRows=()=>{
        const q=(search.value||'').trim().toLowerCase();list.innerHTML='';
        objects.filter(o=>{const label=(o.dataset.layerName||o.querySelector('.content')?.textContent||o.dataset.caption||o.dataset.id||'').toLowerCase();return !q||label.includes(q)||(o.dataset.objectType||'').includes(q)}).forEach(o => {
            const row = document.createElement('div');
            row.className = `layer-row${selectedObjects.has(o) ? ' active' : ''}`;
            row.dataset.layerId=o.dataset.id;
            const typeMap = { image:'Image', text:'Text', shape:'Shape', decoration:'Decoration' };
            const type = typeMap[o.dataset.objectType] || (o.classList.contains('image-object') ? 'Image' : 'Text');
            const defaultLabel = o.querySelector('.content')?.textContent?.trim().slice(0, 28) || o.dataset.caption || o.dataset.id;
            const label=o.dataset.layerName||defaultLabel||type;
            row.innerHTML = `<button type="button" class="layer-eye" aria-label="${o.dataset.visible==='false'?'Show':'Hide'} layer">${o.dataset.visible==='false'?'○':'◉'}</button><button type="button" class="layer-main"><span>${o.dataset.groupId ? '◫' : type === 'Image' ? '▧' : type === 'Shape' ? '□' : type === 'Decoration' ? '✦' : 'T'}</span><strong></strong></button><button type="button" class="layer-lock" aria-label="${o.dataset.locked==='true'?'Unlock':'Lock'} layer">${o.dataset.locked==='true'?'🔒':'◇'}</button>`;
            row.querySelector('strong').textContent = label;
            row.querySelector('.layer-main').onclick = event => select(o, event.shiftKey || event.ctrlKey || event.metaKey);
            row.querySelector('.layer-eye').onclick=()=>{o.dataset.visible=o.dataset.visible==='false'?'true':'false';applyObjectVisualStyle(o);save();renderLayers()};
            row.querySelector('.layer-lock').onclick=()=>{o.dataset.locked=o.dataset.locked==='true'?'false':'true';o.classList.toggle('locked',o.dataset.locked==='true');save();renderLayers()};
            row.querySelector('strong').ondblclick=async event=>{event.stopPropagation();const next=await uiPrompt('Choose a clear layer name:',o.dataset.layerName||defaultLabel||type,{title:'Rename layer',confirmText:'Rename'});if(next!=null){o.dataset.layerName=next.trim().slice(0,80);save();renderLayers()}};
            list.append(row)
        })
    };
    search.oninput=renderRows;panel.querySelector('[data-layer-select-all]').onclick=()=>setSelection(objects.filter(o=>o.dataset.visible!=='false'));
    renderRows()
}

function renderGalleryManager() {
    const panel = $('#galleryManager');
    if (!panel) return;
    const photos = orderedPhotos(capture());
    panel.innerHTML = '';
    if (!photos.length) {
        panel.innerHTML = '<p class="hint">Upload an image and click it in Materials to add it to the invitation.</p>';
        return
    }
    photos.forEach((photo, index) => {
        const row = document.createElement('div');
        row.className = 'gallery-item-editor';
        const img = document.createElement('img');
        img.src = photo.src;
        img.alt = photo.alt || `Gallery photo ${index + 1}`;
        const body = document.createElement('div');
        const caption = document.createElement('input');
        caption.placeholder = 'Optional caption';
        caption.value = photo.caption || '';
        caption.oninput = () => {
            const object = document.querySelector(`[data-id="${CSS.escape(photo.id)}"]`);
            if (object) object.dataset.caption = caption.value;
            save()
        };
        const alt = document.createElement('input');
        alt.placeholder = 'Accessible image description';
        alt.value = photo.alt || '';
        alt.oninput = () => {
            const object = document.querySelector(`[data-id="${CSS.escape(photo.id)}"]`);
            if (object) {
                object.dataset.alt = alt.value;
                const image = object.querySelector('img');
                if (image) image.alt = alt.value
            }
            save()
        };
        const controls = document.createElement('div');
        controls.className = 'mini-actions';
        const up = document.createElement('button'); up.type = 'button'; up.textContent = '↑'; up.title = 'Move earlier';
        const down = document.createElement('button'); down.type = 'button'; down.textContent = '↓'; down.title = 'Move later';
        const selectButton = document.createElement('button'); selectButton.type = 'button'; selectButton.textContent = 'Select';
        up.disabled = index === 0; down.disabled = index === photos.length - 1;
        up.onclick = () => moveGalleryItem(photo.id, -1);
        down.onclick = () => moveGalleryItem(photo.id, 1);
        selectButton.onclick = () => {
            const object = document.querySelector(`[data-id="${CSS.escape(photo.id)}"]`);
            if (object) select(object)
        };
        controls.append(up, down, selectButton);
        if (photo.id !== 'hero') {
            const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Remove'; remove.className = 'danger';
            remove.onclick = () => removeGalleryImage(photo.id);
            controls.append(remove)
        }
        body.append(caption, alt, controls); row.append(img, body); panel.append(row)
    })
}

function renderCustomBlocksManager() {
    const panel = $('#customBlocksManager');
    if (!panel) return;
    const blocks = state.customBlocks || [];
    panel.innerHTML = '';
    if (!blocks.length) {
        panel.innerHTML = '<p class="hint">No custom blocks yet. Add a story, dress code, important note, or custom section.</p>';
        return
    }
    blocks.forEach((block, index) => {
        const card = document.createElement('div');
        card.className = 'custom-block-editor';
        card.innerHTML = `<div class="custom-block-head"><strong>${safeHtml(customBlockLabel(block.type))}</strong><label class="inline-toggle"><input type="checkbox" ${block.enabled === false ? '' : 'checked'}> Show</label></div>`;
        const enabled = card.querySelector('input[type="checkbox"]');
        enabled.onchange = () => { block.enabled = enabled.checked; save() };
        const fields = [
            ['Heading — English','heading',false], ['Heading — Khmer','headingKm',true],
            ['Body — English','body',false], ['Body — Khmer','bodyKm',true]
        ];
        fields.forEach(([label,key,khmer],fieldIndex) => {
            const wrap = document.createElement('label'); wrap.textContent = label;
            const control = fieldIndex < 2 ? document.createElement('input') : document.createElement('textarea');
            control.value = block[key] || ''; if (khmer) control.classList.add('khmer-text');
            control.oninput = () => { block[key] = control.value; save() };
            wrap.append(control); card.append(wrap)
        });
        const actions = document.createElement('div'); actions.className = 'mini-actions';
        const up = document.createElement('button'), down = document.createElement('button'), duplicate = document.createElement('button'), saveTemplate = document.createElement('button'), remove = document.createElement('button');
        up.type = down.type = duplicate.type = saveTemplate.type = remove.type = 'button'; up.textContent = '↑ Earlier'; down.textContent = '↓ Later'; duplicate.textContent='Duplicate'; saveTemplate.textContent='Save template'; remove.textContent = 'Remove'; remove.className = 'danger';
        up.disabled = index === 0; down.disabled = index === blocks.length - 1;
        up.onclick = () => moveCustomBlock(block.id,-1); down.onclick = () => moveCustomBlock(block.id,1);
        duplicate.onclick=()=>{const copy=clone(block);copy.id='block-'+Date.now()+'-'+Math.random().toString(36).slice(2,5);const at=blocks.findIndex(x=>x.id===block.id);state.customBlocks=[...blocks.slice(0,at+1),copy,...blocks.slice(at+1)];save()};
        saveTemplate.onclick=()=>saveBlockTemplate(block);
        remove.onclick = async () => { if(await uiConfirm('Remove this custom section?',{title:'Remove custom section',danger:true,confirmText:'Remove'})) { state.customBlocks = blocks.filter(x => x.id !== block.id); save() } };
        actions.append(up,down,duplicate,saveTemplate,remove); card.append(actions); panel.append(card)
    })
}
function readBlockTemplates(){try{const data=JSON.parse(localStorage.getItem(savedBlockTemplatesKey)||'[]');return Array.isArray(data)?data:[]}catch{return[]}}
async function saveBlockTemplate(block){const name=await uiPrompt('Name this reusable content block:',block.heading||customBlockLabel(block.type),{title:'Save content block'});if(!name)return;try{if(serverInvite&&localStorage.getItem('sovan-auth-token')){const saved=await api('/api/components',{method:'POST',body:JSON.stringify({kind:'block',name:name.trim(),category:block.type||'custom',payload:clone(block)})});accountBlockTemplates.unshift(saved)}else{const templates=readBlockTemplates();templates.push({id:`content-template-${Date.now()}`,name:name.trim(),block:clone(block)});localStorage.setItem(savedBlockTemplatesKey,JSON.stringify(templates))}renderSavedBlockTemplates()}catch(error){alert(`The content block could not be saved: ${error.message}`)}}
function insertBlockTemplate(template){const block=clone(template.block||template.payload||{});block.id='block-'+Date.now()+'-'+Math.random().toString(36).slice(2,5);block.enabled=true;state.customBlocks=[...(state.customBlocks||[]),block];if(!(state.sectionOrder||[]).includes('custom'))state.sectionOrder=[...(state.sectionOrder||[]),'custom'];save()}
async function deleteBlockTemplate(template){if(!(await uiConfirm(`Delete saved content block “${template.name}”?`,{title:'Delete saved block',danger:true,confirmText:'Delete'})))return;try{if(template.remote){await api(`/api/components/${template.id}`,{method:'DELETE'});accountBlockTemplates=accountBlockTemplates.filter(x=>x.id!==template.id)}else{localStorage.setItem(savedBlockTemplatesKey,JSON.stringify(readBlockTemplates().filter(x=>x.id!==template.id)))}renderSavedBlockTemplates()}catch(error){alert(error.message)}}
function renderSavedBlockTemplates(){const panel=$('#savedBlockTemplates');if(!panel)return;const templates=[...accountBlockTemplates.map(x=>({...x,remote:true,block:x.payload})),...readBlockTemplates().map(x=>({...x,remote:false}))];panel.innerHTML=templates.length?'':'<p class="hint">No saved content blocks yet.</p>';templates.forEach(template=>{const row=document.createElement('div');row.className='saved-page-template-row';const title=document.createElement('strong');title.textContent=template.name;const badge=document.createElement('small');badge.textContent=template.remote?'Account':'This browser';const actions=document.createElement('div');actions.className='mini-actions';const insert=document.createElement('button'),remove=document.createElement('button');insert.type=remove.type='button';insert.textContent='Insert';remove.textContent='Delete';remove.className='danger';insert.onclick=()=>insertBlockTemplate(template);remove.onclick=()=>deleteBlockTemplate(template);actions.append(insert,remove);row.append(title,badge,actions);panel.append(row)})}

function renderRsvpFieldsManager(){
    const panel=$('#rsvpFieldsManager');if(!panel)return;const fields=state.rsvpFields||[];panel.innerHTML=fields.length?'':'<p class="hint">No custom RSVP questions. The standard attendance, guest count, and message fields remain available.</p>';
    fields.forEach((field,index)=>{const card=document.createElement('div');card.className='custom-block-editor rsvp-field-editor';card.innerHTML=`<div class="custom-block-head"><strong>Question ${index+1}</strong><label class="toggle-row"><span>Required</span><input type="checkbox" data-rsvp-required ${field.required?'checked':''}></label></div><label>Label — English<input data-rsvp-label maxlength="200"></label><label>Label — Khmer<input class="khmer-text" data-rsvp-label-km maxlength="200"></label><label>Answer type<select data-rsvp-type><option value="text">Short text</option><option value="textarea">Long text</option><option value="select">Choice list</option><option value="number">Number</option></select></label><label data-rsvp-options-wrap>Choices — comma separated<input data-rsvp-options placeholder="Standard, Vegetarian, Vegan"></label><div class="mini-actions"><button type="button" data-rsvp-up>↑ Earlier</button><button type="button" data-rsvp-down>↓ Later</button><button type="button" class="danger" data-rsvp-remove>Remove</button></div>`;card.querySelector('[data-rsvp-label]').value=field.label||'';card.querySelector('[data-rsvp-label-km]').value=field.labelKm||'';card.querySelector('[data-rsvp-type]').value=field.type||'text';card.querySelector('[data-rsvp-options]').value=(field.options||[]).join(', ');const toggleOptions=()=>card.querySelector('[data-rsvp-options-wrap]').hidden=card.querySelector('[data-rsvp-type]').value!=='select';toggleOptions();
        card.querySelector('[data-rsvp-label]').oninput=e=>{field.label=e.target.value;save()};card.querySelector('[data-rsvp-label-km]').oninput=e=>{field.labelKm=e.target.value;save()};card.querySelector('[data-rsvp-required]').onchange=e=>{field.required=e.target.checked;save()};card.querySelector('[data-rsvp-type]').onchange=e=>{field.type=e.target.value;toggleOptions();save()};card.querySelector('[data-rsvp-options]').oninput=e=>{field.options=e.target.value.split(',').map(x=>x.trim()).filter(Boolean).slice(0,30);save()};card.querySelector('[data-rsvp-up]').disabled=index===0;card.querySelector('[data-rsvp-down]').disabled=index===fields.length-1;card.querySelector('[data-rsvp-up]').onclick=()=>{[fields[index-1],fields[index]]=[fields[index],fields[index-1]];state.rsvpFields=fields;save()};card.querySelector('[data-rsvp-down]').onclick=()=>{[fields[index],fields[index+1]]=[fields[index+1],fields[index]];state.rsvpFields=fields;save()};card.querySelector('[data-rsvp-remove]').onclick=()=>{state.rsvpFields=fields.filter(x=>x.id!==field.id);save()};panel.append(card)})
}
function addRsvpField(){state.rsvpFields=[...(state.rsvpFields||[]),{id:`question-${Date.now()}-${Math.random().toString(36).slice(2,6)}`,label:'Additional question',labelKm:'',type:'text',required:false,options:[]}];save()}
$('#addRsvpField')?.addEventListener('click',addRsvpField);

function customBlockLabel(type) {
    return ({story:'Our Story','dress-code':'Dress Code',note:'Important Note',quote:'Quote',accommodation:'Accommodation',gift:'Gift Note',custom:'Custom Section'})[type] || 'Custom Section'
}
function addCustomBlock(type='custom') {
    const presets = {
        story: { heading:'Our Story', headingKm:'រឿងរ៉ាវរបស់យើង', body:'Share the story that brought you to this special day.', bodyKm:'ចែករំលែករឿងរ៉ាវដែលនាំអ្នកមកដល់ថ្ងៃដ៏ពិសេសនេះ។' },
        'dress-code': { heading:'Dress Code', headingKm:'ការស្លៀកពាក់', body:'We would be delighted to celebrate with you in elegant formal attire.', bodyKm:'យើងខ្ញុំនឹងរីករាយដែលបានអបអរសាទរជាមួយលោកអ្នកក្នុងសម្លៀកបំពាក់សមរម្យ និងស្រស់ស្អាត។' },
        note: { heading:'Important Note', headingKm:'សេចក្តីជូនដំណឹង', body:'Please add any important information your guests should know.', bodyKm:'សូមបន្ថែមព័ត៌មានសំខាន់ដែលភ្ញៀវគួរដឹង។' },
        quote: { heading:'A Special Thought', headingKm:'ពាក្យពេចន៍ដ៏ពិសេស', body:'Add a meaningful quote or message that reflects your celebration.', bodyKm:'បន្ថែមពាក្យពេចន៍ ឬសារដែលមានអត្ថន័យសម្រាប់កម្មវិធីរបស់អ្នក។' },
        accommodation: { heading:'Accommodation', headingKm:'កន្លែងស្នាក់នៅ', body:'Share hotel, transportation, or accommodation information for your guests.', bodyKm:'ចែករំលែកព័ត៌មានអំពីសណ្ឋាគារ ការធ្វើដំណើរ ឬកន្លែងស្នាក់នៅសម្រាប់ភ្ញៀវ។' },
        gift: { heading:'Gift Note', headingKm:'សារអំពីអំណោយ', body:'Add any thoughtful guidance about gifts, contributions, or your preferred arrangements.', bodyKm:'បន្ថែមការណែនាំអំពីអំណោយ ការចូលរួមចំណែក ឬការរៀបចំដែលអ្នកចង់បាន។' },
        custom: { heading:'Additional Information', headingKm:'ព័ត៌មានបន្ថែម', body:'Add your custom message here.', bodyKm:'បន្ថែមសាររបស់អ្នកនៅទីនេះ។' }
    };
    state.customBlocks = [...(state.customBlocks || []), { id:'block-'+Date.now(), type, enabled:true, ...(presets[type] || presets.custom) }];
    if (!(state.sectionOrder || []).includes('custom')) state.sectionOrder = [...(state.sectionOrder || []), 'custom'];
    save()
}
function moveCustomBlock(id,direction) {
    const blocks = state.customBlocks || [], index = blocks.findIndex(x => x.id === id), target = index + direction;
    if (index < 0 || target < 0 || target >= blocks.length) return;
    [blocks[index],blocks[target]] = [blocks[target],blocks[index]]; state.customBlocks = blocks; save()
}
function pageObject(type, options={}) {
    return {
        type, left: options.left || '12%', top: options.top || '20%', width: options.width || '76%', height: options.height || '100px',
        html: options.html || '', src: options.src || '', alt: options.alt || '', font: options.font || 'Georgia,serif', color: options.color || '#3d292f',
        fontSize: Number(options.fontSize || (type === 'text' ? 32 : 0)), textAlign: options.textAlign || 'center', fontWeight: options.fontWeight || '400',
        fontStyle: options.fontStyle || 'normal', letterSpacing: Number(options.letterSpacing || 0), lineHeight: Number(options.lineHeight || 1.35),
        fillColor: options.fillColor || '#d9a6ad', shapeKind: options.shapeKind || 'rectangle', opacity: options.opacity ?? 1,
        borderWidth: Number(options.borderWidth || 0), borderColor: options.borderColor || '#ffffff', borderRadius: Number(options.borderRadius || 0),
        shadowBlur: Number(options.shadowBlur || 0), shadowColor: options.shadowColor || '#000000', animation: options.animation || 'fade-up', duration: String(options.duration || 900),
        locked: false, rotation: Number(options.rotation || 0), imageFit: options.imageFit || 'cover', imagePositionX: Number(options.imagePositionX ?? 50), imagePositionY: Number(options.imagePositionY ?? 50),
        imageMask: options.imageMask || 'none', imageFrame: options.imageFrame || 'none', showInHero: false, showInGallery: false, groupId: '', zIndex: Number(options.zIndex || 1),
        backgroundEnabled: !!options.backgroundEnabled, backgroundColor: options.backgroundColor || '#ffffff', backgroundOpacity: Number(options.backgroundOpacity ?? 100), blendMode: options.blendMode || 'normal',
        fillMode: options.fillMode || 'solid', gradientStart: options.gradientStart || '#d9a6ad', gradientEnd: options.gradientEnd || '#9d4555', gradientAngle: Number(options.gradientAngle ?? 135),
        textGradientEnabled: !!options.textGradientEnabled, textGradientStart: options.textGradientStart || '#9d4555', textGradientEnd: options.textGradientEnd || '#b58a3a', textGradientAngle: Number(options.textGradientAngle ?? 90),
        textStrokeWidth: Number(options.textStrokeWidth || 0), textStrokeColor: options.textStrokeColor || '#ffffff', textShadowBlur: Number(options.textShadowBlur || 0), textShadowColor: options.textShadowColor || '#000000', textTransform: options.textTransform || 'none',
        animationDelay: Number(options.animationDelay || 0), caption: '', shapeKind: options.shapeKind || 'rectangle'
    }
}
function designPagePreset(type='title') {
    const pageId = `page-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
    const oid = suffix => `${pageId}-${suffix}`;
    const heroImage = state.objects?.hero?.src || document.querySelector('[data-id="hero"] img')?.src || '';
    const base = { id:pageId, preset:type, enabled:true, background:'#fffaf6', backgroundImage:'', backgroundSize:'cover', backgroundOverlay:0, useMasterBackground:true, animation:{preset:'fade-up',duration:900}, transition:{preset:'soft',duration:600}, objects:{} };
    if (type === 'photo') return { ...base, name:'Photo Feature', objects:{
        [oid('photo')]: pageObject('image',{src:heroImage,alt:'Featured invitation photo',left:'8%',top:'9%',width:'84%',height:'590px',imageMask:'arch',imageFrame:'white',shadowBlur:22,zIndex:1}),
        [oid('title')]: pageObject('text',{html:'A Beautiful Moment',left:'10%',top:'78%',width:'80%',height:'90px',fontSize:34,color:'#7f3f4c',zIndex:2})
    }};
    if (type === 'quote') return { ...base, name:'Quote Page', background:'#f7efe8', objects:{
        [oid('mark')]: pageObject('decoration',{html:'“',left:'36%',top:'16%',width:'28%',height:'120px',fontSize:92,color:'#b58a3a',zIndex:1}),
        [oid('quote')]: pageObject('text',{html:'The best journeys are the ones we take together.',left:'12%',top:'35%',width:'76%',height:'220px',fontSize:38,fontStyle:'italic',lineHeight:1.45,color:'#3d292f',zIndex:2}),
        [oid('line')]: pageObject('shape',{left:'28%',top:'72%',width:'44%',height:'3px',fillColor:'#b58a3a',shapeKind:'line',zIndex:1})
    }};
    if (type === 'story') return { ...base, name:'Our Story Page', objects:{
        [oid('title')]: pageObject('text',{html:'Our Story',left:'12%',top:'10%',width:'76%',height:'100px',fontSize:44,color:'#9d4555',zIndex:2}),
        [oid('body')]: pageObject('text',{html:'Share the moments, memories, and journey that brought you to this special celebration.',left:'14%',top:'31%',width:'72%',height:'260px',fontSize:23,lineHeight:1.65,color:'#4c3639',zIndex:2}),
        [oid('ornament')]: pageObject('decoration',{html:'❦',left:'39%',top:'68%',width:'22%',height:'100px',fontSize:58,color:'#b58a3a',zIndex:1})
    }};
    if (type === 'details') return { ...base, name:'Event Details Page', background:'#fff9ed', objects:{
        [oid('title')]: pageObject('text',{html:'Celebration Details',left:'10%',top:'11%',width:'80%',height:'100px',fontSize:42,color:'#8a6220',zIndex:2}),
        [oid('date')]: pageObject('text',{html:state.fields?.date || '27 December 2026',left:'16%',top:'34%',width:'68%',height:'90px',fontSize:30,color:'#4b3716',zIndex:2}),
        [oid('venue')]: pageObject('text',{html:state.fields?.venue || 'Your Event Venue',left:'12%',top:'50%',width:'76%',height:'140px',fontSize:25,lineHeight:1.5,color:'#4b3716',zIndex:2}),
        [oid('diamond')]: pageObject('decoration',{html:'◇',left:'40%',top:'70%',width:'20%',height:'100px',fontSize:54,color:'#a87616',zIndex:1})
    }};
    if (type === 'collage') return { ...base, name:'Photo Collage', background:'#fffdf9', objects:{
        [oid('title')]: pageObject('text',{html:'Captured Moments',left:'10%',top:'6%',width:'80%',height:'90px',fontSize:38,color:'#7f3f4c',zIndex:4}),
        [oid('photo1')]: pageObject('image',{src:heroImage,alt:'Invitation photo',left:'7%',top:'21%',width:'52%',height:'310px',imageFrame:'white',rotation:-4,shadowBlur:16,zIndex:1}),
        [oid('photo2')]: pageObject('image',{src:heroImage,alt:'Invitation photo',left:'43%',top:'42%',width:'50%',height:'300px',imageFrame:'white',rotation:5,shadowBlur:18,zIndex:2}),
        [oid('sparkle')]: pageObject('decoration',{html:'✦',left:'76%',top:'18%',width:'14%',height:'70px',fontSize:42,color:'#b58a3a',zIndex:5})
    }};
    if (type === 'split') return { ...base, name:'Split Feature', background:'#f9f3ee', objects:{
        [oid('photo')]: pageObject('image',{src:heroImage,alt:'Invitation feature photo',left:'0%',top:'0%',width:'52%',height:'844px',imageFit:'cover',zIndex:1}),
        [oid('title')]: pageObject('text',{html:'Our Next Chapter',left:'58%',top:'22%',width:'34%',height:'180px',fontSize:42,textAlign:'left',color:'#8e3f50',zIndex:3}),
        [oid('body')]: pageObject('text',{html:'A beautiful celebration begins with the people who make life meaningful.',left:'58%',top:'48%',width:'34%',height:'250px',fontSize:20,textAlign:'left',lineHeight:1.65,color:'#4c3639',zIndex:3})
    }};
    if (type === 'ceremony') return { ...base, name:'Ceremony Page', background:'#fff8e9', objects:{
        [oid('ornament')]: pageObject('decoration',{html:'◆ ◇ ◆',left:'25%',top:'10%',width:'50%',height:'70px',fontSize:28,color:'#a87616',zIndex:1}),
        [oid('title')]: pageObject('text',{html:'Ceremony',left:'12%',top:'23%',width:'76%',height:'110px',fontSize:46,color:'#8a6220',zIndex:2}),
        [oid('date')]: pageObject('text',{html:state.fields?.date || '27 December 2026',left:'15%',top:'43%',width:'70%',height:'90px',fontSize:29,color:'#4b3716',zIndex:2}),
        [oid('venue')]: pageObject('text',{html:state.fields?.venue || 'Your Event Venue',left:'12%',top:'58%',width:'76%',height:'170px',fontSize:24,lineHeight:1.55,color:'#4b3716',zIndex:2})
    }};
    if (type === 'thankyou') return { ...base, name:'Thank You Page', background:'#f8efeb', objects:{
        [oid('heart')]: pageObject('decoration',{html:'♡',left:'38%',top:'14%',width:'24%',height:'100px',fontSize:70,color:'#b58a3a',zIndex:1}),
        [oid('title')]: pageObject('text',{html:'Thank You',left:'10%',top:'36%',width:'80%',height:'110px',fontSize:50,color:'#8e3f50',zIndex:2}),
        [oid('body')]: pageObject('text',{html:'Your presence, love, and warm wishes mean more to us than words can say.',left:'15%',top:'55%',width:'70%',height:'190px',fontSize:23,lineHeight:1.6,color:'#5e444a',zIndex:2})
    }};
    return { ...base, name:'Title Page', objects:{
        [oid('ornament')]: pageObject('decoration',{html:'✦',left:'40%',top:'12%',width:'20%',height:'90px',fontSize:52,color:'#b58a3a',zIndex:1}),
        [oid('title')]: pageObject('text',{html:state.fields?.names || 'Your Celebration',left:'8%',top:'31%',width:'84%',height:'130px',fontSize:48,color:'#8e3f50',zIndex:2}),
        [oid('subtitle')]: pageObject('text',{html:'A day to remember',left:'15%',top:'54%',width:'70%',height:'100px',fontSize:24,fontStyle:'italic',color:'#5e444a',zIndex:2})
    }}
}
function designPageToken(id){ return `page:${id}` }
function designPageByCanvasId(canvasId=activeCanvasId){ return (state.designPages || []).find(page => designPageToken(page.id) === canvasId) }
function insertDesignPage(type='title', pageData=null) {
    const page = pageData ? clone(pageData) : designPagePreset(type);
    if (pageData) {
        const oldId = page.id; page.id = `page-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
        page.name = `${page.name || 'Saved Page'} Copy`;
        const remapped = {};
        Object.entries(page.objects || {}).forEach(([id,obj],index) => remapped[`${page.id}-object-${index}-${Math.random().toString(36).slice(2,5)}`] = clone(obj));
        page.objects = remapped
    }
    state.designPages = [...(state.designPages || []), page];
    const token = designPageToken(page.id), order = [...(state.sectionOrder || initial.sectionOrder)];
    const insertAt = Math.max(0, order.indexOf('venue'));
    if (insertAt >= 0) order.splice(insertAt,0,token); else order.push(token);
    state.sectionOrder = order;
    $('#sectionOrder').value = order.join('\n');
    save(); switchCanvas(token)
}
function switchCanvas(canvasId) {
    capture();
    if (canvasId !== 'hero' && !designPageByCanvasId(canvasId)) return;
    activeCanvasId = canvasId;
    selected = null; selectedObjects.clear();
    apply()
}
function updateCanvasContextUI() {
    const page = designPageByCanvasId();
    const label = $('#activeCanvasLabel'); if (label) label.textContent = page ? `Editing page: ${page.name}` : 'Main hero canvas';
    $('#editHeroCanvas')?.classList.toggle('active', activeCanvasId === 'hero');
    $$('#designPagesManager [data-edit-page]').forEach(button => button.classList.toggle('active', designPageToken(button.dataset.editPage) === activeCanvasId));
    const stage=$('#stage');
    const decor=stage?.querySelector('.decor'); if(decor) decor.style.display=page?'none':'';
    const heroToggle=$('#showInHero')?.closest('label'); if(heroToggle) heroToggle.hidden=!!page;
    const galleryToggle=$('#showInGallery')?.closest('label'); if(galleryToggle) galleryToggle.hidden=!!page;
    if(stage&&page){
        const master=state.masterPageStyle||initial.masterPageStyle, source=(page.useMasterBackground&&master.enabled)?master:page;
        const image=safeSectionImageUrl(source.backgroundImage),overlay=Math.max(0,Math.min(80,Number(source.backgroundOverlay||0)))/100;
        stage.style.backgroundColor=source.background||'#fffaf6';
        stage.style.backgroundImage=image?`linear-gradient(rgba(0,0,0,${overlay}),rgba(0,0,0,${overlay})),url("${image.replace(/"/g,'%22')}")`:'';
        stage.style.backgroundSize=source.backgroundSize==='contain'?'contain':'cover'; stage.style.backgroundPosition='center'; stage.style.backgroundRepeat='no-repeat'
    }else if(stage){
        stage.style.backgroundImage=''; stage.style.backgroundSize=''; stage.style.backgroundPosition=''; stage.style.backgroundRepeat=''; applyPaletteToEditor()
    }
}
function moveDesignPage(id,direction) {
    const token=designPageToken(id), order=[...(state.sectionOrder||[])], index=order.indexOf(token), target=index+direction;
    if(index<0||target<0||target>=order.length)return;
    [order[index],order[target]]=[order[target],order[index]]; state.sectionOrder=order; $('#sectionOrder').value=order.join('\n'); save()
}
function duplicateDesignPage(id) {
    const source=(state.designPages||[]).find(page=>page.id===id); if(!source)return;
    const copy=clone(source), oldToken=designPageToken(source.id), oldIndex=(state.sectionOrder||[]).indexOf(oldToken);
    copy.id=`page-${Date.now()}-${Math.random().toString(36).slice(2,7)}`; copy.name=`${source.name} Copy`;
    const objects={}; Object.entries(copy.objects||{}).forEach(([key,obj],index)=>objects[`${copy.id}-object-${index}-${Math.random().toString(36).slice(2,5)}`]=obj); copy.objects=objects;
    state.designPages=[...(state.designPages||[]),copy]; const order=[...(state.sectionOrder||[])]; order.splice(oldIndex>=0?oldIndex+1:order.length,0,designPageToken(copy.id)); state.sectionOrder=order; $('#sectionOrder').value=order.join('\n'); save()
}
async function removeDesignPage(id) {
    if(!(await uiConfirm('Remove this visual page from the invitation?',{title:'Remove visual page',danger:true,confirmText:'Remove'})))return;
    const token=designPageToken(id); state.designPages=(state.designPages||[]).filter(page=>page.id!==id); state.sectionOrder=(state.sectionOrder||[]).filter(item=>item!==token);
    if(activeCanvasId===token) activeCanvasId='hero'; $('#sectionOrder').value=state.sectionOrder.join('\n'); save(); apply()
}
async function savePageTemplate(id) {
    capture(); const page=(state.designPages||[]).find(item=>item.id===id); if(!page)return;
    const name=await uiPrompt('Name this reusable page template:',page.name,{title:'Save page template'}); if(!name)return;
    try{
        if(serverInvite&&localStorage.getItem('sovan-auth-token')){
            const saved=await api('/api/page-templates',{method:'POST',body:JSON.stringify({name:name.trim(),category:page.preset||'General',page:clone(page)})});accountPageTemplates.unshift(saved)
        }else{
            const templates=readPageTemplates(); templates.push({id:`template-${Date.now()}`,name:name.trim(),category:page.preset||'General',page:clone(page),localOnly:true}); localStorage.setItem(savedPageTemplatesKey,JSON.stringify(templates))
        }
        renderSavedPageTemplates()
    }catch(error){alert(`The page template could not be saved: ${error.message}`)}
}
function readPageTemplates(){try{const data=JSON.parse(localStorage.getItem(savedPageTemplatesKey)||'[]');return Array.isArray(data)?data:[]}catch{return[]}}
async function loadAccountPageTemplates(){
    if(serverInvite&&localStorage.getItem('sovan-auth-token')){try{accountPageTemplates=await api('/api/page-templates')}catch{accountPageTemplates=[]}}
    renderSavedPageTemplates()
}
async function deleteReusablePageTemplate(template){
    if(!(await uiConfirm(`Delete reusable page template “${template.name}”?`,{title:'Delete page template',danger:true,confirmText:'Delete'})))return;
    try{
        if(template.remote){await api(`/api/page-templates/${template.id}`,{method:'DELETE'});accountPageTemplates=accountPageTemplates.filter(x=>x.id!==template.id)}
        else{const locals=readPageTemplates().filter(x=>x.id!==template.id);localStorage.setItem(savedPageTemplatesKey,JSON.stringify(locals))}
        renderSavedPageTemplates()
    }catch(error){alert(error.message)}
}
function renderSavedPageTemplates(){
    const panel=$('#savedPageTemplates');if(!panel)return;
    const templates=[...accountPageTemplates.map(x=>({...x,remote:true})),...readPageTemplates().map(x=>({...x,remote:false}))];
    panel.innerHTML=templates.length?'':'<p class="hint">No reusable page templates saved yet.</p>';
    templates.forEach(template=>{const row=document.createElement('div');row.className='saved-page-template-row';const name=document.createElement('strong');name.textContent=template.name;const badge=document.createElement('small');badge.textContent=template.remote?'Account':'This browser';const actions=document.createElement('div');actions.className='mini-actions';const insert=document.createElement('button'),remove=document.createElement('button');insert.type=remove.type='button';insert.textContent='Insert';remove.textContent='Delete';remove.className='danger';insert.onclick=()=>insertDesignPage('custom',template.page);remove.onclick=()=>deleteReusablePageTemplate(template);actions.append(insert,remove);row.append(name,badge,actions);panel.append(row)})
}
function pageThumbnailObjects(page, root) {
    const objects=Object.entries(page?.objects||{}).sort(([,a],[,b])=>Number(a.zIndex||0)-Number(b.zIndex||0)).slice(0,24);
    objects.forEach(([,obj])=>{
        const el=document.createElement('span'); el.className=`page-thumb-object page-thumb-${obj.type||'text'}`;
        el.style.left=obj.left||'10%'; el.style.top=obj.top||'10%'; el.style.width=obj.width||'50%';
        const rawHeight=String(obj.height||'80px'); el.style.height=rawHeight.includes('%')?rawHeight:`${Math.max(2,parseFloat(rawHeight||80)/844*100)}%`;
        el.style.zIndex=String(obj.zIndex||1); el.style.transform=`rotate(${Number(obj.rotation||0)}deg)`;
        if(obj.type==='image'&&obj.src){el.style.backgroundImage=`url("${String(obj.src).replace(/"/g,'%22')}")`;el.style.backgroundSize='cover';el.style.backgroundPosition=`${Number(obj.imagePositionX??50)}% ${Number(obj.imagePositionY??50)}%`}
        else if(obj.type==='shape'){el.style.background=obj.fillColor||'#d9a6ad'; if(obj.shapeKind==='circle')el.style.borderRadius='999px'}
        else {el.textContent=String(obj.html||'').replace(/<[^>]+>/g,' ').slice(0,35);el.style.color=obj.color||'#5a4148';el.style.fontSize='5px';el.style.overflow='hidden';el.style.textAlign=obj.textAlign||'center'}
        root.append(el)
    })
}
function pageBackgroundSource(page){const master=state.masterPageStyle||initial.masterPageStyle;return page?.useMasterBackground&&master.enabled?master:page}
function renderPageNavigator(){
    const panel=$('#pageNavigator');if(!panel)return;panel.innerHTML='';
    const hero=document.createElement('button');hero.type='button';hero.className=`page-nav-card hero-card${activeCanvasId==='hero'?' active':''}`;hero.innerHTML='<div class="page-thumb hero-thumb"><span>MAIN</span></div><strong>Main hero</strong>';hero.onclick=()=>switchCanvas('hero');panel.append(hero);
    (state.designPages||[]).forEach(page=>{
        const card=document.createElement('div');card.className=`page-nav-card${designPageToken(page.id)===activeCanvasId?' active':''}${page.enabled===false?' disabled':''}`;card.draggable=true;card.dataset.pageId=page.id;
        const thumb=document.createElement('button');thumb.type='button';thumb.className='page-thumb';const source=pageBackgroundSource(page)||{};thumb.style.backgroundColor=source.background||'#fffaf6';const image=safeSectionImageUrl(source.backgroundImage);if(image){thumb.style.backgroundImage=`linear-gradient(rgba(0,0,0,${Number(source.backgroundOverlay||0)/100}),rgba(0,0,0,${Number(source.backgroundOverlay||0)/100})),url("${image.replace(/"/g,'%22')}")`;thumb.style.backgroundSize=source.backgroundSize==='contain'?'contain':'cover'}pageThumbnailObjects(page,thumb);thumb.onclick=()=>switchCanvas(designPageToken(page.id));
        const label=document.createElement('strong');label.textContent=page.name||'Visual Page';card.append(thumb,label);
        card.addEventListener('dragstart',e=>{card.classList.add('dragging');e.dataTransfer.setData('text/plain',page.id);e.dataTransfer.effectAllowed='move'});card.addEventListener('dragend',()=>card.classList.remove('dragging'));
        card.addEventListener('dragover',e=>{e.preventDefault();card.classList.add('drag-over')});card.addEventListener('dragleave',()=>card.classList.remove('drag-over'));
        card.addEventListener('drop',e=>{e.preventDefault();card.classList.remove('drag-over');const moving=e.dataTransfer.getData('text/plain');if(moving&&moving!==page.id)reorderVisualPages(moving,page.id)});
        panel.append(card)
    })
}
function reorderVisualPages(movingId,targetId){
    capture();const pages=[...(state.designPages||[])],from=pages.findIndex(p=>p.id===movingId),to=pages.findIndex(p=>p.id===targetId);if(from<0||to<0)return;const [moved]=pages.splice(from,1);pages.splice(to,0,moved);state.designPages=pages;
    const reorderedTokens=pages.map(p=>designPageToken(p.id));let cursor=0;state.sectionOrder=(state.sectionOrder||[]).map(token=>String(token).startsWith('page:')?reorderedTokens[cursor++]:token);$('#sectionOrder').value=state.sectionOrder.join('\n');save()
}
function selectedObjectData(){capture();const source=activeCanvasId==='hero'?(state.objects||{}):(designPageByCanvasId()?.objects||{});return currentSelection().map(item=>({id:item.dataset.id,data:clone(source[item.dataset.id]||{})})).filter(x=>x.data&&Object.keys(x.data).length)}
function copySelectionToClipboard(){const items=selectedObjectData();if(!items.length)return alert('Select one or more objects to copy.');localStorage.setItem(objectClipboardKey,JSON.stringify({copiedAt:Date.now(),items}));$('#pasteObjects').disabled=false}
function offsetDimension(value,delta){const text=String(value||'0');const number=parseFloat(text)||0;return text.includes('%')?`${Math.max(0,Math.min(95,number+delta))}%`:`${number+Math.round(delta*3.9)}px`}
function pasteObjectsFromClipboard(){let payload;try{payload=JSON.parse(localStorage.getItem(objectClipboardKey)||'null')}catch{}if(!payload?.items?.length)return alert('Nothing has been copied yet.');capture();const groupMap=new Map(),created=[];payload.items.forEach((entry,index)=>{const data=clone(entry.data||{}),id=`pasted-${Date.now()}-${index}-${Math.random().toString(36).slice(2,6)}`;if(data.groupId){if(!groupMap.has(data.groupId))groupMap.set(data.groupId,`group-${Date.now()}-${groupMap.size}`);data.groupId=groupMap.get(data.groupId)}const object=createObject(id,data.type||'text');hydrateObjectFromData(object,data);object.style.left=offsetDimension(data.left,3);object.style.top=offsetDimension(data.top,3);object.style.width=data.width||'40%';object.style.height=data.height||'100px';object.style.zIndex=String(nextZIndex()+index);$('#stage').append(object);created.push(object)});setSelection(created);save()}

function renderDesignPagesManager() {
    const panel=$('#designPagesManager'); if(!panel)return; const pages=state.designPages||[]; panel.innerHTML='';
    if(!pages.length){panel.innerHTML='<p class="hint">No visual pages yet. Add one from the library above.</p>';return}
    pages.forEach(page=>{
        const card=document.createElement('details'); card.className='design-page-editor'; card.open=designPageToken(page.id)===activeCanvasId;
        card.innerHTML=`<summary><strong></strong><span>${page.enabled===false?'Hidden':'Published'}</span></summary>
          <label>Page name<input data-page-name maxlength="120"></label>
          <label class="toggle-row"><span>Show this page</span><input data-page-enabled type="checkbox"></label>
          <label class="toggle-row"><span>Use master background</span><input data-page-use-master type="checkbox"></label>
          <label>Background color<input data-page-background type="color"></label>
          <label>Background image URL<input data-page-image type="text" placeholder="Image URL or uploaded asset URL"></label>
          <div class="mini-actions"><button type="button" data-page-pick-image>Choose material</button><button type="button" data-page-use-selected>Use selected image</button><button type="button" data-page-clear-image>Clear image</button></div>
          <label>Background fit<select data-page-size><option value="cover">Cover</option><option value="contain">Contain</option></select></label>
          <label>Dark overlay <span data-page-overlay-value></span><input data-page-overlay type="range" min="0" max="80" step="1"></label>
          <label>Entrance animation<select data-page-animation><option value="fade-up">Fade up</option><option value="soft-zoom">Soft zoom</option><option value="slide-left">Slide left</option><option value="blur-in">Blur reveal</option><option value="bounce-in">Elegant bounce</option><option value="flip-in">Card flip</option><option value="float">Gentle float</option><option value="none">None</option></select></label>
          <label>Duration <input data-page-duration type="range" min="300" max="3000" step="100"></label>
          <label>Transition to this page<select data-page-transition><option value="soft">Soft fade edge</option><option value="overlap">Layered overlap</option><option value="sweep">Diagonal sweep</option><option value="none">No transition</option></select></label>
          <label>Transition duration <input data-page-transition-duration type="range" min="200" max="2000" step="100"></label>
          <div class="page-editor-actions"><button type="button" data-edit-page>Open canvas</button><button type="button" data-duplicate-page>Duplicate</button><button type="button" data-save-template>Save template</button></div>
          <div class="mini-actions"><button type="button" data-page-earlier>↑ Earlier</button><button type="button" data-page-later>↓ Later</button><button type="button" class="danger" data-remove-page>Remove</button></div>`;
        card.querySelector('summary strong').textContent=page.name; card.querySelector('[data-page-name]').value=page.name; card.querySelector('[data-page-enabled]').checked=page.enabled!==false; card.querySelector('[data-page-use-master]').checked=page.useMasterBackground===true; card.querySelector('[data-page-background]').value=page.background||'#fffaf6'; card.querySelector('[data-page-image]').value=page.backgroundImage||''; card.querySelector('[data-page-size]').value=page.backgroundSize||'cover'; card.querySelector('[data-page-overlay]').value=page.backgroundOverlay||0; card.querySelector('[data-page-overlay-value]').textContent=`${page.backgroundOverlay||0}%`; card.querySelector('[data-page-animation]').value=page.animation?.preset||'fade-up'; card.querySelector('[data-page-duration]').value=page.animation?.duration||900; card.querySelector('[data-page-transition]').value=page.transition?.preset||'soft'; card.querySelector('[data-page-transition-duration]').value=page.transition?.duration||600; card.querySelector('[data-edit-page]').dataset.editPage=page.id;
        const commit=()=>{page.name=card.querySelector('[data-page-name]').value.trim()||'Visual Page';page.enabled=card.querySelector('[data-page-enabled]').checked;page.useMasterBackground=card.querySelector('[data-page-use-master]').checked;page.background=card.querySelector('[data-page-background]').value;page.backgroundImage=card.querySelector('[data-page-image]').value.trim();page.backgroundSize=card.querySelector('[data-page-size]').value;page.backgroundOverlay=Number(card.querySelector('[data-page-overlay]').value||0);page.animation={preset:card.querySelector('[data-page-animation]').value,duration:Number(card.querySelector('[data-page-duration]').value||900)};page.transition={preset:card.querySelector('[data-page-transition]').value,duration:Number(card.querySelector('[data-page-transition-duration]').value||600)};card.querySelector('[data-page-overlay-value]').textContent=`${page.backgroundOverlay}%`;save()};
        card.querySelectorAll('input,select').forEach(control=>control.addEventListener('input',commit));
        card.querySelector('[data-edit-page]').onclick=()=>switchCanvas(designPageToken(page.id)); card.querySelector('[data-duplicate-page]').onclick=()=>duplicateDesignPage(page.id); card.querySelector('[data-save-template]').onclick=()=>savePageTemplate(page.id); card.querySelector('[data-page-earlier]').onclick=()=>moveDesignPage(page.id,-1); card.querySelector('[data-page-later]').onclick=()=>moveDesignPage(page.id,1); card.querySelector('[data-remove-page]').onclick=()=>removeDesignPage(page.id);
        card.querySelector('[data-page-pick-image]').onclick=()=>openMaterialPicker(`${page.name} background`,url=>{card.querySelector('[data-page-image]').value=url;commit()});
        card.querySelector('[data-page-use-selected]').onclick=()=>{const imageObject=selected?.dataset.objectType==='image'?selected:currentSelection().find(item=>item.dataset.objectType==='image');const src=imageObject?.querySelector('img')?.src;if(!src)return alert('Select an image object first.');card.querySelector('[data-page-image]').value=src;commit()};card.querySelector('[data-page-clear-image]').onclick=()=>{card.querySelector('[data-page-image]').value='';commit()}; panel.append(card)
    }); updateCanvasContextUI()
}

function moveGalleryItem(id, direction) {
    capture();
    const order = state.galleryOrder || [];
    const index = order.indexOf(id), target = index + direction;
    if (index < 0 || target < 0 || target >= order.length) return;
    [order[index], order[target]] = [order[target], order[index]];
    state.galleryOrder = order;
    save()
}

async function removeGalleryImage(id) {
    const object = document.querySelector(`[data-id="${CSS.escape(id)}"]`);
    if (!object || id === 'hero') return;
    if (!(await uiConfirm('Remove this photo from the invitation? The original material remains in your library.',{title:'Remove photo',danger:true,confirmText:'Remove'}))) return;
    object.remove();
    state.galleryOrder = (state.galleryOrder || []).filter(x => x !== id);
    if (selected === object) {
        selected = null;
        $('#properties').hidden = true;
        $('#noSelection').hidden = false
    }
    save()
}

function clearSnapGuides() {
    $$('.snap-guide').forEach(g => g.remove())
}
function showSnapGuide(axis, percent) {
    const stage = $('#stage');
    let guide = stage.querySelector(`.snap-guide.${axis}`);
    if (!guide) {
        guide = document.createElement('div');
        guide.className = `snap-guide ${axis}`;
        stage.append(guide)
    }
    if (axis === 'vertical') guide.style.left = `${percent}%`;
    else guide.style.top = `${percent}%`
}

function currentSelection() {
    return [...selectedObjects].filter(o => o?.isConnected)
}

function clearSelection() {
    $$('.object').forEach(x => x.classList.remove('selected', 'multi-selected'));
    selectedObjects.clear();
    selected = null;
    $('#properties').hidden = true;
    $('#noSelection').hidden = false;
    $('#selectionBounds')?.remove();
    renderLayers()
}

function ensureObjectHandles(o) {
    const resize = o.querySelector('i');
    if (resize) resize.classList.add('resize-handle');
    if (!o.querySelector('.rotate-handle')) {
        const handle = document.createElement('span');
        handle.className = 'rotate-handle';
        handle.title = 'Drag to rotate';
        o.append(handle)
    }
}

function applyObjectVisualStyle(o) {
    if (!o) return;
    const opacity = Math.max(.1, Math.min(1, Number(o.dataset.opacity ?? 1)));
    const borderWidth = Math.max(0, Math.min(12, Number(o.dataset.borderWidth || 0)));
    const borderRadius = Math.max(0, Math.min(120, Number(o.dataset.borderRadius || 0)));
    const shadowBlur = Math.max(0, Math.min(60, Number(o.dataset.shadowBlur || 0)));
    const borderColor = o.dataset.borderColor || '#ffffff';
    const shadowColor = o.dataset.shadowColor || '#000000';
    o.style.display = o.dataset.visible === 'false' ? 'none' : '';
    o.style.opacity = String(opacity);
    o.style.mixBlendMode = o.dataset.blendMode || 'normal';
    o.style.setProperty('--object-border-width', `${borderWidth}px`);
    o.style.setProperty('--object-border-color', borderColor);
    o.style.setProperty('--object-radius', `${borderRadius}px`);
    o.style.setProperty('--object-shadow', shadowBlur ? `0 ${Math.max(2, Math.round(shadowBlur/3))}px ${shadowBlur}px ${shadowColor}55` : 'none');
    if (o.dataset.backgroundEnabled === 'true') {
        const bg = o.dataset.backgroundColor || '#ffffff';
        const alpha = Math.max(0, Math.min(100, Number(o.dataset.backgroundOpacity ?? 100))) / 100;
        const hex = bg.replace('#','');
        const rgb = /^[0-9a-f]{6}$/i.test(hex) ? `${parseInt(hex.slice(0,2),16)},${parseInt(hex.slice(2,4),16)},${parseInt(hex.slice(4,6),16)}` : '255,255,255';
        o.style.background = `rgba(${rgb},${alpha})`;
    } else o.style.background = '';
    const content = o.querySelector('.content');
    if (content) {
        const align = o.dataset.textAlign || 'center';
        content.style.fontFamily = o.dataset.font || '';
        content.style.color = o.dataset.color || '';
        content.style.fontSize = Number(o.dataset.fontSize || 0) ? `${Number(o.dataset.fontSize)}px` : '';
        content.style.textAlign = align;
        content.style.justifyContent = align === 'left' ? 'flex-start' : align === 'right' ? 'flex-end' : 'center';
        const vertical = o.dataset.textVerticalAlign || 'middle';
        content.style.alignItems = vertical === 'top' ? 'flex-start' : vertical === 'bottom' ? 'flex-end' : 'center';
        content.style.padding = `${Math.max(0, Math.min(64, Number(o.dataset.textPadding ?? 8)))}px`;
        content.style.fontWeight = o.dataset.fontWeight || '400';
        content.style.fontStyle = o.dataset.fontStyle || 'normal';
        content.style.letterSpacing = `${Number(o.dataset.letterSpacing || 0)}px`;
        content.style.lineHeight = String(Number(o.dataset.lineHeight || 1.35));
        content.style.textTransform = o.dataset.textTransform || 'none';
        content.style.webkitTextStroke = `${Math.max(0, Number(o.dataset.textStrokeWidth || 0))}px ${o.dataset.textStrokeColor || '#ffffff'}`;
        const textShadowBlur = Math.max(0, Number(o.dataset.textShadowBlur || 0));
        content.style.textShadow = textShadowBlur ? `0 ${Math.max(1, Math.round(textShadowBlur/4))}px ${textShadowBlur}px ${o.dataset.textShadowColor || '#000000'}` : 'none';
        if (o.dataset.textGradientEnabled === 'true') {
            content.style.backgroundImage = `linear-gradient(${Number(o.dataset.textGradientAngle || 90)}deg, ${o.dataset.textGradientStart || '#9d4555'}, ${o.dataset.textGradientEnd || '#b58a3a'})`;
            content.style.webkitBackgroundClip = 'text'; content.style.backgroundClip = 'text'; content.style.color = 'transparent';
        } else {
            content.style.backgroundImage = ''; content.style.webkitBackgroundClip = ''; content.style.backgroundClip = ''; content.style.color = o.dataset.color || '';
        }
    }
    const image = o.querySelector('img');
    if (image) {
        const masks = { none:'none', circle:'ellipse(50% 50% at 50% 50%)', arch:'inset(0 round 48% 48% 12% 12%)', diamond:'polygon(50% 0,100% 50%,50% 100%,0 50%)', hexagon:'polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)', blob:'polygon(50% 0,78% 8%,96% 35%,91% 72%,66% 100%,31% 94%,6% 68%,0 32%,22% 7%)' };
        const frames = { none:['0','transparent'], white:['8px','#ffffff'], gold:['8px','#c79b42'], dark:['8px','#201b1b'] };
        const frame = frames[o.dataset.imageFrame || 'none'] || frames.none;
        image.style.clipPath = masks[o.dataset.imageMask || 'none'] || 'none';
        image.style.padding = frame[0];
        image.style.background = frame[1];
        image.style.boxSizing = 'border-box';
        image.style.filter = imageFilterStyle(o.dataset);
        image.style.transform = `scaleX(${o.dataset.imageFlipX==='true'?-1:1}) scaleY(${o.dataset.imageFlipY==='true'?-1:1})`
    }
    const surface = o.querySelector('.shape-surface');
    if (surface) {
        const kind = o.dataset.shapeKind || 'rectangle';
        surface.style.background = o.dataset.fillMode === 'gradient' ? `linear-gradient(${Number(o.dataset.gradientAngle || 135)}deg, ${o.dataset.gradientStart || '#d9a6ad'}, ${o.dataset.gradientEnd || '#9d4555'})` : (o.dataset.fillColor || '#d9a6ad');
        surface.style.borderRadius = kind === 'circle' ? '999px' : 'inherit';
        surface.className = `shape-surface shape-${kind}`
    }
}

function updateSelectionBounds() {
    const stage = $('#stage');
    let bounds = $('#selectionBounds');
    const items = currentSelection();
    if (!items.length || !stage) {
        bounds?.remove();
        return
    }
    if (!bounds) {
        bounds = document.createElement('div');
        bounds.id = 'selectionBounds';
        bounds.className = 'selection-bounds';
        bounds.innerHTML = '<span></span>';
        stage.append(bounds)
    }
    const sr = stage.getBoundingClientRect();
    const rects = items.map(item => item.getBoundingClientRect());
    const left = Math.min(...rects.map(r => r.left));
    const top = Math.min(...rects.map(r => r.top));
    const right = Math.max(...rects.map(r => r.right));
    const bottom = Math.max(...rects.map(r => r.bottom));
    bounds.style.left = `${(left - sr.left) / sr.width * 100}%`;
    bounds.style.top = `${(top - sr.top) / sr.height * 100}%`;
    bounds.style.width = `${(right - left) / sr.width * 100}%`;
    bounds.style.height = `${(bottom - top) / sr.height * 100}%`;
    const groupIds = new Set(items.map(item => item.dataset.groupId).filter(Boolean));
    bounds.querySelector('span').textContent = groupIds.size === 1 && items.every(item => item.dataset.groupId) ? `Group · ${items.length}` : items.length > 1 ? `${items.length} selected` : '';
    bounds.hidden = items.length === 1 && !items[0].dataset.groupId
}

function wireObject(o) {
    if (!o.dataset.objectType) o.dataset.objectType = o.classList.contains('image-object') ? 'image' : o.classList.contains('shape-object') ? 'shape' : o.classList.contains('decoration-object') ? 'decoration' : 'text';
    ensureObjectHandles(o);
    applyObjectVisualStyle(o);
    o.addEventListener('pointerdown', e => {
        const additive = e.shiftKey || e.ctrlKey || e.metaKey;
        select(o, additive);
        if (o.dataset.locked === 'true') return;
        const rotate = e.target.classList?.contains('rotate-handle');
        const resize = e.target.classList?.contains('resize-handle') || e.target.tagName === 'I';
        const sx = e.clientX, sy = e.clientY;
        const r = o.getBoundingClientRect(), p = $('#stage').getBoundingClientRect();

        let targets = (resize || rotate) ? currentSelection() : currentSelection();
        if (!targets.includes(o)) targets = [o];
        if (o.dataset.groupId) {
            const grouped = $$('.object').filter(item => item.dataset.groupId === o.dataset.groupId);
            targets = [...new Set([...targets, ...grouped])]
        }
        const startFrames = new Map(targets.map(item => [item, {
            left: parseFloat(item.style.left) || ((item.getBoundingClientRect().left - p.left) / p.width * 100),
            top: parseFloat(item.style.top) || ((item.getBoundingClientRect().top - p.top) / p.height * 100),
            rotation: Number(item.dataset.rotation || 0)
        }]));
        const centerX = r.left + r.width / 2, centerY = r.top + r.height / 2;
        const startAngle = Math.atan2(sy - centerY, sx - centerX) * 180 / Math.PI;

        o.setPointerCapture(e.pointerId);
        clearSnapGuides();
        const snap = (value, points, threshold = 1.4) => {
            const hit = points.find(point => Math.abs(value - point.value) <= threshold);
            if (hit) showSnapGuide(hit.axis, hit.guide);
            return hit?.value ?? value
        };
        const otherRects = $$('.object').filter(item => !targets.includes(item)).map(item => {
            const rect = item.getBoundingClientRect();
            return {
                left:(rect.left-p.left)/p.width*100, right:(rect.right-p.left)/p.width*100, centerX:(rect.left+rect.width/2-p.left)/p.width*100,
                top:(rect.top-p.top)/p.height*100, bottom:(rect.bottom-p.top)/p.height*100, centerY:(rect.top+rect.height/2-p.top)/p.height*100
            }
        });
        const move = x => {
            if (rotate) {
                const angle = Math.atan2(x.clientY - centerY, x.clientX - centerX) * 180 / Math.PI;
                let delta = angle - startAngle;
                if (x.shiftKey) delta = Math.round(delta / 15) * 15;
                targets.forEach(item => {
                    if (item.dataset.locked === 'true') return;
                    const value = Math.round((startFrames.get(item).rotation + delta) * 10) / 10;
                    item.dataset.rotation = String(value);
                    item.style.transform = `rotate(${value}deg)`
                });
                $('#rotation').value = Math.max(-180, Math.min(180, Number(o.dataset.rotation || 0)));
                $('#rotationValue').textContent = `${Math.round(Number(o.dataset.rotation || 0))}°`;
            } else if (resize) {
                let nextWidthPct = Math.max(5, Math.min(100, (r.width + x.clientX - sx) / p.width * 100));
                let nextHeightPct = Math.max(4, Math.min(100, (r.height + x.clientY - sy) / p.height * 100));
                if (x.shiftKey) {
                    const ratio = Math.max(.05, r.width / Math.max(1, r.height));
                    const widthDrivenHeight = (nextWidthPct * p.width / ratio) / p.height * 100;
                    const heightDrivenWidth = (nextHeightPct * p.height * ratio) / p.width * 100;
                    if (Math.abs(x.clientX - sx) >= Math.abs(x.clientY - sy)) nextHeightPct = Math.max(4, Math.min(100, widthDrivenHeight));
                    else nextWidthPct = Math.max(5, Math.min(100, heightDrivenWidth));
                }
                o.style.width = nextWidthPct + '%'; o.style.height = nextHeightPct + '%'
            } else {
                const currentRect = o.getBoundingClientRect();
                const widthPct = currentRect.width / p.width * 100,
                    heightPct = currentRect.height / p.height * 100;
                const deltaX = (x.clientX - sx) / p.width * 100,
                    deltaY = (x.clientY - sy) / p.height * 100,
                    primaryStart = startFrames.get(o);
                let moveX = deltaX, moveY = deltaY;
                if (x.shiftKey) {
                    if (Math.abs(deltaX) >= Math.abs(deltaY)) moveY = 0;
                    else moveX = 0;
                }
                let left = Math.max(0, Math.min(100 - widthPct, primaryStart.left + moveX)),
                    top = Math.max(0, Math.min(100 - heightPct, primaryStart.top + moveY));
                const centerLeft = 50 - widthPct / 2, centerTop = 50 - heightPct / 2;
                clearSnapGuides();
                const objectXPoints = otherRects.flatMap(rect => [
                    {value:rect.left,axis:'vertical',guide:rect.left},
                    {value:rect.centerX-widthPct/2,axis:'vertical',guide:rect.centerX},
                    {value:rect.right-widthPct,axis:'vertical',guide:rect.right}
                ]);
                const objectYPoints = otherRects.flatMap(rect => [
                    {value:rect.top,axis:'horizontal',guide:rect.top},
                    {value:rect.centerY-heightPct/2,axis:'horizontal',guide:rect.centerY},
                    {value:rect.bottom-heightPct,axis:'horizontal',guide:rect.bottom}
                ]);
                left = snap(left, [
                    {value:0,axis:'vertical',guide:0}, {value:25,axis:'vertical',guide:25},
                    {value:centerLeft,axis:'vertical',guide:50}, {value:75-widthPct,axis:'vertical',guide:75},
                    {value:100-widthPct,axis:'vertical',guide:100}, ...objectXPoints
                ], .9);
                top = snap(top, [
                    {value:0,axis:'horizontal',guide:0}, {value:25,axis:'horizontal',guide:25},
                    {value:centerTop,axis:'horizontal',guide:50}, {value:75-heightPct,axis:'horizontal',guide:75},
                    {value:100-heightPct,axis:'horizontal',guide:100}, ...objectYPoints
                ], .9);
                const adjustedDx = left - primaryStart.left, adjustedDy = top - primaryStart.top;
                targets.forEach(item => {
                    if (item.dataset.locked === 'true') return;
                    const frame = startFrames.get(item);
                    const itemRect = item.getBoundingClientRect();
                    const itemWidthPct = itemRect.width / p.width * 100;
                    const itemHeightPct = itemRect.height / p.height * 100;
                    item.style.left = Math.max(0, Math.min(100 - itemWidthPct, frame.left + adjustedDx)) + '%';
                    item.style.top = Math.max(0, Math.min(100 - itemHeightPct, frame.top + adjustedDy)) + '%'
                })
            }
            updateSelectionBounds()
        };
        o.onpointermove = move;
        o.onpointerup = () => {
            o.onpointermove = null;
            clearSnapGuides();
            updateSelectionBounds();
            save()
        };
        e.stopPropagation();
        e.preventDefault()
    })
}

function refreshSelectionUI() {
    const items = currentSelection();
    if (!items.length) return clearSelection();
    selected = selected && selectedObjects.has(selected) ? selected : items.at(-1);
    $$('.object').forEach(item => {
        item.classList.toggle('selected', item === selected);
        item.classList.toggle('multi-selected', selectedObjects.has(item) && item !== selected)
    });
    $('#noSelection').hidden = true;
    $('#properties').hidden = false;
    const content = selected.querySelector('.content');
    const textItems = items.filter(item => item.querySelector('.content'));
    $('#selectionCount').textContent = `${items.length} selected`;
    $('#textContentLabel').hidden = !content || items.length > 1;
    $('#textContent').value = content?.textContent || '';
    $('#font').disabled = !textItems.length;
    $('#color').disabled = !textItems.length;
    $('#fontSize').disabled = !textItems.length;
    $('#textAlign').disabled = !textItems.length;
    $('#font').value = selected.dataset.font || 'Georgia,serif';
    $('#color').value = selected.dataset.color || '#47252d';
    const fontSize = Number(selected.dataset.fontSize || parseFloat(getComputedStyle(content || selected).fontSize) || 32);
    $('#fontSize').value = Math.max(10, Math.min(160, fontSize));
    $('#fontSizeValue').textContent = `${Math.round(fontSize)}px`;
    $('#textAlign').value = selected.dataset.textAlign || 'center';
    $('#fontBold').setAttribute('aria-pressed', selected.dataset.fontWeight === '700' ? 'true' : 'false');
    $('#fontItalic').setAttribute('aria-pressed', selected.dataset.fontStyle === 'italic' ? 'true' : 'false');
    $('#letterSpacing').value = Number(selected.dataset.letterSpacing || 0);
    $('#letterSpacingValue').textContent = `${Number(selected.dataset.letterSpacing || 0)}px`;
    $('#lineHeight').value = Number(selected.dataset.lineHeight || 1.35);
    $('#lineHeightValue').textContent = Number(selected.dataset.lineHeight || 1.35).toFixed(2).replace(/0$/,'');
    $('#fillColor').value = selected.dataset.fillColor || '#d9a6ad';
    $('#shapeKind').value = selected.dataset.shapeKind || 'rectangle';
    const textLike = ['text','decoration'].includes(selected.dataset.objectType || 'text');
    $('#typographyControls').hidden = !textLike;
    $('#textContentLabel').hidden = !textLike;
    $('#shapeControls').hidden = selected.dataset.objectType !== 'shape';
    $('#animation').value = selected.dataset.animation || 'fade-up';
    $('#duration').value = selected.dataset.duration || '900';
    $('#rotation').value = Math.max(-180, Math.min(180, Number(selected.dataset.rotation || 0)));
    $('#rotationValue').textContent = `${Math.round(Number(selected.dataset.rotation || 0))}°`;
    const opacity = Math.round(Number(selected.dataset.opacity ?? 1) * 100);
    $('#objectOpacity').value = opacity;
    $('#opacityValue').textContent = `${opacity}%`;
    $('#borderWidth').value = selected.dataset.borderWidth || '0';
    $('#borderWidthValue').textContent = `${selected.dataset.borderWidth || 0}px`;
    $('#borderColor').value = selected.dataset.borderColor || '#ffffff';
    $('#borderRadius').value = selected.dataset.borderRadius || '0';
    $('#borderRadiusValue').textContent = `${selected.dataset.borderRadius || 0}px`;
    $('#shadowBlur').value = selected.dataset.shadowBlur || '0';
    $('#shadowBlurValue').textContent = `${selected.dataset.shadowBlur || 0}px`;
    $('#shadowColor').value = selected.dataset.shadowColor || '#000000';
    const isImage = selected.dataset.objectType === 'image' && items.length === 1;
    $('#imageControls').hidden = !isImage;
    if (isImage) {
        $('#imageFit').value = selected.dataset.imageFit || 'cover';
        $('#imagePositionX').value = selected.dataset.imagePositionX || '50';
        $('#imagePositionY').value = selected.dataset.imagePositionY || '50';
        $('#imageMask').value = selected.dataset.imageMask || 'none';
        $('#imageFrame').value = selected.dataset.imageFrame || 'none';
        $('#showInGallery').checked = selected.dataset.showInGallery !== 'false';
        updateCropPreview()
    }
    $('#showInHero').checked = items.every(item => item.dataset.showInHero !== 'false');
    $('#objectLocked').checked = items.every(item => item.dataset.locked === 'true');
    updateSelectionBounds();
    renderLayers()
}

function select(o, additive = false) {
    if (!o) return clearSelection();
    const groupItems = o.dataset.groupId ? $$('.object').filter(item => item.dataset.groupId === o.dataset.groupId) : [o];
    if (!additive) {
        selectedObjects.clear();
        groupItems.forEach(item => selectedObjects.add(item))
    } else {
        const allSelected = groupItems.every(item => selectedObjects.has(item));
        groupItems.forEach(item => allSelected ? selectedObjects.delete(item) : selectedObjects.add(item))
    }
    selected = selectedObjects.has(o) ? o : currentSelection().at(-1) || null;
    refreshSelectionUI()
}

function setSelection(items, additive = false) {
    if (!additive) selectedObjects.clear();
    const expanded = new Set();
    items.forEach(item => {
        if (item.dataset.groupId) $$('.object').filter(other => other.dataset.groupId === item.dataset.groupId).forEach(other => expanded.add(other));
        else expanded.add(item)
    });
    expanded.forEach(item => selectedObjects.add(item));
    selected = items.at(-1) || currentSelection().at(-1) || null;
    refreshSelectionUI()
}


function wireStageMarquee() {
    const stage = $('#stage');
    if (!stage || stage.dataset.marqueeWired === 'true') return;
    stage.dataset.marqueeWired = 'true';
    stage.addEventListener('pointerdown', event => {
        if (panMode || spacePan || event.target.closest('.object') || event.target.closest('.selection-bounds') || event.button !== 0) return;
        const additive = event.shiftKey || event.ctrlKey || event.metaKey;
        const sr = stage.getBoundingClientRect();
        const startX = Math.max(0, Math.min(sr.width, event.clientX - sr.left));
        const startY = Math.max(0, Math.min(sr.height, event.clientY - sr.top));
        const marquee = document.createElement('div');
        marquee.className = 'selection-marquee';
        marquee.style.left = `${startX/sr.width*100}%`;
        marquee.style.top = `${startY/sr.height*100}%`;
        stage.append(marquee);
        stage.setPointerCapture(event.pointerId);
        let moved = false;
        const onMove = moveEvent => {
            const x = Math.max(0, Math.min(sr.width, moveEvent.clientX - sr.left));
            const y = Math.max(0, Math.min(sr.height, moveEvent.clientY - sr.top));
            const left = Math.min(startX, x), top = Math.min(startY, y);
            const width = Math.abs(x - startX), height = Math.abs(y - startY);
            moved = moved || width > 3 || height > 3;
            Object.assign(marquee.style, { left:`${left/sr.width*100}%`, top:`${top/sr.height*100}%`, width:`${width/sr.width*100}%`, height:`${height/sr.height*100}%` });
            if (!moved) return;
            const selectionRect = { left:sr.left+left, top:sr.top+top, right:sr.left+left+width, bottom:sr.top+top+height };
            const hits = $$('.object').filter(item => {
                const r = item.getBoundingClientRect();
                return r.right >= selectionRect.left && r.left <= selectionRect.right && r.bottom >= selectionRect.top && r.top <= selectionRect.bottom
            });
            $$('.object').forEach(item => item.classList.toggle('marquee-hit', hits.includes(item)))
        };
        const onUp = () => {
            stage.onpointermove = null;
            stage.onpointerup = null;
            const hits = $$('.object').filter(item => item.classList.contains('marquee-hit'));
            $$('.object').forEach(item => item.classList.remove('marquee-hit'));
            marquee.remove();
            if (moved) setSelection(hits, additive);
            else if (!additive) clearSelection()
        };
        stage.onpointermove = onMove;
        stage.onpointerup = onUp;
        event.preventDefault()
    })
}

function previewSelected() {
    if (!selected) return;
    let key = {
        'fade-up': 'fadeUp',
        'soft-zoom': 'softZoom',
        'slide-left': 'slideLeft',
        'blur-in': 'blurIn',
        'bounce-in': 'bounceIn',
        'flip-in': 'flipIn',
        float: 'float',
        none: ''
    } [selected.dataset.animation];
    selected.style.animation = 'none';
    requestAnimationFrame(() => selected.style.animation = key ? `${key} ${selected.dataset.duration||900}ms both` : 'none')
}
$$('.object').forEach((o, index) => {
    if (!o.style.zIndex) o.style.zIndex = String(index + 1);
    if (!o.dataset.locked) o.dataset.locked = 'false';
    if (!o.dataset.showInHero) o.dataset.showInHero = 'true';
    if (!o.dataset.showInGallery) o.dataset.showInGallery = o.dataset.id === 'hero' ? 'false' : 'true';
    if (!o.dataset.groupId) o.dataset.groupId = '';
    if (!o.dataset.fontSize) o.dataset.fontSize = o.dataset.id === 'title' ? '46' : o.dataset.id === 'subtitle' ? '17' : '17';
    if (!o.dataset.textAlign) o.dataset.textAlign = 'center';
    if (!o.dataset.opacity) o.dataset.opacity = '1';
    if (!o.dataset.borderWidth) o.dataset.borderWidth = '0';
    if (!o.dataset.borderColor) o.dataset.borderColor = '#ffffff';
    if (!o.dataset.borderRadius) o.dataset.borderRadius = '0';
    if (!o.dataset.shadowBlur) o.dataset.shadowBlur = '0';
    if (!o.dataset.shadowColor) o.dataset.shadowColor = '#000000';
    if (!o.dataset.imageMask) o.dataset.imageMask = 'none';
    if (!o.dataset.imageFrame) o.dataset.imageFrame = 'none';
    wireObject(o)
});
wireStageMarquee();
$('#textContent').oninput = e => {
    if (!selected) return;
    const content = selected.querySelector('.content');
    if (!content) return;
    content.textContent = e.target.value;
    if (selected.dataset.id === 'title') {
        const field = $('#languageMode').value === 'km' ? $('#namesKm') : $('#names');
        field.value = e.target.value
    } else if (selected.dataset.id === 'subtitle') {
        const field = $('#languageMode').value === 'km' ? $('#messageKm') : $('#message');
        field.value = e.target.value
    }
    save()
};
$('#objectLocked').onchange = e => {
    if (!selected) return;
    currentSelection().forEach(item => {
        item.dataset.locked = e.target.checked ? 'true' : 'false';
        item.classList.toggle('locked', e.target.checked)
    });
    save()
};
$('#showInHero').onchange = e => {
    currentSelection().forEach(item => item.dataset.showInHero = e.target.checked ? 'true' : 'false');
    save()
};
$('#showInGallery').onchange = e => {
    if (!selected || !selected.classList.contains('image-object')) return;
    selected.dataset.showInGallery = e.target.checked ? 'true' : 'false';
    if (e.target.checked && !(state.galleryOrder || []).includes(selected.dataset.id)) state.galleryOrder = [...(state.galleryOrder || []), selected.dataset.id];
    save()
};
function moveSelectedLayer(direction) {
    if (!selected) return;
    const layers = $$('.object').slice().sort((a, b) => Number(a.style.zIndex || 0) - Number(b.style.zIndex || 0));
    const index = layers.indexOf(selected), target = index + direction;
    if (index < 0 || target < 0 || target >= layers.length) return;
    [layers[index], layers[target]] = [layers[target], layers[index]];
    layers.forEach((o, i) => o.style.zIndex = String(i + 1));
    save()
}
$('#bringForward').onclick = () => moveSelectedLayer(1);
$('#sendBackward').onclick = () => moveSelectedLayer(-1);
function normalizeZIndexes() {
    $$('.object').slice().sort((a, b) => Number(a.style.zIndex || 0) - Number(b.style.zIndex || 0)).forEach((o, i) => o.style.zIndex = String(i + 1))
}
$('#font').onchange = e => {
    currentSelection().filter(item => item.querySelector('.content')).forEach(item => {
        item.dataset.font = e.target.value;
        item.querySelector('.content').style.fontFamily = e.target.value
    });
    save()
};
$('#color').oninput = e => {
    currentSelection().filter(item => item.querySelector('.content')).forEach(item => {
        item.dataset.color = e.target.value;
        item.querySelector('.content').style.color = e.target.value
    });
    save()
};
$('#fontSize').oninput = e => {
    const value = Number(e.target.value);
    $('#fontSizeValue').textContent = `${value}px`;
    currentSelection().filter(item => item.querySelector('.content')).forEach(item => {
        item.dataset.fontSize = String(value);
        applyObjectVisualStyle(item)
    });
    updateSelectionBounds();
    save()
};
$('#textAlign').onchange = e => {
    currentSelection().filter(item => item.querySelector('.content')).forEach(item => {
        item.dataset.textAlign = e.target.value;
        applyObjectVisualStyle(item)
    });
    save()
};
$('#animation').onchange = e => {
    if (selected) {
        selected.dataset.animation = e.target.value;
        previewSelected();
        save()
    }
};
$('#duration').oninput = e => {
    if (selected) {
        selected.dataset.duration = e.target.value;
        previewSelected();
        save()
    }
};
$('#rotation').oninput = e => {
    if (!selected) return;
    currentSelection().forEach(item => {
        if (item.dataset.locked === 'true') return;
        item.dataset.rotation = e.target.value;
        item.style.transform = `rotate(${e.target.value}deg)`
    });
    $('#rotationValue').textContent = `${e.target.value}°`;
    updateSelectionBounds();
    save()
};
function applyTextStyleToSelection(datasetKey, value) {
    currentSelection().filter(item => ['text','decoration'].includes(item.dataset.objectType || 'text')).forEach(item => {
        item.dataset[datasetKey] = String(value);
        applyObjectVisualStyle(item)
    });
    updateSelectionBounds();
    save()
}
$('#fontBold').onclick = () => {
    const active = $('#fontBold').getAttribute('aria-pressed') === 'true';
    const value = active ? '400' : '700';
    $('#fontBold').setAttribute('aria-pressed', active ? 'false' : 'true');
    applyTextStyleToSelection('fontWeight', value)
};
$('#fontItalic').onclick = () => {
    const active = $('#fontItalic').getAttribute('aria-pressed') === 'true';
    const value = active ? 'normal' : 'italic';
    $('#fontItalic').setAttribute('aria-pressed', active ? 'false' : 'true');
    applyTextStyleToSelection('fontStyle', value)
};
$('#letterSpacing').oninput = e => { $('#letterSpacingValue').textContent = `${e.target.value}px`; applyTextStyleToSelection('letterSpacing', e.target.value) };
$('#lineHeight').oninput = e => { $('#lineHeightValue').textContent = Number(e.target.value).toFixed(2).replace(/0$/,''); applyTextStyleToSelection('lineHeight', e.target.value) };
$('#fillColor').oninput = e => { currentSelection().filter(item=>item.dataset.objectType==='shape').forEach(item=>{item.dataset.fillColor=e.target.value;applyObjectVisualStyle(item)});save() };
$('#shapeKind').onchange = e => { currentSelection().filter(item=>item.dataset.objectType==='shape').forEach(item=>{item.dataset.shapeKind=e.target.value;if(e.target.value==='circle')item.dataset.borderRadius='120';applyObjectVisualStyle(item)});refreshSelectionUI();save() };

function addDesignElement(kind) {
    const id = `element-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
    let type = ['heart','sparkle','flourish','diamond'].includes(kind) ? 'decoration' : 'shape';
    const object = createObject(id, type);
    if (type === 'shape') {
        object.dataset.shapeKind = kind === 'panel' ? 'rectangle' : kind;
        object.dataset.fillColor = kind === 'line' ? (state.accent || '#9d4555') : (kind === 'panel' ? '#ffffff' : (state.accent || '#9d4555'));
        if (kind === 'circle') { object.style.width='160px'; object.style.height='160px'; object.dataset.borderRadius='120' }
        else if (kind === 'line') { object.style.width='70%'; object.style.height='8px'; object.style.left='15%'; object.style.top='46%' }
        else if (kind === 'panel') { object.style.left='5%'; object.style.top='18%'; object.style.width='90%'; object.style.height='420px'; object.dataset.opacity='.32'; object.dataset.borderRadius='24'; object.style.zIndex='1' }
        else { object.style.width='220px'; object.style.height='140px' }
    } else {
        const glyphs = {heart:'♥',sparkle:'✦',flourish:'❦',diamond:'◇'};
        object.querySelector('.content').textContent = glyphs[kind] || '✦';
        object.dataset.fontSize = kind === 'flourish' ? '74' : '62';
        object.dataset.color = state.accent || '#9d4555';
        object.style.width='120px'; object.style.height='110px';
        object.style.left='35%'; object.style.top='38%'
    }
    applyObjectVisualStyle(object);
    $('#stage').append(object);
    clearSelection();
    setSelection([object]);
    save()
}
document.querySelectorAll('[data-add-element]').forEach(button => button.onclick = () => addDesignElement(button.dataset.addElement));

function updateAppearanceControl(id, datasetKey, formatter, apply = true) {
    $('#' + id).oninput = e => {
        const value = e.target.value;
        const label = $('#' + formatter.id);
        if (label) label.textContent = formatter.text(value);
        currentSelection().forEach(item => {
            item.dataset[datasetKey] = datasetKey === 'opacity' ? String(Number(value) / 100) : value;
            if (apply) applyObjectVisualStyle(item)
        });
        updateSelectionBounds();
        save()
    }
}
updateAppearanceControl('objectOpacity','opacity',{id:'opacityValue',text:v=>`${v}%`});
updateAppearanceControl('borderWidth','borderWidth',{id:'borderWidthValue',text:v=>`${v}px`});
updateAppearanceControl('borderRadius','borderRadius',{id:'borderRadiusValue',text:v=>`${v}px`});
updateAppearanceControl('shadowBlur','shadowBlur',{id:'shadowBlurValue',text:v=>`${v}px`});
$('#borderColor').oninput = e => { currentSelection().forEach(item => { item.dataset.borderColor=e.target.value; applyObjectVisualStyle(item) }); save() };
$('#shadowColor').oninput = e => { currentSelection().forEach(item => { item.dataset.shadowColor=e.target.value; applyObjectVisualStyle(item) }); save() };
$('#imageMask').onchange = e => { if (selected?.dataset.objectType === 'image') { selected.dataset.imageMask = e.target.value; applyObjectVisualStyle(selected); updateCropPreview(); save() } };
$('#imageFrame').onchange = e => { if (selected?.dataset.objectType === 'image') { selected.dataset.imageFrame = e.target.value; applyObjectVisualStyle(selected); updateCropPreview(); save() } };

function updateCropPreview() {
    if (!selected || !selected.classList.contains('image-object')) return;
    const source = selected.querySelector('img')?.src;
    const preview = $('#cropPreview img');
    if (!source || !preview) return;
    preview.src = source;
    preview.style.objectFit = $('#imageFit').value;
    preview.style.objectPosition = `${$('#imagePositionX').value}% ${$('#imagePositionY').value}%`;
    const masks = { none:'none', circle:'ellipse(50% 50% at 50% 50%)', arch:'inset(0 round 48% 48% 12% 12%)', diamond:'polygon(50% 0,100% 50%,50% 100%,0 50%)', hexagon:'polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)', blob:'polygon(50% 0,78% 8%,96% 35%,91% 72%,66% 100%,31% 94%,6% 68%,0 32%,22% 7%)' };
    const frames = { none:['0','transparent'], white:['8px','#fff'], gold:['8px','#c79b42'], dark:['8px','#201b1b'] };
    const frame = frames[$('#imageFrame').value] || frames.none;
    preview.style.clipPath = masks[$('#imageMask').value] || 'none';
    preview.style.padding = frame[0]; preview.style.background = frame[1]; preview.style.boxSizing = 'border-box';
    $('#cropFocus').style.left = `${$('#imagePositionX').value}%`;
    $('#cropFocus').style.top = `${$('#imagePositionY').value}%`
}
function updateSelectedImageCrop() {
    if (!selected || !selected.classList.contains('image-object')) return;
    const img = selected.querySelector('img'); if (!img) return;
    selected.dataset.imageFit = $('#imageFit').value;
    selected.dataset.imagePositionX = $('#imagePositionX').value;
    selected.dataset.imagePositionY = $('#imagePositionY').value;
    img.style.objectFit = selected.dataset.imageFit;
    img.style.objectPosition = `${selected.dataset.imagePositionX}% ${selected.dataset.imagePositionY}%`;
    updateCropPreview();
    save()
}
['imageFit','imagePositionX','imagePositionY'].forEach(id => $('#'+id).addEventListener(id==='imageFit'?'change':'input', updateSelectedImageCrop));
$('#cropPreview').addEventListener('pointerdown', event => {
    if (!selected || !selected.classList.contains('image-object')) return;
    const rect = event.currentTarget.getBoundingClientRect();
    $('#imagePositionX').value = Math.round(Math.max(0, Math.min(100, (event.clientX - rect.left) / rect.width * 100)));
    $('#imagePositionY').value = Math.round(Math.max(0, Math.min(100, (event.clientY - rect.top) / rect.height * 100)));
    updateSelectedImageCrop()
});

function deleteSelection() {
    const protectedIds = new Set(['title','subtitle','details','hero']);
    const removable = currentSelection().filter(item => !protectedIds.has(item.dataset.id));
    if (!removable.length) return;
    removable.forEach(item => {
        state.galleryOrder = (state.galleryOrder || []).filter(id => id !== item.dataset.id);
        selectedObjects.delete(item);
        item.remove()
    });
    selected = currentSelection().at(-1) || null;
    if (selected) refreshSelectionUI();
    else clearSelection();
    save()
}
$('#deleteBtn').onclick = deleteSelection;

function copyObjectData(source, target, data, offsetIndex = 0) {
    const stageRect = $('#stage').getBoundingClientRect();
    const sourceRect = source.getBoundingClientRect();
    const left = (sourceRect.left - stageRect.left) / stageRect.width * 100 + 3 + offsetIndex * 1.2;
    const top = (sourceRect.top - stageRect.top) / stageRect.height * 100 + 2 + offsetIndex * 1.2;
    target.style.left = `${Math.min(92, left)}%`;
    target.style.top = `${Math.min(92, top)}%`;
    target.style.width = source.style.width;
    target.style.height = source.style.height;
    const keys = ['objectType','font','color','animation','duration','caption','alt','rotation','imageFit','imagePositionX','imagePositionY','imageMask','imageFrame','imageBrightness','imageContrast','imageSaturation','imageGrayscale','imageSepia','imageBlur','imageHue','imageFlipX','imageFlipY','showInHero','showInGallery','fontSize','textAlign','textVerticalAlign','textPadding','fontWeight','fontStyle','letterSpacing','lineHeight','fillColor','shapeKind','opacity','borderWidth','borderColor','borderRadius','shadowBlur','shadowColor','backgroundEnabled','backgroundColor','backgroundOpacity','blendMode','fillMode','gradientStart','gradientEnd','gradientAngle','textGradientEnabled','textGradientStart','textGradientEnd','textGradientAngle','textStrokeWidth','textStrokeColor','textShadowBlur','textShadowColor','textTransform','animationDelay','visible','layerName'];
    keys.forEach(key => target.dataset[key] = source.dataset[key] ?? data[key] ?? '');
    target.dataset.locked = 'false';
    target.style.transform = `rotate(${Number(target.dataset.rotation || 0)}deg)`;
    target.style.zIndex = String(nextZIndex());
    if (data.type === 'image') {
        const img = target.querySelector('img');
        img.src = data.src;
        img.alt = data.alt || 'Invitation image';
        img.style.objectFit = data.imageFit || 'cover';
        img.style.objectPosition = `${data.imagePositionX ?? 50}% ${data.imagePositionY ?? 50}%`
    } else {
        const content = target.querySelector('.content');
        content.innerHTML = data.html || 'New text';
        content.style.fontFamily = data.font || '';
        content.style.color = data.color || ''
    }
    applyObjectVisualStyle(target)
}

function duplicateSelection() {
    const originals = currentSelection();
    if (!originals.length) return;
    const snapshot = capture().objects;
    const newItems = [];
    const groupMap = new Map();
    originals.forEach((source, index) => {
        const data = snapshot[source.dataset.id];
        if (!data) return;
        const id = `obj-${Date.now()}-${index}`;
        const duplicate = createObject(id, data.type);
        $('#stage').append(duplicate);
        copyObjectData(source, duplicate, data, index);
        if (source.dataset.groupId) {
            if (!groupMap.has(source.dataset.groupId)) groupMap.set(source.dataset.groupId, `group-${Date.now()}-${groupMap.size}`);
            duplicate.dataset.groupId = groupMap.get(source.dataset.groupId)
        }
        if (data.type === 'image' && data.showInGallery !== false) state.galleryOrder = [...(state.galleryOrder || []), id];
        newItems.push(duplicate)
    });
    setSelection(newItems);
    save()
}
$('#duplicate').onclick = duplicateSelection;

function readSavedGroups(){try{return JSON.parse(localStorage.getItem(savedGroupsKey)||'[]')}catch{return[]}}
function writeSavedGroups(groups){localStorage.setItem(savedGroupsKey,JSON.stringify(groups));renderSavedGroups()}
async function loadAccountComponents(){if(serverInvite&&localStorage.getItem('sovan-auth-token')){try{const [blocks,groups]=await Promise.all([api('/api/components?kind=block'),api('/api/components?kind=group')]);accountBlockTemplates=blocks;accountSavedGroups=groups}catch{accountBlockTemplates=[];accountSavedGroups=[]}}renderSavedBlockTemplates();renderSavedGroups()}
async function deleteSavedGroup(group){if(!(await uiConfirm(`Delete reusable group “${group.name}”?`,{title:'Delete reusable group',danger:true,confirmText:'Delete'})))return;try{if(group.remote){await api(`/api/components/${group.id}`,{method:'DELETE'});accountSavedGroups=accountSavedGroups.filter(x=>x.id!==group.id)}else writeSavedGroups(readSavedGroups().filter(x=>x.id!==group.id));renderSavedGroups()}catch(error){alert(error.message)}}
function renderSavedGroups(){const panel=$('#savedGroups');if(!panel)return;const groups=[...accountSavedGroups.map(x=>({...x,...clone(x.payload),remote:true})),...readSavedGroups().map(x=>({...x,remote:false}))];panel.innerHTML=groups.length?'':'<p class="hint">No reusable groups saved yet.</p>';groups.forEach(group=>{const row=document.createElement('div');row.className='saved-group-row';row.innerHTML='<strong></strong><small></small><div class="mini-actions"><button type="button" data-insert>Insert</button><button type="button" class="danger" data-delete>Delete</button></div>';row.querySelector('strong').textContent=group.name;row.querySelector('small').textContent=group.remote?'Account':'This browser';row.querySelector('[data-insert]').onclick=()=>insertSavedGroup(group);row.querySelector('[data-delete]').onclick=()=>deleteSavedGroup(group);panel.append(row)})}
async function saveSelectedReusableGroup(){const items=currentSelection();if(!items.length)return alert('Select one or more objects first.');const name=await uiPrompt('Name this reusable element group:','My design group',{title:'Save reusable group'});if(!name)return;capture();const sr=$('#stage').getBoundingClientRect(),frames=items.map(item=>{const r=item.getBoundingClientRect();return{id:item.dataset.id,left:(r.left-sr.left)/sr.width*100,top:(r.top-sr.top)/sr.height*100,width:r.width/sr.width*100,height:r.height/sr.height*100,data:clone(state.objects[item.dataset.id])}});const minL=Math.min(...frames.map(x=>x.left)),minT=Math.min(...frames.map(x=>x.top)),maxR=Math.max(...frames.map(x=>x.left+x.width)),maxB=Math.max(...frames.map(x=>x.top+x.height)),w=Math.max(1,maxR-minL),h=Math.max(1,maxB-minT);const group={id:`saved-${Date.now()}`,name:name.slice(0,80),createdAt:Date.now(),aspect:w/h,items:frames.map(x=>({data:x.data,rel:{left:(x.left-minL)/w,top:(x.top-minT)/h,width:x.width/w,height:x.height/h}}))};try{if(serverInvite&&localStorage.getItem('sovan-auth-token')){const saved=await api('/api/components',{method:'POST',body:JSON.stringify({kind:'group',name:group.name,category:'Design group',payload:group})});accountSavedGroups.unshift(saved);renderSavedGroups()}else{const groups=readSavedGroups();groups.unshift(group);writeSavedGroups(groups.slice(0,40))}alert('Reusable group saved.')}catch(error){alert(`The reusable group could not be saved: ${error.message}`)}}
function hydrateObjectFromData(object,data){Object.entries(data||{}).forEach(([key,value])=>{if(['left','top','width','height','html','src','zIndex','type'].includes(key))return;const datasetKey=key;object.dataset[datasetKey]=typeof value==='boolean'?(value?'true':'false'):String(value??'')});const content=object.querySelector('.content');if(content)content.innerHTML=data.html||'New text';const image=object.querySelector('img');if(image&&data.src){image.src=data.src;image.alt=data.alt||'Invitation image'};applyObjectVisualStyle(object)}
function insertSavedGroup(group){if(!group?.items?.length)return;const groupId=`group-${Date.now()}`,baseLeft=12,baseTop=18;let targetWidth=55,targetHeight=targetWidth/(group.aspect||1);if(targetHeight>68){targetHeight=68;targetWidth=Math.min(76,targetHeight*(group.aspect||1))}const created=[];group.items.forEach((item,index)=>{const id=`element-${Date.now()}-${index}-${Math.random().toString(36).slice(2,6)}`,object=createObject(id,item.data.type||'text');hydrateObjectFromData(object,item.data);object.dataset.groupId=groupId;object.style.left=`${baseLeft+item.rel.left*targetWidth}%`;object.style.top=`${baseTop+item.rel.top*targetHeight}%`;object.style.width=`${item.rel.width*targetWidth}%`;object.style.height=`${item.rel.height*targetHeight}%`;object.style.zIndex=String(nextZIndex()+index);$('#stage').append(object);created.push(object)});setSelection(created);save()}
$('#saveElementGroup').onclick=saveSelectedReusableGroup;

function groupSelection() {
    const items = currentSelection();
    if (items.length < 2) return alert('Select at least two objects with Shift/Ctrl-click.');
    const id = `group-${Date.now()}`;
    items.forEach(item => item.dataset.groupId = id);
    save();
    setSelection(items)
}
function ungroupSelection() {
    const groups = new Set(currentSelection().map(item => item.dataset.groupId).filter(Boolean));
    if (!groups.size) return;
    $$('.object').forEach(item => { if (groups.has(item.dataset.groupId)) item.dataset.groupId = '' });
    updateSelectionBounds();
    save();
    renderLayers()
}
function alignSelection(mode) {
    const items = currentSelection();
    if (items.length < 2) return;
    const stage = $('#stage').getBoundingClientRect();
    const frames = items.map(item => ({ item, rect:item.getBoundingClientRect() }));
    const minL = Math.min(...frames.map(x => x.rect.left)), maxR = Math.max(...frames.map(x => x.rect.right));
    const minT = Math.min(...frames.map(x => x.rect.top)), maxB = Math.max(...frames.map(x => x.rect.bottom));
    frames.forEach(({item,rect}) => {
        if (item.dataset.locked === 'true') return;
        let left = rect.left, top = rect.top;
        if (mode === 'left') left = minL;
        if (mode === 'center') left = (minL + maxR - rect.width) / 2;
        if (mode === 'right') left = maxR - rect.width;
        if (mode === 'top') top = minT;
        if (mode === 'middle') top = (minT + maxB - rect.height) / 2;
        if (mode === 'bottom') top = maxB - rect.height;
        item.style.left = `${(left - stage.left) / stage.width * 100}%`;
        item.style.top = `${(top - stage.top) / stage.height * 100}%`
    });
    updateSelectionBounds();
    save()
}
function distributeSelection(axis) {
    const items = currentSelection();
    if (items.length < 3) return alert('Select at least three objects to distribute.');
    const stage = $('#stage').getBoundingClientRect();
    const frames = items.map(item => ({item, rect:item.getBoundingClientRect()}))
        .sort((a,b) => axis === 'horizontal' ? a.rect.left - b.rect.left : a.rect.top - b.rect.top);
    const first = frames[0].rect, last = frames.at(-1).rect;
    if (axis === 'horizontal') {
        const available = last.right - first.left - frames.reduce((sum,x)=>sum+x.rect.width,0);
        const gap = available / (frames.length - 1);
        let cursor = first.left;
        frames.forEach(({item,rect},index) => {
            if (index && item.dataset.locked !== 'true') item.style.left = `${(cursor - stage.left) / stage.width * 100}%`;
            cursor += rect.width + gap
        })
    } else {
        const available = last.bottom - first.top - frames.reduce((sum,x)=>sum+x.rect.height,0);
        const gap = available / (frames.length - 1);
        let cursor = first.top;
        frames.forEach(({item,rect},index) => {
            if (index && item.dataset.locked !== 'true') item.style.top = `${(cursor - stage.top) / stage.height * 100}%`;
            cursor += rect.height + gap
        })
    }
    updateSelectionBounds();
    save()
}
$('#groupObjects').onclick = groupSelection;
$('#ungroupObjects').onclick = ungroupSelection;
$$('[data-align]').forEach(button => button.onclick = () => alignSelection(button.dataset.align));
$$('[data-distribute]').forEach(button => button.onclick = () => distributeSelection(button.dataset.distribute));

$$('[data-add-block]').forEach(button => button.onclick = () => addCustomBlock(button.dataset.addBlock));
$('#addCustomBlock').onclick = () => addCustomBlock($('#newBlockType').value);
$$('[data-add-page]').forEach(button => button.onclick = () => insertDesignPage(button.dataset.addPage));
$('#editHeroCanvas').onclick = () => switchCanvas('hero');
$('#copyObjects').onclick=copySelectionToClipboard;$('#pasteObjects').onclick=pasteObjectsFromClipboard;$('#pasteObjects').disabled=!localStorage.getItem(objectClipboardKey);
['masterPageEnabled','masterPageBackground','masterPageImage','masterPageSize','masterPageOverlay'].forEach(id=>$('#'+id)?.addEventListener('input',()=>{if($('#masterPageOverlayValue'))$('#masterPageOverlayValue').textContent=`${$('#masterPageOverlay').value}%`;save()}));
$('#masterPageUseSelected').onclick=()=>{const imageObject=selected?.dataset.objectType==='image'?selected:currentSelection().find(item=>item.dataset.objectType==='image');const src=imageObject?.querySelector('img')?.src;if(!src)return alert('Select an image object first.');$('#masterPageImage').value=src;$('#masterPageEnabled').checked=true;save()};
$('#masterPageClearImage').onclick=()=>{$('#masterPageImage').value='';save()};
$('#addText').onclick = () => {
    let o = createObject('text-' + Date.now(), 'text');
    $('#stage').append(o);
    select(o);
    save()
};
function updateCanvasView() {
    const stage=$('#stage'), frame=$('#canvasFrame'), zoomSelect=$('#zoomLevel'); if(!stage||!frame)return;
    editorZoom=Math.max(.35,Math.min(2,editorZoom)); localStorage.setItem('sovan-editor-zoom',String(editorZoom));
    /* Give the artboard an intrinsic width before measuring it. A percentage
       width creates a feedback loop when the canvas was initialized inside a
       hidden content-mode panel: frame shrinks -> stage shrinks -> frame
       shrinks again. Device buttons still replace this with their chosen
       explicit width. */
    if(!stage.style.width)stage.style.width='390px';
    stage.style.transform=`scale(${editorZoom})`; stage.style.transformOrigin='top left';
    const gutter=28; frame.style.width=`${Math.ceil(stage.offsetWidth*editorZoom+gutter)}px`; frame.style.height=`${Math.ceil(stage.offsetHeight*editorZoom+gutter)}px`;
    if(zoomSelect){ const nearest=[.5,.75,1,1.25,1.5,2].reduce((a,b)=>Math.abs(b-editorZoom)<Math.abs(a-editorZoom)?b:a,1); zoomSelect.value=String(nearest) }
    requestAnimationFrame(updateSelectionBounds)
}
function setZoom(value){editorZoom=Math.max(.35,Math.min(2,Number(value)||1));updateCanvasView()}
$('#zoomOut').onclick=()=>setZoom(editorZoom-.25); $('#zoomIn').onclick=()=>setZoom(editorZoom+.25); $('#zoomLevel').onchange=e=>setZoom(e.target.value);
$('#fitCanvas').onclick=()=>{const viewport=$('#canvasViewport'),stage=$('#stage');const fit=Math.min((viewport.clientWidth-70)/stage.offsetWidth,(viewport.clientHeight-70)/stage.offsetHeight,1.5);setZoom(Math.max(.35,fit))};
$('#panToggle').onclick=()=>{panMode=!panMode;$('#panToggle').setAttribute('aria-pressed',String(panMode));$('#canvasViewport').classList.toggle('pan-mode',panMode)};
$('#rulersToggle').onclick=()=>{const active=!$('#canvasFrame').classList.contains('show-rulers');$('#canvasFrame').classList.toggle('show-rulers',active);$('#rulersToggle').setAttribute('aria-pressed',String(active))};
$('#safeMarginToggle').onclick=()=>{const active=!$('#stage').classList.contains('show-safe-margins');$('#stage').classList.toggle('show-safe-margins',active);$('#safeMarginToggle').setAttribute('aria-pressed',String(active))};
(function wireCanvasPan(){const viewport=$('#canvasViewport');let start=null;viewport.addEventListener('pointerdown',e=>{if(!(panMode||spacePan)||e.button!==0)return;start={x:e.clientX,y:e.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};viewport.setPointerCapture(e.pointerId);viewport.classList.add('panning');e.preventDefault();e.stopPropagation()},true);viewport.addEventListener('pointermove',e=>{if(!start)return;viewport.scrollLeft=start.left-(e.clientX-start.x);viewport.scrollTop=start.top-(e.clientY-start.y)},true);viewport.addEventListener('pointerup',()=>{start=null;viewport.classList.remove('panning')},true)})();
$$('[data-device]').forEach(b => b.onclick = () => { $('#stage').style.width = Math.min(+b.dataset.device, Math.max(390,$('.stage-wrap').clientWidth - 70)) + 'px'; requestAnimationFrame(updateCanvasView) });
async function optimizeImageFile(file) {
    if (!file || file.type === 'image/gif' || typeof createImageBitmap !== 'function') return file;
    try {
        const bitmap = await createImageBitmap(file), maxSide = 2200;
        if (file.size <= 1_500_000 && Math.max(bitmap.width, bitmap.height) <= maxSide) {
            bitmap.close?.();
            return file
        }
        const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
        const width = Math.max(1, Math.round(bitmap.width * scale)), height = Math.max(1, Math.round(bitmap.height * scale));
        const canvas = document.createElement('canvas'); canvas.width = width; canvas.height = height;
        canvas.getContext('2d', { alpha: true }).drawImage(bitmap, 0, 0, width, height); bitmap.close?.();
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/webp', .88));
        if (!blob || blob.size >= file.size) return file;
        const base = file.name.replace(/\.[^.]+$/, '') || 'image';
        return new File([blob], `${base}.webp`, { type: 'image/webp', lastModified: Date.now() })
    } catch {
        return file
    }
}
async function uploadFileToServer(file){
    if(!serverInvite||!localStorage.getItem('sovan-auth-token'))return null;
    const token=localStorage.getItem('sovan-auth-token');
    if(window.EInviteUpload?.upload)return window.EInviteUpload.upload(serverInvite.id,file,{token,name:file.name});
    const response=await fetch(`/api/invitations/${serverInvite.id}/assets/raw`,{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':file.type,'X-File-Name':encodeURIComponent(file.name)},body:file});
    const payload=await response.json().catch(()=>({}));if(!response.ok)throw Error(payload.error||'Material upload failed');return payload
}
$('#photoUpload').onchange = async e => {
    let file = e.target.files[0];
    if (!file) return;
    if (!['image/jpeg','image/png','image/webp','image/gif'].includes(file.type)) return alert('Please choose a JPEG, PNG, WebP, or GIF image.');
    if (file.size > 15e6) return alert('Please choose an image under 15 MB.');
    try {
        file = await optimizeImageFile(file);
        let asset = {
            id: Date.now(),
            name: file.name,
            type: file.type,
            size: file.size,
            blob: file,
            createdAt: new Date().toISOString()
        };
        if (serverInvite && localStorage.getItem('sovan-auth-token')) {
            const uploaded = await uploadFileToServer(file);
            asset.serverUrl = uploaded.url;
            asset.serverId = uploaded.id
        }
        await assetStore.put(asset);
        await renderAssets()
    } catch (error) {
        alert(`The material could not be stored: ${error.message||'unknown error'}`)
    }
};
$('#videoUpload')?.addEventListener('change', async e => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!['video/mp4','video/webm'].includes(file.type)) return alert('Please choose an MP4 or WebM video.');
    if (file.size > 50e6) return alert('Please choose a video under 50 MB.');
    try {
        const asset = { id:'video-'+Date.now(), name:file.name, type:file.type, size:file.size, blob:file, createdAt:new Date().toISOString() };
        if (serverInvite && localStorage.getItem('sovan-auth-token')) {
            const uploaded = await uploadFileToServer(file);
            asset.serverUrl=uploaded.url; asset.serverId=uploaded.id
        }
        await assetStore.put(asset);
        state.video={assetId:asset.id,name:asset.name,url:asset.serverUrl||await usableAssetUrl(asset),mime:asset.type};
        $('#videoEnabled').checked=true;
        $('#videoState').textContent=`Selected: ${asset.name}`;
        save(); await renderAssets()
    } catch(error) { alert(`The video could not be stored: ${error.message||'unknown error'}`) }
});
$('#clearVideo')?.addEventListener('click',()=>{state.video=null;$('#videoEnabled').checked=false;$('#videoState').textContent='No featured video selected.';save()});
$('#musicUpload').onchange = async e => {
    let file = e.target.files[0];
    if (!file) return;
    if (!['audio/mpeg', 'audio/mp4'].includes(file.type)) return alert('Please choose an MP3 or M4A audio file.');
    if (file.size > 15e6) return alert('Please choose music under 15 MB.');
    try {
        let asset = {
            id: 'music-' + Date.now(),
            name: file.name,
            type: file.type,
            size: file.size,
            blob: file,
            createdAt: new Date().toISOString()
        };
        if (serverInvite && localStorage.getItem('sovan-auth-token')) {
            const uploaded = await uploadFileToServer(file);
            asset.serverUrl = uploaded.url;
            asset.serverId = uploaded.id
        }
        await assetStore.put(asset);
        state.music = {
            assetId: asset.id,
            name: asset.name,
            url: asset.serverUrl || ''
        };
        $('#musicEnabled').checked = true;
        $('#musicState').textContent = `Selected: ${asset.name}`;
        save()
    } catch (error) {
        alert(`The music could not be stored: ${error.message||'unknown error'}`)
    }
};
async function listAllAssets() {
    let assets = await assetStore.list();
    if (localStorage.getItem('sovan-auth-token')) {
        try {
            const remote = await api('/api/assets');
            const known = new Set(assets.map(a => a.serverId || a.serverUrl));
            remote.forEach(item => {
                if (!known.has(item.id) && !known.has(item.url)) assets.push({
                    id: `server-${item.id}`, serverId:item.id, serverUrl:item.url, invitationId:item.invitationId,
                    invitationSlug:item.invitationSlug, name:item.name, type:item.mime, size:item.size,
                    createdAt:item.createdAt, remoteOnly:true
                })
            })
        } catch {}
    }
    return assets
}
function blobAsDataUrl(blob){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=reject;reader.readAsDataURL(blob)})}
async function usableAssetUrl(asset){if(asset.serverUrl)return asset.serverUrl;if(asset.blob)return blobAsDataUrl(asset.blob);return ''}
async function openMaterialPicker(title,onChoose){
    const assets=(await listAllAssets()).filter(a=>a.type?.startsWith('image/'));
    const modal=$('#modal'),body=$('#modalBody');body.innerHTML=`<h2>${safeHtml(title||'Choose material')}</h2><p class="hint">Choose an image already stored in your material library.</p><div class="material-picker-grid"></div>`;
    const grid=body.querySelector('.material-picker-grid');
    if(!assets.length)grid.innerHTML='<p class="hint">No stored images yet. Upload one in Materials first.</p>';
    for(const asset of assets){const url=await usableAssetUrl(asset);if(!url)continue;const button=document.createElement('button');button.type='button';button.className='material-picker-card';button.innerHTML=`<img src="${safeHtml(url)}" alt=""><span>${safeHtml(asset.name||'Image')}</span>`;button.onclick=()=>{onChoose(url,asset);modal.close()};grid.append(button)}
    modal.showModal()
}
async function renderAssets() {
    let assets = await listAllAssets();
    const query=($('#assetSearch')?.value||'').trim().toLowerCase(),filter=$('#assetTypeFilter')?.value||'image',folderQuery=($('#assetFolderFilter')?.value||'').trim().toLowerCase();
    const filtered=assets.filter(a=>{const typeOk=filter==='all'||(filter==='image'&&a.type?.startsWith('image/'))||(filter==='audio'&&a.type?.startsWith('audio/'))||(filter==='video'&&a.type?.startsWith('video/'))||(filter==='favorites'&&a.favorite);const haystack=[a.name,a.folder,...(a.tags||[])].join(' ').toLowerCase();const searchOk=!query||haystack.includes(query);const folderOk=!folderQuery||String(a.folder||'').toLowerCase().includes(folderQuery);return typeOk&&searchOk&&folderOk});
    $('#assets').innerHTML = '';if($('#assetLibraryStats'))$('#assetLibraryStats').textContent=`${filtered.length} of ${assets.length} stored material${assets.length===1?'':'s'} shown`;
    filtered.forEach(a => {
        if(a.type?.startsWith('audio/')){const card=document.createElement('button');card.type='button';card.className='asset-audio-card';card.innerHTML=`<span>♫</span><strong>${safeHtml(a.name||'Audio')}</strong>${a.favorite?'<em>★</em>':''}`;card.onclick=()=>{state.music={assetId:a.id,name:a.name,url:a.serverUrl||''};$('#musicEnabled').checked=true;$('#musicState').textContent=`Selected: ${a.name}`;save()};card.oncontextmenu=e=>{e.preventDefault();openAssetOrganizer(a)};$('#assets').append(card);return}
        if(a.type?.startsWith('video/')){const card=document.createElement('button');card.type='button';card.className='asset-video-card';const src=a.serverUrl||(a.blob?URL.createObjectURL(a.blob):'');card.innerHTML=`<span class="asset-video-preview">▶</span><strong>${safeHtml(a.name||'Video')}</strong>${a.favorite?'<em>★</em>':''}`;card.onclick=async()=>{state.video={assetId:a.id,name:a.name,url:src||await usableAssetUrl(a),mime:a.type};$('#videoEnabled').checked=true;$('#videoState').textContent=`Selected: ${a.name}`;save()};card.oncontextmenu=e=>{e.preventDefault();openAssetOrganizer(a)};$('#assets').append(card);return}
        let img = new Image,
            src = a.serverUrl || (a.blob ? URL.createObjectURL(a.blob) : '');
        if (!src) return;
        img.src = src;
        img.title = `${a.name} — click to add`;
        img.onclick = () => {
            let o = createObject('img-' + Date.now(), 'image');
            const finish = source => {
                o.querySelector('img').src = source;
                o.querySelector('img').alt = a.name || 'Invitation image';
                o.dataset.alt = a.name || '';
                o.dataset.showInHero = 'true';
                o.dataset.showInGallery = 'true';
                $('#stage').append(o);
                state.galleryOrder = [...(state.galleryOrder || []), o.dataset.id];
                select(o);
                save()
            };
            if (a.serverUrl) finish(a.serverUrl);
            else if (a.blob) {
                let reader = new FileReader();
                reader.onload = () => finish(reader.result);
                reader.readAsDataURL(a.blob)
            }
        };
        img.oncontextmenu = e => { e.preventDefault(); openAssetOrganizer(a) };
        $('#assets').append(img)
    })
}

async function openAssetOrganizer(asset){
    const modal=$('#modal'),body=$('#modalBody');
    body.innerHTML=`<h2>Organize material</h2><p class="hint">Right-click any material to rename, categorize, tag, favorite, or delete it.</p><form id="assetOrganizerForm"><label>Name<input id="assetOrganizerName" maxlength="180" value="${safeHtml(asset.name||'')}"></label><label>Folder<input id="assetOrganizerFolder" maxlength="80" placeholder="e.g. Pre-wedding" value="${safeHtml(asset.folder||'')}"></label><label>Tags — comma separated<input id="assetOrganizerTags" maxlength="500" value="${safeHtml((asset.tags||[]).join(', '))}"></label><label class="toggle-row"><span>Favorite</span><input id="assetOrganizerFavorite" type="checkbox" ${asset.favorite?'checked':''}></label><div class="mini-actions"><button class="primary" type="submit">Save details</button><button id="deleteOrganizedAsset" class="danger" type="button">Delete material</button></div></form>`;
    body.querySelector('#assetOrganizerForm').onsubmit=async e=>{e.preventDefault();const payload={name:$('#assetOrganizerName').value.trim(),folder:$('#assetOrganizerFolder').value.trim(),tags:$('#assetOrganizerTags').value.split(',').map(x=>x.trim()).filter(Boolean).slice(0,30),favorite:$('#assetOrganizerFavorite').checked};try{if(asset.serverId&&localStorage.getItem('sovan-auth-token')){const updated=await api(`/api/assets/${asset.serverId}`,{method:'PUT',body:JSON.stringify(payload)});Object.assign(asset,{name:updated.name,folder:updated.folder,tags:updated.tags,favorite:updated.favorite})}else{Object.assign(asset,payload);if(!asset.remoteOnly)await assetStore.put(asset)}modal.close();renderAssets()}catch(error){alert(error.message||'Could not update material')}};
    body.querySelector('#deleteOrganizedAsset').onclick=async()=>{if(!(await uiConfirm(`Remove ${asset.name||'this material'}? Existing invitation objects using it will remain.`,{title:'Remove material',danger:true,confirmText:'Remove'})))return;try{if(asset.serverId&&serverInvite&&localStorage.getItem('sovan-auth-token'))await api(`/api/invitations/${asset.invitationId||serverInvite.id}/assets/${asset.serverId}`,{method:'DELETE'});if(!asset.remoteOnly)await assetStore.delete(asset.id);modal.close();renderAssets()}catch(error){alert(`The material could not be removed: ${error.message||'unknown error'}`)}};
    modal.showModal()
}
renderAssets();
$('#assetSearch')?.addEventListener('input',renderAssets);$('#assetTypeFilter')?.addEventListener('change',renderAssets);$('#assetFolderFilter')?.addEventListener('input',renderAssets);$('#refreshAssets')?.addEventListener('click',renderAssets);
$('#masterPageChooseMaterial')?.addEventListener('click',()=>openMaterialPicker('Master page background',url=>{$('#masterPageImage').value=url;$('#masterPageEnabled').checked=true;save()}));

async function saveCompleteInvitationTemplate(){
    capture();
    const body=$('#modalBody'),modal=$('#modal'),defaultName=`${state.fields?.names||'Invitation'} Design`;
    body.innerHTML=`<h2>Save complete invitation template</h2><p class="hint">This saves the entire reusable design, including visual pages, objects, section layouts, animation, palette, and structure. Guest-specific RSVP records are not part of the design document.</p><form id="fullTemplateForm"><label>Template name<input id="fullTemplateName" maxlength="120" required></label><label>Category<select id="fullTemplateCategory"><option>Wedding</option><option>Birthday</option><option>Business</option><option>Other</option></select></label><label>Description<textarea id="fullTemplateDescription" maxlength="500" placeholder="Describe the visual style and ideal use case"></textarea></label><label>Tags — comma separated<input id="fullTemplateTags" placeholder="Luxury, Khmer, Floral"></label><div class="dialog-actions"><button type="button" id="cancelFullTemplate">Cancel</button><button class="primary" type="submit">Save template</button></div></form>`;
    $('#fullTemplateName').value=defaultName;$('#fullTemplateCategory').value=['Wedding','Birthday','Business'].includes(state.eventType)?state.eventType:'Other';$('#cancelFullTemplate').onclick=()=>modal.close();
    $('#fullTemplateForm').onsubmit=async event=>{event.preventDefault();const name=$('#fullTemplateName').value.trim(),category=$('#fullTemplateCategory').value,description=$('#fullTemplateDescription').value.trim(),tags=$('#fullTemplateTags').value.split(',').map(x=>x.trim()).filter(Boolean),documentData=clone(capture());if(!name)return;const status=$('#templateSaveState');try{let saved;if(serverInvite&&localStorage.getItem('sovan-auth-token'))saved=await api('/api/templates',{method:'POST',body:JSON.stringify({name,category,description,tags,document:documentData})});else{let items;try{items=JSON.parse(localStorage.getItem(savedFullTemplatesKey)||'[]')}catch{items=[]}saved={id:crypto.randomUUID(),name,category,description,tags,document:documentData,createdAt:Date.now(),updatedAt:Date.now()};items.unshift(saved);localStorage.setItem(savedFullTemplatesKey,JSON.stringify(items.slice(0,100)))}if(status)status.textContent=`Saved template: ${saved.name}. It is now available from Create invitation on the dashboard.`;modal.close()}catch(error){alert(`The template could not be saved: ${error.message}`)}};modal.showModal()
}
$('#saveFullTemplateBtn')?.addEventListener('click',saveCompleteInvitationTemplate);

function setupTemplateEditMode(){
    if(!templateEditId||!localStorage.getItem('sovan-auth-token'))return;
    const anchor=$('#saveFullTemplateBtn');if(!anchor||$('#updateTemplateVersionBtn'))return;
    const button=document.createElement('button');button.id='updateTemplateVersionBtn';button.type='button';button.className='primary';button.textContent='Update template as new version';anchor.insertAdjacentElement('afterend',button);
    const note=document.createElement('p');note.className='hint';note.id='templateEditModeNote';note.textContent='Template edit mode: publishing this invitation does not update the template. Use the button above to save a new template version.';button.insertAdjacentElement('afterend',note);
    button.onclick=async()=>{if(!(await uiConfirm('Save the current complete design as a new version of the source template?',{title:'Update template version',confirmText:'Save new version'})))return;button.disabled=true;button.textContent='Saving template version…';try{const updated=await api(`/api/templates/${encodeURIComponent(templateEditId)}`,{method:'PUT',body:JSON.stringify({document:clone(capture())})});$('#templateSaveState').textContent=`Template updated to version ${updated.currentVersion}.`;note.textContent=`Template edit mode · Current saved version: ${updated.currentVersion}`;}catch(error){alert(`The template could not be updated: ${error.message}`)}finally{button.disabled=false;button.textContent='Update template as new version'}}
}
setupTemplateEditMode();


async function setupPublishingSettings(){
    if(!serverInvite||!localStorage.getItem('sovan-auth-token'))return;
    try{serverInvite=await api('/api/invitations/'+encodeURIComponent(serverInvite.id));inviteStore.write(`sovan-server-invite:${activeInviteId}`,serverInvite)}catch{}
    const slugInput=$('#publicSlug'),mode=$('#accessMode'),passwordLabel=$('#accessPasswordLabel'),password=$('#accessPassword'),status=$('#publishingSettingsState'),button=$('#savePublishingSettings');
    if(!slugInput||!mode||!button)return;slugInput.value=serverInvite.slug||'';mode.value=serverInvite.accessMode||'unlisted';passwordLabel.hidden=mode.value!=='password';
    mode.onchange=()=>passwordLabel.hidden=mode.value!=='password';
    button.onclick=async()=>{button.disabled=true;status.textContent='Saving publishing settings…';try{const slugResult=await api(`/api/invitations/${serverInvite.id}/slug`,{method:'PUT',body:JSON.stringify({slug:slugInput.value})});const accessResult=await api(`/api/invitations/${serverInvite.id}/access`,{method:'PUT',body:JSON.stringify({mode:mode.value,password:password.value})});serverInvite.slug=slugResult.slug;serverInvite.accessMode=accessResult.accessMode;slugInput.value=slugResult.slug;password.value='';inviteStore.write(`sovan-server-invite:${activeInviteId}`,serverInvite);status.innerHTML=`Saved. Public URL: <a href="${location.origin}${slugResult.url}" target="_blank">${location.origin}${slugResult.url}</a>${accessResult.accessMode==='password'?' · Password protected':''}`;}catch(error){status.textContent=error.message}finally{button.disabled=false}};
}

function snapshot() {
    return {
        id: crypto.randomUUID?.() || Date.now() + '',
        version: Date.now(),
        publishedAt: new Date().toISOString(),
        document: structuredClone(capture())
    }
}
$('#unpublishBtn')?.addEventListener('click',async()=>{if(!serverInvite)return alert('Unpublish is available when the backend is connected.');if(!(await uiConfirm('Take this invitation offline? Published version history will be preserved.',{title:'Unpublish invitation',danger:true,confirmText:'Unpublish'})))return;try{await api(`/api/invitations/${serverInvite.id}/unpublish`,{method:'POST',body:'{}'});serverInvite.published=false;$('#publishInfo').innerHTML='<strong>Unpublished</strong><br>The public link is currently offline. Version history is preserved.';alert('Invitation unpublished.')}catch(error){alert(error.message)}});

$('#publishBtn').onclick = async () => {
    let snap = snapshot();
    inviteStore.write(publishKey, snap);
    inviteStore.append(historyKey, snap);
    let message = 'Published locally. Guest preview now uses an immutable snapshot.';
    if (serverInvite) {
        try {
            let result = await api('/api/invitations/' + serverInvite.id + '/publish', {
                method: 'POST',
                body: JSON.stringify({
                    document: snap.document
                })
            });
            message = `Published! Public URL: ${location.origin+result.url}`;
            $('#publishInfo').dataset.publicUrl = result.url
        } catch {
            message += ' Server publishing is temporarily unavailable.'
        }
    }
    refreshPublish();
    alert(message)
};

function refreshPublish() {
    let p = inviteStore.read(publishKey);
    $('#publishInfo').innerHTML = p ? `<strong>Published</strong><br>${new Date(p.publishedAt).toLocaleString()}<br>Snapshot ${String(p.version).slice(-6)}` : 'No snapshot published yet.'
}

function safeHtml(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
}
function languageText(en, km, mode) {
    if (mode === 'km') return `<span class="i18n i18n-km khmer-text">${safeHtml(km || en)}</span>`;
    if (mode === 'both') return `<span class="i18n i18n-en">${safeHtml(en)}</span><span class="i18n i18n-km khmer-text">${safeHtml(km || en)}</span>`;
    return `<span class="i18n i18n-en">${safeHtml(en)}</span>`
}
function languageSwitcher(mode) {
    return mode === 'both' ? '<div class="language-switch" role="group" aria-label="Invitation language"><button type="button" data-guest-lang="en" class="active">EN</button><button type="button" data-guest-lang="km">ខ្មែរ</button></div>' : ''
}
function normalizedTelegram(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    if (/^https:\/\/t\.me\/[A-Za-z0-9_]{5,}$/i.test(raw)) return raw;
    const username = raw.replace(/^@/, '');
    return /^[A-Za-z0-9_]{5,}$/.test(username) ? `https://t.me/${username}` : ''
}
function featuredVideoMarkup(d) {
    if (d.settings?.videoEnabled !== true || !d.video?.url) return '';
    const url=String(d.video.url||'');
    if (!(url.startsWith('/uploads/') || url.startsWith('/data/uploads/') || /^https?:\/\//i.test(url) || /^data:video\/(?:mp4|webm);base64,/i.test(url))) return '';
    const mode=d.languageMode||'both';
    return `<section class="video-section reveal" style="${combinedSectionStyle(d,'video')}"><h2>${languageText('Featured Video','វីដេអូពិសេស',mode)}</h2><video class="invitation-video" controls playsinline preload="metadata" src="${safeHtml(url)}"></video></section>`
}

function contactMarkup(d) {
    if (d.settings?.contactEnabled === false) return '';
    const phone = String(d.contactPhone || '').trim(), telegram = normalizedTelegram(d.contactTelegram);
    const phoneHref = /^[+0-9() .-]{5,30}$/.test(phone) ? `tel:${phone.replace(/[^+0-9]/g, '')}` : '';
    if (!phoneHref && !telegram) return '';
    const mode = d.languageMode || 'both';
    return `<section class="contact-section reveal" style="${combinedSectionStyle(d,'contact')}"><h2>${languageText('Contact the hosts','ទំនាក់ទំនងម្ចាស់កម្មវិធី',mode)}</h2><div class="contact-actions">${phoneHref?`<a href="${safeHtml(phoneHref)}">☎ ${languageText('Call','ទូរស័ព្ទ',mode)}</a>`:''}${telegram?`<a href="${safeHtml(telegram)}" target="_blank" rel="noopener">✈ Telegram</a>`:''}</div></section>`
}
function templateDecorMarkup(theme) {
    const marks = {
        rose: '<span class="template-symbol">❦</span>',
        gold: '<span class="template-symbol khmer-ornament">◆ ◇ ◆</span>',
        emerald: '<span class="template-symbol">❧</span>',
        midnight: '<span class="template-symbol">✦ ✧ ✦</span>'
    };
    return marks[theme] || marks.rose
}
function customBlocksMarkup(d) {
    const mode = d.languageMode || 'both', blocks = (d.customBlocks || []).filter(block => block.enabled !== false);
    if (!blocks.length) return '';
    const layout = safeHtml(d.sectionLayouts?.custom || 'cards');
    return `<div class="custom-blocks custom-layout-${layout} reveal" style="${combinedSectionStyle(d,'custom')}">${blocks.map(block => `<section class="custom-info-block block-${safeHtml(block.type || 'custom')}"><div class="block-icon">${block.type==='story'?'♥':block.type==='dress-code'?'✦':block.type==='note'?'!':block.type==='quote'?'“':block.type==='accommodation'?'⌂':block.type==='gift'?'◇':'◇'}</div><h2>${languageText(block.heading||customBlockLabel(block.type),block.headingKm||block.heading||customBlockLabel(block.type),mode)}</h2><p>${languageText(block.body||'',block.bodyKm||block.body||'',mode)}</p></section>`).join('')}</div>`
}


function sectionAnimationStyle(d, name) {
    const setting = d.sectionAnimations?.[name] || initial.sectionAnimations?.[name] || { preset:'fade-up', duration:900 };
    const animation = animationName(setting.preset);
    return animation ? `animation-name:${animation};animation-duration:${Math.max(300,Math.min(3000,Number(setting.duration||900)))}ms` : 'animation:none'
}

function safeSectionImageUrl(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    if (/^https?:\/\//i.test(raw) || raw.startsWith('/data/uploads/') || /^data:image\/(?:jpeg|png|webp|gif);base64,/i.test(raw)) return raw;
    return ''
}

function sectionVisualStyle(d, name) {
    const value = d.sectionStyles?.[name];
    if (!value) return '';
    const rules = [];
    if (value.backgroundEnabled && /^#[0-9a-f]{6}$/i.test(value.background || '')) rules.push(`background-color:${value.background}`);
    const imageUrl = safeSectionImageUrl(value.backgroundImage);
    if (value.backgroundImageEnabled && imageUrl) {
        const overlay = Math.max(0, Math.min(80, Number(value.backgroundOverlay || 0))) / 100;
        const image = `url(&quot;${safeHtml(imageUrl)}&quot;)`;
        rules.push(`background-image:linear-gradient(rgba(0,0,0,${overlay}),rgba(0,0,0,${overlay})),${image}`, `background-size:${value.backgroundSize==='contain'?'contain':'cover'}`, 'background-position:center', 'background-repeat:no-repeat')
    }
    if (value.textColorEnabled && /^#[0-9a-f]{6}$/i.test(value.textColor || '')) rules.push(`color:${value.textColor}`, `--section-text:${value.textColor}`);
    const radius = Math.max(0, Math.min(60, Number(value.radius || 0)));
    if (radius) rules.push(`border-radius:${radius}px`);
    return rules.join(';')
}
function combinedSectionStyle(d, name) {
    return [sectionAnimationStyle(d,name), sectionVisualStyle(d,name)].filter(Boolean).join(';')
}

function objectDimension(value, axis='x') {
    return window.EInviteRenderer?.objectDimension ? EInviteRenderer.objectDimension(value,axis) : (!value ? (axis === 'x' ? '50%' : '80px') : value)
}
function imageFilterStyle(o) {
    return window.EInviteRenderer?.imageFilterStyle ? EInviteRenderer.imageFilterStyle(o) : ''
}

function advancedObjectStyle(o) {
    const blend = ['normal','multiply','screen','overlay','soft-light','darken','lighten'].includes(o.blendMode) ? o.blendMode : 'normal';
    const delay = Math.max(0, Math.min(5000, Number(o.animationDelay || 0)));
    let background = 'transparent';
    if (o.backgroundEnabled) {
        const hex = /^#[0-9a-f]{6}$/i.test(o.backgroundColor||'') ? o.backgroundColor : '#ffffff';
        const alpha = Math.max(0,Math.min(100,Number(o.backgroundOpacity ?? 100)))/100;
        const h=hex.slice(1); background=`rgba(${parseInt(h.slice(0,2),16)},${parseInt(h.slice(2,4),16)},${parseInt(h.slice(4,6),16)},${alpha})`;
    }
    return `mix-blend-mode:${blend};background:${background};animation-delay:${delay}ms`;
}
function advancedTextStyle(o) {
    const transform=['none','uppercase','lowercase','capitalize'].includes(o.textTransform)?o.textTransform:'none';
    const stroke=Math.max(0,Math.min(8,Number(o.textStrokeWidth||0))),strokeColor=/^#[0-9a-f]{6}$/i.test(o.textStrokeColor||'')?o.textStrokeColor:'#ffffff';
    const shadowBlur=Math.max(0,Math.min(40,Number(o.textShadowBlur||0))),shadowColor=/^#[0-9a-f]{6}$/i.test(o.textShadowColor||'')?o.textShadowColor:'#000000';
    const shadow=shadowBlur?`text-shadow:0 ${Math.max(1,Math.round(shadowBlur/4))}px ${shadowBlur}px ${shadowColor};`:'';
    const gradient=o.textGradientEnabled?`background-image:linear-gradient(${Math.max(0,Math.min(360,Number(o.textGradientAngle||90)))}deg,${safeHtml(o.textGradientStart||'#9d4555')},${safeHtml(o.textGradientEnd||'#b58a3a')});background-clip:text;-webkit-background-clip:text;color:transparent;`:'';
    return `text-transform:${transform};-webkit-text-stroke:${stroke}px ${strokeColor};${shadow}${gradient}`;
}
function shapeFillStyle(o) {
    return o.fillMode==='gradient' ? `linear-gradient(${Math.max(0,Math.min(360,Number(o.gradientAngle||135)))}deg,${safeHtml(o.gradientStart||'#d9a6ad')},${safeHtml(o.gradientEnd||'#9d4555')})` : safeHtml(o.fillColor||'#d9a6ad');
}

function artisticHeroMarkup(d) {
    const mode=d.languageMode||'both',f=d.fields||{},objects=Object.entries(d.objects||{}).filter(([,o])=>o.showInHero!==false&&o.visible!==false).sort(([,a],[,b])=>Number(a.zIndex||0)-Number(b.zIndex||0));
    if(!objects.length)return'';
    const contentFor=(id,o)=>{if(id==='title')return languageText(f.names||'',f.namesKm||f.names||'',mode);if(id==='subtitle')return languageText(f.message||'',f.messageKm||f.message||'',mode);if(id==='details'){const date=gregorianLabel(f),venue=languageText(f.venue||'',f.venueKm||f.venue||'',mode);return`${safeHtml(date)}${f.time?` · ${safeHtml(f.time)}`:''}<br>${venue}`}return window.EInviteRenderer?EInviteRenderer.sanitizeRichText(o.html||''):safeHtml(String(o.html||'').replace(/<[^>]+>/g,' ').trim())};
    const rendered=window.EInviteRenderer?.renderObject?objects.map(([id,o])=>EInviteRenderer.renderObject(o,{id,pageHeight:844,content:contentFor(id,o),heroTitle:id==='title'})).join(''):'';
    return`<section class="artistic-hero-section reveal" style="${sectionAnimationStyle(d,'hero')}"><div class="published-artboard">${rendered}</div></section>`
}

function galleryMarkup(d) {
    if (d.settings?.galleryEnabled === false) return '';
    const photos = orderedPhotos(d);
    if (!photos.length) return '';
    return `<section class="photo-gallery gallery-${safeHtml(d.galleryStyle||'grid')} reveal" style="${combinedSectionStyle(d,'gallery')}" aria-label="Photo gallery">${photos.map((photo,index)=>{
        const animation = animationName(photo.animation), duration = Math.max(300, Math.min(3000, +(photo.duration || 900))), delay = Math.min(index * .12, .72);
        return `<figure class="gallery-photo"><img src="${safeHtml(photo.src)}" alt="${safeHtml(photo.alt||`Celebration photo ${index+1}`)}" loading="${index?'lazy':'eager'}" class="reveal" style="animation-name:${animation};animation-duration:${duration}ms;animation-delay:${delay}s;object-fit:${safeHtml(photo.imageFit||'cover')};object-position:${Number(photo.imagePositionX??50)}% ${Number(photo.imagePositionY??50)}%;filter:${imageFilterStyle(photo)};transform:scaleX(${photo.imageFlipX?-1:1}) scaleY(${photo.imageFlipY?-1:1})">${photo.caption?`<figcaption>${safeHtml(photo.caption)}</figcaption>`:''}</figure>`
    }).join('')}</section>`
}
function bindLanguageSwitch(scope, mode) {
    if (mode !== 'both') return;
    const guest = scope.querySelector?.('.guest');
    if (!guest) return;
    const setLanguage = lang => {
        guest.dataset.language = lang;
        scope.querySelectorAll?.('[data-guest-lang]').forEach(button => button.classList.toggle('active', button.dataset.guestLang === lang));
        scope.querySelectorAll?.('option[data-en]').forEach(option => option.textContent = option.dataset[lang] || option.dataset.en)
    };
    scope.querySelectorAll?.('[data-guest-lang]').forEach(button => button.onclick = () => setLanguage(button.dataset.guestLang));
    setLanguage('en')
}

const palettePresets = {
    rose:{ background:'#fff6f3', surface:'#fffdfc', text:'#3d292f', heading:'#9d4555', accent:'#9d4555' },
    gold:{ background:'#fff9eb', surface:'#fffdf7', text:'#4b3716', heading:'#a87616', accent:'#a87616' },
    emerald:{ background:'#eef8f1', surface:'#ffffff', text:'#29443a', heading:'#1f7158', accent:'#1f7158' },
    midnight:{ background:'#100e19', surface:'#211b2d', text:'#f4efff', heading:'#c8b5ff', accent:'#8065c7' },
    'ivory-navy':{ background:'#f7f2e8', surface:'#fffdf8', text:'#263248', heading:'#1f365d', accent:'#b08a4b' }
};
function backgroundTextureImages(effect) {
    const opacity = Math.max(0, Math.min(60, Number(effect?.textureOpacity ?? 18))) / 100;
    const ink = `rgba(255,255,255,${(opacity*.45).toFixed(3)})`;
    const shade = `rgba(0,0,0,${(opacity*.24).toFixed(3)})`;
    const texture = effect?.texture || 'none';
    if (texture === 'dots') return [`radial-gradient(circle at 1px 1px,${ink} 1px,transparent 1.4px)`,'18px 18px'];
    if (texture === 'grid') return [`linear-gradient(${ink} 1px,transparent 1px),linear-gradient(90deg,${ink} 1px,transparent 1px)`,'28px 28px'];
    if (texture === 'paper') return [`radial-gradient(circle at 20% 20%,${ink},transparent 30%),radial-gradient(circle at 78% 64%,${shade},transparent 34%),linear-gradient(115deg,transparent,${ink},transparent)`,'auto'];
    if (texture === 'soft-grain') return [`radial-gradient(circle at 12% 18%,${ink} 0 1px,transparent 1.5px),radial-gradient(circle at 72% 68%,${shade} 0 1px,transparent 1.6px)`,'7px 7px,9px 9px'];
    return ['', 'auto']
}
function backgroundEffectStyle(d) {
    const effect = d?.backgroundEffects || initial.backgroundEffects;
    const valid = value => /^#[0-9a-f]{6}$/i.test(value||'') ? value : '#ffffff';
    const images=[]; let base='';
    if(effect.mode==='solid') base=`background-color:${valid(effect.start)}`;
    if(effect.mode==='gradient'){images.push(`linear-gradient(${Math.max(0,Math.min(360,Number(effect.angle||135)))}deg,${valid(effect.start)},${valid(effect.end)})`);base=`background-color:${valid(effect.start)}`}
    const [texture,size]=backgroundTextureImages(effect);if(texture)images.push(texture);
    if(images.length)base+=`;background-image:${images.join(',')};background-size:${size};background-attachment:scroll`;
    return base
}
function paletteRootStyle(d) {
    const valid = value => /^#[0-9a-f]{6}$/i.test(value||'') ? value : '#ffffff';
    const rules=[];
    if (d.palettePreset && d.palettePreset !== 'template') {
        const p = d.palette || palettePresets[d.palettePreset] || initial.palette;
        rules.push(`--palette-background:${valid(p.background)}`,`--palette-surface:${valid(p.surface)}`,`--palette-text:${valid(p.text)}`,`--palette-heading:${valid(p.heading)}`,`--palette-accent:${valid(d.accent||p.heading)}`)
    }
    const background = backgroundEffectStyle(d); if(background) rules.push(background);
    return rules.join(';')
}
function applyPaletteToEditor() {
    const stage = $('#stage'); if (!stage) return;
    const active = state.palettePreset && state.palettePreset !== 'template';
    stage.classList.toggle('palette-custom', !!active);
    if (active) {
        const p = state.palette || initial.palette;
        stage.style.setProperty('--palette-background', p.background); stage.style.setProperty('--palette-text', p.text); stage.style.setProperty('--palette-heading', p.heading);
        stage.style.background = p.background; stage.style.color = p.text
    } else {
        stage.style.removeProperty('--palette-background'); stage.style.removeProperty('--palette-text'); stage.style.removeProperty('--palette-heading'); stage.style.background = ''; stage.style.color = ''
    }
}

function applyBackgroundEffectsToEditor() {
    const stage = $('#stage'); if(!stage) return;
    const effect = state.backgroundEffects || initial.backgroundEffects;
    stage.dataset.backgroundMode=effect.mode||'none';stage.dataset.backgroundStart=effect.start||'#fff8f2';stage.dataset.backgroundEnd=effect.end||'#ead8d0';stage.dataset.backgroundAngle=String(effect.angle||135);stage.dataset.backgroundTexture=effect.texture||'none';stage.dataset.backgroundTextureOpacity=String(effect.textureOpacity??18);
    const mode=effect.mode||'none';const [texture,size]=backgroundTextureImages(effect);const images=[];
    if(mode==='gradient')images.push(`linear-gradient(${Number(effect.angle||135)}deg,${effect.start||'#fff8f2'},${effect.end||'#ead8d0'})`);
    if(texture)images.push(texture);
    if(mode==='solid')stage.style.backgroundColor=effect.start||'#fff8f2';
    else if(mode==='none')stage.style.backgroundColor=(state.palettePreset&&state.palettePreset!=='template')?(state.palette?.background||''):'';
    if(images.length){stage.style.backgroundImage=images.join(',');stage.style.backgroundSize=size}
    else {stage.style.backgroundImage='';stage.style.backgroundSize=''}
}

function designPageObjectMarkup(objects, pageHeight=844) {
    const entries=Object.entries(objects||{}).filter(([,o])=>o.visible!==false).sort(([,a],[,b])=>Number(a.zIndex||0)-Number(b.zIndex||0));
    if(window.EInviteRenderer?.renderObject)return entries.map(([id,o])=>EInviteRenderer.renderObject(o,{id,pageHeight,content:EInviteRenderer.sanitizeRichText(o.html||'')})).join('');
    return ''
}

function designPageMarkup(d, token) {
    if(!String(token||'').startsWith('page:'))return''; const id=String(token).slice(5),page=(d.designPages||[]).find(item=>item.id===id); if(!page||page.enabled===false)return'';
    const master=d.masterPageStyle||{},source=page.useMasterBackground&&master.enabled?master:page;
    const image=safeSectionImageUrl(source.backgroundImage),overlay=Math.max(0,Math.min(80,Number(source.backgroundOverlay||0)))/100,bg=/^#[0-9a-f]{6}$/i.test(source.background||'')?source.background:'#fffaf6',imageRules=image?`background-image:linear-gradient(rgba(0,0,0,${overlay}),rgba(0,0,0,${overlay})),url(&quot;${safeHtml(image)}&quot;);background-size:${source.backgroundSize==='contain'?'contain':'cover'};background-position:center;background-repeat:no-repeat;`:'';
    const animation=animationName(page.animation?.preset||'fade-up'),duration=Math.max(300,Math.min(3000,Number(page.animation?.duration||900))),motion=animation?`animation-name:${animation};animation-duration:${duration}ms`:'animation:none';
    const transition=['none','soft','overlap','sweep'].includes(page.transition?.preset)?page.transition.preset:'soft',transitionDuration=Math.max(200,Math.min(2000,Number(page.transition?.duration||600)));
    return`<section class="design-page-section reveal page-transition-${transition}" style="--page-transition-duration:${transitionDuration}ms;background:${bg};${imageRules}${motion}"><div class="published-artboard published-page-artboard">${designPageObjectMarkup(page.objects||{})}</div></section>`
}

function previewRsvpCustomFields(d,mode){return(d.rsvpFields||[]).map(field=>{const name=`custom_${String(field.id||'').replace(/[^A-Za-z0-9_-]/g,'')}`,label=languageText(field.label||'Question',field.labelKm||field.label||'Question',mode),required=field.required?' required':'',type=field.type||'text';if(type==='textarea')return`<label>${label}<textarea name="${safeHtml(name)}" maxlength="2000"${required}></textarea></label>`;if(type==='select')return`<label>${label}<select name="${safeHtml(name)}"${required}><option value="">${languageText('Select an option','សូមជ្រើសរើស',mode)}</option>${(field.options||[]).map(option=>`<option value="${safeHtml(option)}">${safeHtml(option)}</option>`).join('')}</select></label>`;if(type==='number')return`<label>${label}<input name="${safeHtml(name)}" type="number"${required}></label>`;return`<label>${label}<input name="${safeHtml(name)}" maxlength="2000"${required}></label>`}).join('')}

function guestHTML(snap) {
    let d = snap.document,
        f = d.fields || {},
        objs = Object.values(d.objects || {}),
        mode = d.languageMode || 'both',
        anim = objs[0]?.animation || 'fade-up',
        duration = Math.max(300, Math.min(3000, +(objs[0]?.duration || 900))),
        gregorian = gregorianLabel(f),
        khmer = d.khmerDate || khmerDateFor(f.date, f.time),
        dateBlock = d.dateFormat === 'khmer' ? `<h2 class="khmer-text">${safeHtml(khmer||gregorian)}</h2>` : d.dateFormat === 'gregorian' ? `<h2>${safeHtml(gregorian)}</h2>` : `<h2 class="khmer-text">${safeHtml(khmer||gregorian)}</h2><p>${safeHtml(gregorian)}</p>`,
        rsvp = d.settings?.rsvpEnabled === false ? '' : `<form id="guestRsvp" class="reveal" style="${combinedSectionStyle(d,'rsvp')}"><h2>${languageText('RSVP','សូមឆ្លើយតបការអញ្ជើញ',mode)}</h2><label>${languageText('Your name','ឈ្មោះរបស់អ្នក',mode)}<input name="name" required maxlength="120"></label><label>${languageText('Will you attend?','តើអ្នកនឹងចូលរួមទេ?',mode)}<select name="status"><option value="Yes, joyfully" data-en="Yes, joyfully" data-km="បាទ/ចាស ខ្ញុំនឹងចូលរួម">Yes, joyfully</option><option value="Unable to attend" data-en="Unable to attend" data-km="សូមអភ័យទោស ខ្ញុំមិនអាចចូលរួមបានទេ">Unable to attend</option><option value="Maybe" data-en="Maybe" data-km="ប្រហែលជា">Maybe</option></select></label><label>${languageText('Number of guests','ចំនួនភ្ញៀវ',mode)}<input name="count" type="number" min="1" max="10" value="1"></label>${previewRsvpCustomFields(d,mode)}<label>${languageText('Message','សារ',mode)}<textarea name="note" maxlength="1000"></textarea></label><button class="primary">${languageText('Send RSVP','ផ្ញើការឆ្លើយតប',mode)}</button></form>`,
        schedule = d.settings?.scheduleEnabled === false ? '' : `<section class="schedule-section schedule-layout-${safeHtml(d.sectionLayouts?.schedule||'timeline')} reveal" style="${combinedSectionStyle(d,'schedule')}"><h2>${languageText('Schedule','កម្មវិធី',mode)}</h2><div class="schedule-list">${(d.schedule||[]).map(x=>`<article><strong>${safeHtml(x.time)}</strong><span>${languageText(x.title||'',x.titleKm||x.title||'',mode)}</span></article>`).join('')}</div></section>`,
        countdown = d.settings?.countdownEnabled === false ? '' : `<section class="countdown-section countdown-layout-${safeHtml(d.sectionLayouts?.countdown||'cards')} reveal" style="${combinedSectionStyle(d,'countdown')}"><h2>${languageText(d.countdownTitle||'Counting down to our celebration',d.countdownTitleKm||d.countdownTitle||'រាប់ថយក្រោយ',mode)}</h2><div class="countdown" data-target="${safeHtml(`${f.date}T${f.time||'00:00'}:00`)}"><span><strong data-unit="days">0</strong>${languageText('Days','ថ្ងៃ',mode)}</span><span><strong data-unit="hours">0</strong>${languageText('Hours','ម៉ោង',mode)}</span><span><strong data-unit="minutes">0</strong>${languageText('Minutes','នាទី',mode)}</span><span><strong data-unit="seconds">0</strong>${languageText('Seconds','វិនាទី',mode)}</span></div></section>`,
        map = /^https?:\/\//i.test(d.mapUrl || '') ? `<p><a href="${safeHtml(d.mapUrl)}" target="_blank" rel="noopener"><button>${languageText('Open map','បើកផែនទី',mode)}</button></a></p>` : '',
        extraVenues = (d.venues || []).map(v => {
            let link = /^https?:\/\//i.test(v.mapUrl || '') ? `<br><a href="${safeHtml(v.mapUrl)}" target="_blank" rel="noopener">${languageText('Open map','បើកផែនទី',mode)}</a>` : '';
            return `<article class="venue-card"><strong>${languageText(v.name||'',v.nameKm||v.name||'',mode)}</strong><p>${languageText(v.address||'',v.addressKm||v.address||'',mode)}</p>${link}</article>`
        }).join(''),
        venue = d.settings?.venueEnabled === false ? '' : `<section class="venue-section venue-layout-${safeHtml(d.sectionLayouts?.venue||'cards')} reveal" style="${combinedSectionStyle(d,'venue')}"><h2>${languageText('Venue','ទីតាំងកម្មវិធី',mode)}</h2><div class="venue-card primary-venue"><strong>${languageText(f.venue||'',f.venueKm||f.venue||'',mode)}</strong>${map}</div>${extraVenues}</section>`,
        wishes = d.settings?.wishesEnabled === true ? `<form id="guestWish" class="reveal" style="${combinedSectionStyle(d,'wishes')}"><h2>${languageText('Send your wishes','ផ្ញើសារជូនពរ',mode)}</h2><label>${languageText('Your name','ឈ្មោះរបស់អ្នក',mode)}<input name="name" required maxlength="120"></label><label>${languageText('Your message','សារជូនពរ',mode)}<textarea name="message" required maxlength="2000"></textarea></label><button class="primary">${languageText('Send wishes','ផ្ញើសារជូនពរ',mode)}</button></form>` : '',
        key = animationName(anim),
        motion = `animation-name:${key};animation-duration:${duration}ms`,
        sections = { gallery: galleryMarkup(d), video: featuredVideoMarkup(d), countdown, schedule, custom: customBlocksMarkup(d), venue, contact: contactMarkup(d), wishes, rsvp },
        ordered = (d.sectionOrder || initial.sectionOrder).map(x => String(x).startsWith('page:') ? designPageMarkup(d,x) : (sections[x] || '')).join('');
    const theme = safeHtml(d.theme || 'rose');
    const paletteClass = d.palettePreset && d.palettePreset !== 'template' ? ' palette-applied' : '';
    return `<div class="guest theme-${theme} template-${theme}${paletteClass}" style="${paletteRootStyle(d)}" data-language="${mode==='km'?'km':'en'}">${languageSwitcher(mode)}${artisticHeroMarkup(d)}<section class="guest-hero guest-summary">${templateDecorMarkup(d.theme||'rose')}<p class="invite-kicker">${languageText('YOU ARE INVITED','សូមគោរពអញ្ជើញ',mode)}</p><div class="hero-date">${dateBlock}</div></section>${ordered}</div>`
}

function startCountdown(scope = document) {
    let box = scope.querySelector?.('.countdown');
    if (!box) return;
    let target = new Date(box.dataset.target).getTime(),
        tick = () => {
            let left = Math.max(0, target - Date.now()),
                values = {
                    days: Math.floor(left / 864e5),
                    hours: Math.floor(left / 36e5) % 24,
                    minutes: Math.floor(left / 6e4) % 60,
                    seconds: Math.floor(left / 1e3) % 60
                };
            Object.entries(values).forEach(([k, v]) => {
                let el = box.querySelector(`[data-unit="${k}"]`);
                if (el) el.textContent = String(v).padStart(2, '0')
            })
        };
    tick();
    return setInterval(tick, 1000)
}

function guestExperience(snap, musicUrl = '') {
    let d = snap.document,
        opening = d.settings?.openingEnabled !== false,
        youtube = d.settings?.musicEnabled === true && d.youtubeId,
        hasAudio = d.settings?.musicEnabled === true && !youtube && musicUrl,
        audio = hasAudio ? `<audio id="guestMusic" src="${musicUrl}" loop></audio>` : '',
        player = youtube ? `<iframe id="youtubePlayer" class="youtube-player" data-video-id="${d.youtubeId}" title="Invitation music" allow="autoplay; encrypted-media" referrerpolicy="strict-origin-when-cross-origin"></iframe>` : '',
        toggle = youtube || hasAudio ? '<button id="musicToggle" class="music-toggle" aria-label="Pause music">♫</button>' : '',
        coverName = d.languageMode === 'km' ? (d.fields?.namesKm || d.fields?.names || 'Open invitation') : (d.fields?.names || 'Open invitation'),
        cover = opening ? `<button id="openCover" class="open-cover opening-${safeHtml(d.openingStyle||'soft')}"><span>${d.languageMode==='km'?'សូមគោរពអញ្ជើញ':'YOU ARE INVITED'}</span><strong>${safeHtml(coverName)}</strong><em>${d.languageMode==='km'?'ចុចដើម្បីបើក':'Tap to open'}</em></button>` : '';
    return `${cover}${audio}${player}${toggle}${guestHTML(snap)}`
}

function startMusic(audio, player) {
    if (player && !player.src) {
        let id = player.dataset.videoId;
        player.src = `https://www.youtube.com/embed/${id}?autoplay=1&loop=1&playlist=${id}&enablejsapi=1&playsinline=1&origin=${encodeURIComponent(location.origin)}`
    } else audio?.play().catch(() => {})
}

function youtubeCommand(player, command) {
    player?.contentWindow?.postMessage(JSON.stringify({
        event: 'command',
        func: command,
        args: []
    }), 'https://www.youtube.com')
}
async function openGuest() {
    let p = inviteStore.read(publishKey) || snapshot(),
        musicUrl = p.document.music?.url || '';
    if (!musicUrl && p.document.music?.assetId) {
        let asset = (await assetStore.list()).find(a => String(a.id) === String(p.document.music.assetId));
        if (asset?.blob) musicUrl = URL.createObjectURL(asset.blob)
    }
    $('#modalBody').innerHTML = guestExperience(p, musicUrl);
    $('#modal').showModal();
    startCountdown($('#modalBody'));
    bindLanguageSwitch($('#modalBody'), p.document.languageMode || 'both');
    let audio = $('#guestMusic'),
        player = $('#youtubePlayer'),
        cover = $('#openCover'),
        toggle = $('#musicToggle'),
        playing = false,
        start = () => {
            startMusic(audio, player);
            playing = true
        };
    if (cover) cover.onclick = () => {
        cover.classList.add('opened');
        start()
    };
    else start();
    if (toggle) toggle.onclick = () => {
        playing ? (audio?.pause(), youtubeCommand(player, 'pauseVideo')) : (audio?.play().catch(() => {}), youtubeCommand(player, 'playVideo'));
        playing = !playing;
        toggle.textContent = playing ? '♫' : '♪'
    };
    let wishForm = $('#guestWish');
    if (wishForm) wishForm.onsubmit = e => {e.preventDefault();let rec=Object.fromEntries(new FormData(e.target));rec.id=crypto.randomUUID?.()||Date.now()+'';rec.createdAt=new Date().toISOString();inviteStore.append(`sovan-invite-wishes-v1:${activeInviteId}`,rec);e.target.innerHTML='<h2>Thank you!</h2><p>Your wishes have been saved.</p>'};
    let form = $('#guestRsvp');
    if (!form) return;
    form.onsubmit = e => {
        e.preventDefault();
        let rec = Object.fromEntries(new FormData(e.target));
        rec.id = crypto.randomUUID?.() || Date.now() + '';
        rec.createdAt = new Date().toISOString();
        rec.publishVersion = p.version;
        inviteStore.append(rsvpKey, rec);
        e.target.innerHTML = '<h2>Thank you!</h2><p>Your response has been saved.</p>'
    }
}
$('#previewBtn').onclick = openGuest;
$('#rsvpBtn').onclick = async () => {
    let rs = inviteStore.read(rsvpKey, []);
    if(serverInvite&&localStorage.getItem('sovan-auth-token')){try{rs=await api(`/api/invitations/${serverInvite.id}/rsvps`)}catch{}}
    const customLabels=Object.fromEntries((state.rsvpFields||[]).map(field=>[`custom_${field.id}`,field.label||field.labelKm||field.id]));
    $('#modalBody').innerHTML = `<div class="responses"><h1>RSVP responses (${rs.length})</h1>${rs.length?rs.map(r=>{const answers=r.answers||Object.fromEntries(Object.entries(r).filter(([key])=>key.startsWith('custom_')));const answerMarkup=Object.entries(answers||{}).filter(([,value])=>String(value||'').trim()).map(([key,value])=>`<div><small><strong>${safeHtml(customLabels[key]||key.replace(/^custom_/,''))}:</strong> ${safeHtml(value)}</small></div>`).join('');return`<div class="response"><strong>${safeHtml(r.name)}</strong> · ${safeHtml(r.status)} · ${safeHtml(r.guest_count??r.count??1)} guest(s)<br><small>${safeHtml(r.note||'')}</small>${answerMarkup}</div>`}).join(''):'<p>No responses yet. Submit one through Guest preview.</p>'}</div>`;
    $('#modal').showModal()
};
$('#wishesBtn')?.addEventListener('click',async()=>{let wishes=inviteStore.read(`sovan-invite-wishes-v1:${activeInviteId}`,[]);if(serverInvite&&localStorage.getItem('sovan-auth-token')){try{wishes=await api(`/api/invitations/${serverInvite.id}/wishes`)}catch{}}const render=()=>{$('#modalBody').innerHTML=`<div class="responses"><h1>Guest wishes (${wishes.length})</h1>${wishes.length?wishes.map(w=>`<div class="response"><strong>${safeHtml(w.name)}</strong><br><small>${safeHtml(w.message)}</small>${w.id&&serverInvite?`<br><button class="danger" data-delete-wish="${safeHtml(w.id)}">Delete</button>`:''}</div>`).join(''):'<p>No guest wishes yet.</p>'}</div>`;$$('[data-delete-wish]').forEach(button=>button.onclick=async()=>{if(!(await uiConfirm('Delete this guest wish?',{title:'Delete guest wish',danger:true,confirmText:'Delete'})))return;try{await api(`/api/invitations/${serverInvite.id}/wishes/${button.dataset.deleteWish}`,{method:'DELETE'});wishes=wishes.filter(x=>x.id!==button.dataset.deleteWish);render()}catch(error){alert(error.message)}})};render();$('#modal').showModal()});

$('#historyBtn').onclick = () => {
    let items = inviteStore.read(historyKey, []).slice().reverse();
    $('#modalBody').innerHTML = `<div class="responses"><h1>Published versions</h1>${items.length?items.map((p,i)=>`<div class="response"><strong>Version ${String(p.version).slice(-6)}</strong><br>${new Date(p.publishedAt).toLocaleString()} <button data-restore-version="${p.version}">Restore as draft</button></div>`).join(''):'<p>No versions published yet.</p>'}</div>`;
    $('#modal').showModal();
    $$('[data-restore-version]').forEach(b => b.onclick = () => {
        let p = items.find(x => String(x.version) === b.dataset.restoreVersion);
        state = structuredClone(p.document);
        inviteStore.write(draftKey, state);
        location.reload()
    })
};
$('#backupBtn').onclick = () => {
    let payload = {
        format: 'e-invitation-website-backup',
        version: 1,
        exportedAt: new Date().toISOString(),
        draft: capture(),
        published: inviteStore.read(publishKey),
        history: inviteStore.read(historyKey, []),
        rsvps: inviteStore.read(rsvpKey, [])
    };
    let a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {
        type: 'application/json'
    }));
    a.download = `invitation-backup-${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href)
};
$('#restoreBtn').onclick = () => $('#restoreFile').click();
$('#restoreFile').onchange = async e => {
    try {
        let data = JSON.parse(await e.target.files[0].text());
        if (!['e-invitation-website-backup','sovan-invite-backup'].includes(data.format) || !data.draft) throw Error();
        inviteStore.write(draftKey, data.draft);
        if (data.published) inviteStore.write(publishKey, data.published);
        inviteStore.write(historyKey, data.history || []);
        inviteStore.write(rsvpKey, data.rsvps || []);
        location.reload()
    } catch {
        alert('This is not a valid E-invitation-website backup.')
    }
};
const lunarMonths = ['មិគសិរ', 'បុស្ស', 'មាឃ', 'ផល្គុន', 'ចេត្រ', 'ពិសាខ', 'ជេស្ឋ', 'អាសាឍ', 'ស្រាពណ៍', 'ភទ្របទ', 'អស្សុជ', 'កត្តិក', 'បឋមាសាឍ', 'ទុតិយាសាឍ'];
$('#khmerDay').innerHTML = Array.from({
    length: 15
}, (_, i) => `<option value="${i+1}">${i+1}</option>`).join('');
$('#khmerMonth').innerHTML = lunarMonths.map((name, i) => `<option value="${i}">${name}</option>`).join('');
$('#useKhmerDate').onclick = () => {
    try {
        if (!window.momentkh) throw Error('Khmer calendar library is not available');
        let converted = momentkh.fromKhmer(+$('#khmerDay').value, +$('#khmerPhase').value, +$('#khmerMonth').value, +$('#khmerYear').value),
            pad = n => String(n).padStart(2, '0');
        $('#date').value = `${converted.year}-${pad(converted.month)}-${pad(converted.day)}`;
        syncFields()
    } catch (error) {
        alert(error.message || 'This Khmer lunar date could not be converted.')
    }
};
function nudgeSelection(direction, step = 1) {
    const stage = $('#stage').getBoundingClientRect();
    currentSelection().forEach(item => {
        if (item.dataset.locked === 'true') return;
        const rect = item.getBoundingClientRect();
        let left = (rect.left - stage.left) / stage.width * 100;
        let top = (rect.top - stage.top) / stage.height * 100;
        const width = rect.width / stage.width * 100, height = rect.height / stage.height * 100;
        if (direction === 'left') left -= step;
        if (direction === 'right') left += step;
        if (direction === 'up') top -= step;
        if (direction === 'down') top += step;
        item.style.left = Math.max(0, Math.min(100 - width, left)) + '%';
        item.style.top = Math.max(0, Math.min(100 - height, top)) + '%'
    });
    updateSelectionBounds();
    save()
}
function resizeSelection(factor) {
    currentSelection().forEach(item => {
        if (item.dataset.locked === 'true') return;
        item.style.width = Math.max(40, item.offsetWidth * factor) + 'px';
        item.style.height = Math.max(30, item.offsetHeight * factor) + 'px'
    });
    updateSelectionBounds();
    save()
}
document.querySelectorAll('[data-nudge]').forEach(b => b.onclick = () => nudgeSelection(b.dataset.nudge, 1));
document.querySelectorAll('[data-size]').forEach(b => b.onclick = () => resizeSelection(b.dataset.size === 'larger' ? 1.08 : .92));
$('.close').onclick = () => $('#modal').close();
$('#rsvpEnabled').checked = state.settings?.rsvpEnabled !== false;
$('#scheduleEnabled').checked = state.settings?.scheduleEnabled !== false;
$('#venueEnabled').checked = state.settings?.venueEnabled !== false;
$('#galleryEnabled').checked = state.settings?.galleryEnabled !== false;
if ($('#videoEnabled')) $('#videoEnabled').checked = state.settings?.videoEnabled === true;
$('#contactEnabled').checked = state.settings?.contactEnabled !== false;
    if ($('#wishesEnabled')) $('#wishesEnabled').checked = state.settings?.wishesEnabled === true;
$('#languageMode').value = state.languageMode || 'both';
$('#contactPhone').value = state.contactPhone || '';
$('#contactTelegram').value = state.contactTelegram || '';
$('#dateFormat').value = state.dateFormat || 'both';
$('#countdownEnabled').checked = state.settings?.countdownEnabled !== false;
$('#countdownTitle').value = state.countdownTitle || initial.countdownTitle;
$('#countdownTitleKm').value = state.countdownTitleKm || initial.countdownTitleKm;
$('#musicEnabled').checked = state.settings?.musicEnabled === true;
$('#openingEnabled').checked = state.settings?.openingEnabled !== false;
$('#designTheme').value = state.theme || 'rose';
$('#openingStyle').value = state.openingStyle || 'soft';
$('#musicState').textContent = state.music?.name ? `Selected: ${state.music.name}` : 'No music selected.';
if ($('#videoState')) $('#videoState').textContent = state.video?.name ? `Selected: ${state.video.name}` : 'No featured video selected.';
$('#youtubeUrl').value = state.youtubeUrl || '';
$('#time').value = state.fields?.time || '16:00';
$('#scheduleText').value = (state.schedule || initial.schedule).map(x => `${x.time} | ${x.title}`).join('\n');
$('#scheduleTextKm').value = (state.schedule || initial.schedule).map(x => `${x.time} | ${x.titleKm || ''}`).join('\n');
$('#mapUrl').value = state.mapUrl || '';
$('#venuesText').value = (state.venues || []).map(x => `${x.name || ''} | ${x.address || ''} | ${x.mapUrl||''}`).join('\n');
$('#venuesTextKm').value = (state.venues || []).map(x => `${x.nameKm || ''} | ${x.addressKm || ''}`).join('\n');
$('#sectionOrder').value = (state.sectionOrder || initial.sectionOrder).join('\n');
$('#namesKm').value = state.fields?.namesKm || '';
$('#venueKm').value = state.fields?.venueKm || '';
$('#messageKm').value = state.fields?.messageKm || '';
$('#undoBtn').onclick = undo;
$('#redoBtn').onclick = redo;
document.addEventListener('keydown', event => {
    const target = event.target;
    const typing = target && (target.matches?.('input,textarea,select') || target.isContentEditable);
    const modifier = event.ctrlKey || event.metaKey;
    const key = event.key.toLowerCase();
    if (modifier && key === 'z' && !event.shiftKey) { event.preventDefault(); return undo() }
    if (modifier && (key === 'y' || (key === 'z' && event.shiftKey))) { event.preventDefault(); return redo() }
    if (event.code === 'Space' && !typing) { spacePan = true; $('#canvasViewport').classList.add('pan-mode'); event.preventDefault(); return }
    if (typing) return;
    if (modifier && key === 'c') { event.preventDefault(); return copySelectionToClipboard() }
    if (modifier && key === 'v') { event.preventDefault(); return pasteObjectsFromClipboard() }
    if (modifier && key === 'd') { event.preventDefault(); return duplicateSelection() }
    if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); return deleteSelection() }
    if (event.key === 'Escape') return clearSelection();
    const arrows = { ArrowLeft:'left', ArrowRight:'right', ArrowUp:'up', ArrowDown:'down' };
    if (arrows[event.key] && currentSelection().length) {
        event.preventDefault();
        return nudgeSelection(arrows[event.key], event.shiftKey ? 5 : 1)
    }
});
document.addEventListener('keyup', event => { if (event.code === 'Space') { spacePan=false; if(!panMode) $('#canvasViewport').classList.remove('pan-mode') } });
window.addEventListener('resize', () => { updateSelectionBounds(); updateCanvasView() });
apply();
renderSavedGroups();
updateCanvasView();
pushHistory(capture());
connectServer();
