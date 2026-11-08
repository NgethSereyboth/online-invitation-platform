import type { APIRequestContext } from '@playwright/test';

export type DocumentModel = Record<string, unknown>;

/**
 * A valid schemaVersion-13 invitation document. Kept in one place so every
 * spec and the seeder publish the same shape the app actually accepts.
 */
export function weddingDocument(title: string, overrides: Partial<Record<string, unknown>> = {}): DocumentModel {
  return {
    schemaVersion: 13,
    fields: {
      names: title,
      date: '2027-03-14',
      time: '10:00',
      venue: 'The Riverside Ballroom, Phnom Penh',
      message: 'Together with our families, we warmly invite you to celebrate our wedding.',
    },
    objects: {},
    designPages: [],
    sectionOrder: ['events', 'guest-info', 'rsvp', 'wishes'],
    settings: {
      rsvpEnabled: true,
      wishesEnabled: true,
      openingEnabled: false,
      musicEnabled: false,
    },
    events: [
      {
        id: 'ceremony',
        name: 'Main Ceremony',
        type: 'ceremony',
        date: '2027-03-14',
        time: '10:00',
        venue: 'Royal Hall',
        enabled: true,
      },
    ],
    ...overrides,
  };
}

export class ApiClient {
  private csrf: string;

  constructor(
    private readonly ctx: APIRequestContext,
    readonly baseURL: string,
    csrf = '',
  ) {
    this.csrf = csrf;
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    return {
      Origin: this.baseURL,
      ...(this.csrf ? { 'X-CSRF-Token': this.csrf } : {}),
      ...extra,
    };
  }

  async login(email: string, password: string) {
    const res = await this.ctx.post('/api/auth/login', {
      data: { email, password },
      headers: { Origin: this.baseURL },
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok()) {
      throw new Error(`login ${email} failed: HTTP ${res.status()} ${JSON.stringify(body)}`);
    }
    this.csrf = body.csrfToken ?? '';
    return body as { user: { id: string; email: string; role: string }; csrfToken: string };
  }

  async register(email: string, password: string) {
    const res = await this.ctx.post('/api/auth/register', {
      data: { email, password },
      headers: { Origin: this.baseURL },
    });
    return { status: res.status(), body: await res.json().catch(() => ({})) };
  }

  /** Register when the account is new, otherwise sign in. Idempotent across runs. */
  async ensureAccount(email: string, password: string) {
    const created = await this.register(email, password);
    if (created.status >= 200 && created.status < 300) {
      this.csrf = (created.body as { csrfToken?: string }).csrfToken ?? '';
      return created.body as { user: { id: string; email: string; role: string } };
    }
    if (created.status !== 409) {
      throw new Error(`register ${email} failed: HTTP ${created.status} ${JSON.stringify(created.body)}`);
    }
    return this.login(email, password);
  }

  async get(path: string) {
    return this.ctx.get(path, { headers: { Origin: this.baseURL } });
  }

  async post(path: string, data: unknown, extra: Record<string, string> = {}) {
    return this.ctx.post(path, { data, headers: this.headers({ 'Content-Type': 'application/json', ...extra }) });
  }

  async put(path: string, data: unknown) {
    return this.ctx.put(path, { data, headers: this.headers({ 'Content-Type': 'application/json' }) });
  }

  async delete(path: string) {
    return this.ctx.delete(path, { headers: this.headers() });
  }

  async me() {
    const res = await this.get('/api/auth/me');
    return { status: res.status(), body: await res.json().catch(() => ({})) };
  }

  async createInvitation(title: string, slug: string) {
    const res = await this.post('/api/invitations', { slug, document: weddingDocument(title) });
    const body = await res.json().catch(() => ({}));
    if (!res.ok()) {
      throw new Error(`createInvitation failed: HTTP ${res.status()} ${JSON.stringify(body)}`);
    }
    return body as { id: string; slug: string; updatedAt: number };
  }

  async publish(invitationId: string, document: DocumentModel, expectedRevision: number | null = null) {
    const res = await this.post(`/api/invitations/${invitationId}/publish`, {
      document,
      expectedRevision,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok()) {
      throw new Error(`publish failed: HTTP ${res.status()} ${JSON.stringify(body)}`);
    }
    return body as { slug: string; url: string; updatedAt: number; version: number };
  }

  /** Public, unauthenticated RSVP submission: this is what a guest's form posts. */
  async rsvp(slug: string, payload: Record<string, unknown>) {
    return this.post(`/api/public/${slug}/rsvps`, payload);
  }

  async wish(slug: string, payload: Record<string, unknown>) {
    return this.post(`/api/public/${slug}/wishes`, payload);
  }

}
