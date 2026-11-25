"""Core ML preprocessing and scoring utilities for transaction fraud detection (TV3)."""

from .preprocessing import (
    ALGORITHMS,
    FEATURE_SET_A,
    FEATURE_SET_AB,
    FEATURE_SET_B_EXTRA,
    FEATURE_SETS,
    FORBIDDEN_COLUMNS,
    build_model_pipeline,
    build_preprocessor,
    get_feature_columns,
    score_model,
    select_feature_frame,
    validate_feature_columns,
)

__all__ = [
    "ALGORITHMS",
    "FEATURE_SET_A",
    "FEATURE_SET_AB",
    "FEATURE_SET_B_EXTRA",
    "FEATURE_SETS",
    "FORBIDDEN_COLUMNS",
    "build_model_pipeline",
    "build_preprocessor",
    "get_feature_columns",
    "score_model",
    "select_feature_frame",
    "validate_feature_columns",
]
