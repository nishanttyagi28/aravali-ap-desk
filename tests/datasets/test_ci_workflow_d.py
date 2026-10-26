from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"

REQUIRED_JOBS = ("test", "frozen-files", "evals", "ocr", "ui")


def test_ci_workflow_required_jobs_and_no_job_level_hashfiles() -> None:
    doc = yaml.safe_load(CI_PATH.read_text(encoding="utf-8"))
    jobs = doc.get("jobs") or {}
    for job_id in REQUIRED_JOBS:
        assert job_id in jobs, f"missing job {job_id!r}"

    for job_id, job in jobs.items():
        job_if = job.get("if")
        if job_if is None:
            continue
        if "hashFiles(" in str(job_if):
            raise AssertionError(
                f"job {job_id!r} uses hashFiles in job-level if (not allowed by GitHub Actions)"
            )
