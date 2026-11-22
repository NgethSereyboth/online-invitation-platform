import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DEFAULT_FLAGS,
  invalidateFeatureFlags,
  loadFlagSnapshot,
  publicFlagsForTier,
} from '../lib/feature-flags.mjs';

test('defaults alone produce the documented tier-less public set', () => {
  const snapshot = loadFlagSnapshot([]);
  const flags = publicFlagsForTier(snapshot, null);
  assert.equal(flags.maintenance_mode, undefined, 'maintenance is excluded by name');
  assert.equal(flags.plugin_marketplace_enabled, undefined, 'creator-tier flag hidden anonymously');
  assert.equal(flags.ai_agent_enabled, true);
  assert.deepEqual(Object.keys(flags).sort(), Object.keys(DEFAULT_FLAGS).filter((k) => k !== 'maintenance_mode').filter((k) => DEFAULT_FLAGS[k].tier === null).sort());
});

test('DB rows override value, keep the default description, and only override tier when non-null', () => {
  const snapshot = loadFlagSnapshot([
    { key: 'ai_agent_enabled', value: 0, description: '', tier: null, updated_at: 42, updated_by: 'admin' },
    { key: 'analytics_enabled', value: 0, description: 'Custom copy', tier: null, updated_at: 43, updated_by: 'admin' },
  ]);
  assert.equal(snapshot.ai_agent_enabled.value, false);
  assert.equal(snapshot.ai_agent_enabled.description, DEFAULT_FLAGS.ai_agent_enabled.description);
  assert.equal(snapshot.ai_agent_enabled.tier, null);
  assert.equal(snapshot.ai_agent_enabled.source, 'db');
  assert.equal(snapshot.ai_agent_enabled.updatedAt, 42);
  assert.equal(snapshot.analytics_enabled.description, 'Custom copy');
  assert.equal(snapshot.analytics_enabled.tier, 'free', 'null tier keeps the default tier');
});

test('an unknown DB key is exposed as a flat flag', () => {
  const snapshot = loadFlagSnapshot([
    { key: 'custom_experiment', value: 1, description: 'Ad-hoc', tier: null, updated_at: 7, updated_by: 'admin' },
  ]);
  const flags = publicFlagsForTier(snapshot, null);
  assert.equal(flags.custom_experiment, true);
  assert.equal(snapshot.custom_experiment.source, 'db');
});

test('tier filtering matches only the caller\'s own tier', () => {
  const snapshot = loadFlagSnapshot([]);
  assert.equal(publicFlagsForTier(snapshot, 'free').analytics_enabled, true);
  assert.equal(publicFlagsForTier(snapshot, 'free').plugin_marketplace_enabled, undefined);
  assert.equal(publicFlagsForTier(snapshot, 'creator').plugin_marketplace_enabled, true);
  assert.equal(publicFlagsForTier(snapshot, 'creator').analytics_enabled, undefined);
  assert.equal(publicFlagsForTier(snapshot, 'pro').plugin_marketplace_enabled, undefined);
});

test('invalidation clears the cached snapshot', () => {
  invalidateFeatureFlags();
  assert.doesNotThrow(invalidateFeatureFlags);
});
