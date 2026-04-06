"""Training sentences and recordings storage (IT dataset, user corrections)."""

from ._base import aiosqlite, DB_PATH


async def import_training_sentences(training_set: str, sentences: list[dict]) -> int:
    """Bulk import sentences if table is empty for this training_set. Returns count inserted."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM training_sentences WHERE training_set = ?", (training_set,)
        ) as cur:
            row = await cur.fetchone()
            if row[0] > 0:
                return 0
        await db.executemany(
            "INSERT INTO training_sentences (training_set, persona, scenario, text) VALUES (?,?,?,?)",
            [(training_set, s.get("persona"), s.get("scenario"), s["text"]) for s in sentences],
        )
        await db.commit()
        return len(sentences)


async def get_random_unrecorded_sentence(training_set: str) -> dict | None:
    """Random sentence with zero recordings. Falls back to any random if all recorded."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT s.id, s.persona, s.scenario, s.text,
                      (SELECT COUNT(*) FROM training_recordings r WHERE r.sentence_id = s.id) AS take_count
               FROM training_sentences s
               WHERE s.training_set = ?
                 AND NOT EXISTS (SELECT 1 FROM training_recordings r WHERE r.sentence_id = s.id)
               ORDER BY RANDOM() LIMIT 1""",
            (training_set,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            async with db.execute(
                "SELECT id, persona, scenario, text FROM training_sentences WHERE training_set = ? ORDER BY RANDOM() LIMIT 1",
                (training_set,),
            ) as cur:
                row = await cur.fetchone()
        if row is None:
            return None
        total = await _count_sentences(db, training_set)
        return {
            "id": row["id"], "persona": row["persona"],
            "scenario": row["scenario"], "text": row["text"], "total": total,
        }


async def get_training_sentence_by_id(sentence_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, training_set, persona, scenario, text FROM training_sentences WHERE id = ?",
            (sentence_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        total = await _count_sentences(db, row["training_set"])
        return {
            "id": row["id"], "training_set": row["training_set"],
            "persona": row["persona"], "scenario": row["scenario"],
            "text": row["text"], "total": total,
        }


async def save_training_recording(
    sentence_id: int, training_set: str, wav_path: str, whisper_out: str, duration_ms: int | None = None
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "INSERT INTO training_recordings (sentence_id, training_set, wav_path, whisper_out, duration_ms) VALUES (?,?,?,?,?)",
            (sentence_id, training_set, wav_path, whisper_out, duration_ms),
        ) as cur:
            row_id = cur.lastrowid
        await db.commit()
    return row_id


async def delete_training_recording(wav_path: str, tenant_id: str = "default") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "DELETE FROM training_recordings WHERE wav_path = ? AND tenant_id = ?", (wav_path, tenant_id)
        ) as cur:
            deleted = cur.rowcount > 0
        await db.commit()
    return deleted


async def get_recordings_for_sentence(sentence_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, wav_path, whisper_out, duration_ms, created_at FROM training_recordings WHERE sentence_id = ? ORDER BY created_at",
            (sentence_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_recorded_sentences(training_set: str) -> list[dict]:
    """All sentences that have at least one recording, with their recordings."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        total = await _count_sentences(db, training_set)
        async with db.execute(
            """SELECT DISTINCT s.id, s.persona, s.scenario, s.text
               FROM training_sentences s
               JOIN training_recordings r ON r.sentence_id = s.id
               WHERE s.training_set = ?
               ORDER BY s.id""",
            (training_set,),
        ) as cur:
            sentences = await cur.fetchall()
        result = []
        for s in sentences:
            async with db.execute(
                "SELECT wav_path, whisper_out FROM training_recordings WHERE sentence_id = ? ORDER BY created_at",
                (s["id"],),
            ) as cur:
                recs = await cur.fetchall()
            result.append({
                "id": s["id"], "persona": s["persona"], "scenario": s["scenario"],
                "text": s["text"], "total": total,
                "recordings": [{"whisper": r["whisper_out"] or "", "wav_path": r["wav_path"]} for r in recs],
            })
    return result


async def _count_sentences(db, training_set: str) -> int:
    async with db.execute(
        "SELECT COUNT(*) FROM training_sentences WHERE training_set = ?", (training_set,)
    ) as cur:
        row = await cur.fetchone()
    return row[0] or 0
