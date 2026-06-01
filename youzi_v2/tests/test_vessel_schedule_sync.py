"""船期全库同步测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from youzi_v2.db.connection import Database
from youzi_v2.db.vessel_schedules_repository import VesselSchedulesRepository
from youzi_v2.services.vessel_schedule_sync import sync_all_vessel_schedules


@pytest.fixture
def repo(tmp_path: Path) -> VesselSchedulesRepository:
    return VesselSchedulesRepository(Database(tmp_path / "test.db"))


def _mock_fetch(_company: str, code: str, *, period: int = 28) -> dict:
    return {
        "vesselVoyage": f"VESSEL {code}",
        "vesselName": "TEST VESSEL",
        "voyageNo": code,
        "vesselCode": code,
        "shippingCompany": "COSCO",
        "notes": "",
        "portCalls": [
            {
                "portName": "Shanghai",
                "sequence": 1,
                "eta": "2026-06-01 08:00:00",
            }
        ],
        "source": {"provider": "cosco_elines", "vesselCode": code, "period": period},
    }


def test_list_carrier_sync_targets_dedupes(repo: VesselSchedulesRepository) -> None:
    repo.create(
        {
            "vesselVoyage": "A V001",
            "shippingCompany": "COSCO",
            "vesselCode": "ABC",
            "portCalls": [{"portName": "Shanghai", "sequence": 1}],
        }
    )
    repo.create(
        {
            "vesselVoyage": "A V002",
            "shippingCompany": "COSCO",
            "vesselCode": "ABC",
            "portCalls": [{"portName": "Ningbo", "sequence": 1}],
        }
    )
    repo.create(
        {
            "vesselVoyage": "B V001",
            "shippingCompany": "COSCO",
            "vesselCode": "XYZ",
            "portCalls": [{"portName": "Qingdao", "sequence": 1}],
        }
    )
    repo.create(
        {
            "vesselVoyage": "NO CODE",
            "shippingCompany": "COSCO",
            "portCalls": [{"portName": "X", "sequence": 1}],
        }
    )

    targets = repo.list_carrier_sync_targets()
    assert len(targets) == 2
    codes = {t["vesselCode"] for t in targets}
    assert codes == {"ABC", "XYZ"}
    assert repo.count_voyages_missing_carrier() == 1


@patch("youzi_v2.services.vessel_schedule_sync.fetch_vessel_schedule", side_effect=_mock_fetch)
def test_sync_all_vessel_schedules(mock_fetch, repo: VesselSchedulesRepository) -> None:
    repo.create(
        {
            "vesselVoyage": "A V001",
            "shippingCompany": "COSCO",
            "vesselCode": "ABC",
            "portCalls": [{"portName": "Old", "sequence": 1}],
        }
    )
    repo.create(
        {
            "vesselVoyage": "B V001",
            "shippingCompany": "MAERSK",
            "vesselCode": "M1",
            "portCalls": [{"portName": "Old", "sequence": 1}],
        }
    )

    result = sync_all_vessel_schedules(repo, period=28)

    assert result["total"] == 2
    assert result["synced"] == 1
    assert result["updated"] == 1
    assert result["failed"] == 0
    assert result["skipped_unsupported"] == 1
    assert mock_fetch.call_count == 1

    detail = repo.get_detail(repo.list_carrier_sync_targets()[0]["id"])
    assert detail is not None
    assert detail["portCalls"][0]["portName"] == "Shanghai"
