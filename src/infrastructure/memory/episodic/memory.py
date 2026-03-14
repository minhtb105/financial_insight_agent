"""
Episodic memory implementation using PostgreSQL with pgvector.

Stores aggregated experiences and semantic search capabilities.
Features:
- Semantic search with pgvector
- Episode aggregation and fact extraction
- Temporal weighting and deduplication
- Migration from short-term memory
"""

import logging
import json
import uuid
from typing import Any, Optional, Dict, List, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class Episode:
    """Represents an aggregated episode in episodic memory."""
    id: str
    query_type: str
    summary: str
    facts: List[Dict[str, Any]]
    confidence: float
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    embedding: Optional[List[float]] = None


@dataclass
class EpisodeFact:
    """Represents an atomic fact within an episode."""
    id: str
    episode_id: str
    fact_type: str
    fact_value: Any
    confidence: float
    source: str
    created_at: datetime
    embedding: Optional[List[float]] = None


class EpisodicMemory:
    """PostgreSQL-based episodic memory with semantic search."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "financial_agent",
        user: str = "postgres",
        password: str = "",
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.7,
        max_episodes: int = 10000,
        cleanup_days: int = 30
    ):
        """
        Initialize episodic memory.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            embedding_model: Sentence transformer model for embeddings
            similarity_threshold: Threshold for semantic similarity
            max_episodes: Maximum number of episodes to store
            cleanup_days: Days to keep episodes before cleanup
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.similarity_threshold = similarity_threshold
        self.max_episodes = max_episodes
        self.cleanup_days = cleanup_days
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info(f"Loaded embedding model: {embedding_model}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
        
        # Database connection parameters
        self.conn_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        
        # Initialize database schema
        self._init_database()
        
        logger.info(f"Initialized EpisodicMemory with {database}@{host}:{port}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """Initialize database schema with pgvector support."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Enable pgvector extension
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    
                    # Create episodes table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS episodes (
                            id VARCHAR(36) PRIMARY KEY,
                            query_type VARCHAR(50) NOT NULL,
                            summary TEXT NOT NULL,
                            facts JSONB NOT NULL,
                            confidence FLOAT NOT NULL,
                            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                            last_accessed TIMESTAMP,
                            access_count INTEGER DEFAULT 0,
                            embedding VECTOR(384)
                        );
                    """)
                    
                    # Create episode_facts table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS episode_facts (
                            id VARCHAR(36) PRIMARY KEY,
                            episode_id VARCHAR(36) REFERENCES episodes(id) ON DELETE CASCADE,
                            fact_type VARCHAR(50) NOT NULL,
                            fact_value JSONB NOT NULL,
                            confidence FLOAT NOT NULL,
                            source VARCHAR(100) NOT NULL,
                            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                            embedding VECTOR(384)
                        );
                    """)
                    
                    # Create indexes
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_query_type ON episodes(query_type);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_created_at ON episodes(created_at);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_embedding ON episodes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_episode_facts_episode_id ON episode_facts(episode_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_episode_facts_fact_type ON episode_facts(fact_type);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_episode_facts_embedding ON episode_facts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
                    
                    conn.commit()
                    logger.info("Episodic memory database schema initialized")
                    
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        if not self.embedding_model:
            return None
        
        try:
            embedding = self.embedding_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def _calculate_confidence(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for episode based on interactions."""
        if not interactions:
            return 0.5
        
        # Simple confidence calculation based on interaction confidence scores
        total_confidence = sum(interaction.get("confidence", 0.5) for interaction in interactions)
        return total_confidence / len(interactions)
    
    def _extract_facts(self, interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract facts from interactions."""
        facts = []
        
        for interaction in interactions:
            context = interaction.get("context", {})
            
            # Extract company facts
            if "tickers" in context:
                for ticker in context["tickers"]:
                    facts.append({
                        "type": "company_mention",
                        "value": ticker,
                        "source": "user_query",
                        "confidence": interaction.get("confidence", 0.5)
                    })
            
            # Extract query type facts
            if "query_type" in context:
                facts.append({
                    "type": "query_type",
                    "value": context["query_type"],
                    "source": "parsed_query",
                    "confidence": interaction.get("confidence", 0.5)
                })
            
            # Extract temporal facts
            if "start" in context or "end" in context:
                facts.append({
                    "type": "temporal_context",
                    "value": {
                        "start": context.get("start"),
                        "end": context.get("end")
                    },
                    "source": "parsed_query",
                    "confidence": interaction.get("confidence", 0.5)
                })
        
        return facts
    
    def migrate_from_short_term(
        self, 
        interactions: List[Dict[str, Any]], 
        summary: Optional[str] = None
    ) -> bool:
        """
        Migrate interactions from short-term memory to episodic memory.
        
        Args:
            interactions: List of interactions to migrate
            summary: Optional summary (auto-generated if None)
            
        Returns:
            True if successful, False otherwise
        """
        if not interactions:
            return False
        
        try:
            # Analyze interactions to create episode
            query_types = [inter.get("context", {}).get("query_type", "unknown") for inter in interactions]
            most_common_type = max(set(query_types), key=query_types.count)
            
            # Generate summary if not provided
            if not summary:
                user_queries = [inter["user_query"] for inter in interactions]
                summary = f"Episode with {len(interactions)} interactions of type '{most_common_type}'"
            
            # Extract facts and calculate confidence
            facts = self._extract_facts(interactions)
            confidence = self._calculate_confidence(interactions)
            
            # Generate embeddings
            summary_embedding = self._generate_embedding(summary)
            
            episode_id = str(uuid.uuid4())
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Insert episode
                    episode_data = (
                        episode_id,
                        most_common_type,
                        summary,
                        json.dumps(facts),
                        confidence,
                        datetime.now(),
                        None,
                        0,
                        summary_embedding
                    )
                    
                    cur.execute("""
                        INSERT INTO episodes (id, query_type, summary, facts, confidence, created_at, last_accessed, access_count, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, episode_data)
                    
                    # Insert facts
                    fact_records = []
                    for fact in facts:
                        fact_id = str(uuid.uuid4())
                        fact_embedding = self._generate_embedding(f"{fact['type']}: {fact['value']}")
                        
                        fact_record = (
                            fact_id,
                            episode_id,
                            fact["type"],
                            json.dumps(fact["value"]),
                            fact["confidence"],
                            fact["source"],
                            datetime.now(),
                            fact_embedding
                        )
                        fact_records.append(fact_record)
                    
                    if fact_records:
                        execute_values(cur, """
                            INSERT INTO episode_facts (id, episode_id, fact_type, fact_value, confidence, source, created_at, embedding)
                            VALUES %s
                        """, fact_records)
                    
                    conn.commit()
                    logger.info(f"Migrated {len(interactions)} interactions to episodic memory as episode {episode_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to migrate to episodic memory: {e}")
            return False
    
    def search_episodes(
        self, 
        query: str, 
        query_type: Optional[str] = None,
        top_k: int = 5,
        min_confidence: float = 0.5
    ) -> List[Episode]:
        """
        Search episodes using semantic similarity.
        
        Args:
            query: Search query
            query_type: Filter by query type
            top_k: Number of results to return
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of matching episodes
        """
        if not self.embedding_model:
            logger.warning("Embedding model not available, returning empty results")
            return []
        
        try:
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                return []
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Build query
                    base_query = """
                        SELECT id, query_type, summary, facts, confidence, created_at, last_accessed, access_count
                        FROM episodes 
                        WHERE confidence >= %s
                    """
                    params = [min_confidence]
                    
                    if query_type:
                        base_query += " AND query_type = %s"
                        params.append(query_type)
                    
                    # Add semantic similarity search
                    base_query += """
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """
                    params.extend([query_embedding, top_k])
                    
                    cur.execute(base_query, params)
                    results = cur.fetchall()
                    
                    episodes = []
                    for row in results:
                        episode = Episode(
                            id=row['id'],
                            query_type=row['query_type'],
                            summary=row['summary'],
                            facts=json.loads(row['facts']),
                            confidence=row['confidence'],
                            created_at=row['created_at'],
                            last_accessed=row['last_accessed'],
                            access_count=row['access_count']
                        )
                        episodes.append(episode)
                    
                    # Update access counts
                    if episodes:
                        self._update_episode_access([ep.id for ep in episodes])
                    
                    return episodes
                    
        except Exception as e:
            logger.error(f"Failed to search episodes: {e}")
            return []
    
    def search_facts(
        self, 
        query: str, 
        fact_type: Optional[str] = None,
        top_k: int = 10,
        min_confidence: float = 0.5
    ) -> List[EpisodeFact]:
        """
        Search facts using semantic similarity.
        
        Args:
            query: Search query
            fact_type: Filter by fact type
            top_k: Number of results to return
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of matching facts
        """
        if not self.embedding_model:
            logger.warning("Embedding model not available, returning empty results")
            return []
        
        try:
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                return []
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Build query
                    base_query = """
                        SELECT ef.id, ef.episode_id, ef.fact_type, ef.fact_value, ef.confidence, ef.source, ef.created_at
                        FROM episode_facts ef
                        JOIN episodes e ON ef.episode_id = e.id
                        WHERE ef.confidence >= %s
                    """
                    params = [min_confidence]
                    
                    if fact_type:
                        base_query += " AND ef.fact_type = %s"
                        params.append(fact_type)
                    
                    # Add semantic similarity search
                    base_query += """
                        ORDER BY ef.embedding <=> %s::vector
                        LIMIT %s
                    """
                    params.extend([query_embedding, top_k])
                    
                    cur.execute(base_query, params)
                    results = cur.fetchall()
                    
                    facts = []
                    for row in results:
                        fact = EpisodeFact(
                            id=row['id'],
                            episode_id=row['episode_id'],
                            fact_type=row['fact_type'],
                            fact_value=json.loads(row['fact_value']),
                            confidence=row['confidence'],
                            source=row['source'],
                            created_at=row['created_at']
                        )
                        facts.append(fact)
                    
                    return facts
                    
        except Exception as e:
            logger.error(f"Failed to search facts: {e}")
            return []
    
    def get_episode_by_id(self, episode_id: str) -> Optional[Episode]:
        """Get episode by ID."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT id, query_type, summary, facts, confidence, created_at, last_accessed, access_count
                        FROM episodes WHERE id = %s
                    """, [episode_id])
                    
                    row = cur.fetchone()
                    if row:
                        episode = Episode(
                            id=row['id'],
                            query_type=row['query_type'],
                            summary=row['summary'],
                            facts=json.loads(row['facts']),
                            confidence=row['confidence'],
                            created_at=row['created_at'],
                            last_accessed=row['last_accessed'],
                            access_count=row['access_count']
                        )
                        
                        # Update access count
                        self._update_episode_access([episode_id])
                        
                        return episode
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get episode by ID: {e}")
            return None
    
    def get_facts_by_type(self, fact_type: str, limit: int = 100) -> List[EpisodeFact]:
        """Get facts by type."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT id, episode_id, fact_type, fact_value, confidence, source, created_at
                        FROM episode_facts 
                        WHERE fact_type = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, [fact_type, limit])
                    
                    results = cur.fetchall()
                    
                    facts = []
                    for row in results:
                        fact = EpisodeFact(
                            id=row['id'],
                            episode_id=row['episode_id'],
                            fact_type=row['fact_type'],
                            fact_value=json.loads(row['fact_value']),
                            confidence=row['confidence'],
                            source=row['source'],
                            created_at=row['created_at']
                        )
                        facts.append(fact)
                    
                    return facts
                    
        except Exception as e:
            logger.error(f"Failed to get facts by type: {e}")
            return []
    
    def _update_episode_access(self, episode_ids: List[str]) -> None:
        """Update access counts and last_accessed for episodes."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE episodes 
                        SET access_count = access_count + 1, last_accessed = NOW()
                        WHERE id = ANY(%s)
                    """, [episode_ids])
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update episode access: {e}")
    
    def cleanup_old_episodes(self, days: Optional[int] = None) -> int:
        """
        Clean up old episodes.
        
        Args:
            days: Number of days to keep episodes (uses cleanup_days if None)
            
        Returns:
            Number of episodes deleted
        """
        cleanup_days = days or self.cleanup_days
        
        try:
            cutoff_date = datetime.now() - timedelta(days=cleanup_days)
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Count episodes to be deleted
                    cur.execute("SELECT COUNT(*) FROM episodes WHERE created_at < %s", [cutoff_date])
                    count = cur.fetchone()[0]
                    
                    if count > 0:
                        # Delete old episodes (facts will be deleted via CASCADE)
                        cur.execute("DELETE FROM episodes WHERE created_at < %s", [cutoff_date])
                        conn.commit()
                        
                        logger.info(f"Cleaned up {count} old episodes")
                    
                    return count
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old episodes: {e}")
            return 0
    
    def deduplicate_facts(self, similarity_threshold: Optional[float] = None) -> int:
        """
        Deduplicate similar facts based on embeddings.
        
        Args:
            similarity_threshold: Threshold for considering facts similar
            
        Returns:
            Number of facts deduplicated
        """
        threshold = similarity_threshold or self.similarity_threshold
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # This is a simplified deduplication
                    # In practice, you might want more sophisticated logic
                    cur.execute("""
                        DELETE FROM episode_facts ef1
                        USING episode_facts ef2
                        WHERE ef1.id < ef2.id
                        AND ef1.fact_type = ef2.fact_type
                        AND ef1.episode_id = ef2.episode_id
                        AND ef1.embedding <=> ef2.embedding < %s
                    """, [threshold])
                    
                    deleted_count = cur.rowcount
                    conn.commit()
                    
                    if deleted_count > 0:
                        logger.info(f"Deduplicated {deleted_count} similar facts")
                    
                    return deleted_count
                    
        except Exception as e:
            logger.error(f"Failed to deduplicate facts: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Episode statistics
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_episodes,
                            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 day') as episodes_24h,
                            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as episodes_7d,
                            AVG(confidence) as avg_confidence,
                            AVG(access_count) as avg_access_count
                        FROM episodes
                    """)
                    episode_stats = cur.fetchone()
                    
                    # Fact statistics
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_facts,
                            COUNT(DISTINCT fact_type) as unique_fact_types,
                            AVG(confidence) as avg_fact_confidence
                        FROM episode_facts
                    """)
                    fact_stats = cur.fetchone()
                    
                    return {
                        "memory_type": "episodic",
                        "episodes": dict(episode_stats) if episode_stats else {},
                        "facts": dict(fact_stats) if fact_stats else {},
                        "embedding_model": self.embedding_model.model_card_data.model_name if self.embedding_model else None,
                        "similarity_threshold": self.similarity_threshold,
                        "max_episodes": self.max_episodes,
                        "cleanup_days": self.cleanup_days
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    def clear(self) -> bool:
        """Clear all episodic memory."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM episodes")
                    conn.commit()
                    logger.info("Cleared all episodic memory")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to clear episodic memory: {e}")
            return False


# Global episodic memory instance
_episodic_memory_instance: Optional[EpisodicMemory] = None


def get_episodic_memory() -> Optional[EpisodicMemory]:
    """Get global episodic memory instance."""
    global _episodic_memory_instance
    if _episodic_memory_instance is None:
        try:
            _episodic_memory_instance = EpisodicMemory()
        except Exception as e:
            logger.error(f"Failed to create episodic memory instance: {e}")
            _episodic_memory_instance = None
    return _episodic_memory_instance


def set_episodic_memory_instance(memory: EpisodicMemory) -> None:
    """Set global episodic memory instance (for testing)."""
    global _episodic_memory_instance
    _episodic_memory_instance = memory