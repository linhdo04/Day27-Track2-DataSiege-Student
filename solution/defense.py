"""
Your defense. Implement register(ctx) and a handler per event type.
See ../README.md for the full interface + toolkit reference, and
../RULES.md before you start.
"""
from api import Verdict

def _verdict(alert, pillar, reasons):
    """Build a consistent verdict and keep error handling fail-closed."""
    return Verdict(
        alert=bool(alert),
        confidence=0.95 if alert else 0.8,
        reason=", ".join(reasons) if reasons else "within calibrated limits",
        pillar=pillar,
    )


def register(ctx):
    ctx.on("data_batch", check_data_batch)
    ctx.on("contract_checkpoint", check_contract_checkpoint)
    ctx.on("lineage_run", check_lineage_run)
    ctx.on("feature_materialization", check_feature_materialization)
    ctx.on("embedding_batch", check_embedding_batch)


def check_data_batch(payload, ctx):
    profile = ctx.tools.batch_profile(payload["batch_id"])
    if "error" in profile:
        return _verdict(False, "checks", [profile["error"]])

    baseline = ctx.baseline
    reasons = []
    if not baseline["row_count_min"] <= profile["row_count"] <= baseline["row_count_max"]:
        reasons.append("row count outside baseline")
    if profile["null_rate"]["customer_id"] > baseline["null_rate_max"]:
        reasons.append("customer-id null rate above baseline")
    if not baseline["mean_amount_min"] <= profile["mean_amount"] <= baseline["mean_amount_max"]:
        reasons.append("amount distribution shifted")
    if profile["staleness_min"] > baseline["staleness_min_max"]:
        reasons.append("batch is stale")
    return _verdict(reasons, "checks", reasons)


def check_contract_checkpoint(payload, ctx):
    diff = ctx.tools.contract_diff(payload["contract_id"], payload["checkpoint_batch_id"])
    if "error" in diff:
        return _verdict(False, "contracts", [diff["error"]])

    reasons = list(diff["violations"])
    if diff["freshness_delay_min"] > ctx.baseline["freshness_delay_max_min"]:
        reasons.append("freshness SLA breached")
    return _verdict(reasons, "contracts", reasons)


def check_lineage_run(payload, ctx):
    graph = ctx.tools.lineage_graph_slice(payload["run_id"])
    if "error" in graph:
        return _verdict(False, "lineage", [graph["error"]])

    reasons = []
    # The event's `inputs` describes the emitted OpenLineage event, not the
    # complete dependency contract. Keep the known contract per job here.
    upstream_contracts = {
        "dbt:stg_orders": {"raw.orders", "raw.customers"},
    }
    expected_upstream = upstream_contracts.get(payload.get("job"))
    expected_downstream = len(payload.get("outputs", ()))
    if expected_upstream is not None and set(graph["actual_upstream"]) != expected_upstream:
        reasons.append("upstream lineage mismatch")
    if graph["actual_downstream_count"] != expected_downstream:
        reasons.append("downstream lineage mismatch")
    if graph["duration_ms"] > ctx.baseline["lineage_duration_ms_max"]:
        reasons.append("lineage runtime anomalous")
    return _verdict(reasons, "lineage", reasons)


def check_feature_materialization(payload, ctx):
    drift = ctx.tools.feature_drift(payload["feature_view"], payload["batch_id"])
    if "error" in drift:
        return _verdict(False, "ai_infra", [drift["error"]])
    reasons = []
    if drift["mean_shift_sigma"] > ctx.baseline["feature_mean_shift_sigma_max"]:
        reasons.append("training-serving feature skew")
    return _verdict(reasons, "ai_infra", reasons)


def check_embedding_batch(payload, ctx):
    drift = ctx.tools.embedding_drift(payload["corpus"], payload["chunk_batch_id"])
    if "error" in drift:
        return _verdict(False, "ai_infra", [drift["error"]])
    reasons = []
    if drift["centroid_shift"] > ctx.baseline["embedding_centroid_shift_max"]:
        reasons.append("embedding centroid drift")
    if drift["avg_doc_age_days"] > ctx.baseline["corpus_avg_doc_age_days_max"]:
        reasons.append("corpus is stale")
    return _verdict(reasons, "ai_infra", reasons)
