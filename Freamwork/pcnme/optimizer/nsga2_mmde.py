from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.mutation import Mutation
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize


class MMDEMutation(Mutation):
    """MMDE mutation operator for integer decision vectors."""

    def __init__(self, *, F: float, CR: float):
        super().__init__()
        self.F = float(F)
        self.CR = float(CR)

    def _do(self, problem, X, **kwargs):
        n, n_var = X.shape
        X_mut = np.array(X, copy=True)
        for i in range(n):
            # choose 3 other indices
            candidates = [j for j in range(n) if j != i]
            if len(candidates) < 3:
                continue
            idxs = np.random.choice(candidates, 3, replace=False)
            r1, r2, r3 = X[idxs[0]], X[idxs[1]], X[idxs[2]]
            for k in range(n_var):
                if np.random.rand() < self.CR:
                    diff = int(round(self.F * (int(r2[k]) - int(r3[k]))))
                    X_mut[i, k] = int(r1[k]) + diff

        # clip and cast to int (pymoo stores xl/xu as arrays)
        xl = getattr(problem, "xl", 0)
        xu = getattr(problem, "xu", getattr(problem, "n_actions", 1) - 1)
        lo = int(np.min(xl)) if hasattr(xl, "__len__") else int(xl)
        hi = int(np.max(xu)) if hasattr(xu, "__len__") else int(xu)
        X_mut = np.clip(np.rint(X_mut), lo, hi).astype(int)
        return X_mut


@dataclass(frozen=True)
class NSGAResult:
    X: np.ndarray
    F: np.ndarray


def run_nsga2_mmde(
    *,
    problem,
    pop_size: int,
    n_gens: int,
    F: float,
    CR: float,
    seed: Optional[int] = None,
    verbose: bool = False,
) -> NSGAResult:
    algorithm = NSGA2(
        pop_size=int(pop_size),
        sampling=IntegerRandomSampling(),
        crossover=TwoPointCrossover(prob=0.9),
        mutation=MMDEMutation(F=float(F), CR=float(CR)),
        eliminate_duplicates=True,
    )
    res = minimize(problem, algorithm, termination=("n_gen", int(n_gens)), seed=seed, verbose=bool(verbose))
    return NSGAResult(X=np.asarray(res.X), F=np.asarray(res.F))
