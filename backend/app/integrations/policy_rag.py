import asyncio

from app.schemas.ai_results import EvidenceItem, PolicyAnalysisResult

from ai_engineering.rag.tools import check_policy_compliance


class PolicyRAGInterface:
    """
    Adapter between the FastAPI backend and the team's policy RAG system.

    The backend does not implement RAG itself.
    It sends the application data to the RAG policy checker and converts
    the RAG result into the backend's standard PolicyAnalysisResult.
    """

    async def analyze_application(self, application_data: dict) -> PolicyAnalysisResult:
        rag_result = await asyncio.to_thread(check_policy_compliance, application_data)

        policy_findings = []
        risk_flags = []
        evidence = []

        # Overall review reasons returned by the RAG checker
        review_reasons = rag_result.get("review_reasons", [])

        for reason in review_reasons:
            policy_findings.append(reason)

        # Convert individual policy results
        for result in rag_result.get("results", []):
            status = result.get("status")
            requirement = result.get("requirement", "")
            explanation = result.get("explanation", "")

            if status == "not_satisfied":
                risk_flags.append(
                    f"{requirement}: {explanation}"
                )

            elif status in {"unclear", "missing"}:
                risk_flags.append(
                    f"{requirement}: {explanation}"
                )

            # Preserve the policy evidence/citation
            quote = result.get("quote")
            citation = result.get("citation")
            source = result.get("source", "policy_rag")
            clause = result.get("clause")

            if quote or citation:
                evidence.append(
                    EvidenceItem(
                        source=source,
                        section=clause,
                        text=quote or citation or ""
                    )
                )

        counts = rag_result.get("counts", {})

        # The RAG result requires review whenever at least one
        # policy rule is not satisfied, unclear, or missing.
        compliant = not rag_result.get("requires_review", False)

        if not policy_findings and compliant:
            policy_findings.append(
                "Policy RAG found no policy rules requiring review."
            )

        policy_findings.append(
            "Policy check counts: "
            f"satisfied={counts.get('satisfied', 0)}, "
            f"not_satisfied={counts.get('not_satisfied', 0)}, "
            f"unclear={counts.get('unclear', 0)}, "
            f"missing={counts.get('missing', 0)}."
        )

        return PolicyAnalysisResult(
            compliant=compliant,
            policy_findings=policy_findings,
            risk_flags=risk_flags,
            evidence=evidence,
        )


policy_rag = PolicyRAGInterface()