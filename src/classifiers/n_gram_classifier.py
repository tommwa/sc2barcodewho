import pandas as pd
import numpy as np
from sklearn.preprocessing import normalize

from features.player_dataclass import PlayerData
from utils.utils import toon_race_to_toon, is_barcode


def n_gram_log_prob(X, Y, c):
    """
    Performs the operation

    The idea of this function is as follows.

    We have a vector X "v_prob_dist" which sums to 1 and hold the probability distribution
    of all different types of n_grams. We also have a vector Y "v_occurrences" which counts the number of the
    different n_grams in some sequence. We want to return the probability of this sequence. For reasons that will become
    clear soon, we will modify it and return something else. Just note that this is the starting idea.

        v_prob_dist = X = (x0, x1, x2, ...), sum = 1
        v_occurrences = Y = (y0, y1, y2, ...)
        sequence_prob = product( X.^Y ) = x0^y0 * x1^y1 * ...
        where:
        .^ refers to elementwise exponent,
        product takes a vector and multiplies all elements together

    Due to lack of training data, "v_prob_dist" is uncertain and in particular will be exactly 0 for most n_grams.
    This will make the probability of any sequence that contain these n_grams exactly 0 since the individual
    probabilities are multiplied.
    To combat this we add a constant "lowest_prob_constant" to each element in the
    probability distribution. (This makes the sum of the probability distribution larger than 1, but it doesn't
    matter for my purpose, I only want to compare probabilities to each other).

        lowest_prob = c
        sequence_prob = product( (X+c).^Y ) = (x0+c)^y0 * (x1+c)^y1 * ...

    The problem is that before adding this constant both vectors were extremely sparse, so adding this constant
    explicitly is not feasible. Instead, I have devised a smart algorithm to avoid this explicit addition.

    Lastly, before looking at this algorithm, note that instead of getting the probability we get the log-probability
    (Since the probability will be extremely tiny and cause numerical issues, and also it allows us to swap exponents
    to multiplications and swap multiplications to additions.) Also note that v_occurrences has been normalized to
    sum 1, again for better comparison between them.

        log_sequence_prob = sum( log(X+c).*Y ) = log(x0+c)*y0 + log(x1+c)*y1 + ...
        where .* is elementwise multiplication.

    This is simply the dot product between the vectors which I will simply denote "*".

        log_sequence_prob = log(X+c)*Y

    To achieve this in a sparse way while still taking advantage of the built-in multiplication method for
    sparse vectors we split the vectors into 2 sections. section 0 will contain all indices where "v_prob_dist" is 0,
    and section 1 will contain all indices where "v_prob_dist" is non-zero.

        X0 = (x_k0, x_k1, x_k2, ...) where k0, k1, k2, ... are the indices where X is zero.
        X1 = (x_i0, x_i1, x_i2, ...) where i0, i1, i2, ... are the indices where X is non-zero
        Note that X0 = (0, 0, 0, ...)

        Y0 = (y_k0, y_k1, y_k2, ...)
        Y1 = (y_i0, y_i1, y_i2, ...)
        Note that Y0 is not necessarily full of zeros, we split both vectors on the same indices depending on where X is 0,
        not depending on where Y is zero.

    We can now rewrite the log_sequence_prob to

        log_sequence_prob = log(X0+c)*Y0 + log(X1+c)*Y1

    Since X0 is just zeros this simplifies to

        log_sequence_prob = log(c) * sum(Y0) + log(X1+c)*Y1

    Almost there, we just need to find a way to calculate sum(Y0).

        sum(Y) = sum(Y0) + sum(Y1)
     => sum(Y0) = sum(Y) - sum(Y1)
        log_sequence_prob = log(c) * (sum(Y) - sum(Y1)) + log(X1+c)*Y1

    X1 and Y1 are easy to treat since they contain only a few elements.
    sum(Y) is easy to calculate for a sparse array.
    In other words, we can calculate this log_sequence_prob with only sparse vectors and basic operations!

    ...But we will rewrite further. Section 1 can be split in section 2 and 3, where section 2 is where Y is non-zero
    and section 3 is where Y is zero. The scalar product's elements are 0 in section 3, so we can rewrite to

        log(X1+c)*Y1 = log(X2+c)*Y2

    Additionally, since section 1 is simply split up in sections 2 and 3,

        sum(Y_1) = sum(Y_2) + sum(Y_3) = sum(Y_2)

    since Y is 0 in section 3.

    This instead allows us to work only in section 2 where both X and Y are non-zero which is even more sparse and also
    easy to access. The final equation is then

         log_sequence_prob = log(c) * (sum(Y) - sum(Y2)) + log(X2+c)*Y2
    """
    # SPEEDUP: instead of repeating this function many times I can call it with the entire db_v n_grams rather than
    # repeating it for every player, will allow me to sort less and remove the slow df.addition appending in
    # the process.

    # First sort the indices and make the data follow the same shuffling
    perm = X.indices.argsort()
    X_ind = X.indices[perm]
    X_data = X.data[perm]
    perm = Y.indices.argsort()
    Y_ind = Y.indices[perm]
    Y_data = Y.data[perm]

    # Get np vectors Y_2 and X_2, using Y_1 = Y[:, section_2_ind] on a csr array was very slow, and I could not find
    # similar syntax for dok / lil, so I do it myself instead.
    X_ind_set = set(X_ind)
    Y_ind_set = set(Y_ind)
    q = [i in X_ind_set for i in Y_ind]
    Y_2 = Y_data[q]
    q = [i in Y_ind_set for i in X_ind]
    X_2 = X_data[q]

    dot_prod = np.dot(np.log(X_2 + c), Y_2)
    sum_Y2 = np.sum(Y_2)
    sum_Y = np.sum(Y.data)
    log_seq_prob = np.log(c) * (sum_Y - sum_Y2) + dot_prod
    return log_seq_prob


def n_gram_classify(config, toon_dict, player_data: PlayerData, n_gram_means, to_visualize: bool):
    """
    Performs the classification of one of the players in a replay using its player_data and a given dbms.

    Can also return extra information for other functions such as for visualization.

    @param to_visualize: Whether to create visualizations of the result.
    @param player_data: PlayerData instance.
    @param dbms: DBMS instance.
    @return: estimate, non_barcode_estimate.
    """

    # For now keep it simple, just pick a single n_gram to look at
    n = 4

    # Get the normalized n_gram for the test player
    df = player_data.n_grams[n - 1]
    ser = df["sparse_n_gram"]
    test_csr_unnormalized = ser.iloc[0]
    test_v = normalize(test_csr_unnormalized, norm="l1", axis=1)

    n_gram_dim = test_v.shape[1]
    lowest_prob = 0.001

    # Build up results_df, which will have index toon_race and columns dist and barcode.
    results_df = pd.DataFrame()
    db_n_grams = n_gram_means[n - 1]
    for toon_race, db_v in db_n_grams.items():
        log_seq_prob = n_gram_log_prob(db_v, test_v, lowest_prob)
        dist = -log_seq_prob

        # check if barcode
        toon = toon_race_to_toon(toon_race)
        names = toon_dict[toon]
        barcode = True
        for name in names:
            if not is_barcode(name):
                barcode = False

        # set up the addition_df with the data.
        data = {"barcode": barcode, "dist": dist}
        addition_df = pd.DataFrame(data, index=[toon_race])
        results_df = pd.concat([results_df, addition_df])

    # Sort by distance with the lowest distance first.
    results_df = results_df.sort_values(by=["dist"])

    # Sort out self (if in db).
    toon_race = player_data.toon_race
    if toon_race in results_df.index:
        results_df.drop(toon_race, inplace=True)

    # find toon estimate
    toon_estimate = results_df.iloc[0].name
    if len(results_df) == 0:
        print("WARNING: There was only one player of this race in the database, try loading more replays into the database.")
    toon_estimate_dist = results_df.iloc[0]["dist"]

    # sort out barcodes
    results_df.drop(results_df[results_df["barcode"] == True].index, inplace=True)
    if len(results_df) == 0:
        print("WARNING: There was no non-barcode players of this race in the database, try loading more replays into the database.")
    non_barcode_toon_estimate = results_df.iloc[0].name

    if to_visualize:
        results_df['names'] = list(map(lambda x: str(toon_dict[toon_race_to_toon(x)]), results_df.index))

        print("--------------------")
        print("N-gram classification result:")
        print(f"closest non-barcode: {toon_dict[toon_race_to_toon(non_barcode_toon_estimate)]}")
        print(f"closest distance INCLUDING other barcodes: {toon_estimate_dist:.6f}")
        print("Table results:")
        print(results_df.head(config["options"]["NEIGHBOURS_TO_PRINT"]))
        print("--------------------")

    return toon_estimate, non_barcode_toon_estimate
