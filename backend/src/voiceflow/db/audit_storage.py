"""Audit log, feedback, tenant stats, and KVKK user data deletion."""

from ._base import aiosqlite, DB_PATH


async def append_audit_log(
    tenant_id: str,
    action: str,
    user_id: str | None = None,
    target: str | None = None,
) -> None:
    """Append an immutable audit log entry (no UPDATE/DELETE on this table)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO audit_log (tenant_id, user_id, action, target) VALUES (?, ?, ?, ?)",
            (tenant_id, user_id, action, target),
        )
        await db.commit()


async def get_audit_log(tenant_id: str, limit: int = 200, offset: int = 0) -> list[dict]:
    """Return audit log entries for a tenant, newest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, tenant_id, user_id, action, target, created_at
               FROM audit_log
               WHERE tenant_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (tenant_id, limit, offset),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def save_feedback(
    raw_whisper: str,
    model_output: str,
    user_action: str,
    tenant_id: str = "default",
    user_id: str | None = None,
    user_edit: str | None = None,
    app_context: str | None = None,
    window_title: str | None = None,
    mode: str | None = None,
    language: str | None = None,
) -> int | None:
    """Save a training feedback entry. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO correction_feedback
               (tenant_id, user_id, raw_whisper, model_output, user_action, user_edit, app_context, window_title, mode, language)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tenant_id, user_id, raw_whisper, model_output, user_action, user_edit, app_context, window_title, mode, language),
        )
        await db.commit()
        return cursor.lastrowid


async def get_tenant_stats(tenant_id: str) -> dict:
    """Tenant bazlı kullanıcı ve transkripsiyon istatistikleri."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            """SELECT
                COUNT(*) AS total_transcriptions,
                SUM(length(text) - length(replace(text, ' ', '')) + 1) AS total_words,
                AVG(duration) AS avg_duration
               FROM transcriptions WHERE tenant_id = ?""",
            (tenant_id,),
        ) as cur:
            row = await cur.fetchone()
            total_transcriptions = row["total_transcriptions"] or 0
            total_words = int(row["total_words"] or 0)
            avg_duration = round(row["avg_duration"] or 0.0, 2)

        async with db.execute(
            """SELECT COUNT(DISTINCT user_id) AS active_users_7d
               FROM transcriptions
               WHERE tenant_id = ?
                 AND user_id IS NOT NULL
                 AND created_at >= datetime('now', '-7 days')""",
            (tenant_id,),
        ) as cur:
            row = await cur.fetchone()
            active_users_7d = row["active_users_7d"] or 0

        async with db.execute(
            """SELECT mode, COUNT(*) AS cnt
               FROM transcriptions
               WHERE tenant_id = ?
               GROUP BY mode""",
            (tenant_id,),
        ) as cur:
            rows = await cur.fetchall()
        mode_breakdown = {"general": 0, "engineering": 0, "office": 0}
        for r in rows:
            key = r["mode"] or "general"
            mode_breakdown[key] = r["cnt"]

        async with db.execute(
            "SELECT COUNT(*) AS total_users FROM users WHERE tenant_id = ? AND is_active = 1",
            (tenant_id,),
        ) as cur:
            row = await cur.fetchone()
            total_users = row["total_users"] or 0

    return {
        "total_transcriptions": total_transcriptions,
        "total_words": total_words,
        "avg_duration": avg_duration,
        "active_users_7d": active_users_7d,
        "total_users": total_users,
        "mode_breakdown": mode_breakdown,
    }


async def delete_user_data(user_id: str, tenant_id: str) -> dict:
    """KVKK: delete all personal data for a user. Returns counts of deleted rows."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM transcriptions WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        transcriptions_deleted = cur.rowcount
        cur = await db.execute(
            "DELETE FROM user_dictionary WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        dictionary_deleted = cur.rowcount
        cur = await db.execute(
            "DELETE FROM snippets WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        snippets_deleted = cur.rowcount
        cur = await db.execute(
            "DELETE FROM correction_feedback WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        feedback_deleted = cur.rowcount
        cur = await db.execute(
            "UPDATE users SET is_active = 0 WHERE id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        user_deactivated = cur.rowcount > 0
        await db.commit()

    # KVKK silme sözlüğü de siliyor — cache bayat kalmasın
    from .dictionary_storage import invalidate_dictionary_cache
    invalidate_dictionary_cache()

    return {
        "transcriptions_deleted": transcriptions_deleted,
        "dictionary_deleted": dictionary_deleted,
        "snippets_deleted": snippets_deleted,
        "feedback_deleted": feedback_deleted,
        "user_deactivated": user_deactivated,
    }
