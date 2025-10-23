#!/usr/bin/env python3

import argparse
import numpy as np
import pandas as pd
import json
import os
import sys
from scipy.linalg import svd
import warnings
warnings.filterwarnings('ignore')


def rnorm(n, mean=0, sd=1):
    """Generate random numbers compatible with R"""
    return np.random.normal(mean, sd, n)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Ranking CLI using spectral method')
    parser.add_argument('--csv', required=True, help='Input CSV file path')
    parser.add_argument('--bigbetter', type=int, required=True, choices=[0, 1],
                       help='Whether higher values are better (1) or lower values are better (0)')
    parser.add_argument('--B', type=int, required=True, help='Number of bootstrap samples')
    parser.add_argument('--seed', type=int, required=True, help='Random seed')
    parser.add_argument('--out', required=True, help='Output directory path')

    args = parser.parse_args()
    return args


def safe_dir_create(path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def process_data(data, bigbetter=False):
    """
    Process data to create comparison matrices (matching R implementation)

    Args:
        data: pandas DataFrame
        bigbetter: boolean, whether higher values are better

    Returns:
        dict with aa, ww matrices and column indices
    """
    Idx = np.array(data.columns.tolist())
    numidx = len(Idx)
    xx = np.zeros((0, numidx))
    ww = np.zeros((0, numidx))

    for ii in range(len(data)):
        target_row = data.iloc[ii].values

        # Generate all pairs like R's combn
        n_methods = len(target_row)
        pairs = []
        for i in range(n_methods):
            for j in range(i+1, n_methods):
                pairs.append([i, j])

        pairs = np.array(pairs)

        # Filter valid pairs (no NA values)
        valid_mask = []
        for pair in pairs:
            if not (np.isnan(target_row[pair[0]]) or np.isnan(target_row[pair[1]])):
                valid_mask.append(True)
            else:
                valid_mask.append(False)
        valid_mask = np.array(valid_mask)

        if not np.any(valid_mask):
            continue

        pairs = pairs[valid_mask]

        if bigbetter:
            # Higher values are better
            condition = target_row[pairs[:, 0]] > target_row[pairs[:, 1]]
            v1 = np.where(condition, Idx[pairs[:, 1]], Idx[pairs[:, 0]])
            v2 = np.where(condition, Idx[pairs[:, 0]], Idx[pairs[:, 1]])
        else:
            # Lower values are better (default)
            condition = target_row[pairs[:, 0]] > target_row[pairs[:, 1]]
            v1 = np.where(condition, Idx[pairs[:, 0]], Idx[pairs[:, 1]])
            v2 = np.where(condition, Idx[pairs[:, 1]], Idx[pairs[:, 0]])

        tmp_xx = np.zeros((len(v1), numidx))
        tmp_ww = np.zeros((len(v1), numidx))

        for jj in range(len(v1)):
            idx_v1 = np.where(Idx == v1[jj])[0][0]
            idx_v2 = np.where(Idx == v2[jj])[0][0]
            tmp_xx[jj, idx_v1] = 1
            tmp_xx[jj, idx_v2] = 1
            tmp_ww[jj, idx_v2] = 1

        xx = np.vstack([xx, tmp_xx]) if xx.size > 0 else tmp_xx
        ww = np.vstack([ww, tmp_ww]) if ww.size > 0 else tmp_ww

    return {
        'aa': xx,
        'ww': ww,
        'idx': Idx
    }


def vanilla_spectrum_method(AA2, WW2, Idx, B=2000):
    """
    Vanilla spectral ranking method

    Args:
        AA2: adjacency matrix
        WW2: weight matrix
        Idx: method names
        B: number of bootstrap samples

    Returns:
        numpy array with ranking results
    """
    n = AA2.shape[1]
    L2 = AA2.shape[0]
    fAvec2 = np.full(L2, 2.0)  # weight for vanilla spectral method

    # Compute matrix P with high precision
    AA2_f64 = AA2.astype(np.float64)
    WW2_f64 = WW2.astype(np.float64)
    fAvec2_f64 = fAvec2.astype(np.float64)

    dval2 = 2.0 * np.max(np.sum(AA2_f64, axis=0))
    P2 = np.zeros((n, n), dtype=np.float64)

    for i in range(n):
        for j in range(n):
            if j != i:
                P2[i, j] = np.sum(AA2_f64[:, i] * AA2_f64[:, j] * WW2_f64[:, j] / fAvec2_f64) / dval2
        P2[i, i] = 1.0 - np.sum(P2[i, :])

    # Compute pihat2 using SVD (matching R implementation)
    # In R: tmp.P2 <- t(t(P2) - diag(n)) %*% (t(P2) - diag(n))
    # This simplifies to: tmp.P2 <- (P2 - diag(n)) %*% (t(P2) - diag(n))
    # Which is: tmp.P2 <- (P2 - I) %*% (P2^T - I) = (P2 - I) %*% (P2 - I)^T
    tmp_P2 = (P2 - np.eye(n, dtype=np.float64)) @ (P2 - np.eye(n, dtype=np.float64)).T

    U, s, Vt = svd(tmp_P2.astype(np.float64))
    # In R, svd returns U, d, V where A = U %*% diag(d) %*% t(V)
    # So v[,n] is the nth column of V (right singular vector)
    # In Python, Vt is V.T, so Vt[:, -1] is the last column of Vt, which is the last row of V.T
    # But we want the nth column of V, which is Vt[-1, :]
    pihat2 = np.abs(Vt[-1, :])

    thetahat2 = np.log(pihat2) - np.mean(np.log(pihat2))

    # Output matrix
    RR2 = np.zeros((6, n))

    # Ranking (higher theta = better rank)
    ranks = np.argsort(-thetahat2) + 1  # rank from 1 to n, 1=best (highest theta)
    RR2[0, :] = thetahat2
    RR2[1, :] = ranks

    # Compute variance estimates
    Vmatrix2 = np.zeros((L2, n))
    tauhatvec2 = np.zeros(n)
    tmp_pimatrix2 = AA2.T * pihat2[:, np.newaxis]
    tmp_pivec2 = np.sum(tmp_pimatrix2, axis=1)
    tmp_var2 = np.zeros(n)

    for oo in range(n):
        tauhatvec2[oo] = np.sum(AA2[:, oo] * (1 - pihat2[oo] / tmp_pivec2[oo]) * pihat2[oo] / fAvec2, axis=0) / dval2
        tmp_var2[oo] = np.sum(AA2[:, oo] * (tmp_pivec2[oo] - pihat2[oo]) / fAvec2 / fAvec2) * pihat2[oo] / dval2 / dval2 / tauhatvec2[oo] / tauhatvec2[oo]
        Vmatrix2[:, oo] = (AA2[:, oo] * WW2[:, oo] * (tmp_pivec2[oo] / dval2) - AA2[:, oo] * pihat2[oo]) / fAvec2

    sigmahatmatrix2 = np.tile(tmp_var2, (n, 1)) + np.tile(tmp_var2, (n, 1)).T

    # Weighted bootstrap for confidence intervals
    Wmatrix2 = rnorm(L2 * B).reshape((L2, B))
    tmp_Vtau2 = (Vmatrix2.T / tauhatvec2[:, np.newaxis]) @ Wmatrix2

    R_left_m2 = np.zeros(n)
    R_right_m2 = np.zeros(n)
    R_left_one_m2 = np.zeros(n)

    for ooo in range(n):
        tmpGMmatrix02 = np.tile(tmp_Vtau2[ooo, :], (n, 1)).T - tmp_Vtau2.T
        tmpGMmatrix2 = np.abs(tmpGMmatrix02 / np.sqrt(sigmahatmatrix2[ooo, :])[np.newaxis, :] / dval2)
        tmpGMmatrixone2 = tmpGMmatrix02 / np.sqrt(sigmahatmatrix2[ooo, :])[np.newaxis, :] / dval2

        tmp_GMvecmax2 = np.max(tmpGMmatrix2, axis=1)
        tmp_GMvecmaxone2 = np.max(tmpGMmatrixone2, axis=1)

        cutval2 = np.quantile(tmp_GMvecmax2, 0.95)
        cutvalone2 = np.quantile(tmp_GMvecmaxone2, 0.95)

        tmp_theta_sd2 = np.sqrt(sigmahatmatrix2[ooo, :])
        tmp_theta_sd2 = np.delete(tmp_theta_sd2, ooo)

        theta_diff = thetahat2[np.arange(n) != ooo] - thetahat2[ooo]

        R_left_m2[ooo] = 1 + np.sum((theta_diff / tmp_theta_sd2) > cutval2)
        R_right_m2[ooo] = n - np.sum((theta_diff / tmp_theta_sd2) < (-cutval2))
        R_left_one_m2[ooo] = 1 + np.sum((theta_diff / tmp_theta_sd2) > cutvalone2)

    # Uniform left-sided CI
    Wmatrix2b = rnorm(L2 * B).reshape((L2, B))
    tmp_Vtau2b = (Vmatrix2.T / tauhatvec2[:, np.newaxis]) @ Wmatrix2b
    GMvecmaxone2 = np.array([])

    for ooo in range(n):
        tmpGMmatrix02 = np.tile(tmp_Vtau2b[ooo, :], (n, 1)).T - tmp_Vtau2b.T
        tmpGMmatrixone2 = tmpGMmatrix02 / np.sqrt(sigmahatmatrix2[ooo, :])[np.newaxis, :] / dval2
        tmp_GMvecmaxone2 = np.max(tmpGMmatrixone2, axis=1)
        GMvecmaxone2 = np.concatenate([GMvecmaxone2, tmp_GMvecmaxone2])

    GMmaxmatrixone2 = GMvecmaxone2.reshape((n, B)).T
    GMmaxone2 = np.max(GMmaxmatrixone2, axis=1)
    cutvalone2 = np.quantile(GMmaxone2, 0.95)
    R_left_one2 = np.zeros(n)

    for oooo in range(n):
        tmp_theta_sd2 = np.sqrt(sigmahatmatrix2[oooo, :])
        tmp_theta_sd2 = np.delete(tmp_theta_sd2, oooo)
        theta_diff = thetahat2[np.arange(n) != oooo] - thetahat2[oooo]
        R_left_one2[oooo] = 1 + np.sum((theta_diff / tmp_theta_sd2) > cutvalone2)

    RR2[2, :] = R_left_m2
    RR2[3, :] = R_right_m2
    RR2[4, :] = R_left_one_m2
    RR2[5, :] = R_left_one2

    return RR2


def main():
    """Main function"""
    import time
    start_time = time.time()

    args = parse_args()
    csv_path = args.csv
    out_dir = args.out
    bigbetter_flag = bool(args.bigbetter)
    B = args.B
    seed = args.seed

    safe_dir_create(out_dir)
    np.random.seed(seed)

    # Read CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        sys.exit(1)

    # Drop non-numeric columns and known metadata columns if present
    columns_to_drop = []
    if 'case_num' in df.columns:
        columns_to_drop.append('case_num')
    if 'model' in df.columns:
        columns_to_drop.append('model')
    if 'description' in df.columns:
        columns_to_drop.append('description')

    df = df.drop(columns=columns_to_drop, errors='ignore')

    # Keep only numeric columns
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    df = df[numeric_columns]

    if len(df.columns) < 2:
        print("At least two numeric method columns are required", file=sys.stderr)
        sys.exit(1)

    pdata = process_data(df, bigbetter=bigbetter_flag)
    RR2 = vanilla_spectrum_method(pdata['aa'], pdata['ww'], pdata['idx'], B=B)

    methods = pdata['idx']
    theta_hat = RR2[0, :]  # First row
    rank_vals = RR2[1, :]  # Second row
    ci_left_two = RR2[2, :]  # Third row
    ci_right_two = RR2[3, :]  # Fourth row
    ci_left = RR2[4, :]  # Fifth row
    ci_uniform_left = RR2[5, :]  # Sixth row

    results_df = pd.DataFrame({
        'method': methods,
        'theta_hat': theta_hat,
        'rank': rank_vals.astype(int),
        'ci_two_left': ci_left_two.astype(int),
        'ci_two_right': ci_right_two.astype(int),
        'ci_left': ci_left.astype(int),
        'ci_uniform_left': ci_uniform_left.astype(int)
    })

    runtime_sec = time.time() - start_time

    payload = {
        "job_id": os.path.basename(os.path.dirname(out_dir)),
        "params": {
            "bigbetter": bigbetter_flag,
            "B": B,
            "seed": seed
        },
        "methods": [
            {
                "name": results_df.iloc[i]['method'],
                "theta_hat": float(results_df.iloc[i]['theta_hat']),
                "rank": int(results_df.iloc[i]['rank']),
                "ci_two_sided": [int(results_df.iloc[i]['ci_two_left']), int(results_df.iloc[i]['ci_two_right'])],
                "ci_left": int(results_df.iloc[i]['ci_left']),
                "ci_uniform_left": int(results_df.iloc[i]['ci_uniform_left'])
            }
            for i in range(len(results_df))
        ],
        "metadata": {
            "n_samples": len(df),
            "k_methods": len(df.columns),
            "runtime_sec": runtime_sec
        }
    }

    # Write JSON output
    json_path = os.path.join(out_dir, "ranking_results.json")
    with open(json_path, 'w') as f:
        json.dump(payload, f, indent=2)

    # Write CSV output
    csv_out_path = os.path.join(out_dir, "ranking_results.csv")
    results_df.to_csv(csv_out_path, index=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
