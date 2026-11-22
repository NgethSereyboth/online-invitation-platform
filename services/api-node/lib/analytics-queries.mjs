// S12c: the creator-analytics read model (features/analytics/queries.py).
// SQL, ordering, rounding and masking are copied; the only changes are the
// placeholder style (db.mjs rewrites `?`) and explicit number conversion,
// because psycopg hands Python Decimal strings where Node sees text too.
export function nowMs() {
  return Date.now();
}

/** Python round(): ties to even. SQL ROUND() is used wherever Python uses SQL. */
export function pyRound(value, digits = 0) {
  const factor = 10 ** digits;
  const scaled = value * factor;
  const floor = Math.floor(scaled);
  const diff = scaled - floor;
  let rounded;
  if (Math.abs(diff - 0.5) < 1e-9) rounded = floor % 2 === 0 ? floor : floor + 1;
  else rounded = Math.round(scaled);
  return rounded / factor;
}

export function utcDay(tsMs) {
  const date = new Date(tsMs);
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** _last_n_days(): UTC day strings, oldest first. */
export function lastNDays(now, count) {
  const out = [];
  for (let i = count - 1; i >= 0; i -= 1) out.push(utcDay(now - i * 24 * 60 * 60 * 1000));
  return out;
}

/** _extract_event_date(): fields.eventDate, meta.eventDate, settings.eventDate, eventDate. */
export function extractEventDate(doc) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) return 0;
  const candidates = [
    doc.fields?.eventDate,
    doc.meta?.eventDate,
    doc.settings?.eventDate,
    doc.eventDate,
  ];
  for (const value of candidates) {
    if (value) {
      const parsed = Math.trunc(Number(value));
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return 0;
}

function intOrZero(value) {
  if (value === null || value === undefined || value === '') return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.trunc(parsed) : 0;
}

/** invitation_analytics_summary(): the dashboard payload. */
export async function invitationAnalyticsSummary(db, invitationId, { days = 30 } = {}) {
  const window = Math.max(1, Math.min(days, 365));
  const now = nowMs();
  const periodStart = now - window * 24 * 60 * 60 * 1000;
  const prevStart = periodStart - window * 24 * 60 * 60 * 1000;

  async function periodStats(start, end) {
    const sessionRows = await db.query(
      'SELECT id, recipient_id, duration_ms, max_scroll_pct FROM analytics_sessions ' +
        'WHERE invitation_id=? AND started_at>=? AND started_at<?',
      [invitationId, start, end],
    );
    const totalViews = sessionRows.rows.length;
    const recipients = new Set();
    for (const row of sessionRows.rows) if (row.recipient_id) recipients.add(row.recipient_id);
    const durations = sessionRows.rows
      .filter((row) => row.duration_ms !== null && row.duration_ms !== undefined)
      .map((row) => intOrZero(row.duration_ms));
    const avgDur = durations.length
      ? Math.trunc(durations.reduce((sum, value) => sum + value, 0) / durations.length)
      : 0;
    const openRow = await db.query(
      "SELECT COUNT(*) AS n FROM analytics_events WHERE invitation_id=? AND event_type='invitation.rsvp.open' " +
        'AND created_at>=? AND created_at<?',
      [invitationId, start, end],
    );
    const submitRow = await db.query(
      "SELECT COUNT(*) AS n FROM analytics_events WHERE invitation_id=? AND event_type='invitation.rsvp.submit' " +
        'AND created_at>=? AND created_at<?',
      [invitationId, start, end],
    );
    const rsvpOpen = intOrZero(openRow.rows[0]?.n);
    const rsvpSubmit = intOrZero(submitRow.rows[0]?.n);
    const rsvpConv = rsvpOpen ? pyRound((rsvpSubmit / rsvpOpen) * 100, 1) : 0;
    return {
      totalViews,
      uniqueRecipients: recipients.size,
      avgDurationMs: avgDur,
      rsvpConversion: rsvpConv,
    };
  }

  const cur = await periodStats(periodStart, now);
  const prev = await periodStats(prevStart, periodStart);

  const delta = (current, previous) => {
    if (!previous) return current ? 100 : 0;
    return pyRound(((current - previous) / previous) * 100, 1);
  };

  const deltas = {
    totalViews: delta(cur.totalViews, prev.totalViews),
    uniqueRecipients: delta(cur.uniqueRecipients, prev.uniqueRecipients),
    avgDurationMs: delta(cur.avgDurationMs, prev.avgDurationMs),
    rsvpConversion: pyRound(cur.rsvpConversion - prev.rsvpConversion, 1),
  };

  const dayList = lastNDays(now, window);
  const timeRows = await db.query(
    "SELECT event_type, created_at FROM analytics_events WHERE invitation_id=? AND created_at>=? " +
      "AND event_type IN ('invitation.view', 'invitation.rsvp.submit')",
    [invitationId, periodStart],
  );
  const viewsByDay = Object.fromEntries(dayList.map((day) => [day, 0]));
  const rsvpsByDay = Object.fromEntries(dayList.map((day) => [day, 0]));
  for (const row of timeRows.rows) {
    const day = utcDay(intOrZero(row.created_at));
    if (day in viewsByDay) {
      if (row.event_type === 'invitation.view') viewsByDay[day] += 1;
      else if (row.event_type === 'invitation.rsvp.submit') rsvpsByDay[day] += 1;
    }
  }

  const distinct = async (eventType) => {
    const result = await db.query(
      'SELECT COUNT(DISTINCT session_id) AS n FROM analytics_events WHERE invitation_id=? AND event_type=?',
      [invitationId, eventType],
    );
    return intOrZero(result.rows[0]?.n);
  };
  const funnelView = await distinct('invitation.view');
  const funnelOpen = await distinct('invitation.rsvp.open');
  const funnelSubmit = await distinct('invitation.rsvp.submit');
  const base = Math.max(1, funnelView);
  const funnel = [
    { step: 'view', count: funnelView, pct: pyRound(100.0, 1) },
    { step: 'rsvp.open', count: funnelOpen, pct: pyRound((funnelOpen / base) * 100, 1) },
    { step: 'rsvp.submit', count: funnelSubmit, pct: pyRound((funnelSubmit / base) * 100, 1) },
  ];

  const refRows = await db.query(
    'SELECT referrer_domain, COUNT(*) AS n FROM analytics_sessions ' +
      "WHERE invitation_id=? AND referrer_domain IS NOT NULL AND referrer_domain<>'' " +
      'GROUP BY referrer_domain ORDER BY n DESC',
    [invitationId],
  );
  const topRefs = [];
  let otherCount = 0;
  for (const row of refRows.rows) {
    const count = intOrZero(row.n);
    if (count < 3) otherCount += count;
    else topRefs.push({ domain: row.referrer_domain, count });
  }
  if (otherCount) topRefs.push({ domain: 'Other', count: otherCount });

  const scrollRows = await db.query(
    'SELECT max_scroll_pct FROM analytics_sessions WHERE invitation_id=? AND max_scroll_pct IS NOT NULL',
    [invitationId],
  );
  const scrolls = scrollRows.rows.map((row) => intOrZero(row.max_scroll_pct));
  const avgScroll = scrolls.length
    ? pyRound(scrolls.reduce((sum, value) => sum + value, 0) / scrolls.length, 1)
    : 0;
  const buckets = [
    { pct: 25, count: scrolls.filter((value) => value < 25).length },
    { pct: 50, count: scrolls.filter((value) => value >= 25 && value < 50).length },
    { pct: 75, count: scrolls.filter((value) => value >= 50 && value < 75).length },
    { pct: 100, count: scrolls.filter((value) => value >= 75).length },
  ];

  const devRows = await db.query(
    'SELECT device_type, COUNT(*) AS n FROM analytics_sessions WHERE invitation_id=? GROUP BY device_type',
    [invitationId],
  );
  const colors = { mobile: '#3b82f6', tablet: '#a855f7', desktop: '#10b981' };
  const deviceTotal = devRows.rows.reduce((sum, row) => sum + intOrZero(row.n), 0) || 1;
  let deviceSplit = devRows.rows.map((row) => ({
    label: row.device_type || 'desktop',
    value: intOrZero(row.n),
    color: colors[row.device_type] ?? '#64748b',
  }));
  if (!deviceSplit.length) deviceSplit = [{ label: 'desktop', value: 0, color: colors.desktop }];

  const countryRows = await db.query(
    'SELECT country_code, COUNT(*) AS n FROM analytics_sessions ' +
      "WHERE invitation_id=? AND country_code IS NOT NULL AND country_code<>'' " +
      'GROUP BY country_code ORDER BY n DESC LIMIT 5',
    [invitationId],
  );
  const countrySplit = countryRows.rows.map((row) => ({
    code: row.country_code,
    count: intOrZero(row.n),
  }));

  return {
    stats: { ...cur, deltas },
    timeseries: {
      days: dayList,
      views: dayList.map((day) => viewsByDay[day] ?? 0),
      rsvps: dayList.map((day) => rsvpsByDay[day] ?? 0),
    },
    funnel,
    topReferrers: topRefs,
    scrollDepth: { average: avgScroll, buckets },
    deviceSplit,
    countrySplit,
    deviceTotal,
  };
}

/** invitation_live_activity(): active sessions + last event timestamp. */
export async function invitationLiveActivity(db, invitationId) {
  const now = nowMs();
  const cutoff = now - 5 * 60 * 1000;
  const active = await db.query(
    'SELECT COUNT(DISTINCT s.id) AS n FROM analytics_sessions s ' +
      'LEFT JOIN analytics_events e ON e.session_id = s.id ' +
      'WHERE s.invitation_id=? AND (s.ended_at IS NULL OR s.ended_at >= ?) ' +
      'AND (e.created_at IS NULL OR e.created_at >= ?)',
    [invitationId, cutoff, cutoff],
  );
  const last = await db.query(
    'SELECT MAX(created_at) AS last FROM analytics_events WHERE invitation_id=?',
    [invitationId],
  );
  const activeValue = active.rows[0]?.n;
  const lastValue = last.rows[0]?.last;
  return {
    activeSessions: activeValue === null || activeValue === undefined ? 0 : intOrZero(activeValue),
    lastEventAt: lastValue === null || lastValue === undefined ? null : intOrZero(lastValue),
  };
}

const SORT_COLUMNS = {
  title: 'title',
  eventDate: 'event_date',
  status: 'status',
  views: 'views',
  avgDurationMs: 'avg_dur',
  rsvps: 'rsvps',
  conversion: 'conversion',
  updatedAt: 'updated_at',
};

/** account_creations_table(): sort/filter/limit stay on the server, as in Python. */
export async function accountCreationsTable(
  db,
  ownerId,
  { sort = 'updatedAt', order = 'desc', statusFilter = null, limit = 100, offset = 0 } = {},
) {
  const sortCol = SORT_COLUMNS[sort] ?? 'updated_at';
  const orderDir = String(order).toLowerCase() === 'asc' ? 'ASC' : 'DESC';
  const where = ['i.owner_id=?', 'i.deleted_at IS NULL'];
  const params = [ownerId];
  if (['draft', 'published', 'archived'].includes(statusFilter)) {
    if (statusFilter === 'draft') {
      where.push('i.is_published=0');
      where.push('i.archived=0');
    } else if (statusFilter === 'published') {
      where.push('i.is_published=1');
      where.push('i.archived=0');
    } else if (statusFilter === 'archived') {
      where.push('i.archived=1');
    }
  }
  const sql =
    'SELECT i.id AS id, i.slug AS slug, i.draft_json AS draft_json, ' +
    'i.is_published AS is_published, i.archived AS archived, i.updated_at AS updated_at, ' +
    'COALESCE(a.views, 0) AS views, COALESCE(a.avg_dur, 0) AS avg_dur, ' +
    'COALESCE(a.rsvps, 0) AS rsvps, ' +
    'CASE WHEN a.views > 0 THEN ROUND(100.0 * a.rsvps / a.views, 1) ELSE 0.0 END AS conversion, ' +
    'a.last_activity AS last_activity ' +
    'FROM invitations i LEFT JOIN (' +
    'SELECT s.invitation_id AS invitation_id, COUNT(DISTINCT s.id) AS views, ' +
    'AVG(s.duration_ms) AS avg_dur, ' +
    "SUM(CASE WHEN e.event_type='invitation.rsvp.submit' THEN 1 ELSE 0 END) AS rsvps, " +
    'MAX(e.created_at) AS last_activity ' +
    'FROM analytics_sessions s LEFT JOIN analytics_events e ON e.session_id = s.id ' +
    'GROUP BY s.invitation_id' +
    ') a ON a.invitation_id = i.id ' +
    `WHERE ${where.join(' AND ')} ORDER BY ${sortCol} ${orderDir} LIMIT ? OFFSET ?`;
  params.push(Number(limit), Number(offset));
  const rows = await db.query(sql, params);
  const items = rows.rows.map((row) => {
    let doc = {};
    try {
      doc = row.draft_json ? JSON.parse(row.draft_json) : {};
    } catch {
      doc = {};
    }
    const title =
      doc?.fields?.names || doc?.meta?.title || 'Untitled invitation';
    const status = row.archived ? 'archived' : row.is_published ? 'published' : 'draft';
    return {
      id: row.id,
      slug: row.slug,
      title,
      eventDate: intOrZero(extractEventDate(doc) || 0),
      status,
      views: intOrZero(row.views),
      avgDurationMs: intOrZero(row.avg_dur),
      rsvps: intOrZero(row.rsvps),
      conversion: Number(row.conversion ?? 0),
      lastActivity: intOrZero(row.last_activity),
      updatedAt: intOrZero(row.updated_at),
    };
  });
  return {
    items,
    sort,
    order: orderDir.toLowerCase(),
    limit: Number(limit),
    offset: Number(offset),
    count: items.length,
  };
}

/** account_analytics_summary(): the account rollup. */
export async function accountAnalyticsSummary(db, ownerId) {
  const rows = await db.query(
    'SELECT i.id AS id, COALESCE(a.views, 0) AS views, COALESCE(a.rsvps, 0) AS rsvps ' +
      'FROM invitations i LEFT JOIN (' +
      'SELECT s.invitation_id AS invitation_id, COUNT(DISTINCT s.id) AS views, ' +
      "SUM(CASE WHEN e.event_type='invitation.rsvp.submit' THEN 1 ELSE 0 END) AS rsvps " +
      'FROM analytics_sessions s LEFT JOIN analytics_events e ON e.session_id = s.id ' +
      'GROUP BY s.invitation_id' +
      ') a ON a.invitation_id = i.id ' +
      'WHERE i.owner_id=? AND i.deleted_at IS NULL',
    [ownerId],
  );
  const totalInvitations = rows.rows.length;
  const totalViews = rows.rows.reduce((sum, row) => sum + intOrZero(row.views), 0);
  const totalRsvps = rows.rows.reduce((sum, row) => sum + intOrZero(row.rsvps), 0);
  const avgViews = totalInvitations ? pyRound(totalViews / totalInvitations, 1) : 0;
  return {
    totalInvitations,
    totalViews,
    totalRsvps,
    averageViewsPerInvitation: avgViews,
    accountConversion: totalViews ? pyRound((totalRsvps / totalViews) * 100, 1) : 0,
  };
}
