"""
Extract a random sample of synthetic trajectories from training_sims_6_classes.hdf
and format them for the unifying algorithm analysis (uaa.run_miop_affine_fit_on_trajectories).

One parquet per scenario is written to Data/Synthetic_Flies_for_Unifying/.

Formatting mirrors FigureGeneration/Main/fig_5_unifying_algo_analysis/analysis_scripts/preprocess_cfd_data.py:
  - time_relative_to_flash = 'time stamp' / 1000   (ms -> s; sims are 100 Hz)
  - obj_id_unique_event    = obj_id_unique
  - course, course_smoothish, ang_vel_smoothish from braid_analysis.flymath
    (same filter settings used for the fly and CFD-sim data)

The first frame of brownian / run-and-tumble / random-turns sims has zero velocity
(course undefined), so frames with exactly zero xy speed are dropped before computing course.

Usage (from anywhere):
    python extract_synthetic_trajectories.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

from braid_analysis import flymath

REPO_ROOT = Path(__file__).resolve().parents[4]  # <repo>/FigureGeneration/Supplemental/Supplemental_Figure_Shuffled_Synthetic_UAA/<this dir>/<this file>
SRC_HDF = REPO_ROOT / 'Data' / 'Simulated_Trajectory_Data' / 'training_sims_6_classes.hdf'
OUT_DIR = REPO_ROOT / 'Data' / 'Synthetic_Flies_for_Unifying'

N_TRAJECS = 200
SEED = 0

# dataset_name in the HDF  ->  output file stem
SCENARIOS = {
    '150ms_to_450ms_random_turns': 'random_turns',
    'levysmooth':                  'levy_flight',
    'run and tumble':              'run_and_tumble',
    'brownian':                    'brownian',
}

KEEP_COLS = ['time stamp', 'x', 'y', 'xvel', 'yvel', 'obj_id_unique', 'dataset_name',
             'time_relative_to_flash', 'obj_id_unique_event',
             'course', 'course_smoothish', 'ang_vel_smoothish']


def format_for_uaa(df):
    df = df.copy()
    df = df[np.hypot(df.xvel, df.yvel) > 0]  # drop undefined-course frames
    df = df.sort_values(['obj_id_unique', 'time stamp']).reset_index(drop=True)
    df['time_relative_to_flash'] = df['time stamp'] / 1000.
    df['obj_id_unique_event'] = df['obj_id_unique']
    df = flymath.assign_course_and_ang_vel_to_dataframe(df, dt=0.01, obj_id_key='obj_id_unique')
    return df[KEEP_COLS].reset_index(drop=True)


if __name__ == '__main__':
    rng = np.random.default_rng(SEED)
    df_all = pd.read_hdf(SRC_HDF)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for dataset_name, stem in SCENARIOS.items():
        df = df_all[df_all.dataset_name == dataset_name]
        obj_ids = df.obj_id_unique.unique()
        chosen = rng.choice(obj_ids, size=N_TRAJECS, replace=False)
        df = df[df.obj_id_unique.isin(chosen)]

        df = format_for_uaa(df)

        out = OUT_DIR / f'synthetic_{stem}_n{N_TRAJECS}.parquet'
        df.to_parquet(out)
        lengths = df.groupby('obj_id_unique_event').size()
        print(f'{dataset_name:30s} -> {out.name}: {df.obj_id_unique_event.nunique()} trajecs, '
              f'length min/max {lengths.min()}/{lengths.max()}')
