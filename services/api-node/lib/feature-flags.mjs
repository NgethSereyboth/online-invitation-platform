// S12c: the feature-flag read used at page boot (features/feature_flags.py).
// The defaults, the merge order and the tier filter are copied; the 60-second
// process cache is copied deliberately — Python caches per process too, so an
// admin toggle is stale for the same window on both backends instead of
// diverging by "Node is fresher".
const CACHE_TTL_SECONDS = 60;

export const DEFAULT_FLAGS = {
  ai_agent_enabled: { value: true, description: 'Master switch for the AI creative agent', tier: null },
  canva_bridge_enabled: { value: true, description: 'Allow Canva import/export bridge', tier: null },
  plugin_marketplace_enabled: {
    value: true,
    description: 'Allow installing signed plugins from the marketplace',
    tier: 'creator',
  },
  collaboration_v52_enabled: {
    value: true,
    description: 'Use the Y.js CRDT V52 collaboration protocol',
    tier: null,
  },
  analytics_enabled: { value: true, description: 'Creator analytics tracking', tier: 'free' },
  analytics_live_enabled: {
    value: false,
    description: 'Live activity polling on creator dashboard',
    tier: 'creator',
  },
  guest_album_enabled: { value: true, description: 'Guest photo album on public invitation pages', tier: null },
  guest_signup_sheets_enabled: { value: true, description: 'Guest sign-up sheets', tier: null },
  guest_polls_enabled: { value: true, description: 'Guest polls', tier: null },
  guest_gift_registry_enabled: { value: true, description: 'Guest gift registry', tier: null },
  multi_channel_delivery_enabled: {
    value: true,
    description: 'SMS/WhatsApp/Telegram delivery channels',
    tier: 'creator',
  },
  maintenance_mode: {
    value: false,
    description: 'Return 503 to non-admins (maintenance window)',
    tier: null,
  },
};

let cache = null;
let cacheAt = 0;

export function invalidateFeatureFlags() {
  cache = null;
  cacheAt = 0;
}

/** _load_snapshot(): DB rows layered over the code defaults. */
export function loadFlagSnapshot(rows) {
  const snapshot = {};
  for (const [key, meta] of Object.entries(DEFAULT_FLAGS)) {
    snapshot[key] = {
      key,
      value: Boolean(meta.value),
      description: meta.description,
      tier: meta.tier ?? null,
      updatedAt: 0,
      updatedBy: '',
      source: 'default',
    };
  }
  for (const row of rows) {
    const key = row.key;
    if (!snapshot[key]) {
      snapshot[key] = {
        key,
        value: Boolean(row.value),
        description: row.description || '',
        tier: row.tier ?? null,
        updatedAt: Number(row.updated_at ?? 0),
        updatedBy: row.updated_by || '',
        source: 'db',
      };
      continue;
    }
    const entry = snapshot[key];
    entry.value = Boolean(row.value);
    entry.description = row.description || entry.description;
    entry.tier = row.tier !== null && row.tier !== undefined ? row.tier : entry.tier;
    entry.updatedAt = Number(row.updated_at ?? 0);
    entry.updatedBy = row.updated_by || '';
    entry.source = 'db';
  }
  return snapshot;
}

/** _snapshot(): 60-second process cache; a missing table degrades to defaults. */
export async function flagSnapshot(db) {
  const now = Date.now() / 1000;
  if (cache !== null && now - cacheAt <= CACHE_TTL_SECONDS) return cache;
  let rows = [];
  try {
    const result = await db.query(
      'SELECT key,value,description,tier,updated_at,updated_by FROM feature_flags',
    );
    rows = result.rows;
  } catch {
    rows = [];
  }
  cache = loadFlagSnapshot(rows);
  cacheAt = now;
  return cache;
}

export function isFlagEnabled(snapshot, key) {
  const flag = snapshot[key];
  if (flag) return Boolean(flag.value);
  return Boolean(DEFAULT_FLAGS[key]?.value);
}

/** public_flags_for_tier(): maintenance_mode is excluded by name, by design. */
export function publicFlagsForTier(snapshot, tier) {
  const out = {};
  for (const [key, entry] of Object.entries(snapshot)) {
    if (key === 'maintenance_mode') continue;
    const flagTier = entry.tier ?? null;
    if (flagTier === null || (tier && flagTier === tier)) out[key] = Boolean(entry.value);
  }
  return out;
}
