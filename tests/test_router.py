"""Tests for network95_router — HTTP endpoints via FastAPI TestClient."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.network95_router import router, set_agent
from src.agents.network95_agent import Network95Agent
from src.core.mission_manager import MissionStatus


@pytest.fixture(scope="module")
def agent():
    return Network95Agent(config={"persist_missions": False})


@pytest.fixture(scope="module")
def client(agent):
    app = FastAPI()
    set_agent(agent)
    app.include_router(router)
    return TestClient(app)


# ── Agent not initialised ─────────────────────────────────────────────────────

def test_503_when_no_agent():
    app = FastAPI()
    set_agent(None)
    app.include_router(router)
    c = TestClient(app)
    resp = c.get("/api/v1/missions")
    assert resp.status_code == 503
    # Restore
    set_agent(None)


# ── POST /api/v1/missions ─────────────────────────────────────────────────────

class TestCreateMission:

    def test_create_returns_201(self, client, agent):
        set_agent(agent)
        resp = client.post("/api/v1/missions", json={"objective": "test mission"})
        assert resp.status_code == 201

    def test_create_returns_mission_id(self, client, agent):
        set_agent(agent)
        resp = client.post("/api/v1/missions", json={"objective": "another test"})
        data = resp.json()
        assert "mission_id" in data
        assert len(data["mission_id"]) > 8

    def test_create_default_status_queued(self, client, agent):
        set_agent(agent)
        resp = client.post("/api/v1/missions", json={"objective": "queued test"})
        data = resp.json()
        assert data["status"] == MissionStatus.QUEUED.value

    def test_create_with_priority(self, client, agent):
        set_agent(agent)
        resp = client.post("/api/v1/missions", json={"objective": "high priority", "priority": 1})
        assert resp.status_code == 201
        mid = resp.json()["mission_id"]
        m = agent.mission_manager.get(mid)
        assert m.priority == 1

    def test_create_auto_run_flag_accepted(self, client, agent):
        set_agent(agent)
        resp = client.post("/api/v1/missions", json={"objective": "auto run test", "auto_run": True})
        assert resp.status_code == 201
        assert resp.json()["auto_run"] is True


# ── GET /api/v1/missions ──────────────────────────────────────────────────────

class TestListMissions:

    def test_list_returns_200(self, client, agent):
        set_agent(agent)
        resp = client.get("/api/v1/missions")
        assert resp.status_code == 200

    def test_list_has_missions_key(self, client, agent):
        set_agent(agent)
        resp = client.get("/api/v1/missions")
        assert "missions" in resp.json()

    def test_list_view_queue(self, client, agent):
        set_agent(agent)
        resp = client.get("/api/v1/missions?view=queue")
        data = resp.json()
        assert data["view"] == "queue"
        assert isinstance(data["missions"], list)

    def test_list_view_running(self, client, agent):
        set_agent(agent)
        resp = client.get("/api/v1/missions?view=running")
        data = resp.json()
        assert data["view"] == "running"

    def test_list_limit_parameter(self, client, agent):
        set_agent(agent)
        for i in range(5):
            client.post("/api/v1/missions", json={"objective": f"limit test {i}"})
        resp = client.get("/api/v1/missions?limit=2")
        data = resp.json()
        assert len(data["missions"]) <= 2


# ── GET /api/v1/missions/{id} ─────────────────────────────────────────────────

class TestGetMission:

    def test_get_existing_mission(self, client, agent):
        set_agent(agent)
        create_resp = client.post("/api/v1/missions", json={"objective": "fetch me"})
        mid = create_resp.json()["mission_id"]
        resp = client.get(f"/api/v1/missions/{mid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mission_id"] == mid
        assert data["objective"] == "fetch me"

    def test_get_404_for_missing_mission(self, client, agent):
        set_agent(agent)
        resp = client.get("/api/v1/missions/nonexistent-id-xyz")
        assert resp.status_code == 404

    def test_get_mission_has_full_fields(self, client, agent):
        set_agent(agent)
        create_resp = client.post("/api/v1/missions", json={"objective": "full fields test"})
        mid = create_resp.json()["mission_id"]
        resp = client.get(f"/api/v1/missions/{mid}")
        data = resp.json()
        for field in ("mission_id", "objective", "status", "stage", "stages_completed", "priority"):
            assert field in data


# ── POST /api/v1/missions/{id}/run ────────────────────────────────────────────

class TestRunMission:

    def test_run_queued_mission_returns_202_style(self, client, agent):
        set_agent(agent)
        create_resp = client.post("/api/v1/missions", json={"objective": "run trigger test"})
        mid = create_resp.json()["mission_id"]
        resp = client.post(f"/api/v1/missions/{mid}/run")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running_async"

    def test_run_nonexistent_mission_404(self, client, agent):
        set_agent(agent)
        resp = client.post("/api/v1/missions/bad-id/run")
        assert resp.status_code == 404

    def test_run_already_running_mission_409(self, client, agent):
        set_agent(agent)
        mid = agent.create_mission("conflict test")
        agent.mission_manager.start(mid)  # manually set to RUNNING
        resp = client.post(f"/api/v1/missions/{mid}/run")
        assert resp.status_code == 409


# ── GET /api/v1/missions/status ───────────────────────────────────────────────

class TestAgentStatus:

    def test_status_returns_200(self, client, agent):
        set_agent(agent)
        resp = client.get("/api/v1/missions/status")
        assert resp.status_code == 200

    def test_status_has_system_key(self, client, agent):
        set_agent(agent)
        resp = client.get("/api/v1/missions/status")
        data = resp.json()
        assert data["system"] == "NETWORK-95"

    def test_status_has_all_sections(self, client, agent):
        set_agent(agent)
        resp = client.get("/api/v1/missions/status")
        data = resp.json()
        for key in ("mission_dashboard", "intake", "pipeline_learner", "devices"):
            assert key in data
