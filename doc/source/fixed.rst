Fixed places
============
Assign always the same place to the same pod in :ref:`small system <small-test-system>`.

For this tutorial we need following modules

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: import prp.core.warehouse
    :end-at: import prp.solvers.optimal_fixed as optimal_fixed

If you want to switch on logging, add

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: import logging
    :lines: 1

and call later

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: logging.basicConfig(level=logging.INFO)
    :lines: 1

Parameters
----------

We define paths to JSON files of a small warehouse system:

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: LAYOUT_FILE =
    :end-at: DEPARTURES_FILE =

and store the solution and the optimal initial state to files:

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: SOLUTION_FILE =
    :end-at: OPTIMAL_INITIAL_STATE_FILE =

Solve with fixed positions.
---------------------------

Load a warehouse model from JSON files.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: def load_problem():
    :end-at: warehouse = load_problem()


Send the pod to the same place as in the initial state. In the :ref:`small system <small-test-system>`, that means, assign pod *n* to place *n*.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: solver = FixedPlaceSolver(warehouse)
    :end-at: warehouse.next(place_id)
    :lines: 1,3-

Print results and save them to a JSON file.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: print("Total costs: {} at time {}."
    :end-at: recorder.store_solution_to_json
    :lines: 1,3,4

Calculate optimal fixed positions
---------------------------------
Find an optimal initial state and a mapping "pod->place", such that the fixed-place solution is optimal.

Find optimal mapping "pod->place" and print it out.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: optimal_fixed.optimal_assignment(warehouse)
    :lines: 2


Reload the problem.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: # Reload problem.
    :lines: 2

Calculate optimal mapping "pod->place" and print it.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: optimal_positions = optimal_fixed.optimal_assignment(warehouse)
    :lines: 1-2

Reorder places by their optimal fixed positions before staring the system. And store this
optimal initial state to a JSON file. It can differ from the original initial state.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: utils.create_missing_directories_of_file(OPTIMAL_INITIAL_STATE_FILE)
    :end-at: recorder.store_initial_state_to_json

Solve the system with fixed places staring with the optimal initial state.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: solver = FixedPlaceSolver(warehouse)
    :end-at: warehouse.next(place_id)
    :lines: 1,3-

Print out the best solution and save it to a JSON file.

.. literalinclude:: ../../examples/use-fixed.py
    :start-at: print("Total costs for optimal fixed solution 
    :end-at: recorder.store_solution_to_json
