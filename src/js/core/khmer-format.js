/*! core/khmer-format.js — Khmer numerals and locale-safe date/number formatting
 * LT-2.2 (OD-29), 2026-10-25.
 *
 * Pure, dependency-free helpers used by the guest page and the editor:
 *   - toKhmerDigits / toLatinDigits: digit conversion from Unicode code points.
 *     Khmer digits are generated with String.fromCodePoint(0x17E0 + n); no Khmer
 *     character is written into this file.
 *   - formatDate: Intl.DateTimeFormat with an explicit locale, optional Khmer
 *     digits (`nu-khmr`) and optional Buddhist Era calendar (`ca-buddhist`).
 *     A build without Khmer ICU data falls back to English month names, then
 *     converts the digits itself so the numeral setting still holds.
 *   - formatTime / formatNumber: the same numeral choice for clock labels and
 *     countdown values.
 *
 * The module never mutates stored invitation text. The editor command calls
 * toKhmerDigits() on the selected text only when the user runs it.
 */
(function (global) {
  'use strict';

  const KHMER_DIGIT_BASE = 0x17E0;
  const KHMER_DIGITS = Array.from({ length: 10 }, (_, digit) => String.fromCodePoint(KHMER_DIGIT_BASE + digit)).join('');
  const KHMER_DIGIT_PATTERN = new RegExp(
    '[' + String.fromCodePoint(KHMER_DIGIT_BASE) + '-' + String.fromCodePoint(KHMER_DIGIT_BASE + 9) + ']',
    'g'
  );

  function toKhmerDigits(value) {
    return String(value == null ? '' : value).replace(/[0-9]/g, digit => KHMER_DIGITS[Number(digit)]);
  }

  function toLatinDigits(value) {
    return String(value == null ? '' : value).replace(KHMER_DIGIT_PATTERN, character => String(character.codePointAt(0) - KHMER_DIGIT_BASE));
  }

  function hasKhmerDigits(value) {
    KHMER_DIGIT_PATTERN.lastIndex = 0;
    return KHMER_DIGIT_PATTERN.test(String(value == null ? '' : value));
  }

  function numeralsChoice(value) {
    return value === 'khmr' || value === true ? 'khmr' : 'latn';
  }

  function localeFor(language, numerals, era) {
    const base = language === 'km' ? 'km-KH' : 'en-US';
    const extensions = [];
    if (numerals === 'khmr') extensions.push('nu-khmr');
    if (era === 'be') extensions.push('ca-buddhist');
    return extensions.length ? base + '-u-' + extensions.join('-') : base;
  }

  function localeSupported(locale) {
    try {
      return Intl.DateTimeFormat.supportedLocalesOf([locale]).length > 0;
    } catch (error) {
      return false;
    }
  }

  function toDate(value) {
    if (value instanceof Date) return new Date(value.getTime());
    if (typeof value === 'number') {
      const fromNumber = new Date(value);
      return Number.isNaN(fromNumber.getTime()) ? null : fromNumber;
    }
    const text = String(value == null ? '' : value).trim();
    if (!text) return null;
    // Date-only values are calendar dates; parse them in local time so the
    // displayed day never shifts with the server's timezone.
    const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
    if (dateOnly) return new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]));
    const parsed = new Date(text);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function formatDate(value, options) {
    const settings = options || {};
    const date = toDate(value);
    if (!date) return String(value == null ? '' : value);
    const language = settings.lang === 'km' ? 'km' : 'en';
    const numerals = numeralsChoice(settings.numerals);
    const era = settings.era === 'be' ? 'be' : 'ce';
    let locale = localeFor(language, numerals, era);
    if (!localeSupported(locale)) locale = localeFor('en', numerals, era);
    if (!localeSupported(locale)) locale = 'en-US';
    let formatted;
    try {
      formatted = new Intl.DateTimeFormat(locale, { dateStyle: 'long' }).format(date);
    } catch (error) {
      formatted = date.toISOString().slice(0, 10);
    }
    if (numerals === 'khmr' && /[0-9]/.test(formatted)) formatted = toKhmerDigits(formatted);
    return formatted;
  }

  function formatTime(value, options) {
    const text = String(value == null ? '' : value).trim();
    const settings = options || {};
    if (!/^\d{1,2}:\d{2}/.test(text)) return text;
    const clock = /^\d{1,2}:\d{2}/.exec(text)[0];
    const rest = text.slice(clock.length);
    return (numeralsChoice(settings.numerals) === 'khmr' ? toKhmerDigits(clock) : clock) + rest;
  }

  function formatNumber(value, options) {
    const settings = options || {};
    const number = Number(value);
    if (!Number.isFinite(number)) return String(value == null ? '' : value);
    let formatted;
    try {
      formatted = new Intl.NumberFormat(settings.lang === 'km' ? 'km-KH' : 'en-US').format(number);
    } catch (error) {
      formatted = String(number);
    }
    return numeralsChoice(settings.numerals) === 'khmr' ? toKhmerDigits(formatted) : formatted;
  }

  global.EInviteKhmerFormat = Object.freeze({
    toKhmerDigits,
    toLatinDigits,
    hasKhmerDigits,
    formatDate,
    formatTime,
    formatNumber,
    numerals: numeralsChoice
  });
})(typeof window !== 'undefined' ? window : globalThis);
