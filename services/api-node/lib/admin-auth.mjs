// Admin gate, copied from core/admin_ip_allowlist.py + _admin_gate():
// an IP allowlist check runs before authentication, then require_role.
import { currentUser } from './authz.mjs';

const ADMIN_ROLES = new Set(['admin', 'super_admin']);

function expandIPv6(address) {
  // Returns eight 16-bit groups as BigInts, or null when unparseable.
  let text = address;
  if (text.includes('%')) text = text.split('%')[0];
  let tail = [];
  if (text.includes('.')) {
    const lastColon = text.lastIndexOf(':');
    const v4 = text.slice(lastColon + 1).split('.').map(Number);
    if (v4.length !== 4 || v4.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return null;
    tail = [(v4[0] << 8) | v4[1], (v4[2] << 8) | v4[3]];
    text = `${text.slice(0, lastColon + 1)}0:0`;
  }
  const [head, rest] = text.split('::');
  const headParts = head ? head.split(':') : [];
  const restParts = rest !== undefined && rest !== '' ? rest.split(':') : [];
  const parts = rest === undefined ? headParts : [...headParts, ...new Array(8 - headParts.length - restParts.length).fill('0'), ...restParts];
  const groups = parts.slice(0, 8).map((part) => (/^[0-9a-fA-F]{1,4}$/.test(part) ? parseInt(part, 16) : null));
  if (groups.length !== 8 || groups.some((value) => value === null)) return null;
  if (tail.length) groups.splice(6, 2, ...tail);
  return groups.map((value) => BigInt(value));
}

function parseAddress(raw) {
  const text = String(raw ?? '').trim();
  if (!text) return null;
  if (text.includes(':')) {
    const mapped = /^::ffff:(\d+\.\d+\.\d+\.\d+)$/i.exec(text);
    if (mapped) return parseAddress(mapped[1]);
    const groups = expandIPv6(text);
    if (!groups) return null;
    let value = 0n;
    for (const group of groups) value = (value << 16n) | group;
    return { version: 6, value, bits: 128 };
  }
  const octets = text.split('.');
  if (octets.length !== 4) return null;
  let value = 0n;
  for (const octet of octets) {
    if (!/^\d{1,3}$/.test(octet)) return null;
    const part = Number(octet);
    if (part > 255) return null;
    value = (value << 8n) | BigInt(part);
  }
  return { version: 4, value, bits: 32 };
}

function parseNetwork(entry) {
  const [addressPart, prefixPart] = entry.split('/');
  const address = parseAddress(addressPart);
  if (!address) return null;
  const prefix = prefixPart === undefined ? address.bits : Number(prefixPart);
  if (!Number.isInteger(prefix) || prefix < 0 || prefix > address.bits) return null;
  return { version: address.version, prefix, value: address.value, bits: address.bits };
}

/** Parses EINVITE_ADMIN_IP_ALLOWLIST exactly like AdminIPAllowlist._parse(). */
export function parseAdminAllowlist(rawValue) {
  const raw = String(rawValue ?? '');
  if (!raw.trim()) return [];
  const networks = [];
  for (const entry of raw.split(',').map((part) => part.trim())) {
    if (!entry) continue;
    const network = parseNetwork(entry);
    if (!network) throw new Error(`Invalid CIDR/IP in EINVITE_ADMIN_IP_ALLOWLIST: ${entry}`);
    networks.push(network);
  }
  return networks;
}

export function addressInNetwork(address, network) {
  if (address.version !== network.version) return false;
  const shift = BigInt(network.bits - network.prefix);
  return address.value >> shift === network.value >> shift;
}

/** check_admin_ip_allowed(): an empty allowlist is unrestricted. */
export function checkAdminIpAllowed(clientIp, rawValue) {
  const networks = parseAdminAllowlist(rawValue);
  if (!networks.length) return true;
  const address = parseAddress(clientIp);
  if (!address) return false;
  return networks.some((network) => addressInNetwork(address, network));
}

/**
 * _admin_gate(): 403 "Insufficient permissions" when the IP is not allowed or
 * the role is not admin-level; 401 "Authentication required" without a session.
 * Returns the user, or null after the caller has already sent the response.
 */
export async function requireAdmin(db, request, reply, rawAllowlist) {
  if (!checkAdminIpAllowed(request.ip, rawAllowlist)) {
    await reply.code(403).send({ error: 'Insufficient permissions' });
    return null;
  }
  const user = await currentUser(db, request);
  if (!user) {
    await reply.code(401).send({ error: 'Authentication required' });
    return null;
  }
  if (!ADMIN_ROLES.has(user.role)) {
    await reply.code(403).send({ error: 'Insufficient permissions' });
    return null;
  }
  return user;
}
