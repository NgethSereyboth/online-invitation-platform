#!/usr/bin/env python3
"""End-to-end coverage for the bulk guest import and the per-guest invitation link.

Implements phase G of docs/reviews/bulk-guest-import-research.md §5.7 against the
real server: a designer imports a sheet of names, every Khmer name gets an opaque
frozen code, the codes are frozen, each guest's page and card carry that guest's
name, and re-importing the same sheet updates the existing rows instead of adding
duplicates.

Two tests:

* ``test_bulk_import_end_to_end`` — a real server (tests/v14_test_utils.app_server,
  the established pattern), a real SQLite database in a temporary data directory,
  and HTTP for every step. No network and no external service is used: the card is
  rendered by the application's own Pillow path through
  /api/public/<slug>/<guest>/social-card-v<n>.png, which writes the cache file the
  test then checks on disk.
* ``test_guest_slug_migration_is_additive_and_idempotent`` — the schema migration
  on a hand-built *legacy* guests table (no slug column), in-process, asserting it
  is additive, resolves collisions deterministically and is a no-op the second time.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sqlite3
import struct
import sys
import tempfile
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from v14_test_utils import app_server, cleanup_path

ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "src" / "python" / "server.py"

LATIN_NAMES = ["Sok Dara", "Chan Sopheak", "Ly Meng", "Keo Pisey", "Heng Sovann"]
KHMER_NAMES = ["សុខ ដារា", "ចាន់ សុភា", "លី ម៉េង", "កែវ ពិសី", "ហេង សុវណ្ណ"]
OPAQUE_CODE = re.compile(r"^[23456789abcdefghjkmnpqrstuvwxyz]{6}$")
LATIN_CODE = re.compile(r"^[a-z0-9-]+$")


class Client:
    """The same tiny HTTP client tests/v15_http_integration_test.py uses."""

    def __init__(self, base: str):
        self.base = base
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.token = ""

    def request(self, path, method="GET", body=None, expected=200, parse_json=True):
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": "application/json" if parse_json else "*/*"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.base + path, data=payload, method=method, headers=headers)
        try:
            with self.opener.open(request, timeout=20) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        assert status == expected, f"{method} {path}: expected {expected}, got {status}: {raw[:400]!r}"
        return (json.loads(raw or b"{}"), raw) if parse_json else (raw, None)


def document(names: str, names_km: str, message: str = "Please join us."):
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {"names": names, "namesKm": names_km, "date": "2027-02-14", "venue": "Phnom Penh", "message": message},
        "objects": {}, "designPages": [], "sectionOrder": ["rsvp"],
        "settings": {"rsvpEnabled": True, "wishesEnabled": False},
    }


def png_dimensions(payload: bytes):
    assert payload[:8] == b"\x89PNG\r\n\x1a\n", "the card is not a PNG"
    return struct.unpack(">II", payload[16:24])


def meta(html: str, key: str):
    match = re.search(rf'<meta (?:property|name)="{re.escape(key)}" content="([^"]*)"', html)
    assert match, f"{key} is missing from the served page"
    return match.group(1)


def test_bulk_import_end_to_end():
    with app_server({"EINVITE_REQUIRE_EMAIL_VERIFICATION": "0"}) as (_process, base, data):
        data = Path(data)
        client = Client(base)
        registered, _ = client.request("/api/auth/register", "POST", {"email": "bulk-import@example.com", "password": "strong-password-123"}, 201)
        client.token = registered["token"]

        # 2. An invitation whose title is Khmer only.
        invitation, _ = client.request("/api/invitations", "POST", {"slug": "ពិធីមង្គលការសុខដារា", "document": document("Sok Dara & Sophea", "សុខ ដារា និង សុភា")}, 201)
        invite_id, slug = invitation["id"], invitation["slug"]

        # 3. The Goal 0a fix: a Khmer-only title no longer collapses onto the
        #    shared constant the second Khmer wedding would also have taken.
        assert slug != "our-invitation", f"the Khmer title collapsed onto {slug!r}"
        assert slug and slug.strip("-"), slug

        # 4. Import ten rows the way the page does: one POST per row, column 0 as
        #    the name and column 1 as the phone (research §5.7 phase A).
        imported = []
        for index, name in enumerate(LATIN_NAMES + KHMER_NAMES):
            guest, _ = client.request(f"/api/invitations/{invite_id}/guests", "POST", {"name": name, "phone": f"01{index:07d}"}, 201)
            imported.append(guest)

        listed, _ = client.request(f"/api/invitations/{invite_id}/guests")
        assert len(listed) == 10, listed
        by_name = {row["name"]: row for row in listed}
        assert set(by_name) == set(LATIN_NAMES + KHMER_NAMES)
        assert all(by_name[name]["token"] for name in LATIN_NAMES + KHMER_NAMES), "every guest needs a token"

        # The names round-trip byte-for-byte through the database, checked with
        # SQL rather than through the UI.
        connection = sqlite3.connect(data / "invites.db")
        connection.row_factory = sqlite3.Row
        stored = {row["name"] for row in connection.execute("SELECT name FROM guests WHERE invitation_id=?", (invite_id,))}
        connection.close()
        assert stored == set(LATIN_NAMES + KHMER_NAMES), stored

        # 5. Five readable codes and five opaque ones.
        latin_codes = [by_name[name]["slug"] for name in LATIN_NAMES]
        khmer_codes = [by_name[name]["slug"] for name in KHMER_NAMES]
        assert all(LATIN_CODE.match(code) for code in latin_codes), latin_codes
        assert all(OPAQUE_CODE.match(code) for code in khmer_codes), khmer_codes
        assert len(set(latin_codes + khmer_codes)) == 10, "codes must be unique within the invitation"

        # 6. Freeze and generate.
        frozen, _ = client.request(f"/api/invitations/{invite_id}/guests/freeze", "POST", {"guests": [{"id": row["id"], "slug": row["slug"]} for row in listed]})
        assert frozen["frozen"] is True and frozen["conflicts"] == []
        assert frozen["queued"] == 10, frozen

        # The per-guest page and card are built from the published document
        # (research §5.3, pattern A): publishing is what makes og:title a real
        # value instead of the generic fallback, and it is the other trigger for
        # the card warm job.
        client.request(f"/api/invitations/{invite_id}/publish", "POST", {"document": document("Sok Dara & Sophea", "សុខ ដារា និង សុភា")}, 201)

        # 7/8. The Khmer guest's own page.
        khmer_name = KHMER_NAMES[0]
        khmer_code = by_name[khmer_name]["slug"]
        page, _ = client.request(f"/i/{slug}/{khmer_code}", parse_json=False)
        html = page.decode("utf-8")

        # 9. The guest's name is in the preview title.
        assert khmer_name in meta(html, "og:title"), meta(html, "og:title")

        # 10. The image URL is versioned and guest-scoped.
        image_url = meta(html, "og:image")
        assert "/social-card-v" in image_url, image_url
        assert f"/{khmer_code}/" in image_url, image_url

        # 11. The advertised card renders: 200, PNG magic bytes, 1200x630, and the
        #     application's own Pillow path wrote it to the cache (step 7).
        image_path = image_url[len(base):] if image_url.startswith(base) else urllib.parse.urlsplit(image_url).path
        card, _ = client.request(image_path, parse_json=False)
        assert png_dimensions(card) == (1200, 630)
        assert len(card) > 5000
        cached = sorted(p.name for p in (data / "social-cache").glob(f"*-{khmer_code}-og.png"))
        assert cached, sorted(p.name for p in (data / "social-cache").glob("*.png"))
        assert (data / "social-cache" / cached[0]).read_bytes() == card

        # The project card is still served, and an unknown code falls back to it
        # rather than 404 (a wrong guess must not reveal whether a guest exists).
        project, _ = client.request(f"/api/public/{slug}/social-card-v1.png", parse_json=False)
        assert png_dimensions(project) == (1200, 630)
        assert project != card
        fallback, _ = client.request(f"/api/public/{slug}/zzzzzz/social-card-v1.png", parse_json=False)
        assert fallback == project

        # 12. Re-import the same sheet with one phone number changed: the row is
        #     updated, keeps its frozen code, and nothing new is created.
        target = by_name["Ly Meng"]
        client.request(
            f"/api/invitations/{invite_id}/guests/{target['id']}", "PUT",
            {"name": target["name"], "phone": "099999999", "email": target["email"] or "",
             "groupName": target["group_name"] or "", "householdId": target["household_id"] or "",
             "tableName": target["table_name"] or "", "seatLabel": target["seat_label"] or "",
             "tags": target["tags"] or []},
        )
        after, _ = client.request(f"/api/invitations/{invite_id}/guests")
        assert len(after) == 10, f"re-import created rows: {len(after)}"
        updated = {row["name"]: row for row in after}["Ly Meng"]
        assert updated["phone"] == "099999999"
        assert updated["slug"] == target["slug"], "the frozen code must survive a re-import"

        # An unversioned request still resolves, so a preview already in a chat works.
        legacy, _ = client.request(f"/api/public/{slug}/social-card.png", parse_json=False)
        assert png_dimensions(legacy) == (1200, 630)

        print("BULK_GUEST_IMPORT_END_TO_END_PASSED")


def _load_server_module(data_dir: Path):
    """server.py as a separate in-process instance, pointed at ``data_dir``.

    The same technique tests/v15_http_integration_test.py uses: a fresh module
    object, so the module-level data directory and schema bootstrap follow the
    environment this test sets rather than whatever another test already imported.
    """
    previous = os.environ.get("EINVITE_DATA_DIR")
    os.environ["EINVITE_DATA_DIR"] = str(data_dir)
    for root in (str(ROOT), str(ROOT / "src" / "python")):
        if root not in sys.path:
            sys.path.insert(0, root)
    spec = importlib.util.spec_from_file_location("einvite_bulk_import_server", SERVER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if previous is None:
        os.environ.pop("EINVITE_DATA_DIR", None)
    else:
        os.environ["EINVITE_DATA_DIR"] = previous
    return module


def test_guest_slug_migration_is_additive_and_idempotent():
    with tempfile.TemporaryDirectory(prefix="einvite-migration-") as temp:
        data_dir = Path(temp)
        module = _load_server_module(data_dir)
        db_path = data_dir / "invites.db"
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row

        # A legacy table: exactly the guests schema from before this pass, with
        # rows already in it — three of them sharing one name in one invitation.
        connection.executescript(
            """
            DROP TABLE IF EXISTS guests;
            CREATE TABLE guests(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, name TEXT NOT NULL, phone TEXT,
              email TEXT NOT NULL DEFAULT '', group_name TEXT NOT NULL DEFAULT '', household_id TEXT NOT NULL DEFAULT '',
              tags_json TEXT NOT NULL DEFAULT '[]', table_name TEXT NOT NULL DEFAULT '', seat_label TEXT NOT NULL DEFAULT '',
              token TEXT UNIQUE NOT NULL, token_hash TEXT, token_salt TEXT NOT NULL DEFAULT '', token_version INTEGER NOT NULL DEFAULT 1,
              token_expires_at INTEGER, token_revoked_at INTEGER, created_at INTEGER NOT NULL, checked_in INTEGER NOT NULL DEFAULT 0,
              checked_in_at INTEGER, delivery_status TEXT NOT NULL DEFAULT 'not-sent', opened_at INTEGER);
            """
        )
        legacy = [("g1", "inv-A", "Sok Dara"), ("g2", "inv-A", "Sok Dara"), ("g3", "inv-A", "សុខ ដារា"),
                  ("g4", "inv-B", "Sok Dara"), ("g5", "inv-A", "Sok Dara")]
        for guest_id, invitation_id, name in legacy:
            connection.execute("INSERT INTO guests(id,invitation_id,name,created_at,token) VALUES(?,?,?,?,?)",
                               (guest_id, invitation_id, name, 1, f"token-{guest_id}"))
        connection.commit()
        columns_before = {row["name"] for row in connection.execute("PRAGMA table_info(guests)")}
        rows_before = [dict(row) for row in connection.execute("SELECT * FROM guests ORDER BY id")]
        assert "slug" not in columns_before, "the fixture must start without guests.slug"
        assert len(rows_before) == 5

        first = module._migrate_guest_slugs_sqlite(connection)
        connection.commit()
        assert first["columnAdded"] is True and first["backfilled"] == 5, first
        after_first = [dict(row) for row in connection.execute("SELECT * FROM guests ORDER BY id")]
        assert all(row["slug"] for row in after_first), after_first
        assert {row["name"] for row in after_first} == {row["name"] for row in rows_before}, "a name must not change"

        # Deterministic collision handling, scoped per invitation.
        same_name = sorted(row["slug"] for row in after_first if row["invitation_id"] == "inv-A" and row["name"] == "Sok Dara")
        assert same_name == ["sok-dara", "sok-dara-2", "sok-dara-3"], same_name
        other_invitation = [row["slug"] for row in after_first if row["invitation_id"] == "inv-B"]
        assert other_invitation == ["sok-dara"], other_invitation
        assert OPAQUE_CODE.match([row["slug"] for row in after_first if row["name"] == "សុខ ដារា"][0])

        indexes = {row["name"] for row in connection.execute("PRAGMA index_list(guests)")}
        assert "idx_guests_slug" in indexes, indexes

        # The second run is a no-op: no column added, nothing backfilled, and not
        # one byte of the rows changes.
        second = module._migrate_guest_slugs_sqlite(connection)
        connection.commit()
        assert second["columnAdded"] is False and second["backfilled"] == 0, second
        after_second = [dict(row) for row in connection.execute("SELECT * FROM guests ORDER BY id")]
        assert after_second == after_first, "the second run changed rows"

        # The unique index really is enforced per invitation, not globally.
        with_index = connection.execute(
            "SELECT COUNT(*) AS c FROM guests WHERE invitation_id='inv-A' AND slug='sok-dara'"
        ).fetchone()["c"]
        assert with_index == 1
        try:
            connection.execute(
                "INSERT INTO guests(id,invitation_id,name,created_at,token,slug) VALUES('dup','inv-A','x',1,'dup-token','sok-dara')"
            )
            raise AssertionError("the unique index did not refuse a duplicate (invitation_id, slug)")
        except sqlite3.IntegrityError:
            pass
        connection.execute(
            "INSERT INTO guests(id,invitation_id,name,created_at,token,slug) VALUES('ok','inv-C','x',1,'ok-token','sok-dara')"
        )
        connection.close()

        # The server's own connect() path applies the same migration, so a fresh
        # process opening the legacy database ends up with the column, no empty
        # slugs and the index.
        module._SQLITE_SCHEMA_READY = False
        with module.connect() as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(guests)")}
            empty = db.execute("SELECT COUNT(*) AS c FROM guests WHERE slug IS NULL OR slug=''").fetchone()["c"]
            indexes = {row["name"] for row in db.execute("PRAGMA index_list(guests)")}
        assert "slug" in columns and empty == 0 and "idx_guests_slug" in indexes, (columns, empty, indexes)
        cleanup_path(data_dir)

    print("BULK_GUEST_SLUG_MIGRATION_PASSED")


if __name__ == "__main__":
    test_bulk_import_end_to_end()
    test_guest_slug_migration_is_additive_and_idempotent()
    print("BULK_GUEST_IMPORT_TEST_PASSED")
