"""Solve warehouse problem with binary integer programming.

.. moduleauthor: Ruslan Krenzler

18. April 2018.

"""
import logging

import gurobipy
import prp.solvers.bip as bip
from datetime import datetime


CSV_HEADERS = ["StartTime", "IntervalBegin", "IntervalEnd",
               "AddConstraintsBegin", "PrepareTime",
               "AddConstraintsStop", "AddConstraintsTime",
               "StopTime", "IntervalTime", "IntervalCosts",
               "Status", "NumVars", "NumConstraints"
               ]


class _IntervalSolver(bip._IntervalSolver):
    def __init__(self, orgn_system):
        super(_IntervalSolver, self).__init__(orgn_system)
        self.callback = None  # Call this function when intermediate results are available.

    def get_decision_variables(self, model: gurobipy.Model, costs: gurobipy.tupledict):
        """Create variables with (t,p) indices."""
        x = model.addVars(costs.keys(), name="x", vtype=gurobipy.GRB.BINARY, obj=costs)
        return x

    def get_costs(self, end_t):
        cs = gurobipy.tupledict()
        for occupation in self.occupations:
            t = occupation.begin - 1  # T is the decision time.
            if t not in self.must_take_actions_T:
                continue

            # Recall, occupations are sorted by arrival times.
            if t >= end_t:
                break

            for p in self.P:
                cs[(t, p)] = self.place_costs(occupation, p, end_t)

        return cs

    def convert_solution_to_actions(self, vars, t_begin, t_end):
        actions = (t_end - t_begin) * [0]  # Mathematical action_{t_begin} corresponds to actions[0] in python.

        for ((t, p), v) in vars.items():
            if v == 1:
                actions[t - t_begin] = p
        return actions

    def _solve_partially(self, previous_results, t_begin, t_end, threads=None):
        entry = {}
        entry["StartTime"] = datetime.now()
        entry["IntervalBegin"] = t_begin
        entry["IntervalEnd"] = t_end
        # Determine current set of time to take an action.
        curr_T = []  # noqa: N806
        for t in range(t_begin, t_end):
            if t in self.must_take_actions_T:
                curr_T.append(t)

        # Create model.
        m = gurobipy.Model("storage")
        costs = self.get_costs(t_end)

        x = self.get_decision_variables(m, costs=costs)

        logging.info("Number of decision variables: %d." % len(x))
        entry["AddConstraintsBegin"] = datetime.now()
        entry["PrepareTime"] = entry["AddConstraintsBegin"] - entry["StartTime"]
        # Add one decision constraint.
        logging.info("Adding \"Select only one place.\" constraints")
        m.addConstrs((x.sum(t, '*') == 1 for t in curr_T), "OnePlace")
        constr_num = len(curr_T)

        # Add "no overlapping" constraints.
        B = self.calc_B_end(self.occupations, t_end)  # noqa: N806
        interval_B_init = self.calc_interval_B_init(self.B_init, B, previous_results)  # noqa: N806
        BIG_M = t_end + 1  # noqa: N806 Or better to use just "end_t" ?
        logging.info("Calculating for the time interval [{}, {})".format(t_begin, t_end))
        logging.debug("BIG_M is %d" % BIG_M)
        logging.info("Adding \"Prevent storage time overlapping.\" constraints")
        # If upper cost bound is defined use it.
        #        if self.upper_cost_bound is not None:
        #            lhs = pulp.lpSum([cs[name] * x[name] for name in x.keys()])
        #            rhs = self.upper_cost_bound
        #            problem += lhs <= rhs
        #            constr_num += 1

        # Count number of overlapping constraints which may be skipped.
        n_overlapping_skipped = 0
        # Add initial constraints.
        for t in curr_T:
            for p in self.P:
                lhs = min(interval_B_init[p], t_end + 1)
                #                rhs = (t + 1) * x[arrived_x_name] + BIG_M * (1 - x[arrived_x_name])
                # Simplified version of the line above:
                rhs = (t + 1 - BIG_M) * x[(t, p)] + BIG_M
                m.addConstr(lhs, gurobipy.GRB.LESS_EQUAL, rhs, "InitialCondition")
                #                problem += lhs <= rhs
                constr_num += 1

        nP = len(self.P)  # noqa: N806
        for t in curr_T:
            if constr_num % 100000 == 0:
                logging.info("%d Prevent-overlapping constraints added." % constr_num)
            for tau in range(min(curr_T), t):
                if tau not in curr_T:
                    continue
                if B[tau] <= t + 1 and self.reduce_overlapping_constraints:
                    n_overlapping_skipped += 1
                    continue

                constr = (B[tau] * x[(tau, p)] <= (t + 1 - BIG_M) * x[(t, p)] + BIG_M for p in self.P)
                m.addConstrs(constr, "No Overlapping")
                constr_num += nP
                if (constr_num // nP) % (100000 // nP) == 0:
                    logging.info("%d Prevent-overlapping constraints added." % constr_num)

        logging.info("Total constraints number: {}.".format(constr_num))
        logging.info("{} overlapping constraints skipped.".format(n_overlapping_skipped))
        entry["AddConstraintsStop"] = datetime.now()
        entry["AddConstraintsTime"] = entry["AddConstraintsStop"] - entry["AddConstraintsBegin"]
        logging.info("Solving problem...")
        m.optimize()
        solution = m.getAttr("x", x)
        logging.info("Complete. Status: {}".format(m.status))
        # Convert the BIP solution back to actions.
        actions = previous_results + self.convert_solution_to_actions(solution, t_begin, t_end)
        entry["StopTime"] = datetime.now()
        entry["IntervalTime"] = entry["StopTime"] - entry["StartTime"]
        entry["Status"] = m.status
        entry["NumVars"] = m.numVars
        entry["NumConstraints"] = m.numConstrs
        entry["IntervalCosts"] = m.objVal

        # Call statistics if defined.
        if self.callback is not None:
            self.callback(entry)

        return actions, m

    def solve_by_intervals(self, interval_length, end_t=None, threads=None):
        # If max_t was not specified then set it to a real max_t value.
        # keep max_t as small as possible because it will be used for
        # determining of big M values in the binary programming.
        if end_t is None:
            end_t = self.t_init + self.N

        Is = bip.get_intervals(self.t_init, end_t, interval_length)  # noqa: N806
        actions = []
        logging.info("Solving problem in intervals...")
        for I in Is:
            (actions, model) = self._solve_partially(previous_results=actions, t_begin=I[0], t_end=I[1],
                                                     threads=threads)
            if model.status != gurobipy.GRB.OPTIMAL:
                break

        logging.info("Done.")
        return (actions, model)


def solve_by_intervals(orgn_system, interval_length, end_t=None, threads=None, costs_upper_bound=None):
    """Solve a warehouse prolem intervatively with BIP for every iteratively for every interval_length decisions."""
    solver = _IntervalSolver(orgn_system)
    solver.upper_cost_bound = costs_upper_bound
    return solver.solve_by_intervals(interval_length, end_t, threads)


def solve(orgn_system, max_t=None, threads=None, costs_upper_bound=None):
    """Solve a warehouse problem exactly with Binary Integer Programming (BIP)."""
    return solve_by_intervals(orgn_system, len(orgn_system.departure_generator), max_t, threads, costs_upper_bound)


def count_constrains(orgn_system, max_t=None):
    """Count number of BIP constraints for a warehouse problem."""
    solver = _IntervalSolver(orgn_system)
    return solver.only_count_constraints(max_t)
