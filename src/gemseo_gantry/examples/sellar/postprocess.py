# pyright: reportOptionalMemberAccess=false, reportArgumentType=false
from pathlib import Path

from gemseo.algos.optimization_problem import OptimizationProblem

problem = OptimizationProblem.from_hdf(Path(__file__).parent / "Sellar.h5")
dataset = problem.to_dataset()

meta = dataset.misc["optimization_metadata"]
solution = problem.solution

print("Objective:          ", meta.objective_name)
print("Optimum iteration:  ", meta.optimum_iteration)
print("Feasible iterations:", meta.feasible_iterations)
print("Constraints:        ", meta.output_names_to_constraint_names)
print("Solution:           ", solution)
print()
print(f"OPTIMUM_OBJECTIVE: {float(solution.f_opt):.6f}")
