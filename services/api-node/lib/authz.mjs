// S10: invitation authorisation, copied from server.py's Handler helpers.
// Roles come from the invitation's owner and invitation_collaborators; the
// order matters because a deleted invitation demotes its owner to whatever
// collaborator row (if any) remains.
import { resolveSession } from './session.mjs';

export const AUTH_REQUIRED = { error: 'Authentication required' };
export const INVITATION_NOT_FOUND = { error: 'Invitation not found' };
export const MANAGEMENT_REQUIRED = { error: 'Invitation management permission required' };

export async function currentUser(db, request) {
  const session = await resolveSession(db, { cookieHeader: request.headers.cookie });
  return session?.user ?? null;
}

/** invitation_role(): "owner" | collaborator role | null. */
export async function invitationRole(db, invitationId, userId) {
  const owned = await db.query(
    'SELECT 1 FROM invitations WHERE id=? AND owner_id=? AND deleted_at IS NULL',
    [invitationId, userId],
  );
  if (owned.rows.length) return 'owner';
  const collaborator = await db.query(
    'SELECT role FROM invitation_collaborators WHERE invitation_id=? AND user_id=?',
    [invitationId, userId],
  );
  return collaborator.rows[0]?.role ?? null;
}

export const canReadInvitation = (role) => role !== null;
export const canEditInvitation = (role) => ['owner', 'content', 'designer', 'manager'].includes(role);
export const canManageInvitation = (role) => role === 'owner' || role === 'manager';

/** _invitation_role_from_row(): the same rule against a row already fetched. */
export function roleFromRow(row, userId) {
  if (!row) return null;
  if (row.owner_id === userId && row.deleted_at === null) return 'owner';
  return row.collaborator_role ?? null;
}
