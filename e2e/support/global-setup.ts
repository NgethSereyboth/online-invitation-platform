import fs from 'node:fs';
import path from 'node:path';
import { request, type FullConfig } from '@playwright/test';
import { ApiClient, weddingDocument } from './api';
import { ADMIN, AUTH_DIR, OWNER, SEED_PATH, TENANT_B, uniqueSlug, type Seed } from './seed';

/**
 * Waits for the application origin and seeds all data the suites share:
 * three accounts (owner, second tenant for isolation checks, administrator),
 * their storage states, one published invitation, one deliberately unpublished
 * invitation owned by the second tenant, and one owned-but-unpublished draft.
 *
 * Nothing here touches src/. The server must already be running against an
 * isolated EINVITE_DATA_DIR (see docs/qa/PLAYWRIGHT-QA-REPORT.md).
 */
export default async function globalSetup(config: FullConfig) {
  const baseURL = (config.projects[0]?.use?.baseURL as string) || 'http://127.0.0.1:4310';
  fs.mkdirSync(AUTH_DIR, { recursive: true });

  const health = await request.newContext({ baseURL });
  const deadline = Date.now() + 90_000;
  let lastError = '';
  for (;;) {
    try {
      const res = await health.get('/api/health', { timeout: 5_000 });
      if (res.status() === 200) break;
      lastError = `HTTP ${res.status()}`;
    } catch (error) {
      lastError = String(error);
    }
    if (Date.now() > deadline) {
      await health.dispose();
      throw new Error(`Application origin ${baseURL} never answered /api/health (last: ${lastError}).`);
    }
    await new Promise((resolve) => setTimeout(resolve, 1_000));
  }
  await health.dispose();

  async function accountFor(email: string, password: string, file: string) {
    const context = await request.newContext({ baseURL });
    const api = new ApiClient(context, baseURL);
    const body = await api.ensureAccount(email, password);
    const target = path.join(AUTH_DIR, file);
    const state = await context.storageState({ path: target });
    // Registration returns the session cookie but not necessarily a body token;
    // reuse the double-submit cookie so seeded mutations pass the CSRF gate.
    const csrf = (body as { csrfToken?: string }).csrfToken
      ?? state.cookies.find((cookie) => cookie.name === 'einvite_csrf')?.value
      ?? '';
    const authedApi = new ApiClient(context, baseURL, csrf);
    return { api: authedApi, context, id: body.user.id, email, password, storageState: target };
  }

  const owner = await accountFor(OWNER.email, OWNER.password, 'owner.json');
  const tenantB = await accountFor(TENANT_B.email, TENANT_B.password, 'tenant-b.json');
  const admin = await accountFor(ADMIN.email, ADMIN.password, 'admin.json');

  // Login-failure tests must never consume the real accounts' failed-attempt
  // budget (five failures lock an account for 15 minutes). One throwaway
  // account per run keeps that budget isolated and repeatable.
  const victimEmail = `qa.victim.${Date.now().toString(36)}@einvite.test`;
  const victimContext = await request.newContext({ baseURL });
  const victimApi = new ApiClient(victimContext, baseURL);
  await victimApi.ensureAccount(victimEmail, 'Qa-Passw0rd-2026');
  await victimContext.storageState();
  await victimContext.dispose();

  // Published invitation the guest-page and RSVP journeys use.
  const slug = uniqueSlug('qa-wedding');
  const title = 'QA Wedding Alpha';
  const created = await owner.api.createInvitation(title, slug);
  const publication = await owner.api.publish(created.id, weddingDocument(title));

  // Second tenant's invitation: published, and never visible to the owner.
  const otherTitle = 'QA Tenant B Celebration';
  const otherSlug = uniqueSlug('qa-tenant-b');
  const otherCreated = await tenantB.api.createInvitation(otherTitle, otherSlug);
  await tenantB.api.publish(otherCreated.id, weddingDocument(otherTitle));

  // Owner's private draft: unpublished, so it must never resolve as a guest page.
  const draftTitle = 'QA Draft Only';
  const draftSlug = uniqueSlug('qa-draft');
  const draft = await owner.api.createInvitation(draftTitle, draftSlug);

  const seed: Seed = {
    baseURL,
    owner: { email: owner.email, password: owner.password, id: owner.id, storageState: owner.storageState },
    tenantB: { email: tenantB.email, password: tenantB.password, id: tenantB.id, storageState: tenantB.storageState },
    admin: { email: admin.email, password: admin.password, id: admin.id, storageState: admin.storageState },
    victim: { email: victimEmail, password: 'Qa-Passw0rd-2026' },
    invitation: {
      id: created.id,
      slug: created.slug,
      title,
      url: publication.url,
      publishedAt: publication.updatedAt,
    },
    otherInvitation: { id: otherCreated.id, slug: otherCreated.slug, title: otherTitle },
    emptyInvitation: { id: draft.id, slug: draft.slug, title: draftTitle },
  };
  fs.writeFileSync(SEED_PATH, JSON.stringify(seed, null, 2));

  for (const account of [owner, tenantB, admin]) await account.context.dispose();
}
