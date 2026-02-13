from __future__ import annotations

from pathlib import Path

import pytest

from eval.dataset import load_cases


def test_load_cases_parses_jsonl(tmp_path: Path) -> None:
    data = (
        '{"case_id":"c1","gene":"EGFR","hgvs":"c.1A>G","variant_type":"SNV",'
        '"disease_context":"nsclc","assay_context":"tumor-only",'
        '"expected":{"expected_abstain":true}}\n'
    )
    data_path = tmp_path / "cases.jsonl"
    data_path.write_text(data, encoding="utf-8")

    cases = load_cases(data_path)
    assert len(cases) == 1
    assert cases[0].case_id == "c1"
    assert cases[0].expected_abstain is True
    assert cases[0].request["gene"] == "EGFR"


def test_load_cases_rejects_missing_expected(tmp_path: Path) -> None:
    data_path = tmp_path / "cases.jsonl"
    data_path.write_text(
        '{"case_id":"c1","gene":"EGFR","hgvs":"c.1A>G","variant_type":"SNV",'
        '"disease_context":"nsclc","assay_context":"tumor-only"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected"):
        load_cases(data_path)
