"""Unit tests for EpisodicStore (embedder + Qdrant client mocked)."""

import pytest

from infrastructure.memory.episodic import store as episodic_store
from infrastructure.memory.episodic.schemas import Episode
from infrastructure.memory.episodic.store import EpisodicStore


class FakeEmbedder:
    dim = 4

    def embed(self, texts):
        # deterministic 4-dim vectors from text length
        return [[float(len(t) % 7), 0.1, 0.2, 0.3] for t in texts]


class FakePoint:
    def __init__(self, pid, score, payload):
        self.id = pid
        self.score = score
        self.payload = payload


class FakeQueryResult:
    def __init__(self, points):
        self.points = points


class FakeQdrant:
    """Records calls and returns canned results."""

    def __init__(self):
        self.indexes = []
        self.upserted = []
        self.deleted = []
        self.hits = []
        self.last_filter = None

    def create_payload_index(self, collection_name, field_name, field_schema):
        self.indexes.append((collection_name, field_name))

    def query_points(self, collection_name, query, query_filter=None, limit=5, with_payload=True):
        self.last_filter = query_filter
        return FakeQueryResult(self.hits[:limit])

    def scroll(  # noqa: PLR0917
        self, collection_name, scroll_filter=None, limit=100, offset=None,
        with_payload=False, with_vectors=False,
    ):
        return ([], None)

    def delete(self, collection_name, points_selector):
        self.deleted.extend(points_selector)
        return True

    def count(self, collection_name, count_filter=None, exact=True):
        class R:
            count = 3
        return R()


@pytest.fixture
def fake_qdrant(monkeypatch):
    fq = FakeQdrant()
    monkeypatch.setattr(episodic_store.vs, "_client", lambda: fq)
    monkeypatch.setattr(episodic_store.vs, "ensure_collection", lambda name, dim=1536, recreate=False: None)
    upserted = []

    def fake_upsert(collection, points, batch_size=100):
        upserted.extend(points)
        fq.upserted.extend(points)
        return len(points)

    monkeypatch.setattr(episodic_store.vs, "upsert_points", fake_upsert)
    monkeypatch.setattr(
        episodic_store.vs, "collection_info", lambda name: {"name": name, "points_count": 9}
    )
    return fq


@pytest.fixture
def store():
    return EpisodicStore(embedder=FakeEmbedder(), min_score=0.0)


def test_ensure_creates_user_indexes(store, fake_qdrant):
    store.ensure()
    fields = [f for _, f in fake_qdrant.indexes]
    assert "user_id" in fields
    assert "session_id" in fields


def test_add_episode_payload_shape(store, fake_qdrant):
    episode_id = store.add_episode(user_id="u1", text="HPG tăng trần hôm nay", session_id="s1")
    assert episode_id
    assert len(fake_qdrant.upserted) == 1
    point = fake_qdrant.upserted[0]
    assert point["payload"]["user_id"] == "u1"
    assert point["payload"]["text"] == "HPG tăng trần hôm nay"
    assert point["payload"]["session_id"] == "s1"


def test_add_episode_empty_text(store, fake_qdrant):
    assert store.add_episode(user_id="u1", text="   ") is None
    assert fake_qdrant.upserted == []


def test_search_scopes_to_user_and_formats_context(store, fake_qdrant):
    fake_qdrant.hits = [
        FakePoint("id1", 0.9, {"text": "HPG steel analysis", "user_id": "u1"}),
        FakePoint("id2", 0.1, {"text": "unrelated", "user_id": "u1"}),
    ]
    store.min_score = 0.5
    result = store.search_episodes("thép HPG", user_id="u1", top_k=5)
    assert result["count"] == 1
    assert result["hits"][0]["id"] == "id1"
    assert "HPG steel analysis" in result["context"]
    # user_id filter was sent to Qdrant
    assert fake_qdrant.last_filter is not None
    conds = fake_qdrant.last_filter.must
    assert any(getattr(c, "key", None) == "user_id" for c in conds)


def test_search_min_score_filters(store, fake_qdrant):
    fake_qdrant.hits = [FakePoint("id1", 0.2, {"text": "x"})]
    result = store.search_episodes("q", user_id="u1", min_score=0.9)
    assert result["count"] == 0
    assert result["hits"] == []


def test_episode_schema_roundtrip():
    ep = Episode(text="hello", user_id="u1", session_id="s1")
    payload = ep.to_payload()
    back = Episode.from_payload(ep.id, payload)
    assert back.text == "hello"
    assert back.user_id == "u1"
    assert back.session_id == "s1"
