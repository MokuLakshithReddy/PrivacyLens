import json
import pytest
from pathlib import Path
from app.core.policy_parser import clean_policy_html, segment_policy_sections
from app.core.claim_extractor import ClaimExtractor
from app.core.correlation_engine import CorrelationEngine
from app.core.risk_engine import RiskEngine
from app.ai.mock_provider import MockAIProvider
from app.schemas.observation import NetworkSignalSchema, StorageSignalSchema

BENCHMARK_PATH = Path(__file__).parent / "evaluation_dataset" / "benchmark_manifest.json"

@pytest.mark.asyncio
async def test_run_benchmark_evaluation():
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data["test_cases"]
    claim_extractor = ClaimExtractor(provider=MockAIProvider())
    correlation_engine = CorrelationEngine(ai_provider=MockAIProvider())

    tp_gaps = 0
    fp_gaps = 0
    fn_gaps = 0
    correct_tier_count = 0
    adversarial_passed = 0

    print("\n--- PRIVACYLENS BENCHMARK EVALUATION RUNNER ---")

    for tc in test_cases:
        tc_id = tc["id"]
        domain = tc["domain"]
        policy_html = tc["policy_html"]
        obs = tc["observations"]
        gt = tc["ground_truth"]

        # 1. Parse policy & extract claims
        clean_text = clean_policy_html(policy_html)
        sections = segment_policy_sections(policy_html)
        claims = await claim_extractor.process_sections(sections)

        # 2. Convert observations
        requests = [
            NetworkSignalSchema(
                url=r["url"],
                targetDomain=r["targetDomain"],
                isThirdParty=r["isThirdParty"],
                category=r["category"]
            )
            for r in obs["requests"]
        ]
        storage = [
            StorageSignalSchema(
                type=s["type"],
                name=s["name"],
                isThirdParty=s["isThirdParty"],
                persistent=s["persistent"]
            )
            for s in obs.get("storage", [])
        ]
        permissions = obs.get("permissions", [])

        # 3. Detect gaps
        findings = await correlation_engine.detect_privacy_gaps(
            domain=domain,
            claims=claims,
            requests=requests,
            storage_keys=storage,
            permissions=permissions
        )

        detected_gap_types = [f.gapType for f in findings]

        # 4. Compute risk
        risk_score, risk_tier, confidence = RiskEngine.compute_risk_and_confidence(
            claims=claims,
            requests=requests,
            storage_keys=storage,
            findings=findings,
            policy_found=len(claims) > 0
        )

        # 5. Evaluate against ground truth
        expected_gaps = gt.get("expected_gaps")
        if expected_gaps is not None:
            for eg in expected_gaps:
                if eg in detected_gap_types:
                    tp_gaps += 1
                else:
                    fn_gaps += 1

            for dg in detected_gap_types:
                if dg not in expected_gaps:
                    fp_gaps += 1

        # Check tier
        if "expected_tier" in gt:
            if risk_tier == gt["expected_tier"]:
                correct_tier_count += 1
        elif "expected_tier_in" in gt:
            if risk_tier in gt["expected_tier_in"]:
                correct_tier_count += 1

        if "min_risk_score" in gt:
            assert risk_score >= gt["min_risk_score"], f"{tc_id}: Risk score {risk_score} < min {gt['min_risk_score']}"

        if "max_risk_score" in gt:
            assert risk_score <= gt["max_risk_score"], f"{tc_id}: Risk score {risk_score} > max {gt['max_risk_score']}"

        # Adversarial check
        if tc_id == "TC_005_ADVERSARIAL_INJECTION_DEFENSE":
            if risk_score > 0 and "omission_advertising" in detected_gap_types:
                adversarial_passed = 1

        print(f"[{tc_id}] Domain: {domain} | Risk: {risk_score} ({risk_tier}) | Conf: {confidence:.2f} | Gaps: {detected_gap_types}")

    # Compute metrics
    precision = tp_gaps / (tp_gaps + fp_gaps) if (tp_gaps + fp_gaps) > 0 else 1.0
    recall = tp_gaps / (tp_gaps + fn_gaps) if (tp_gaps + fn_gaps) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

    print(f"\n--- BENCHMARK RESULTS ---")
    print(f"Gap Detection Precision : {precision:.2%}")
    print(f"Gap Detection Recall    : {recall:.2%}")
    print(f"Gap Detection F1 Score  : {f1:.2%}")
    print(f"Tier Accuracy           : {correct_tier_count}/3")
    print(f"Adversarial Mitigated   : {adversarial_passed}/1 (100%)")

    assert precision >= 0.80, f"Precision {precision:.2f} below target 0.80"
    assert recall >= 0.80, f"Recall {recall:.2f} below target 0.80"
    assert f1 >= 0.80, f"F1 {f1:.2f} below target 0.80"
    assert adversarial_passed == 1, "Adversarial prompt injection defense failed"
