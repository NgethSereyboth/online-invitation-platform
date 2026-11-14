// Python's str.lower() and str.strip() are not JavaScript's toLowerCase() and
// trim(). email_hash is built from them, so the difference is not cosmetic: it
// would produce a different hash for the same address.
//
//  * lower(): Unicode Final_Sigma — Σ lowercases to ς at the end of a word
//    ("ΑΣ".lower() == "ας"), which toLowerCase() renders "ασ".
//  * strip(): Python's whitespace set includes \x1c–\x1f, \x85 and the Unicode
//    spaces, while JS trim() also strips the BOM (\uFEFF), which Python keeps.
const PY_WHITESPACE = '\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000';
const STRIP_EDGES = new RegExp(`^[${PY_WHITESPACE}]+|[${PY_WHITESPACE}]+$`, 'g');

export function pythonStrip(value) {
  return String(value).replace(STRIP_EDGES, '');
}

export function pythonLower(value) {
  return String(value)
    .toLowerCase()
    .replace(/(\p{Cased})\u03C3(?!\p{Cased})/gu, (_match, before) => `${before}\u03C2`);
}
