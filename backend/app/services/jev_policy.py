"""Inspectable policy snapshot. Provisional thresholds are not promotion evidence."""
from ..config import Config


def decision_configuration():
    from .interview_selection import POLICY_VERSION as interview, MIN_SCORE
    from .evidence_reranker import POLICY_VERSION as rerank
    from .evidence_verifier import POLICY_VERSION as evidence, MIN_CONFIDENCE
    modes = {'interview': (Config.JEV_INTERVIEW_MODE, interview),
             'rerank': (Config.JEV_RERANK_MODE, rerank), 'evidence': (Config.JEV_EVIDENCE_MODE, evidence)}
    return {'model': Config.TYPESAFE_MODEL, 'configured': bool(Config.TYPESAFE_API_KEY),
            'timeout_seconds': Config.TYPESAFE_TIMEOUT_SECONDS, 'calibration': 'provisional',
            'thresholds': {'interview_min_score': MIN_SCORE, 'evidence_min_confidence': MIN_CONFIDENCE},
            'features': {key: {'mode': mode, 'policy_version': version,
                               'available': bool(Config.TYPESAFE_API_KEY) and mode in {'shadow', 'on'},
                               'reason': 'disabled' if mode == 'off' else ('invalid_mode' if mode not in {'on', 'shadow'} else ('' if Config.TYPESAFE_API_KEY else 'missing_credentials'))}
                         for key, (mode, version) in modes.items()}}
