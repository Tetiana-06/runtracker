from app.services.report_builder import build_report_summary


def build_json_report(runs: list[dict]) -> dict:
    return build_report_summary(runs)