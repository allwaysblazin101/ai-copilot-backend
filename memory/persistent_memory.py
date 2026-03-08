import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from sqlalchemy import Column, Integer, Text, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from backend.utils.logger import logger

# 1. Async Setup
DB_DIR = os.path.expanduser("~/ai-copilot/backend/secrets")
os.makedirs(DB_DIR, exist_ok=True)

# Use 'sqlite+aiosqlite' for asynchronous support
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DB_DIR, 'ai_memory.db')}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class MemoryTable(Base):
    __tablename__ = "memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    # Use standard UTC for storage
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class PersistentMemoryStore:
    """Async persistent memory store for non-blocking AI operations."""

    async def init_db(self):
        """Run this once at startup to create tables."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # --- CRITICAL FIX: Method Alias ---
    async def update_entity(self, key: str, value: Any) -> bool:
        """
        Alias for save_entity to match MasterBrain expectations.
        Called when the Brain learns a new specific fact.
        """
        return await self.save_entity(key, value)

    async def save_entity(self, key: str, value: Any) -> bool:
        """
        Saves a structured 'Fact' about the user.
        Useful for long-term preferences (e.g., 'pref_pizza': 'pepperoni').
        """
        async with AsyncSessionLocal() as db:
            try:
                # We store entities as log entries with a special prefix.
                # get_entity() fetches the latest one.
                entry = MemoryTable(
                    input=f"ENTITY_UPDATE:{key}",
                    output=json.dumps(value),
                    context="STRUCTURAL_MEMORY"
                )
                db.add(entry)
                await db.commit()
                return True
            except Exception as e:
                await db.rollback()
                logger.error(f"Entity Save Error: {e}")
                return False

    async def get_entity(self, key: str) -> Optional[Any]:
        """Directly retrieve a specific fact by key."""
        async with AsyncSessionLocal() as db:
            stmt = select(MemoryTable).where(
                MemoryTable.input == f"ENTITY_UPDATE:{key}"
            ).order_by(MemoryTable.created_at.desc()).limit(1)
            
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()
            
            if row:
                try:
                    return json.loads(row.output)
                except json.JSONDecodeError:
                    return row.output
            return None

    async def save(self, input_text: str, output_text: str, context: Optional[Any] = None) -> bool:
        """Saves a standard conversation turn."""
        async with AsyncSessionLocal() as db:
            try:
                context_str = json.dumps(context) if context else None
                entry = MemoryTable(input=input_text, output=output_text, context=context_str)
                db.add(entry)
                await db.commit()
                return True
            except Exception as e:
                await db.rollback()
                logger.error(f"Conversation Save Error: {e}")
                return False

    async def search(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Keyword search across conversation history."""
        async with AsyncSessionLocal() as db:
            pattern = f"%{keyword}%"
            stmt = select(MemoryTable).where(
                (MemoryTable.input.ilike(pattern)) | (MemoryTable.output.ilike(pattern))
            ).order_by(MemoryTable.created_at.desc()).limit(limit)
            
            result = await db.execute(stmt)
            return [self._to_dict(r) for r in result.scalars().all()]

     # Fixed indentation and ensured no leading invisible characters
    async def recall_recent(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recalls the most recent chat turns."""
        async with AsyncSessionLocal() as db:
            # We filter by user_id if you implement a user_id column in MemoryTable later
            # For now, it pulls the global most recent history
            stmt = select(MemoryTable).order_by(MemoryTable.created_at.desc()).limit(limit)
            result = await db.execute(stmt)
            rows = result.scalars().all()
            return [self._to_dict(r) for r in rows]

    def _to_dict(self, row) -> Dict[str, Any]:
        return {
            "input": row.input,
            "output": row.output,
            "context": row.context,
            "created_at": row.created_at.isoformat()
        }
