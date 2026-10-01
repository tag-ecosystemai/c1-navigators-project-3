from ..utils.error_handler import log_error

DEFAULT_POLICIES = {"dti_threshold": 50.0, "gambling_ratio_threshold": 10.0, "income_variance_threshold": 25.0, "risk_level_rules": {}}


def load_policies(policies):
    if not isinstance(policies, dict): return DEFAULT_POLICIES.copy(), [log_error("policy_failure", "policies missing; defaults used", "policy_loader")]
    merged = DEFAULT_POLICIES.copy(); merged.update({key: value for key, value in policies.items() if value is not None})
    return merged, []
