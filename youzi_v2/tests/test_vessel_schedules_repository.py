"""航次船期仓储测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from youzi_v2.db.connection import Database
from youzi_v2.db.vessel_schedules_repository import VesselSchedulesRepository


@pytest.fixture
def repo(tmp_path: Path) -> VesselSchedulesRepository:
    return VesselSchedulesRepository(Database(tmp_path / "test.db"))


def test_port_call_time_fields_updated_on_change(repo: VesselSchedulesRepository) -> None:
    detail = repo.create(
        {
            "vesselVoyage": "TEST V001",
            "portCalls": [
                {
                    "portName": "Shanghai",
                    "sequence": 1,
                    "eta": "2026-06-01 08:00:00",
                    "etd": "2026-06-02 08:00:00",
                }
            ],
        }
    )
    pc = detail["portCalls"][0]
    assert pc["timeFieldsUpdated"] == []

    updated = repo.update(
        detail["id"],
        {
            "portCalls": [
                {
                    "id": pc["id"],
                    "portName": "Shanghai",
                    "sequence": 1,
                    "eta": "2026-06-01 10:00:00",
                    "etd": "2026-06-02 08:00:00",
                }
            ]
        },
    )
    changed = updated["portCalls"][0]
    assert changed["timeFieldsUpdated"] == ["eta"]

    unchanged = repo.update(
        detail["id"],
        {
            "portCalls": [
                {
                    "id": pc["id"],
                    "portName": "Shanghai",
                    "sequence": 1,
                    "eta": "2026-06-01 10:00:00",
                    "etd": "2026-06-02 08:00:00",
                }
            ]
        },
    )
    assert unchanged["portCalls"][0]["timeFieldsUpdated"] == ["eta"]
