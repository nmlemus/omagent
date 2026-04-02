import pytest
from omagent.core.planner import AgentPlan, PlanStep, PlanStore


def test_plan_creation():
    plan = AgentPlan(goal="Analyze sales data")
    plan.add_step("Load the CSV file")
    plan.add_step("Clean missing values")
    plan.add_step("Generate visualizations")
    assert len(plan.steps) == 3
    assert plan.progress == "0/3"


def test_plan_step_lifecycle():
    plan = AgentPlan(goal="Test")
    plan.add_step("Step 1")
    plan.add_step("Step 2")

    plan.start_step(1, tool_name="read_file")
    assert plan.steps[0].status == "in_progress"

    plan.complete_step(1, result_summary="File loaded")
    assert plan.steps[0].status == "completed"
    assert plan.progress == "1/2"


def test_plan_auto_complete():
    plan = AgentPlan(goal="Test")
    plan.add_step("Only step")
    plan.complete_step(1)
    assert plan.status == "completed"


def test_parse_from_text():
    text = """Here's my approach to analyze the data:

1. Load the dataset from sales.csv
2. Check for missing values and clean the data
3. Generate summary statistics
4. Create visualizations for key metrics
"""
    plan = AgentPlan.parse_from_text(text)
    assert plan is not None
    assert len(plan.steps) == 4
    assert "Load the dataset" in plan.steps[0].description


def test_parse_no_plan():
    text = "Just a regular response with no numbered steps."
    plan = AgentPlan.parse_from_text(text)
    assert plan is None


def test_serialization():
    plan = AgentPlan(goal="Test goal")
    plan.add_step("Step 1")
    plan.complete_step(1)

    data = plan.to_dict()
    restored = AgentPlan.from_dict(data)
    assert restored.goal == "Test goal"
    assert restored.steps[0].status == "completed"


@pytest.mark.asyncio
async def test_plan_store(tmp_path):
    store = PlanStore(db_path=tmp_path / "test.db")
    plan = AgentPlan(goal="Store test")
    plan.add_step("Step 1")

    await store.save("sess-1", plan)
    loaded = await store.load("sess-1")
    assert loaded is not None
    assert loaded.goal == "Store test"
    assert len(loaded.steps) == 1
