"""This module contains a small modification of deap.algorithms.eaSimple.

   This file is under LGPL as the original file deap.algorithms.eaSimple.
   See deap.algorithms.py and <http://www.gnu.org/licenses/>.

.. moduleauthor: Ruslan Krenzler

1. September 2018.
"""

import random
import pickle
import deap.algorithms
import deap.tools as tools


def min_fitness(population):
    """Determine minimal fitness of populataion.

    The population is a list of individuals"""
    ret_val = float("inf")
    for ind in population:
        if ind.fitness.values[0] < ret_val:
            ret_val = ind.fitness.values[0]

    return ret_val


# This is modified version of deap.algorithm.eaSimple. The only modification is additional stopping
# criteria. Maximal number of generation without improvment. maxnoimprovment
def eaSimple(population, toolbox, cxpb, mutpb, ngen, maxnoimprovments=None, stats=None,
             halloffame=None, verbose=__debug__, checkpoint_prefix=None, checkpoint_frequency=100,
             results_csv=None):
    """This algorithm reproduce the simplest evolutionary algorithm as
    presented in chapter 7 of [Back2000]_.

    :param population: A list of individuals.
    :param toolbox: A :class:`~deap.base.Toolbox` that contains the evolution
                    operators.
    :param cxpb: The probability of mating two individuals.
    :param mutpb: The probability of mutating an individual.
    :param ngen: The number of generation.
    :param maxnoimprovments: Stopping criterial. The algorithm stops if there was no imrovement in the last
        maxnoimprovment generations.
    :param stats: A :class:`~deap.tools.Statistics` object that is updated
                  inplace, optional.
    :param halloffame: A :class:`~deap.tools.HallOfFame` object that will
                       contain the best individuals, optional.
    :param verbose: Whether or not to log the statistics.
    :returns: The final population
    :returns: A class:`~deap.tools.Logbook` with the statistics of the
              evolution

    The algorithm takes in a population and evolves it in place using the
    :meth:`varAnd` method. It returns the optimized population and a
    :class:`~deap.tools.Logbook` with the statistics of the evolution. The
    logbook will contain the generation number, the number of evalutions for
    each generation and the statistics if a :class:`~deap.tools.Statistics` is
    given as argument. The *cxpb* and *mutpb* arguments are passed to the
    :func:`varAnd` function. The pseudocode goes as follow ::

        evaluate(population)
        for g in range(ngen):
            population = select(population, len(population))
            offspring = varAnd(population, toolbox, cxpb, mutpb)
            evaluate(offspring)
            population = offspring

    As stated in the pseudocode above, the algorithm goes as follow. First, it
    evaluates the individuals with an invalid fitness. Second, it enters the
    generational loop where the selection procedure is applied to entirely
    replace the parental population. The 1:1 replacement ratio of this
    algorithm **requires** the selection procedure to be stochastic and to
    select multiple times the same individual, for example,
    :func:`~deap.tools.selTournament` and :func:`~deap.tools.selRoulette`.
    Third, it applies the :func:`varAnd` function to produce the next
    generation population. Fourth, it evaluates the new individuals and
    compute the statistics on this population. Finally, when *ngen*
    generations are done, the algorithm returns a tuple with the final
    population and a :class:`~deap.tools.Logbook` of the evolution.

    .. note::

        Using a non-stochastic selection method will result in no selection as
        the operator selects *n* individuals from a pool of *n*.

    This function expects the :meth:`toolbox.mate`, :meth:`toolbox.mutate`,
    :meth:`toolbox.select` and :meth:`toolbox.evaluate` aliases to be
    registered in the toolbox.

    .. [Back2000] Back, Fogel and Michalewicz, "Evolutionary Computation 1 :
       Basic Algorithms and Operators", 2000.
    """
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])
    # If results_csv is set save csv files.
    csv_writer = None
    if results_csv is not None:
        import csv
        csvfile = open(results_csv, 'w+')
        csv_writer = csv.DictWriter(csvfile, fieldnames=logbook.header)
        csv_writer.writeheader()

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    if halloffame is not None:
        halloffame.update(population)

    record = stats.compile(population) if stats else {}
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    if verbose:
        print(logbook.stream)

    if maxnoimprovments is None:
        maxnoimprovments = ngen + 1
    noimprovements = 0
    best_fitness_so_far = min_fitness(population)

    # Begin the generational process
    for gen in range(1, ngen + 1):
        # Select the next generation individuals
        offspring = toolbox.select(population, len(population))

        # Vary the pool of individuals
        offspring = deap.algorithms.varAnd(offspring, toolbox, cxpb, mutpb)

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # Update the hall of fame with the generated individuals
        if halloffame is not None:
            halloffame.update(offspring)

        # Replace the current population by the offspring
        population[:] = offspring

        # Append the current generation statistics to the logbook
        record = stats.compile(population) if stats else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        if verbose:
            print(logbook.stream)
        if csv_writer is not None:
            csv_writer.writerow(logbook[-1])
            csvfile.flush()
        # Check if this generation has some improvements.
        generation_fitnes = min_fitness(population)
        if generation_fitnes < best_fitness_so_far:
            best_fitness_so_far = generation_fitnes
            noimprovements = 0
        else:
            noimprovements += 1

        if checkpoint_prefix is not None:
            if gen % checkpoint_frequency == 0:
                # Fill the dictionary using the dict(key=value[, ...]) constructor
                cp = dict(population=population, generation=gen, halloffame=halloffame,
                          logbook=logbook, rndstate=random.getstate())

                filename = checkpoint_prefix + "-gen-{}.pkl".format(gen)
                with open(filename, "wb") as cp_file:
                    pickle.dump(cp, cp_file)

        if noimprovements >= maxnoimprovments:
            if verbose:
                print("Maximal number of not improved genrations {} reached.".format(maxnoimprovments))
            break

    return population, logbook
