import pytest
from pathlib import Path
from omagent.core.memory import ConversationSummarizer, MemoryStore


@pytest.fixture
def summarizer():
    return ConversationSummarizer(max_messages=5, keep_recent=2)


@pytest.fixture
def store(tmp_path):
    return MemoryStore(db_path=tmp_path / "test.db")


def test_needs_summarization(summarizer):
    short = [{"role": "user", "content": "hi"}] * 3
    long = [{"role": "user", "content": "hi"}] * 10
    assert not summarizer.needs_summarization(short)
    assert summarizer.needs_summarization(long)


def test_fallback_summary(summarizer):
    messages = [
        {"role": "user", "content": "analyze sales data"},
        {"role": "assistant", "content": "I'll look at the data"},
        {"role": "user", "content": "show me the trends"},
        {"role": "tool", "content": '{"output": "done"}'},
    ]
    summary = summarizer._fallback_summary(messages)
    assert "4 messages" in summary
    assert "analyze sales data" in summary


def test_messages_to_transcript(summarizer):
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    transcript = summarizer._messages_to_transcript(messages)
    assert "USER: hello" in transcript
    assert "ASSISTANT: hi there" in transcript


@pytest.mark.asyncio
async def test_memory_store_set_get(store):
    await store.set("sess-1", "dataset", "sales.csv loaded, 1000 rows")
    value = await store.get("sess-1", "dataset")
    assert value == "sales.csv loaded, 1000 rows"


@pytest.mark.asyncio
async def test_memory_store_get_all(store):
    await store.set("sess-1", "key1", "val1")
    await store.set("sess-1", "key2", "val2")
    all_mems = await store.get_all("sess-1")
    assert len(all_mems) == 2
    assert all_mems["key1"] == "val1"


@pytest.mark.asyncio
async def test_memory_store_delete(store):
    await store.set("sess-1", "temp", "data")
    deleted = await store.delete("sess-1", "temp")
    assert deleted
    assert await store.get("sess-1", "temp") is None


@pytest.mark.asyncio
async def test_context_injection(store):
    await store.set("sess-1", "dataset", "sales.csv")
    await store.set("sess-1", "finding", "revenue up 15%")
    ctx = await store.get_context_injection("sess-1")
    assert "[Agent Memory]" in ctx
    assert "dataset: sales.csv" in ctx


@pytest.mark.asyncio
async def test_context_injection_empty(store):
    ctx = await store.get_context_injection("empty-sess")
    assert ctx is None
