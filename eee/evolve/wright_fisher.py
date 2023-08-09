"""
Functions to run a Wright-Fisher simulation given an ensemble.
"""

from eee.evolve import GenotypeContainer

import numpy as np
from tqdm.auto import tqdm


def wright_fisher(gc,
                  population,
                  mutation_rate,
                  num_generations):
    """
    Run a Wright-Fisher simulation. This is a relatively low-level function. 
    Most users should probably call this via other simulation functions. 
    
    Parameters
    ----------
    gc : GenotypeContainer
        container holding genotypes with either a wildtype sequence or a 
        sequences from a previous evolutionary simulation. This will bring in 
        everything we need to calculate fitness of each genotype. 
    population : dict, list-like, or int
        population for the simulation. Can be a dictionary of populations where
        keys are genotypes and values are populations. Can be an array where the
        length is the total population size and the values are the genotypes. 
        {5:2,4:1,0:2} is equivalent to [5,5,4,0,0]. If an integer, interpret as
        the population size. Create an initial population consisting of all 
        wildtype.
    mutation_rate : float
        Lambda for poisson distribution to select the number of genotypes to 
        mutate at each generation. Should be >= 0. 
    num_generations : int
        number of generations to run the simulation. Should be >= 1. 
    
    Returns
    -------
    gc : GenotypeContainer
        updated GenotypeContainer holding all new genotypes that appeared over 
        the simulation
    generations : list
        list of dicts where each entry in the list is a generation. each dict
        holds the population at that generation with keys as genotypes and 
        values as populations. 
    """

    if not issubclass(type(gc),GenotypeContainer):
        err = "\ngc should be a GenotypeContainer instance.\n\n"
        raise ValueError(err)

    parse_err = \
    """
    population should be a population dictionary, array of genotype indexes,
    or a positive integer indicating the population size.
    """

    if hasattr(population,"__iter__"):

        # If someone passes in something like {5:10,8:40,9:1}, where keys are 
        # genotype indexes and values are population size, expand to a list of 
        # genotypes
        if issubclass(type(population),dict):
            _population = []
            for p in population:
                _population.extend([p for _ in range(population[p])])
            population = _population

        # Make sure population is a numpy array, whether passed in by user as 
        # a list or from the list built from _population above. 
        population = np.array(population,dtype=int)
        population_size = len(population)

    else:

        # Get the population size
        try:
            population_size = int(population)
        except (ValueError,TypeError):
            raise(parse_err)
        
        # Build a population of all wildtype
        population = np.zeros(population_size,dtype=int)
            
    # Check for sane population size
    if population_size < 1:
        raise ValueError(parse_err)
    
    # Check for sane mutation rate
    if mutation_rate < 0:
        err = "\nmutation_rate should be a float > 0\n\n"
        raise ValueError(err)
    
    if num_generations < 1:
        err = "\nnum_generations should be an integer >= 1\n\n"
        raise ValueError(err)

    # Get the mutation rate
    expected_num_mutations = mutation_rate*population_size

    # Dictionary of genotype populations
    seen, counts = np.unique(population,return_counts=True)
    generations = [(seen,counts)]

    # Current population as a vector with individual genotypes.
    for _ in tqdm(range(1,num_generations)):

        # Get the probability of each genotype: it's frequency times its 
        # relative fitness. Get the current genotypes and their counts from the
        # last generation recorded
        current_genotypes, counts = generations[-1]
        prob = np.array([gc.fitnesses[g] for g in current_genotypes])
        prob = prob*counts
        
        # If total prob is zero, give all equal weights. (edge case -- all 
        # genotypes equally terrible)
        if np.sum(prob) == 0:
           prob = np.ones(population_size)

        # Calculate relative probability
        prob = prob/np.sum(prob)

        # Select offspring, with replacement weighted by prob
        population = np.random.choice(current_genotypes,
                                      size=population_size,
                                      p=prob,
                                      replace=True)

        # Introduce mutations
        num_to_mutate = np.random.poisson(expected_num_mutations)

        # If we have a ridiculously high mutation rate, do not mutate each
        # genotype more than once.
        if num_to_mutate > population_size:
            num_to_mutate = population_size

        # Mutate first num_to_mutate population members
        for j in range(num_to_mutate):

            # Generate a new mutant with a new index, then store that new index
            # in the population. 
            new_index = gc.mutate(index=population[j])        
            population[j] = new_index

        # Record populations
        seen, counts = np.unique(population,return_counts=True)
        generations.append((seen,counts))

    generations = [dict(zip(*g)) for g in generations]

    return gc, generations
