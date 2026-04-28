What are pop_size and n_gen?
Because NSGA-II is a Genetic Algorithm, it solves problems through "evolution." When we feed row #1 into NSGA-II:

pop_size=20 (Population Size): NSGA-II randomly guesses 20 different routing plans for that specific row.
n_gen=10 (Number of Generations): NSGA-II takes those 20 guesses, figures out which ones are the best, mutates them, and tries again. It repeats this evolutionary cycle 10 times to find the absolute best mathematical answer.
It takes the winning answer, saves it as the "action" for row #1, and then moves on to row #2 to do it all over again.

Why did we change it?
In the original default constants (NSGA_POP = 100, NSGA_GENS = 200), the algorithm was told to make 100 guesses and evolve them 200 times. Doing 100 × 200 calculations for just one row takes a few seconds. Doing that for 2,000 rows would take hours.

By dropping it to 20 guesses and 10 evolutions per row (pop_size=20, n_gen=10), NSGA-II still finds a highly accurate, mathematically real answer, but it finds it in a fraction of a second. Multiply that by 2,000 rows, and your pre-training dataset finishes generating in a couple of minutes instead of a couple of days.