"""Solve warehouse problem with binary integer programming.

.. moduleauthor: Ruslan Krenzler

18. April 2018.

"""
import copy
import logging

import pulp
import prp.core.objects
import prp.stats as stats
import prp.core.costs as costs_mod
from prp.core.objects import INVALID_ID

# pulp.pulpTestAll() # Show all available algorithms.


class _IntervalSolver:
    def __init__(self, orgn_system):
        # Make a copy of the original system
        system = prp.stats.copy_warehouse(orgn_system)
        self.t_init = system.t  # Save initial time.
        self.N = len(system.departure_generator)  # Save last departure time + 1
        # Save occupations sorted by arrival times.
        self.occupations = self.get_occupations(system)
        self.B_init = self.calc_initial_B(self.occupations, orgn_system.places)
        # Calculate times when a place must be assigned. The pod is not allowed
        # to stay in the queue in the next time step.
        self.must_take_actions_T = self.calculate_action_times(self.occupations)
        self.P = system.places
        self.costs = costs_mod.DictCosts(system.costs)
        self.reduce_overlapping_constraints = True
        self.upper_cost_bound = None

    def solve_by_intervals(self, interval_length, end_t=None, threads=None):
        # If max_t was not specified then set it to a real max_t value.
        # keep max_t as small as possible because it will be used for
        # determining of big M values in the binary programming.
        if end_t is None:
            end_t = self.t_init + self.N

        Is = get_intervals(self.t_init, end_t, interval_length)   # noqa: N806
        actions = []
        logging.info("Solving problem in intervals...")
        for I in Is:
            (actions, problem) = self._solve_partially(
                previous_results=actions, t_begin=I[0], t_end=I[1], threads=threads)
            if problem.status != pulp.LpStatusOptimal:
                break

        logging.info("Done.")
        # print(problem)
        return (actions, problem)

    @staticmethod
    def get_occupations(system):
        """Get occupation times sorted by arrival times."""
        occupations = stats.get_occupations(system)
        # Sort occupations by arrival times
        occupations = sorted(occupations, key=lambda oc: oc.begin)
        return occupations

    @staticmethod
    def calculate_action_times(occupations):
        """Define a set of time points when we need to select new place.

        Note, the decision is made one time unit before the pod actually moves to the storage area.
        The pods which starts whose occupation time begins with "-inf" are part of the inital conditions.
        their position cannot be changed.

        :param occupations:
        :return: set of times.
        """
        action_t = set()
        minus_inf = float("-inf")
        for occupation in occupations:
            if occupation.begin > minus_inf:
                action_t.add(occupation.begin - 1)

        return action_t

    @staticmethod
    def calc_initial_B(occupations, places):   # noqa: N802
        B_init = dict(zip(places, len(places) * [0]))  # noqa: N806
        min_inf = float("-inf")
        for occupation in occupations:
            if occupation.begin == min_inf:
                B_init[occupation.place_id] = occupation.end
        return B_init

    @staticmethod
    def calc_B_end(occupations, end_t):   # noqa: N802
        """Calculate departure times for pods, whose placement was chosen at time t."""
        B = {}  # noqa: N806
        minus_inf = float("-inf")
        for occupation in occupations:
            t = occupation.begin - 1  # Decision time when occupation was determined.
            if t >= end_t:
                break
            if t > minus_inf:
                B[t] = min(occupation.end, end_t + 1)

        return B

    @staticmethod
    def calc_interval_B_init(B_init, B, actions):  # noqa: N802, N803
        iB = copy.deepcopy(B_init)  # noqa: N806
        for t in range(0, len(actions)):
            curr_action = actions[t]
            if curr_action != INVALID_ID:
                iB[curr_action] = max(iB[curr_action], B[t])
        return iB

    def place_costs(self, occupation, p, end_t):
        c = self.costs.from_station(occupation.from_station_id, p)
        if occupation.to_station_id != INVALID_ID and occupation.end <= end_t:
            c += self.costs.to_station(p, occupation.to_station_id)
        return c

    def get_decision_variables(self, T):  # noqa: N803
        """Create variables with (t,p) indices."""
        x_names = []
        for t in T:
            for p in self.P:
                name = "x_%d_%d" % (t, p)
                x_names.append(name)
        x = pulp.LpVariable.dict("Decision", x_names, cat=pulp.LpBinary)

        return x

    def get_costs(self, end_t):
        cs = {}
        for occupation in self.occupations:
            t = occupation.begin - 1  # T is the decision time.
            if t not in self.must_take_actions_T:
                continue

            # Recall, occupations are sorted by arrival times is sorted.
            if t >= end_t:
                break

            for p in self.P:
                name = "x_%d_%d" % (t, p)
                cs[name] = self.place_costs(occupation, p, end_t)

        return cs

    def convert_solution_to_actions(self, problem, t_begin, t_end):
        actions = (t_end - t_begin) * [0]  # mathematical action_{t_begin} corresponds to actions[0] in python

        for v in problem.variables():
            if v.varValue == 1:
                # Parse name Decision_x_t_p to (t,p)
                sub_str = v.name.split("_")
                (t, p) = (int(sub_str[2]), int(sub_str[3]))
                actions[t - t_begin] = p
        return actions

    def _solve_partially(self, previous_results, t_begin, t_end, threads=None):
        # Determine current set of time to take an action.
        curr_T = []  # noqa: N806
        for t in range(t_begin, t_end):
            if t in self.must_take_actions_T:
                curr_T.append(t)

        problem = pulp.LpProblem("Warehouse", pulp.LpMinimize)

        # Create a dictionary with variable names.
        # map names to (t,p) indices.
        x = self.get_decision_variables(curr_T)
        logging.info("Number of decision variables: %d." % len(x))

        # First add objective function
        cs = self.get_costs(t_end)
        problem += pulp.lpSum([cs[name] * x[name] for name in x.keys()])

        # Add one decision constraint.
        logging.info("Adding \"Select only one place.\" constraints")
        for t in curr_T:
            index_subset = []
            for p in self.P:
                name = "x_%d_%d" % (t, p)
                index_subset.append(name)
            problem += pulp.lpSum(x[name] for name in index_subset) == 1

        # Add "no overlapping" constraints.
        B = self.calc_B_end(self.occupations, t_end)  # noqa: N806
        interval_B_init = self.calc_interval_B_init(self.B_init, B, previous_results)  # noqa: N806
        BIG_M = t_end + 1    # noqa: N806
        logging.info("Calculating for the time interval [{}, {})".format(t_begin, t_end))
        logging.debug("BIG_M is %d" % BIG_M)
        logging.info("Adding \"Prevent storage time overlapping.\" constraints")
        constr_num = 0
        # If upper cost bound is defined use it.
        if self.upper_cost_bound is not None:
            lhs = pulp.lpSum([cs[name] * x[name] for name in x.keys()])
            rhs = self.upper_cost_bound
            problem += lhs <= rhs
            constr_num += 1

        # Count number of overapping constraints which may be skipped
        n_overlapping_skipped = 0
        for t in curr_T:
            for p in self.P:
                arrived_x_name = "x_%d_%d" % (t, p)
                lhs = min(interval_B_init[p], t_end + 1)
#                rhs = (t + 1) * x[arrived_x_name] + BIG_M * (1 - x[arrived_x_name])
                # Simplified version of the line above:
                rhs = (t + 1 - BIG_M) * x[arrived_x_name] + BIG_M

                problem += lhs <= rhs
                constr_num += 1
                if constr_num % 100000 == 0:
                    logging.info("%d Prevent-overlapping constraints added." % constr_num)
                for tau in range(min(curr_T), t):
                    if tau not in curr_T:
                        continue
                    previous_name = "x_%d_%d" % (tau, p)
                    if B[tau] <= t + 1 and self.reduce_overlapping_constraints:
                        n_overlapping_skipped += 1
                        continue
                    lhs = B[tau] * x[previous_name]
#                    rhs = (t+1) * x[arrived_x_name] + BIG_M * (1 - x[arrived_x_name])
                    # Simplified version of the line above:
                    rhs = (t + 1 - BIG_M) * x[arrived_x_name] + BIG_M
                    problem += lhs <= rhs
                    constr_num += 1
                    if constr_num % 100000 == 0:
                        logging.info("%d Prevent-overlapping constraints added." % constr_num)

        logging.info("Total constraints number: {}.".format(len(problem.constraints)))
        logging.info("{} overlapping constraints skipped.".format(n_overlapping_skipped))

        # print(problem)
        logging.info("Solving problem...")

        if threads is None:
            problem.solve()
        else:
            solver = pulp.solvers.COIN_CMD(msg=True, threads=threads)  # Experimental.
#            solver = pulp.solvers.GLPK_CMD() # Experimental.
            solver.solve(problem)  # Experimental

        logging.info("Complete.")
        logging.info("Status: {}".format(pulp.LpStatus[problem.status]))
        # Convert BP solution back to actions
        actions = previous_results + self.convert_solution_to_actions(problem, t_begin, t_end)

        return (actions, problem)

    def only_count_constraints(self,  max_t):
        t_begin = 0
        t_end = max_t

        logging.info("Count constraints only")
        # Detremine current set of instant to take an action.
        curr_T = []  # noqa: N806
        for t in range(t_begin, t_end):
            if t in self.must_take_actions_T:
                curr_T.append(t)

        # Create a dictionary with variable names.
        # map names to (t,p) indices.
        x = self.get_decision_variables(curr_T)
        logging.info("Number of decision variables: %d." % len(x))

        # Add one decision constraint.
        logging.info("Adding \"Select only one place.\" constraints")
        n_one_place_constraints = 0
        for t in curr_T:
            index_subset = []
            for p in self.P:
                name = "x_%d_%d" % (t, p)
                index_subset.append(name)
            n_one_place_constraints += 1

        # Add "no overlapping" constraints.
        B = self.calc_B_end(self.occupations, t_end)  # noqa: N806
        BIG_M = t_end + 1  # noqa: N806
        logging.info("Calculating for the time interval [{}, {})".format(t_begin, t_end))
        logging.debug("BIG_M is %d" % BIG_M)
        logging.info("Adding \"Prevent storage time overlapping.\" constraints")

        # Count number of overapping constraints which may be skipped
        n_overlapping_skipped = 0
        n_overlapping_constraints = 0
        n_skipped_printed = n_overlapping_skipped
        for t in curr_T:
            logging.info("t={}".format(t))
            # for p in self.P:
            nP = len(self.P)  # noqa: N806
            n_overlapping_constraints += nP
            if n_overlapping_constraints % 100000 == 0:
                logging.info("%d Prevent-overlapping constraints added." % n_overlapping_constraints)
            for tau in range(min(curr_T), t):
                if tau not in curr_T:
                    continue
                if B[tau] <= t + 1 and self.reduce_overlapping_constraints:
                    n_overlapping_skipped += nP
                    continue
                # lhs = B[tau] * x[previous_name]
                # Simplified version of the line above:
                # rhs = (t + 1 - BIG_M) * x[arrived_x_name] + BIG_M
                # problem += lhs <= rhs
                n_overlapping_constraints += nP
                if (n_overlapping_constraints // nP) % (1000000 // nP) == 0:
                    logging.info("%d Prevent-overlapping constraints added." % n_overlapping_constraints)
                if (n_overlapping_skipped // nP) % (1000000 // nP) == 0 and n_overlapping_skipped != n_skipped_printed:
                    logging.info("%d Prevent-overlapping constraints skipped." % n_overlapping_skipped)
                    # not all overlapping constrains are updated in this cycle therefore do not print it twice.
                    n_skipped_printed = n_overlapping_skipped

        total_constraints = n_one_place_constraints + n_overlapping_constraints
        logging.info("Total constraints number: {}.".format(total_constraints))
        logging.info("{} overlapping constraints skipped.".format(n_overlapping_skipped))

        return (n_one_place_constraints + n_overlapping_constraints)


def get_intervals(begin_t, end_t, interval_length):
    """Split large interval halp open interval [begin_t, end_t) into small ones.

    :return: List of tuples. Each tuple is the right and the left bound of a smaller interval.
       The length of the smaller interval is '''interval_length''' if it fits within (begin_t, end_t].
       If the last small interval is too large, it is cropped to end_t.
    """
    t = list(range(begin_t, end_t, interval_length))
    intervals = []
    for i in range(0, len(t) - 1):
        intervals.append((t[i], t[i + 1]))
    intervals.append((t[-1], end_t))
    return intervals


def solve_by_intervals(orgn_system, interval_length, end_t=None, threads=None, costs_upper_bound=None):
    """Solve a warehouse prolem intervatively with BIP for every iteratively for every interval_length decisions."""
    solver = _IntervalSolver(orgn_system)
    solver.upper_cost_bound = costs_upper_bound
    return solver.solve_by_intervals(interval_length, end_t, threads)


def solve(orgn_system, max_t=None, threads=None, costs_upper_bound=None):
    """Solve a warehouse prolem exactly with Binary Integer Programming (BIP)."""
    return solve_by_intervals(orgn_system, len(orgn_system.departure_generator), max_t, threads, costs_upper_bound)


def count_constrains(orgn_system, max_t=None):
    """Count number of BIP constraints for a warehouse problem."""
    solver = _IntervalSolver(orgn_system)
    return solver.only_count_constraints(max_t)
