"""
Long-term memory implementation using PostgreSQL.

Stores persistent knowledge including company profiles, market patterns,
query patterns, and model learnings with temporal weighting.
"""

import logging
import json
import uuid
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class CompanyProfile:
    """Represents a company profile in long-term memory."""
    ticker: str
    profile: Dict[str, Any]
    last_updated: datetime
    confidence: float
    source: str
    temporal_weight: float = 1.0


@dataclass
class MarketPattern:
    """Represents a market pattern in long-term memory."""
    pattern_type: str
    description: str
    pattern_data: Dict[str, Any]
    confidence: float
    discovered_at: datetime
    last_verified: datetime
    temporal_weight: float = 1.0


@dataclass
class QueryPattern:
    """Represents a query pattern in long-term memory."""
    query_type: str
    pattern_data: Dict[str, Any]
    success_rate: float
    avg_response_time: float
    last_used: datetime
    temporal_weight: float = 1.0


@dataclass
class ModelLearning:
    """Represents model learning in long-term memory."""
    learning_type: str
    learning_data: Dict[str, Any]
    confidence: float
    learned_at: datetime
    temporal_weight: float = 1.0


class LongTermMemory:
    """PostgreSQL-based long-term memory for persistent knowledge."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "financial_agent",
        user: str = "postgres",
        password: str = "",
        embedding_model: str = "all-MiniLM-L6-v2",
        temporal_decay_rate: float = 0.1,  # Monthly decay rate
        max_company_profiles: int = 1000,
        max_market_patterns: int = 500,
        cleanup_months: int = 12
    ):
        """
        Initialize long-term memory.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            embedding_model: Sentence transformer model for embeddings
            temporal_decay_rate: Rate at which temporal weights decay
            max_company_profiles: Maximum company profiles to store
            max_market_patterns: Maximum market patterns to store
            cleanup_months: Months to keep data before cleanup
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.temporal_decay_rate = temporal_decay_rate
        self.max_company_profiles = max_company_profiles
        self.max_market_patterns = max_market_patterns
        self.cleanup_months = cleanup_months
        
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
        
        logger.info(f"Initialized LongTermMemory with {database}@{host}:{port}")
    
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
        """Initialize database schema."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Enable pgvector extension
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    
                    # Create company_profiles table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS company_profiles (
                            ticker VARCHAR(10) PRIMARY KEY,
                            profile JSONB NOT NULL,
                            last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
                            confidence FLOAT NOT NULL,
                            source VARCHAR(100) NOT NULL,
                            temporal_weight FLOAT DEFAULT 1.0,
                            embedding VECTOR(384)
                        );
                    """)
                    
                    # Create market_patterns table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS market_patterns (
                            id VARCHAR(36) PRIMARY KEY,
                            pattern_type VARCHAR(50) NOT NULL,
                            description TEXT NOT NULL,
                            pattern_data JSONB NOT NULL,
                            confidence FLOAT NOT NULL,
                            discovered_at TIMESTAMP NOT NULL DEFAULT NOW(),
                            last_verified TIMESTAMP NOT NULL DEFAULT NOW(),
                            temporal_weight FLOAT DEFAULT 1.0,
                            embedding VECTOR(384)
                        );
                    """)
                    
                    # Create query_patterns table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS query_patterns (
                            query_type VARCHAR(50) PRIMARY KEY,
                            pattern_data JSONB NOT NULL,
                            success_rate FLOAT NOT NULL,
                            avg_response_time FLOAT NOT NULL,
                            last_used TIMESTAMP NOT NULL DEFAULT NOW(),
                            temporal_weight FLOAT DEFAULT 1.0,
                            embedding VECTOR(384)
                        );
                    """)
                    
                    # Create model_learnings table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS model_learnings (
                            id VARCHAR(36) PRIMARY KEY,
                            learning_type VARCHAR(50) NOT NULL,
                            learning_data JSONB NOT NULL,
                            confidence FLOAT NOT NULL,
                            learned_at TIMESTAMP NOT NULL DEFAULT NOW(),
                            temporal_weight FLOAT DEFAULT 1.0,
                            embedding VECTOR(384)
                        );
                    """)
                    
                    # Create indexes
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_company_profiles_last_updated ON company_profiles(last_updated);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_company_profiles_confidence ON company_profiles(confidence);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_company_profiles_embedding ON company_profiles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
                    
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_patterns_pattern_type ON market_patterns(pattern_type);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_patterns_discovered_at ON market_patterns(discovered_at);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_patterns_embedding ON market_patterns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
                    
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_query_patterns_success_rate ON query_patterns(success_rate);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_query_patterns_last_used ON query_patterns(last_used);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_query_patterns_embedding ON query_patterns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
                    
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_model_learnings_learning_type ON model_learnings(learning_type);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_model_learnings_learned_at ON model_learnings(learned_at);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_model_learnings_embedding ON model_learnings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
                    
                    conn.commit()
                    logger.info("Long-term memory database schema initialized")
                    
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
    
    def _calculate_temporal_weight(self, last_updated: datetime) -> float:
        """Calculate temporal weight based on decay rate."""
        age_months = (datetime.now() - last_updated).days / 30
        return max(0.1, np.exp(-self.temporal_decay_rate * age_months))
    
    def _apply_temporal_decay(self) -> None:
        """Apply temporal decay to all records."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Update company profiles
                    cur.execute("""
                        UPDATE company_profiles 
                        SET temporal_weight = GREATEST(0.1, EXP(-%s * (NOW() - last_updated) / INTERVAL '30 days'))
                    """, [self.temporal_decay_rate])
                    
                    # Update market patterns
                    cur.execute("""
                        UPDATE market_patterns 
                        SET temporal_weight = GREATEST(0.1, EXP(-%s * (NOW() - last_verified) / INTERVAL '30 days'))
                    """, [self.temporal_decay_rate])
                    
                    # Update query patterns
                    cur.execute("""
                        UPDATE query_patterns 
                        SET temporal_weight = GREATEST(0.1, EXP(-%s * (NOW() - last_used) / INTERVAL '30 days'))
                    """, [self.temporal_decay_rate])
                    
                    # Update model learnings
                    cur.execute("""
                        UPDATE model_learnings 
                        SET temporal_weight = GREATEST(0.1, EXP(-%s * (NOW() - learned_at) / INTERVAL '30 days'))
                    """, [self.temporal_decay_rate])
                    
                    conn.commit()
                    logger.debug("Applied temporal decay to all records")
                    
        except Exception as e:
            logger.error(f"Failed to apply temporal decay: {e}")
    
    def store_company_profile(
        self, 
        ticker: str, 
        profile: Dict[str, Any], 
        source: str = "agent",
        confidence: float = 0.8
    ) -> bool:
        """
        Store or update company profile.
        
        Args:
            ticker: Company ticker symbol
            profile: Company profile data
            source: Source of the profile
            confidence: Confidence in the profile
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we need to evict old profiles
            self._evict_old_company_profiles()
            
            embedding = self._generate_embedding(json.dumps(profile, ensure_ascii=False))
            temporal_weight = self._calculate_temporal_weight(datetime.now())
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO company_profiles (ticker, profile, last_updated, confidence, source, temporal_weight, embedding)
                        VALUES (%s, %s, NOW(), %s, %s, %s, %s)
                        ON CONFLICT (ticker) 
                        DO UPDATE SET 
                            profile = EXCLUDED.profile,
                            last_updated = EXCLUDED.last_updated,
                            confidence = EXCLUDED.confidence,
                            source = EXCLUDED.source,
                            temporal_weight = EXCLUDED.temporal_weight,
                            embedding = EXCLUDED.embedding
                    """, [ticker, json.dumps(profile), confidence, source, temporal_weight, embedding])
                    
                    conn.commit()
                    logger.debug(f"Stored company profile for {ticker}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to store company profile: {e}")
            return False
    
    def get_company_profile(self, ticker: str) -> Optional[CompanyProfile]:
        """Get company profile by ticker."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT ticker, profile, last_updated, confidence, source, temporal_weight
                        FROM company_profiles 
                        WHERE ticker = %s
                    """, [ticker])
                    
                    row = cur.fetchone()
                    if row:
                        return CompanyProfile(
                            ticker=row['ticker'],
                            profile=json.loads(row['profile']),
                            last_updated=row['last_updated'],
                            confidence=row['confidence'],
                            source=row['source'],
                            temporal_weight=row['temporal_weight']
                        )
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get company profile: {e}")
            return None
    
    def store_market_pattern(
        self, 
        pattern_type: str, 
        description: str, 
        pattern_data: Dict[str, Any],
        confidence: float = 0.7
    ) -> bool:
        """
        Store market pattern.
        
        Args:
            pattern_type: Type of market pattern
            description: Description of the pattern
            pattern_data: Pattern data
            confidence: Confidence in the pattern
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we need to evict old patterns
            self._evict_old_market_patterns()
            
            embedding = self._generate_embedding(description)
            temporal_weight = self._calculate_temporal_weight(datetime.now())
            pattern_id = str(uuid.uuid4())
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO market_patterns (id, pattern_type, description, pattern_data, confidence, discovered_at, last_verified, temporal_weight, embedding)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s, %s)
                    """, [pattern_id, pattern_type, description, json.dumps(pattern_data), confidence, temporal_weight, embedding])
                    
                    conn.commit()
                    logger.debug(f"Stored market pattern: {pattern_type}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to store market pattern: {e}")
            return False
    
    def get_market_patterns(
        self, 
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 100
    ) -> List[MarketPattern]:
        """Get market patterns."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT id, pattern_type, description, pattern_data, confidence, discovered_at, last_verified, temporal_weight
                        FROM market_patterns 
                        WHERE confidence >= %s
                    """
                    params = [min_confidence]
                    
                    if pattern_type:
                        query += " AND pattern_type = %s"
                        params.append(pattern_type)
                    
                    query += " ORDER BY temporal_weight DESC, confidence DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    results = cur.fetchall()
                    
                    patterns = []
                    for row in results:
                        pattern = MarketPattern(
                            pattern_type=row['pattern_type'],
                            description=row['description'],
                            pattern_data=json.loads(row['pattern_data']),
                            confidence=row['confidence'],
                            discovered_at=row['discovered_at'],
                            last_verified=row['last_verified'],
                            temporal_weight=row['temporal_weight']
                        )
                        patterns.append(pattern)
                    
                    return patterns
                    
        except Exception as e:
            logger.error(f"Failed to get market patterns: {e}")
            return []
    
    def update_query_pattern(
        self, 
        query_type: str, 
        success: bool, 
        response_time: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update query pattern with new interaction data.
        
        Args:
            query_type: Type of query
            success: Whether the query was successful
            response_time: Response time in seconds
            additional_data: Additional pattern data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get existing pattern
                    cur.execute("""
                        SELECT pattern_data, success_rate, avg_response_time, last_used
                        FROM query_patterns 
                        WHERE query_type = %s
                    """, [query_type])
                    
                    row = cur.fetchone()
                    
                    if row:
                        # Update existing pattern
                        pattern_data = json.loads(row[0]) if row[0] else {}
                        old_success_rate = row[1] or 0.5
                        old_response_time = row[2] or response_time
                        last_used = row[3]
                        
                        # Simple moving average for success rate and response time
                        new_success_rate = old_success_rate * 0.9 + (1.0 if success else 0.0) * 0.1
                        new_response_time = old_response_time * 0.9 + response_time * 0.1
                        
                        # Update pattern data
                        if additional_data:
                            pattern_data.update(additional_data)
                        
                        temporal_weight = self._calculate_temporal_weight(datetime.now())
                        
                        cur.execute("""
                            UPDATE query_patterns 
                            SET pattern_data = %s, success_rate = %s, avg_response_time = %s, last_used = NOW(), temporal_weight = %s
                            WHERE query_type = %s
                        """, [json.dumps(pattern_data), new_success_rate, new_response_time, temporal_weight, query_type])
                        
                    else:
                        # Create new pattern
                        pattern_data = additional_data or {}
                        success_rate = 1.0 if success else 0.0
                        
                        embedding = self._generate_embedding(query_type)
                        temporal_weight = self._calculate_temporal_weight(datetime.now())
                        
                        cur.execute("""
                            INSERT INTO query_patterns (query_type, pattern_data, success_rate, avg_response_time, last_used, temporal_weight, embedding)
                            VALUES (%s, %s, %s, %s, NOW(), %s, %s)
                        """, [query_type, json.dumps(pattern_data), success_rate, response_time, temporal_weight, embedding])
                    
                    conn.commit()
                    logger.debug(f"Updated query pattern: {query_type}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update query pattern: {e}")
            return False
    
    def get_query_pattern(self, query_type: str) -> Optional[QueryPattern]:
        """Get query pattern by type."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT query_type, pattern_data, success_rate, avg_response_time, last_used, temporal_weight
                        FROM query_patterns 
                        WHERE query_type = %s
                    """, [query_type])
                    
                    row = cur.fetchone()
                    if row:
                        return QueryPattern(
                            query_type=row['query_type'],
                            pattern_data=json.loads(row['pattern_data']),
                            success_rate=row['success_rate'],
                            avg_response_time=row['avg_response_time'],
                            last_used=row['last_used'],
                            temporal_weight=row['temporal_weight']
                        )
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get query pattern: {e}")
            return None
    
    def store_model_learning(
        self, 
        learning_type: str, 
        learning_data: Dict[str, Any],
        confidence: float = 0.6
    ) -> bool:
        """
        Store model learning.
        
        Args:
            learning_type: Type of learning
            learning_data: Learning data
            confidence: Confidence in the learning
            
        Returns:
            True if successful, False otherwise
        """
        try:
            learning_id = str(uuid.uuid4())
            embedding = self._generate_embedding(json.dumps(learning_data, ensure_ascii=False))
            temporal_weight = self._calculate_temporal_weight(datetime.now())
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO model_learnings (id, learning_type, learning_data, confidence, learned_at, temporal_weight, embedding)
                        VALUES (%s, %s, %s, %s, NOW(), %s, %s)
                    """, [learning_id, learning_type, json.dumps(learning_data), confidence, temporal_weight, embedding])
                    
                    conn.commit()
                    logger.debug(f"Stored model learning: {learning_type}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to store model learning: {e}")
            return False
    
    def search_company_profiles(
        self, 
        query: str, 
        min_confidence: float = 0.5,
        top_k: int = 5
    ) -> List[CompanyProfile]:
        """Search company profiles using semantic similarity."""
        if not self.embedding_model:
            logger.warning("Embedding model not available, returning empty results")
            return []
        
        try:
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                return []
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT ticker, profile, last_updated, confidence, source, temporal_weight
                        FROM company_profiles 
                        WHERE confidence >= %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, [min_confidence, query_embedding, top_k])
                    
                    results = cur.fetchall()
                    
                    profiles = []
                    for row in results:
                        profile = CompanyProfile(
                            ticker=row['ticker'],
                            profile=json.loads(row['profile']),
                            last_updated=row['last_updated'],
                            confidence=row['confidence'],
                            source=row['source'],
                            temporal_weight=row['temporal_weight']
                        )
                        profiles.append(profile)
                    
                    return profiles
                    
        except Exception as e:
            logger.error(f"Failed to search company profiles: {e}")
            return []
    
    def _evict_old_company_profiles(self) -> None:
        """Evict old company profiles if limit exceeded."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Count current profiles
                    cur.execute("SELECT COUNT(*) FROM company_profiles")
                    count = cur.fetchone()[0]
                    
                    if count >= self.max_company_profiles:
                        # Remove oldest profiles
                        remove_count = count - self.max_company_profiles + 100  # Remove in batches
                        cur.execute("""
                            DELETE FROM company_profiles 
                            WHERE ticker IN (
                                SELECT ticker FROM company_profiles 
                                ORDER BY last_updated ASC 
                                LIMIT %s
                            )
                        """, [remove_count])
                        
                        conn.commit()
                        logger.info(f"Evicted {remove_count} old company profiles")
                        
        except Exception as e:
            logger.error(f"Failed to evict old company profiles: {e}")
    
    def _evict_old_market_patterns(self) -> None:
        """Evict old market patterns if limit exceeded."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Count current patterns
                    cur.execute("SELECT COUNT(*) FROM market_patterns")
                    count = cur.fetchone()[0]
                    
                    if count >= self.max_market_patterns:
                        # Remove oldest patterns
                        remove_count = count - self.max_market_patterns + 50  # Remove in batches
                        cur.execute("""
                            DELETE FROM market_patterns 
                            WHERE id IN (
                                SELECT id FROM market_patterns 
                                ORDER BY last_verified ASC 
                                LIMIT %s
                            )
                        """, [remove_count])
                        
                        conn.commit()
                        logger.info(f"Evicted {remove_count} old market patterns")
                        
        except Exception as e:
            logger.error(f"Failed to evict old market patterns: {e}")
    
    def cleanup_old_data(self, months: Optional[int] = None) -> Dict[str, int]:
        """
        Clean up old data.
        
        Args:
            months: Number of months to keep data (uses cleanup_months if None)
            
        Returns:
            Dictionary with cleanup counts
        """
        cleanup_months = months or self.cleanup_months
        
        try:
            cutoff_date = datetime.now() - timedelta(days=cleanup_months * 30)
            cleanup_counts = {}
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Clean up old company profiles
                    cur.execute("SELECT COUNT(*) FROM company_profiles WHERE last_updated < %s", [cutoff_date])
                    company_count = cur.fetchone()[0]
                    
                    if company_count > 0:
                        cur.execute("DELETE FROM company_profiles WHERE last_updated < %s", [cutoff_date])
                        cleanup_counts['company_profiles'] = company_count
                    
                    # Clean up old market patterns
                    cur.execute("SELECT COUNT(*) FROM market_patterns WHERE last_verified < %s", [cutoff_date])
                    pattern_count = cur.fetchone()[0]
                    
                    if pattern_count > 0:
                        cur.execute("DELETE FROM market_patterns WHERE last_verified < %s", [cutoff_date])
                        cleanup_counts['market_patterns'] = pattern_count
                    
                    # Clean up old query patterns
                    cur.execute("SELECT COUNT(*) FROM query_patterns WHERE last_used < %s", [cutoff_date])
                    query_count = cur.fetchone()[0]
                    
                    if query_count > 0:
                        cur.execute("DELETE FROM query_patterns WHERE last_used < %s", [cutoff_date])
                        cleanup_counts['query_patterns'] = query_count
                    
                    # Clean up old model learnings
                    cur.execute("SELECT COUNT(*) FROM model_learnings WHERE learned_at < %s", [cutoff_date])
                    learning_count = cur.fetchone()[0]
                    
                    if learning_count > 0:
                        cur.execute("DELETE FROM model_learnings WHERE learned_at < %s", [cutoff_date])
                        cleanup_counts['model_learnings'] = learning_count
                    
                    conn.commit()
                    
                    if cleanup_counts:
                        logger.info(f"Cleaned up old data: {cleanup_counts}")
                    
                    return cleanup_counts
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get long-term memory statistics."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Company profiles stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_profiles,
                            COUNT(*) FILTER (WHERE temporal_weight > 0.5) as recent_profiles,
                            AVG(confidence) as avg_confidence,
                            AVG(temporal_weight) as avg_temporal_weight
                        FROM company_profiles
                    """)
                    company_stats = cur.fetchone()
                    
                    # Market patterns stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_patterns,
                            COUNT(DISTINCT pattern_type) as unique_types,
                            AVG(confidence) as avg_confidence,
                            AVG(temporal_weight) as avg_temporal_weight
                        FROM market_patterns
                    """)
                    pattern_stats = cur.fetchone()
                    
                    # Query patterns stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_patterns,
                            AVG(success_rate) as avg_success_rate,
                            AVG(avg_response_time) as avg_response_time,
                            AVG(temporal_weight) as avg_temporal_weight
                        FROM query_patterns
                    """)
                    query_stats = cur.fetchone()
                    
                    # Model learnings stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_learnings,
                            COUNT(DISTINCT learning_type) as unique_types,
                            AVG(confidence) as avg_confidence,
                            AVG(temporal_weight) as avg_temporal_weight
                        FROM model_learnings
                    """)
                    learning_stats = cur.fetchone()
                    
                    return {
                        "memory_type": "long_term",
                        "company_profiles": dict(company_stats) if company_stats else {},
                        "market_patterns": dict(pattern_stats) if pattern_stats else {},
                        "query_patterns": dict(query_stats) if query_stats else {},
                        "model_learnings": dict(learning_stats) if learning_stats else {},
                        "temporal_decay_rate": self.temporal_decay_rate,
                        "max_company_profiles": self.max_company_profiles,
                        "max_market_patterns": self.max_market_patterns,
                        "cleanup_months": self.cleanup_months
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    def clear(self) -> bool:
        """Clear all long-term memory."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM company_profiles")
                    cur.execute("DELETE FROM market_patterns")
                    cur.execute("DELETE FROM query_patterns")
                    cur.execute("DELETE FROM model_learnings")
                    conn.commit()
                    logger.info("Cleared all long-term memory")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to clear long-term memory: {e}")
            return False


# Global long-term memory instance
_long_term_memory_instance: Optional[LongTermMemory] = None


def get_long_term_memory() -> Optional[LongTermMemory]:
    """Get global long-term memory instance."""
    global _long_term_memory_instance
    if _long_term_memory_instance is None:
        try:
            _long_term_memory_instance = LongTermMemory()
        except Exception as e:
            logger.error(f"Failed to create long-term memory instance: {e}")
            _long_term_memory_instance = None
    return _long_term_memory_instance


def set_long_term_memory_instance(memory: LongTermMemory) -> None:
    """Set global long-term memory instance (for testing)."""
    global _long_term_memory_instance
    _long_term_memory_instance = memory