import fs from 'node:fs';
import path from 'node:path';

/** Shared seed/state contract between global setup, fixtures and specs. */
export type Seed = {
  baseURL: string;
  owner: { email: string; password: string; id: string; storageState: string };
  tenantB: { email: string; password: string; id: string; storageState: string };
  admin: { email: string; password: string; id: string; storageState: string };
  /** Fresh account per run, used only for login-failure tests (never lock the owner). */
  victim: { email: string; password: string };
  invitation: { id: string; slug: string; title: string; url: string; publishedAt: number };
  otherInvitation: { id: string; slug: string; title: string };
  emptyInvitation: { id: string; slug: string; title: string };
};

export const ARTIFACTS = path.resolve(__dirname, '../../artifacts/playwright-e2e');
export const AUTH_DIR = path.join(ARTIFACTS, 'auth');
export const SEED_PATH = path.join(ARTIFACTS, 'seed.json');

export const OWNER = {
  email: process.env.E2E_OWNER_EMAIL || 'qa.owner@einvite.test',
  password: process.env.E2E_OWNER_PASSWORD || 'Qa-Passw0rd-2026',
};
export const TENANT_B = {
  email: 'qa.tenant-b@einvite.test',
  password: 'Qa-Passw0rd-2026',
};
export const ADMIN = {
  email: process.env.E2E_ADMIN_EMAIL || 'admin@einvite.test',
  password: 'Qa-Passw0rd-2026',
};

export function readSeed(): Seed {
  if (!fs.existsSync(SEED_PATH)) {
    throw new Error(
      `Seed file missing at ${SEED_PATH}. Run the suite through Playwright so global setup can seed the server.`,
    );
  }
  return JSON.parse(fs.readFileSync(SEED_PATH, 'utf8')) as Seed;
}

/** The 16 shipped front-end routes (src/html). */
export const ROUTES = [
  { path: '/index.html', name: 'Editor', auth: 'session', risk: 'High' },
  { path: '/dashboard.html', name: 'Dashboard', auth: 'session', risk: 'High' },
  { path: '/templates.html', name: 'Templates', auth: 'session', risk: 'Medium' },
  { path: '/guests.html', name: 'Guests', auth: 'session', risk: 'High' },
  { path: '/responses.html', name: 'Responses', auth: 'session', risk: 'High' },
  { path: '/analytics.html', name: 'Analytics', auth: 'session', risk: 'Medium' },
  { path: '/materials.html', name: 'Materials', auth: 'session', risk: 'Medium' },
  { path: '/checkin.html', name: 'Check-in', auth: 'session', risk: 'High' },
  { path: '/account.html', name: 'Account', auth: 'session', risk: 'High' },
  { path: '/billing.html', name: 'Billing', auth: 'session', risk: 'Medium' },
  { path: '/admin.html', name: 'Admin', auth: 'admin', risk: 'High' },
  { path: '/public.html', name: 'Public fallback', auth: 'none', risk: 'Low' },
  { path: '/privacy.html', name: 'Privacy', auth: 'none', risk: 'Low' },
  { path: '/reset.html', name: 'Password reset', auth: 'none', risk: 'Medium' },
  { path: '/verify.html', name: 'Email verification', auth: 'none', risk: 'Medium' },
  { path: '/designer.html', name: 'Designer workspace', auth: 'designer', risk: 'Low' },
] as const;

export function uniqueSlug(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}
