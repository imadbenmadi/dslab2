from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from pcnme.core.config import Settings
from pcnme.core.topology import Topology
from pcnme.datasets.synthetic import SyntheticGenerator
from pcnme.optimizer.nsga2_mmde import run_nsga2_mmde
from pcnme.optimizer.pareto import KneePoint, select_knee_point
from pcnme.optimizer.problem import OffloadingUnit, TaskOffloadingProblem


@dataclass(frozen=True)
class PretrainBatchOutput:
    batch_index: int
    knee: KneePoint
    front: np.ndarray


def run_offline_pretrain(
    *,
    settings: Settings,
    topology: Topology,
    batches: int,
    batch_size: int,
    out_dir: Path,
    seed: Optional[int] = None,
) -> List[PretrainBatchOutput]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(settings.RANDOM_SEED if seed is None else int(seed))

    gen = SyntheticGenerator(settings=settings, topology=topology, rng=rng)
    outputs: List[PretrainBatchOutput] = []

    for batch_idx in range(int(batches)):
        units = gen.generate_pebble_units(batch_size=int(batch_size), batch_index=batch_idx)
        fog_loads = gen.sample_fog_loads()

        problem = TaskOffloadingProblem(settings=settings, topology=topology, units=units, fog_loads=fog_loads)
        res = run_nsga2_mmde(
            problem=problem,
            pop_size=settings.NSGA_POP_SIZE,
            n_gens=settings.NSGA_GENS,
            F=settings.MMDE_F,
            CR=settings.MMDE_CR,
            seed=int(rng.integers(0, 2**31 - 1)),
            verbose=False,
        )
        front = np.asarray(res.F, dtype=float)
        knee = select_knee_point(front)

        record = {
            "batch": batch_idx,
            "front": front.round(6).tolist(),
            "knee": {"index": int(knee.index), "point": knee.point.round(6).tolist()},
        }
        (out_dir / f"pareto_batch_{batch_idx:04d}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        outputs.append(PretrainBatchOutput(batch_index=batch_idx, knee=knee, front=front))

    return outputs
