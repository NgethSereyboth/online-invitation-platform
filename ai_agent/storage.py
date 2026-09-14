"""Persistent project-scoped conversations and bounded AI job records."""
from __future__ import annotations
import json
import re
import time
import uuid
from typing import Any, Callable


def now_ms() -> int:
    return int(time.time() * 1000)


def uid() -> str:
    return str(uuid.uuid4())


def ensure_agent_schema(connect: Callable[[], Any]) -> None:
    statements = [
        """CREATE TABLE IF NOT EXISTS ai_preferences(
            user_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1,
            retention_days INTEGER NOT NULL DEFAULT 30, allow_low_risk_auto INTEGER NOT NULL DEFAULT 0,
            provider_disclosure INTEGER NOT NULL DEFAULT 1, updated_at INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS ai_conversations(
            id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'New agent chat', status TEXT NOT NULL DEFAULT 'active',
            provider_mode TEXT NOT NULL DEFAULT 'offline', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_conversations_project ON ai_conversations(invitation_id,user_id,updated_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_messages(
            id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, sequence INTEGER NOT NULL,
            role TEXT NOT NULL, message_type TEXT NOT NULL, content_json TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_messages_sequence ON ai_messages(conversation_id,sequence)",
        """CREATE TABLE IF NOT EXISTS ai_plans(
            id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL,
            document_revision INTEGER NOT NULL DEFAULT 0, document_fingerprint TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'proposed', plan_json TEXT NOT NULL DEFAULT '{}',
            confirmation_json TEXT NOT NULL DEFAULT '{}', idempotency_key TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_plans_idempotency ON ai_plans(user_id,idempotency_key) WHERE idempotency_key<>''",
        """CREATE TABLE IF NOT EXISTS ai_jobs(
            id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, plan_id TEXT, invitation_id TEXT NOT NULL,
            user_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', cancellation_requested INTEGER NOT NULL DEFAULT 0,
            progress_json TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_jobs_user ON ai_jobs(user_id,status,updated_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_usage_events(
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, invitation_id TEXT NOT NULL, provider_mode TEXT NOT NULL,
            input_bytes INTEGER NOT NULL DEFAULT 0, output_bytes INTEGER NOT NULL DEFAULT 0,
            tool_calls INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_usage_user ON ai_usage_events(user_id,created_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_feedback(
            id TEXT PRIMARY KEY, message_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
            invitation_id TEXT NOT NULL, user_id TEXT NOT NULL, rating INTEGER NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]', comment TEXT NOT NULL DEFAULT '',
            remember INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
            UNIQUE(message_id,user_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_feedback_user ON ai_feedback(user_id,updated_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_memories(
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, scope TEXT NOT NULL DEFAULT 'account',
            invitation_id TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT 'preference',
            content TEXT NOT NULL, keywords_json TEXT NOT NULL DEFAULT '[]', confidence REAL NOT NULL DEFAULT 1,
            source_feedback_id TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active',
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_memories_lookup ON ai_memories(user_id,status,invitation_id,updated_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_knowledge_sources(
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, scope TEXT NOT NULL DEFAULT 'invitation',
            invitation_id TEXT NOT NULL DEFAULT '', title TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'text', content TEXT NOT NULL,
            keywords_json TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'active',
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_knowledge_lookup ON ai_knowledge_sources(user_id,status,invitation_id,updated_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_tool_outcomes(
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, invitation_id TEXT NOT NULL,
            plan_id TEXT NOT NULL, tool_id TEXT NOT NULL, success INTEGER NOT NULL,
            error_code TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_tool_outcomes_user ON ai_tool_outcomes(user_id,tool_id,created_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_design_blueprints(
            id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL, reference_asset_ids_json TEXT NOT NULL DEFAULT '[]',
            mode TEXT NOT NULL DEFAULT 'style', provider_mode TEXT NOT NULL DEFAULT 'offline', blueprint_json TEXT NOT NULL DEFAULT '{}',
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_blueprints_project ON ai_design_blueprints(invitation_id,user_id,updated_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_verification_results(
            id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 0, result_json TEXT NOT NULL DEFAULT '{}', corrections_json TEXT NOT NULL DEFAULT '[]', created_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ai_verification_plan ON ai_verification_results(plan_id,created_at DESC)",
        """CREATE TABLE IF NOT EXISTS ai_local_provider_configs(
            provider_id TEXT PRIMARY KEY, label TEXT NOT NULL, kind TEXT NOT NULL, endpoint_label TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, updated_at INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS ai_model_capabilities(
            provider_id TEXT NOT NULL, model_id TEXT NOT NULL, capability_json TEXT NOT NULL DEFAULT '{}', health TEXT NOT NULL DEFAULT 'unknown',
            last_successful_check INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL, PRIMARY KEY(provider_id,model_id)
        )""",
    ]
    with connect() as db:
        for statement in statements:
            db.execute(statement)
        for column, definition in (
            ("feedback_learning", "INTEGER NOT NULL DEFAULT 1"),
            ("memory_enabled", "INTEGER NOT NULL DEFAULT 1"),
            ("knowledge_enabled", "INTEGER NOT NULL DEFAULT 1"),
        ):
            try:
                db.execute(f"ALTER TABLE ai_preferences ADD COLUMN {column} {definition}")
            except Exception:
                pass


class AgentStore:
    def __init__(self, connect: Callable[[], Any], retention_default: int = 30):
        self.connect = connect
        self.retention_default = retention_default

    @staticmethod
    def _loads(value: str | None, fallback: Any) -> Any:
        try:
            parsed = json.loads(value or "")
            return parsed
        except Exception:
            return fallback

    def save_design_blueprint(self, invitation_id: str, user_id: str, asset_ids: list[str], mode: str, provider_mode: str, blueprint: dict[str, Any]) -> dict[str, Any]:
        blueprint_id, created = uid(), now_ms()
        with self.connect() as db:
            db.execute("INSERT INTO ai_design_blueprints(id,invitation_id,user_id,reference_asset_ids_json,mode,provider_mode,blueprint_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (blueprint_id, invitation_id, user_id, json.dumps(asset_ids[:12]), mode[:30], provider_mode[:30], json.dumps(blueprint, ensure_ascii=False, separators=(",", ":")), created, created))
        return {"id": blueprint_id, "invitationId": invitation_id, "referenceAssetIds": asset_ids[:12], "mode": mode, "providerMode": provider_mode, "blueprint": blueprint, "createdAt": created, "updatedAt": created}

    def get_design_blueprint(self, invitation_id: str, user_id: str, blueprint_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row=db.execute("SELECT * FROM ai_design_blueprints WHERE id=? AND invitation_id=? AND user_id=?",(blueprint_id,invitation_id,user_id)).fetchone()
        if not row:return None
        return {"id":row["id"],"invitationId":row["invitation_id"],"referenceAssetIds":self._loads(row["reference_asset_ids_json"],[]),"mode":row["mode"],"providerMode":row["provider_mode"],"blueprint":self._loads(row["blueprint_json"],{}),"createdAt":int(row["created_at"]),"updatedAt":int(row["updated_at"])}

    def list_design_blueprints(self, invitation_id: str, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as db:rows=db.execute("SELECT id FROM ai_design_blueprints WHERE invitation_id=? AND user_id=? ORDER BY updated_at DESC LIMIT ?",(invitation_id,user_id,max(1,min(100,int(limit))))).fetchall()
        return [item for row in rows if (item:=self.get_design_blueprint(invitation_id,user_id,row["id"]))]

    def record_verification(self, plan_id: str, invitation_id: str, user_id: str, success: bool, result: dict[str, Any], corrections: list[Any]) -> str:
        record_id=uid()
        with self.connect() as db:db.execute("INSERT INTO ai_verification_results(id,plan_id,invitation_id,user_id,success,result_json,corrections_json,created_at) VALUES(?,?,?,?,?,?,?,?)",(record_id,plan_id,invitation_id,user_id,int(bool(success)),json.dumps(result,ensure_ascii=False)[:30000],json.dumps(corrections[:20],ensure_ascii=False)[:30000],now_ms()))
        return record_id

    def record_local_catalog(self, provider_specs: tuple[dict, ...], catalog: list[dict[str, Any]]) -> None:
        now=now_ms()
        with self.connect() as db:
            for spec in provider_specs:
                provider_id=str(spec.get("id") or "")[:80]
                if not provider_id:continue
                endpoint=str(spec.get("endpoint") or "")
                # Persist only an endpoint label/origin, never credentials or URL paths.
                endpoint_label=endpoint.split("?",1)[0][:300]
                db.execute("INSERT INTO ai_local_provider_configs(provider_id,label,kind,endpoint_label,enabled,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(provider_id) DO UPDATE SET label=excluded.label,kind=excluded.kind,endpoint_label=excluded.endpoint_label,enabled=excluded.enabled,updated_at=excluded.updated_at",(provider_id,str(spec.get("label") or provider_id)[:100],str(spec.get("kind") or "openai")[:30],endpoint_label,int(spec.get("enabled",True) is not False),now))
            for provider in catalog:
                provider_id=str(provider.get("id") or "")[:80];health=str(provider.get("health") or "unknown")[:30];checked=int(provider.get("lastSuccessfulCheck") or provider.get("checkedAt") or 0)
                for model in provider.get("models") or []:
                    model_id=str(model.get("id") or "")[:300]
                    if not provider_id or not model_id:continue
                    db.execute("INSERT INTO ai_model_capabilities(provider_id,model_id,capability_json,health,last_successful_check,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(provider_id,model_id) DO UPDATE SET capability_json=excluded.capability_json,health=excluded.health,last_successful_check=excluded.last_successful_check,updated_at=excluded.updated_at",(provider_id,model_id,json.dumps(model,ensure_ascii=False)[:20000],health,checked,now))

    def preferences(self, user_id: str, enabled_default: bool = True) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT enabled,retention_days,allow_low_risk_auto,provider_disclosure,feedback_learning,memory_enabled,knowledge_enabled,updated_at FROM ai_preferences WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return {"enabled": enabled_default, "retentionDays": self.retention_default, "allowLowRiskAuto": False, "providerDisclosure": True, "feedbackLearning": True, "memoryEnabled": True, "knowledgeEnabled": True, "updatedAt": 0}
        return {"enabled": bool(row["enabled"]), "retentionDays": int(row["retention_days"]), "allowLowRiskAuto": bool(row["allow_low_risk_auto"]), "providerDisclosure": bool(row["provider_disclosure"]), "feedbackLearning": bool(row["feedback_learning"]), "memoryEnabled": bool(row["memory_enabled"]), "knowledgeEnabled": bool(row["knowledge_enabled"]), "updatedAt": int(row["updated_at"])}

    def update_preferences(self, user_id: str, data: dict[str, Any], enabled_default: bool = True) -> dict[str, Any]:
        current = self.preferences(user_id, enabled_default)
        enabled = bool(data.get("enabled", current["enabled"]))
        retention = max(0, min(3650, int(data.get("retentionDays", current["retentionDays"]))))
        auto = bool(data.get("allowLowRiskAuto", current["allowLowRiskAuto"]))
        disclosure = bool(data.get("providerDisclosure", current["providerDisclosure"]))
        feedback_learning = bool(data.get("feedbackLearning", current["feedbackLearning"]))
        memory_enabled = bool(data.get("memoryEnabled", current["memoryEnabled"]))
        knowledge_enabled = bool(data.get("knowledgeEnabled", current["knowledgeEnabled"]))
        updated = now_ms()
        with self.connect() as db:
            db.execute("INSERT INTO ai_preferences(user_id,enabled,retention_days,allow_low_risk_auto,provider_disclosure,feedback_learning,memory_enabled,knowledge_enabled,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled,retention_days=excluded.retention_days,allow_low_risk_auto=excluded.allow_low_risk_auto,provider_disclosure=excluded.provider_disclosure,feedback_learning=excluded.feedback_learning,memory_enabled=excluded.memory_enabled,knowledge_enabled=excluded.knowledge_enabled,updated_at=excluded.updated_at", (user_id, int(enabled), retention, int(auto), int(disclosure), int(feedback_learning), int(memory_enabled), int(knowledge_enabled), updated))
        return self.preferences(user_id, enabled_default)

    def purge_expired(self, user_id: str) -> int:
        prefs = self.preferences(user_id)
        days = int(prefs["retentionDays"])
        if days <= 0:
            return 0
        cutoff = now_ms() - days * 86_400_000
        with self.connect() as db:
            rows = db.execute("SELECT id FROM ai_conversations WHERE user_id=? AND updated_at<?", (user_id, cutoff)).fetchall()
            ids = [row["id"] for row in rows]
            for conversation_id in ids:
                db.execute("DELETE FROM ai_feedback WHERE conversation_id=?", (conversation_id,))
                db.execute("DELETE FROM ai_messages WHERE conversation_id=?", (conversation_id,))
                db.execute("DELETE FROM ai_plans WHERE conversation_id=?", (conversation_id,))
                db.execute("DELETE FROM ai_jobs WHERE conversation_id=?", (conversation_id,))
                db.execute("DELETE FROM ai_conversations WHERE id=?", (conversation_id,))
        return len(ids)

    def create_conversation(self, invitation_id: str, user_id: str, title: str = "New agent chat", provider_mode: str = "offline") -> dict[str, Any]:
        conversation_id, created = uid(), now_ms()
        title = (str(title or "New agent chat").strip() or "New agent chat")[:160]
        with self.connect() as db:
            db.execute("INSERT INTO ai_conversations(id,invitation_id,user_id,title,status,provider_mode,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (conversation_id, invitation_id, user_id, title, "active", provider_mode[:30], created, created))
        return self.get_conversation(conversation_id, invitation_id, user_id, include_messages=True)

    def list_conversations(self, invitation_id: str, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(100, int(limit)))
        with self.connect() as db:
            rows = db.execute("SELECT c.id,c.title,c.status,c.provider_mode,c.created_at,c.updated_at,(SELECT COUNT(*) FROM ai_messages m WHERE m.conversation_id=c.id) message_count FROM ai_conversations c WHERE c.invitation_id=? AND c.user_id=? AND c.status<>'deleted' ORDER BY c.updated_at DESC LIMIT ?", (invitation_id, user_id, limit)).fetchall()
        return [{"id": row["id"], "title": row["title"], "status": row["status"], "providerMode": row["provider_mode"], "createdAt": int(row["created_at"]), "updatedAt": int(row["updated_at"]), "messageCount": int(row["message_count"])} for row in rows]

    def get_conversation(self, conversation_id: str, invitation_id: str, user_id: str, include_messages: bool = True) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT id,title,status,provider_mode,created_at,updated_at FROM ai_conversations WHERE id=? AND invitation_id=? AND user_id=? AND status<>'deleted'", (conversation_id, invitation_id, user_id)).fetchone()
            if not row:
                return None
            messages = []
            if include_messages:
                message_rows = db.execute("SELECT id,sequence,role,message_type,content_json,created_at FROM ai_messages WHERE conversation_id=? ORDER BY sequence", (conversation_id,)).fetchall()
                messages = [{"id": item["id"], "sequence": int(item["sequence"]), "role": item["role"], "type": item["message_type"], "content": self._loads(item["content_json"], {}), "createdAt": int(item["created_at"])} for item in message_rows]
        return {"id": row["id"], "title": row["title"], "status": row["status"], "providerMode": row["provider_mode"], "createdAt": int(row["created_at"]), "updatedAt": int(row["updated_at"]), "messages": messages}

    def archive_conversation(self, conversation_id: str, invitation_id: str, user_id: str) -> bool:
        with self.connect() as db:
            changed = db.execute("UPDATE ai_conversations SET status='archived',updated_at=? WHERE id=? AND invitation_id=? AND user_id=?", (now_ms(), conversation_id, invitation_id, user_id)).rowcount
        return bool(changed)

    def add_message(self, conversation_id: str, role: str, message_type: str, content: dict[str, Any]) -> dict[str, Any]:
        message_id, created = uid(), now_ms()
        encoded = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 500_000:
            raise ValueError("AI message exceeds the bounded storage size")
        with self.connect() as db:
            row = db.execute("SELECT COALESCE(MAX(sequence),0)+1 next_sequence FROM ai_messages WHERE conversation_id=?", (conversation_id,)).fetchone()
            sequence = int(row["next_sequence"] or 1)
            db.execute("INSERT INTO ai_messages(id,conversation_id,sequence,role,message_type,content_json,created_at) VALUES(?,?,?,?,?,?,?)", (message_id, conversation_id, sequence, role[:30], message_type[:40], encoded, created))
            db.execute("UPDATE ai_conversations SET updated_at=? WHERE id=?", (created, conversation_id))
        return {"id": message_id, "sequence": sequence, "role": role, "type": message_type, "content": content, "createdAt": created}

    def create_plan(self, conversation_id: str, invitation_id: str, user_id: str, revision: int, fingerprint: str, plan: dict[str, Any], idempotency_key: str = "") -> dict[str, Any]:
        plan_id, created = uid(), now_ms()
        idempotency_key = str(idempotency_key or "")[:160]
        encoded = json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
        with self.connect() as db:
            if idempotency_key:
                existing = db.execute("SELECT id FROM ai_plans WHERE user_id=? AND idempotency_key=?", (user_id, idempotency_key)).fetchone()
                if existing:
                    return self.get_plan(existing["id"], invitation_id, user_id)
            db.execute("INSERT INTO ai_plans(id,conversation_id,invitation_id,user_id,document_revision,document_fingerprint,status,plan_json,confirmation_json,idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (plan_id, conversation_id, invitation_id, user_id, int(revision or 0), str(fingerprint or "")[:160], "proposed", encoded, "{}", idempotency_key, created, created))
        return self.get_plan(plan_id, invitation_id, user_id)

    def get_plan(self, plan_id: str, invitation_id: str, user_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT id,conversation_id,document_revision,document_fingerprint,status,plan_json,confirmation_json,idempotency_key,created_at,updated_at FROM ai_plans WHERE id=? AND invitation_id=? AND user_id=?", (plan_id, invitation_id, user_id)).fetchone()
        if not row:
            return None
        value = self._loads(row["plan_json"], {})
        value.update({"id": row["id"], "conversationId": row["conversation_id"], "documentRevision": int(row["document_revision"]), "documentFingerprint": row["document_fingerprint"], "status": row["status"], "confirmation": self._loads(row["confirmation_json"], {}), "idempotencyKey": row["idempotency_key"], "createdAt": int(row["created_at"]), "updatedAt": int(row["updated_at"])})
        return value

    def update_plan_status(self, plan_id: str, invitation_id: str, user_id: str, status: str, confirmation: dict[str, Any] | None = None) -> dict[str, Any] | None:
        allowed = {"proposed", "confirmed", "cancelled", "executing", "completed", "failed", "stale"}
        if status not in allowed:
            raise ValueError("Unsupported plan status")
        with self.connect() as db:
            changed = db.execute("UPDATE ai_plans SET status=?,confirmation_json=?,updated_at=? WHERE id=? AND invitation_id=? AND user_id=?", (status, json.dumps(confirmation or {}, ensure_ascii=False, separators=(",", ":")), now_ms(), plan_id, invitation_id, user_id)).rowcount
        return self.get_plan(plan_id, invitation_id, user_id) if changed else None

    def create_job(self, conversation_id: str, invitation_id: str, user_id: str, plan_id: str | None = None) -> dict[str, Any]:
        job_id, created = uid(), now_ms()
        with self.connect() as db:
            db.execute("INSERT INTO ai_jobs(id,conversation_id,plan_id,invitation_id,user_id,status,cancellation_requested,progress_json,created_at,updated_at) VALUES(?,?,?,?,?,'running',0,'{}',?,?)", (job_id, conversation_id, plan_id, invitation_id, user_id, created, created))
        return {"id": job_id, "conversationId": conversation_id, "planId": plan_id, "status": "running", "createdAt": created}

    def cancel_job(self, job_id: str, invitation_id: str, user_id: str) -> bool:
        with self.connect() as db:
            changed = db.execute("UPDATE ai_jobs SET cancellation_requested=1,status=CASE WHEN status IN ('queued','running') THEN 'cancelled' ELSE status END,updated_at=? WHERE id=? AND invitation_id=? AND user_id=?", (now_ms(), job_id, invitation_id, user_id)).rowcount
        return bool(changed)

    def job_cancelled(self, job_id: str) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT cancellation_requested,status FROM ai_jobs WHERE id=?", (job_id,)).fetchone()
        return not row or bool(row["cancellation_requested"]) or row["status"] == "cancelled"

    def finish_job(self, job_id: str, status: str, progress: dict[str, Any] | None = None) -> None:
        with self.connect() as db:
            db.execute("UPDATE ai_jobs SET status=?,progress_json=?,updated_at=? WHERE id=?", (status[:30], json.dumps(progress or {}, ensure_ascii=False, separators=(",", ":")), now_ms(), job_id))

    def record_usage(self, user_id: str, invitation_id: str, provider_mode: str, input_bytes: int, output_bytes: int, tool_calls: int) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO ai_usage_events(id,user_id,invitation_id,provider_mode,input_bytes,output_bytes,tool_calls,created_at) VALUES(?,?,?,?,?,?,?,?)", (uid(), user_id, invitation_id, provider_mode[:30], max(0, int(input_bytes)), max(0, int(output_bytes)), max(0, int(tool_calls)), now_ms()))

    @staticmethod
    def _keywords(text: str) -> list[str]:
        values = re.findall(r"[\w\u1780-\u17ff]+", str(text or "").lower(), flags=re.UNICODE)
        return list(dict.fromkeys(value[:60] for value in values if len(value) > 1))[:80]

    def record_feedback(self, invitation_id: str, user_id: str, message_id: str, rating: int, tags: list[str] | None = None, comment: str = "", remember: bool = False) -> dict[str, Any]:
        rating = 1 if int(rating) > 0 else -1
        tags = [str(tag).strip().lower()[:40] for tag in (tags or [])[:10] if str(tag).strip()]
        comment = str(comment or "").strip()[:4000]
        created = now_ms()
        with self.connect() as db:
            row = db.execute("SELECT m.conversation_id,c.invitation_id FROM ai_messages m JOIN ai_conversations c ON c.id=m.conversation_id WHERE m.id=? AND m.role='assistant' AND c.invitation_id=? AND c.user_id=?", (message_id, invitation_id, user_id)).fetchone()
            if not row:
                raise ValueError("AI message not found")
            existing = db.execute("SELECT id,created_at FROM ai_feedback WHERE message_id=? AND user_id=?", (message_id, user_id)).fetchone()
            feedback_id = existing["id"] if existing else uid()
            original_created = int(existing["created_at"]) if existing else created
            db.execute("INSERT INTO ai_feedback(id,message_id,conversation_id,invitation_id,user_id,rating,tags_json,comment,remember,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(message_id,user_id) DO UPDATE SET rating=excluded.rating,tags_json=excluded.tags_json,comment=excluded.comment,remember=excluded.remember,updated_at=excluded.updated_at", (feedback_id, message_id, row["conversation_id"], invitation_id, user_id, rating, json.dumps(tags, ensure_ascii=False), comment, int(bool(remember)), original_created, created))
        memory = None
        if remember and comment:
            memory = self.create_memory(user_id, comment, scope="invitation", invitation_id=invitation_id, kind="correction" if rating < 0 else "preference", source_feedback_id=feedback_id)
        return {"id": feedback_id, "messageId": message_id, "rating": rating, "tags": tags, "comment": comment, "remember": bool(remember), "memory": memory, "updatedAt": created}

    def create_memory(self, user_id: str, content: str, scope: str = "account", invitation_id: str = "", kind: str = "preference", source_feedback_id: str = "") -> dict[str, Any]:
        content = " ".join(str(content or "").strip().split())[:4000]
        if not content:
            raise ValueError("Memory content is required")
        scope = scope if scope in {"account", "invitation"} else "account"
        kind = kind if kind in {"preference", "correction", "example", "fact"} else "preference"
        invitation_id = str(invitation_id or "")[:120] if scope == "invitation" else ""
        memory_id, created = uid(), now_ms()
        keywords = self._keywords(content)
        with self.connect() as db:
            duplicate = db.execute("SELECT id FROM ai_memories WHERE user_id=? AND scope=? AND invitation_id=? AND lower(content)=lower(?) AND status='active'", (user_id, scope, invitation_id, content)).fetchone()
            if duplicate:
                db.execute("UPDATE ai_memories SET updated_at=? WHERE id=?", (created, duplicate["id"]))
                return self.get_memory(user_id, duplicate["id"])
            db.execute("INSERT INTO ai_memories(id,user_id,scope,invitation_id,kind,content,keywords_json,confidence,source_feedback_id,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,'active',?,?)", (memory_id, user_id, scope, invitation_id, kind, content, json.dumps(keywords, ensure_ascii=False), 1.0, str(source_feedback_id or "")[:120], created, created))
        return self.get_memory(user_id, memory_id)

    def get_memory(self, user_id: str, memory_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT id,scope,invitation_id,kind,content,keywords_json,confidence,status,created_at,updated_at FROM ai_memories WHERE id=? AND user_id=?", (memory_id, user_id)).fetchone()
        if not row:
            return None
        return {"id": row["id"], "scope": row["scope"], "invitationId": row["invitation_id"], "kind": row["kind"], "content": row["content"], "keywords": self._loads(row["keywords_json"], []), "confidence": float(row["confidence"]), "status": row["status"], "createdAt": int(row["created_at"]), "updatedAt": int(row["updated_at"])}

    def list_memories(self, user_id: str, invitation_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT id FROM ai_memories WHERE user_id=? AND status='active' AND (scope='account' OR invitation_id=?) ORDER BY updated_at DESC LIMIT ?", (user_id, str(invitation_id or ""), max(1, min(200, int(limit))))).fetchall()
        return [memory for row in rows if (memory := self.get_memory(user_id, row["id"]))]

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        with self.connect() as db:
            changed = db.execute("UPDATE ai_memories SET status='deleted',updated_at=? WHERE id=? AND user_id=? AND status='active'", (now_ms(), memory_id, user_id)).rowcount
        return bool(changed)

    def create_knowledge_source(self, user_id: str, title: str, content: str, scope: str = "invitation", invitation_id: str = "", source_type: str = "text") -> dict[str, Any]:
        title = " ".join(str(title or "").strip().split())[:200]
        content = str(content or "").strip()[:100_000]
        if not title or not content:
            raise ValueError("Knowledge title and content are required")
        scope = scope if scope in {"account", "invitation"} else "invitation"
        invitation_id = str(invitation_id or "")[:120] if scope == "invitation" else ""
        if scope == "invitation" and not invitation_id:
            raise ValueError("Invitation-scoped knowledge requires an invitation")
        source_type = source_type if source_type in {"text", "markdown", "csv", "json", "policy", "brand"} else "text"
        source_id, created = uid(), now_ms()
        keywords = self._keywords(f"{title} {content}")
        with self.connect() as db:
            db.execute("INSERT INTO ai_knowledge_sources(id,user_id,scope,invitation_id,title,source_type,content,keywords_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,'active',?,?)", (source_id, user_id, scope, invitation_id, title, source_type, content, json.dumps(keywords, ensure_ascii=False), created, created))
        return self.get_knowledge_source(user_id, source_id, include_content=True)

    def get_knowledge_source(self, user_id: str, source_id: str, include_content: bool = False) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT id,scope,invitation_id,title,source_type,content,keywords_json,status,created_at,updated_at FROM ai_knowledge_sources WHERE id=? AND user_id=?", (source_id, user_id)).fetchone()
        if not row:
            return None
        value = {"id": row["id"], "scope": row["scope"], "invitationId": row["invitation_id"], "title": row["title"], "sourceType": row["source_type"], "keywords": self._loads(row["keywords_json"], []), "status": row["status"], "contentLength": len(row["content"] or ""), "createdAt": int(row["created_at"]), "updatedAt": int(row["updated_at"])}
        if include_content:
            value["content"] = row["content"]
        return value

    def list_knowledge_sources(self, user_id: str, invitation_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT id FROM ai_knowledge_sources WHERE user_id=? AND status='active' AND (scope='account' OR invitation_id=?) ORDER BY updated_at DESC LIMIT ?", (user_id, str(invitation_id or ""), max(1, min(200, int(limit))))).fetchall()
        return [source for row in rows if (source := self.get_knowledge_source(user_id, row["id"], include_content=False))]

    def delete_knowledge_source(self, user_id: str, source_id: str) -> bool:
        with self.connect() as db:
            changed = db.execute("UPDATE ai_knowledge_sources SET status='deleted',updated_at=? WHERE id=? AND user_id=? AND status='active'", (now_ms(), source_id, user_id)).rowcount
        return bool(changed)

    def retrieve_knowledge(self, user_id: str, invitation_id: str, prompt: str, maximum: int = 5) -> list[dict[str, Any]]:
        prompt_words = set(self._keywords(prompt))
        with self.connect() as db:
            rows = db.execute("SELECT id,scope,title,source_type,content,keywords_json,updated_at FROM ai_knowledge_sources WHERE user_id=? AND status='active' AND (scope='account' OR invitation_id=?) ORDER BY updated_at DESC LIMIT 200", (user_id, str(invitation_id or ""))).fetchall()
        scored = []
        for row in rows:
            words = set(self._loads(row["keywords_json"], []))
            overlap = len(words & prompt_words)
            score = overlap * 10 + (3 if row["scope"] == "invitation" else 1)
            if not prompt_words or overlap:
                scored.append((score, int(row["updated_at"] or 0), row))
        selected = []
        for _score, _updated, row in sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)[:max(1, min(10, maximum))]:
            selected.append({"id": row["id"], "scope": row["scope"], "title": row["title"], "sourceType": row["source_type"], "excerpt": str(row["content"] or "")[:6000]})
        return selected

    def learning_context(self, user_id: str, invitation_id: str, prompt: str, maximum: int = 8) -> dict[str, Any]:
        prefs = self.preferences(user_id)
        if not prefs.get("feedbackLearning", True):
            return {"enabled": False, "memories": [], "knowledge": [], "toolReliability": [], "feedbackStats": {}}
        prompt_words = set(self._keywords(prompt))
        memories = self.list_memories(user_id, invitation_id, 200) if prefs.get("memoryEnabled", True) else []
        scored = []
        for memory in memories:
            words = set(memory.get("keywords") or [])
            overlap = len(words & prompt_words)
            scope_bonus = 3 if memory.get("scope") == "invitation" else 1
            score = overlap * 10 + scope_bonus + (2 if memory.get("kind") == "correction" else 0)
            if not prompt_words or overlap or memory.get("kind") == "preference":
                scored.append((score, int(memory.get("updatedAt") or 0), memory))
        selected = [item[2] for item in sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)[:max(1, min(20, maximum))]]
        cutoff = now_ms() - 180 * 86_400_000
        with self.connect() as db:
            rows = db.execute("SELECT tool_id,SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) successes,COUNT(*) total FROM ai_tool_outcomes WHERE user_id=? AND created_at>=? GROUP BY tool_id ORDER BY total DESC LIMIT 30", (user_id, cutoff)).fetchall()
            feedback = db.execute("SELECT SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) positive,SUM(CASE WHEN rating=-1 THEN 1 ELSE 0 END) negative,COUNT(*) total FROM ai_feedback WHERE user_id=?", (user_id,)).fetchone()
        reliability = [{"toolId": row["tool_id"], "successes": int(row["successes"] or 0), "total": int(row["total"] or 0), "successRate": round(int(row["successes"] or 0) / max(1, int(row["total"] or 0)), 3)} for row in rows]
        knowledge = self.retrieve_knowledge(user_id, invitation_id, prompt) if prefs.get("knowledgeEnabled", True) else []
        return {"enabled": True, "memories": [{key: memory[key] for key in ("id", "scope", "kind", "content") if key in memory} for memory in selected], "knowledge": knowledge, "toolReliability": reliability, "feedbackStats": {"positive": int((feedback or {})["positive"] or 0), "negative": int((feedback or {})["negative"] or 0), "total": int((feedback or {})["total"] or 0)}}

    def record_plan_outcomes(self, user_id: str, invitation_id: str, plan_id: str, tool_ids: list[str], success: bool, error_code: str = "") -> None:
        created = now_ms()
        with self.connect() as db:
            for tool_id in list(dict.fromkeys(str(value)[:120] for value in tool_ids if value))[:100]:
                db.execute("INSERT INTO ai_tool_outcomes(id,user_id,invitation_id,plan_id,tool_id,success,error_code,created_at) VALUES(?,?,?,?,?,?,?,?)", (uid(), user_id, invitation_id, plan_id, tool_id, int(bool(success)), str(error_code or "")[:120], created))

    def learning_summary(self, user_id: str, invitation_id: str = "") -> dict[str, Any]:
        value = self.learning_context(user_id, invitation_id, "", maximum=5)
        value["memoryCount"] = len(self.list_memories(user_id, invitation_id, 200))
        value["knowledgeSourceCount"] = len(self.list_knowledge_sources(user_id, invitation_id, 200))
        return value
