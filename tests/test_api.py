"""Pure-Python tests for TVA payload parsing and school search."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "ecoles_fermees_quebec"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


parent = types.ModuleType("ecoles_fermees_quebec")
parent.__path__ = [str(PACKAGE)]
sys.modules["ecoles_fermees_quebec"] = parent
_load("ecoles_fermees_quebec.const", PACKAGE / "const.py")
api = _load("ecoles_fermees_quebec.api", PACKAGE / "api.py")
parse_institutions = api.parse_institutions
parse_school_list = api.parse_school_list
parse_tva_datetime = api.parse_tva_datetime
search_schools = api.search_schools
status_for_school = api.status_for_school


SAMPLE_CLOSED = {
    "lastUpdated": "05-12-2023 08:39:18",
    "success": True,
    "result": {
        "institutions": [
            {
                "id": 1274,
                "name": "Bonnier",
                "town": "Mercier",
                "institution_type": {"name": "École secondaire"},
                "parent": {"name": "CSS des Grandes-Seigneuries"},
                "closures": [
                    {
                        "state": "closed",
                        "datetime_start": "2019-02-12T18:12:18-05:00",
                        "datetime_end": "2019-02-13T20:44:00-05:00",
                        "message": "Le mercredi 13 février",
                        "closure_informations": [
                            {"name": "Cours suspendus"},
                            {"name": "Pas de transport pour la journée"},
                        ],
                    }
                ],
            },
            {
                "id": 99,
                "name": "Sans dates",
                "town": "Québec",
                "closures": [],
            },
        ]
    },
}

SAMPLE_LIST = {
    "success": True,
    "result": {
        "institutions": [
            {"id": 428, "name": "à l’Orée-des-Bois", "town": "Québec"},
            {"id": 1274, "name": "Bonnier", "town": "Mercier"},
            {"id": 690, "name": "à l’Orée-des-Bois", "town": "Saint-Colomban"},
        ]
    },
}


def test_parse_and_search() -> None:
    last_updated, institutions = parse_institutions(SAMPLE_CLOSED)
    assert last_updated == datetime(
        2023, 12, 5, 8, 39, 18, tzinfo=ZoneInfo("America/Toronto")
    )
    assert 1274 in institutions

    during = parse_tva_datetime("2019-02-13T08:00:00-05:00")
    assert during is not None
    closed = status_for_school(1274, institutions, last_updated, during)
    assert closed.closed is True
    assert closed.message == "Le mercredi 13 février"
    assert closed.informations == [
        "Cours suspendus",
        "Pas de transport pour la journée",
    ]
    assert closed.css_name == "CSS des Grandes-Seigneuries"

    later = parse_tva_datetime("2026-10-20T19:00:00-04:00")
    assert later is not None
    opened = status_for_school(1274, institutions, last_updated, later)
    assert opened.closed is False

    listed_without_dates = status_for_school(99, institutions, last_updated, later)
    assert listed_without_dates.closed is True

    missing = status_for_school(1, institutions, last_updated, later)
    assert missing.closed is False

    schools = parse_school_list(SAMPLE_LIST)
    quebec = search_schools(schools, "quebec")
    assert [school.school_id for school in quebec] == [428]
    oree = search_schools(schools, "oree")
    assert {school.school_id for school in oree} == {428, 690}
    mercier = search_schools(schools, "Bonnier")
    assert [school.school_id for school in mercier] == [1274]


if __name__ == "__main__":
    test_parse_and_search()
    print("ok")
