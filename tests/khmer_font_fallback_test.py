#!/usr/bin/env python3
"""The Khmer font verdict: both branches of ``khmer_font_status``, exercised.

Goal 0b of docs/reviews/bulk-guest-import-research.md vendored a Khmer face so a
personalized guest card draws script instead of empty boxes, and reports the
verdict at startup with ``KHMER_FONT_STATUS ok …`` / ``KHMER_FONT_STATUS WARN …``.

The previous pass measured only the ``ok`` line: forcing the warning needed the
machine's own Khmer font hidden, which needs administrator rights. That is not
necessary. ``khmer_font_status`` resolves through ``khmer_font_candidates()``, so
pointing that function somewhere else exercises every branch in-process, without
touching the system fonts and without changing any production code:

* ``ok`` — the vendored face resolves and really is Khmer.
* the warning when the resolved file is a Latin-only face. This is risk 1's exact
  failure mode (a .woff2 subset Pillow cannot load, so the card silently drew
  DejaVu), and it is the branch the ``ok`` line alone cannot distinguish from
  success, because Pillow raises nothing in either case.
* the warning when no candidate file exists at all.
* the warning when fontTools is unavailable, so the resolved face cannot be
  verified — "cannot verify" must not be reported as "ready".

Every branch also asserts ``image_font(khmer=True)`` still returns a usable face
rather than raising or returning None, because that is what card rendering does
after the verdict is printed.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('EINVITE_DATA_DIR', tempfile.mkdtemp(prefix='einvite-khmer-font-fallback-'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src' / 'python'))

import pytest  # noqa: E402

import server  # noqa: E402

KHMER_SAMPLE = 'សុខ ដារា'


@pytest.fixture(autouse=True)
def fresh_verdict(monkeypatch):
    """``log_khmer_font_status`` memoizes its verdict; each test needs its own."""
    monkeypatch.setattr(server, '_KHMER_FONT_STATUS_CACHE', None, raising=False)
    yield


def latin_font_path():
    """A real font file that is usable but is not a Khmer face."""
    for candidate in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                      '/usr/share/fonts/truetype/lato/Lato-Medium.ttf',
                      '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                      'C:/Windows/Fonts/arial.ttf'):
        if Path(candidate).is_file():
            return candidate
    return ''


def usable(font):
    """A face that can lay out a Khmer string at all."""
    return font is not None and font.getlength(KHMER_SAMPLE) > 0


def warn_line(capsys):
    line = [row for row in capsys.readouterr().out.splitlines() if row.startswith('KHMER_FONT_STATUS')]
    assert line, 'the verdict was not printed'
    return line[-1]


def test_khmer_face_resolves_and_the_ok_branch_prints(capsys):
    status = server.khmer_font_status()
    assert status['khmerReady'] is True, status
    assert status['vendored'] is True, status
    assert status['reason'] == '', status

    server.log_khmer_font_status()
    printed = warn_line(capsys)
    assert printed.startswith('KHMER_FONT_STATUS ok '), printed
    assert 'vendored=True' in printed, printed
    assert 'support=ready' in printed, printed
    assert Path(status['resolved']).is_relative_to(ROOT), status['resolved']
    assert Path(status['resolved']).name == 'NotoSansKhmer-Regular.ttf', status['resolved']
    # The SVG-style forward-slash substring 'vendor/noto-khmer/' can never match a
    # native POSIX print on Windows, where the path carries backslashes; normalise
    # the separators so the same vendor/noto-khmer directory claim is asserted on
    # every platform instead of only on POSIX hosts.
    assert 'vendor/noto-khmer/' in printed.replace('\\', '/'), printed

    font = server.image_font(32, khmer=True)
    assert usable(font), 'a resolved Khmer face must be able to measure Khmer text'


def test_a_latin_face_is_reported_as_unusable_for_khmer(monkeypatch, capsys):
    """Risk 1: the face loads, so nothing raises — only the verdict tells."""
    path = latin_font_path()
    if not path:
        pytest.skip('no Latin-only font is available on this host')
    monkeypatch.setattr(server, 'khmer_font_candidates', lambda bold=False: [path])

    status = server.khmer_font_status()
    assert status['khmerReady'] is False, status
    assert status['resolved'] == path, status
    assert status['vendored'] is False, status
    assert status['reason'] == 'the resolved face is not usable for Khmer, so guest names would render as empty boxes', status

    server.log_khmer_font_status()
    printed = warn_line(capsys)
    assert printed.startswith('KHMER_FONT_STATUS WARN '), printed
    assert 'empty boxes' in printed, printed

    # The face still loads (Pillow raises nothing for a font with no Khmer
    # coverage) — which is exactly why the verdict, not an exception, is the signal.
    font = server.image_font(32, khmer=True)
    assert font is not None


def test_no_candidate_file_warns_and_names_where_to_vendor(monkeypatch, capsys):
    monkeypatch.setattr(server, 'khmer_font_candidates',
                        lambda bold=False: [str(Path('/nonexistent/khmer-regular.ttf')), str(Path('/nonexistent/khmer-bold.ttf'))])

    status = server.khmer_font_status()
    assert status['khmerReady'] is False, status
    assert status['resolved'] == '', status
    assert status['reason'] == 'no Khmer font file exists in any candidate path', status

    server.log_khmer_font_status()
    printed = warn_line(capsys)
    assert 'resolved=(none)' in printed, printed
    assert 'no Khmer font file exists in any candidate path' in printed, printed
    assert str(server.KHMER_FONT_DIR) in printed, printed

    # Card rendering never raises and never gets None: ``image_font`` still walks
    # its Latin fallbacks after the Khmer candidates all miss.
    font = server.image_font(32, khmer=True)
    assert usable(font), 'the Latin fallback must keep card rendering usable'


def test_unverifiable_face_is_not_reported_as_ready(monkeypatch, capsys):
    """No fontTools means "could not check", which must warn rather than pass."""
    monkeypatch.setitem(sys.modules, 'fontTools.ttLib', None)
    monkeypatch.delitem(sys.modules, 'fontTools', raising=False)

    status = server.khmer_font_status()
    assert status['khmerReady'] is False, status
    assert status['reason'] == 'fontTools is not installed, so the resolved face was not verified', status

    server.log_khmer_font_status()
    printed = warn_line(capsys)
    assert printed.startswith('KHMER_FONT_STATUS WARN '), printed
    assert 'fontTools is not installed' in printed, printed


def test_the_verdict_is_memoized_once_per_process(monkeypatch, capsys):
    """The startup line is printed once, not on every call."""
    server.log_khmer_font_status()
    server.log_khmer_font_status()
    server.log_khmer_font_status()
    printed = [row for row in capsys.readouterr().out.splitlines() if row.startswith('KHMER_FONT_STATUS')]
    assert len(printed) == 1, printed


if __name__ == '__main__':
    print('run under pytest: .venv/bin/python -m pytest tests/khmer_font_fallback_test.py -v')
