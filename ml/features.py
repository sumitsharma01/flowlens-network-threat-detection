"""One shared, strict feature contract for training and serving."""

import numpy as np
import pandas as pd

CATEGORICAL = ["proto", "service", "state"]
FEATURES = [
    "dur",
    "proto",
    "service",
    "state",
    "spkts",
    "dpkts",
    "sbytes",
    "dbytes",
    "rate",
    "sttl",
    "dttl",
    "sload",
    "dload",
    "sloss",
    "dloss",
    "sinpkt",
    "dinpkt",
    "sjit",
    "djit",
    "swin",
    "stcpb",
    "dtcpb",
    "dwin",
    "tcprtt",
    "synack",
    "ackdat",
    "smean",
    "dmean",
    "trans_depth",
    "response_body_len",
    "ct_srv_src",
    "ct_state_ttl",
    "ct_dst_ltm",
    "ct_src_dport_ltm",
    "ct_dst_sport_ltm",
    "ct_dst_src_ltm",
    "is_ftp_login",
    "ct_ftp_cmd",
    "ct_flw_http_mthd",
    "ct_src_ltm",
    "ct_srv_dst",
    "is_sm_ips_ports",
]
METADATA = {"id", "label", "attack_cat"}


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(FEATURES) - set(frame.columns))
    extra = sorted(set(frame.columns) - set(FEATURES) - METADATA)
    if missing or extra:
        raise ValueError(
            f"Invalid feature schema. Missing: {missing}; unexpected: {extra}"
        )
    if frame.empty:
        raise ValueError("At least one flow is required")
    result = frame.loc[:, FEATURES].copy()
    for col in FEATURES:
        if col in CATEGORICAL:
            if result[col].isna().any():
                raise ValueError(f"{col}: missing categorical value")
            result[col] = result[col].astype(str).str.strip()
            if result[col].eq("").any():
                raise ValueError(f"{col}: empty categorical value")
        else:
            try:
                result[col] = pd.to_numeric(result[col], errors="raise").astype(float)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{col}: expected numeric values") from exc
            if not np.isfinite(result[col]).all() or (result[col] < 0).any():
                raise ValueError(f"{col}: expected finite nonnegative values")
    return result


def fingerprints(frame: pd.DataFrame):
    return pd.util.hash_pandas_object(prepare(frame), index=False).astype(str)
