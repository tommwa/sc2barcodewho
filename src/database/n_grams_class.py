import os
import pickle
import copy
from collections import defaultdict

import pandas as pd
import numpy as np
from sklearn.preprocessing import normalize

from utils.utils import toon_race_to_race


class NGrams:
    """
    Holds and manipulates the n_gram data. This docstring will explain the format of the key variables.

    self.n_grams: [pd.DataFrame, ...] where pd_DataFrame has columns "replay_id", "toon_race", "sparse_n_gram" where
    "sparse_n_gram" is a SciPy sparse csr_array. In this array the index is coded for the type of
    n_gram (e.g. [camera action, selection event] and the value is the number of occurrences.

    self._means: list of {toon_race: sparse csr_array}, where the first element of the list is 1_gram, 2_gram etc.
    In this case the array comes from the sum of each one of this player's n_gram vectors which has then been
    normalized to sum 1.

    self._means_not_up_to_date_toon_races: This variable states which players (toon_races) has had their data changed
    without the means of their data having been updated.
    The purpose is to allow changing the data multiple times without updating the mean, but we also
    guarantee than whenever the "get_means()" method is called then the means will first be updated if necessary.
    This is why direct access to the "_means" variable should be considered private, since it might not be up to date.
    """

    def __init__(self, config, data_path):
        self.data_path = data_path
        self.HIGHEST_N = config["hyperparams"]["HIGHEST_N"]
        self.n_grams = []
        self._means = []
        self.means_not_up_to_date_toon_races = set()

    def reset_files(self):
        for n in range(1, self.HIGHEST_N + 1):
            pd.DataFrame().to_pickle(os.path.join(self.data_path, "n_gram", "earlygame", f"sparse_{n}_gram.pkl"))
            with open(
                os.path.join(self.data_path, "n_gram", "earlygame", f"sparse_{n}_gram_mean.pkl"), "wb"
            ) as outfile:
                pickle.dump({}, outfile)

    def save_to_file(self):
        self.update_means("changed")
        n_gram_folder_path = os.path.join(self.data_path, "n_gram", "earlygame")
        for n in range(1, self.HIGHEST_N + 1):
            self.n_grams[n - 1].to_pickle(os.path.join(n_gram_folder_path, f"sparse_{n}_gram.pkl"))
            with open(os.path.join(n_gram_folder_path, f"sparse_{n}_gram_mean.pkl"), "wb") as outfile:
                pickle.dump(self._means[n - 1], outfile)

    def load_from_file(self):
        folder_path = os.path.join(self.data_path, "n_gram", "earlygame")
        self.n_grams = []
        self._means = []
        for n in range(1, self.HIGHEST_N + 1):
            n_gram = pd.read_pickle(os.path.join(folder_path, f"sparse_{n}_gram.pkl"))
            self.n_grams.append(n_gram)
            with open(os.path.join(folder_path, f"sparse_{n}_gram_mean.pkl"), "rb") as infile:
                self._means.append(pickle.load(infile))

    def enter_replay(self, player_data):
        self.means_not_up_to_date_toon_races.add(player_data.toon_race)
        for n in range(1, self.HIGHEST_N + 1):  # n as in n_gram.
            self.n_grams[n - 1] = pd.concat([self.n_grams[n - 1], player_data.n_grams[n - 1]], ignore_index=True)

    def remove_replay(self, toon_race, replay_id):
        """Removes the single row from the database with the given toon_race and replay_id."""
        self.means_not_up_to_date_toon_races.add(toon_race)
        for n in range(1, self.HIGHEST_N + 1):
            df = self.n_grams[n - 1]
            bool_rows_to_keep = (df["replay_id"] != replay_id) | (df["toon_race"] != toon_race)
            self.n_grams[n - 1] = df[bool_rows_to_keep]
            self.n_grams[n - 1].index = np.arange(len(self.n_grams[n - 1]))  # Reset index to 0, 1, 2,... manually.
            assert len(self.n_grams[n - 1]) == len(df) - 1

    def update_means(self, toon_races_to_update: set, max_games_to_use=1000000):
        """
        @param max_games_to_use: Only take this many games to build up the mean. Only used in testing either to speed
        up or to limit the amount of training data used in a quick and easy way.
        @param toon_races_to_update: Either specify a set of toon_races to update and ignore others, or set to "all" or
        "changed" to update all or the ones that were changed since last update.
        """
        if len(self.means_not_up_to_date_toon_races) == 0 and toon_races_to_update != "all":
            return

        # If we only want to update the changed values then use the self variable.
        if toon_races_to_update == "changed":
            toon_races_to_update = copy.copy(self.means_not_up_to_date_toon_races)

        # Create a mapping from toon_race to a list of rows where this player has data.
        toon_race_to_rows = defaultdict(list)
        for i in range(len(self.n_grams[0])):
            t_r = self.n_grams[0].loc[i, "toon_race"]
            toon_race_to_rows[t_r].append(i)

        # Begin by resetting sparse_n_grams_mean if we want to update all of it.
        if toon_races_to_update == "all":
            for i in range(self.HIGHEST_N):
                self._means[i] = {}
        # Check if the toon_race_to_update still exists in the database. If not, then remove this player from _means.
        # Also remove this player from toon_races_to_update since it has already been updated.
        else:
            for toon_race in toon_races_to_update:
                if toon_race not in toon_race_to_rows:
                    for d in self._means:
                        if toon_race in d:
                            d.remove(toon_race)
                        toon_races_to_update.remove(toon_race)
                        self.means_not_up_to_date_toon_races.discard(toon_race)

        # Update means
        for i, df in enumerate(self.n_grams):
            for toon_race in toon_race_to_rows:
                if toon_race in toon_races_to_update or toon_races_to_update == "all":
                    rows = toon_race_to_rows[toon_race]
                    vectors = list(df.loc[rows, "sparse_n_gram"])
                    vectors = vectors[:max_games_to_use]
                    for vectors_i, v in enumerate(vectors):
                        vectors[vectors_i] = v.tocoo()
                    vector_sum = np.sum(vectors)
                    for vectors_i, v in enumerate(vectors):
                        vectors[vectors_i] = v.tocsr()
                    norm_vector = normalize(vector_sum, norm="l1", axis=1)
                    self._means[i][toon_race] = norm_vector

        # Update the self.means_not_up_to_date_toon_races variable
        if toon_races_to_update == "all":
            self.means_not_up_to_date_toon_races = set()
        else:
            for toon_race in toon_races_to_update:
                self.means_not_up_to_date_toon_races.discard(toon_race)

    def get_mean(self):
        if len(self.means_not_up_to_date_toon_races) == 0:
            return self._means
        else:
            self.update_means("changed")
            return self._means

    def race_filter_mean(self, filter_race):
        self.update_means("changed")
        race_only_n_gram_means = []
        for d in self._means:
            race_only_dict = {k: v for k, v in d.items() if toon_race_to_race(k) == filter_race}
            race_only_n_gram_means.append(race_only_dict)
        return race_only_n_gram_means
