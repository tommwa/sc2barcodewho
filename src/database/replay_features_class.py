import json
import os
import copy

import pandas as pd
import numpy as np

from utils.utils import toon_race_to_race


class ReplayFeatures:
    """Holds data structure for replay features. This is mostly database related, the many big functions for extracting
    features are located in the imported extract_features function.

    self.features: A dictionary where the keys are toon_race and the values are pandas DataFrames with all the
    features as columns and index is the replay_hash. visually, {toon_race: pd.DataFrame, ...} with pd.Dataframe being:
    index,        feature1,     feature2, ...
    ---------------------------------------
    replay_id1,    value11,      value12, ...
    replay_id2,    value21,      value22, ...
    .
    .
    .
    for each player_toon.

    self._stats: dict with keys "mean", "std", "general" that each have the value of a pd.DataFrame with toon_race as index and
    features as columns. "std" takes the standard deviation. If there is only 1 game std will be 0. "generaL" holds the
    columns toon / race / n_games where n_games is the number of games from this player which helps Bayesian type
    classifier know accurate the mean and std are.

    self._overall_stats: {average_mean: value, average_std: value} where average refers to the mean of the stat for
    each player.

    self.stats_not_up_to_date_toon_races: This variable states which toon_races have un-updated mean data.
    The purpose is to allow changing the data multiple times without updating the mean, but we also
    guarantee than whenever the "get_means()" method is called then the means will first be updated if necessary.
    This is why direct access to the "_means" variable should be considered private, since it might not be up to date.
    """

    def __init__(self, data_path):
        self.data_path = data_path
        self.features = {}
        self._stats = {"mean": pd.DataFrame(), "std": pd.DataFrame(), "general": pd.DataFrame()}
        self._overall_stats = {"average_mean": {}, "average_std": {}}
        self.stats_not_up_to_date_toon_races = set()

    def update_stats(self):
        """Updates the stats of the features for all players that are not already up to date."""
        if len(self.stats_not_up_to_date_toon_races) == 0:
            return

        toon_races_to_update = copy.copy(self.stats_not_up_to_date_toon_races)

        toons = []
        races = []
        n_games_list = []
        for toon_race_to_update in toon_races_to_update:
            # If this player no longer exist in the database.
            if toon_race_to_update not in self.features:
                if toon_race_to_update in self._stats["mean"].index:
                    self._stats["mean"].drop(toon_race_to_update, inplace=True)
                    self._stats["std"].drop(toon_race_to_update, inplace=True)
                self.stats_not_up_to_date_toon_races.discard(toon_race_to_update)
                continue

            data = self.features[toon_race_to_update]
            n_games = len(data)
            # If this player has features from 0 games (if all added were removed), remove from the mean df.
            if n_games == 0:
                if toon_race_to_update in self._stats["mean"].index:
                    self._stats["mean"].drop(toon_race_to_update, inplace=True)
                    self._stats["std"].drop(toon_race_to_update, inplace=True)
                self.stats_not_up_to_date_toon_races.discard(toon_race_to_update)
                continue

            # Calculate stats for this player
            n_games_list.append(n_games)
            toons.append(data["toon"].iloc[0])  # The 0 is arbitrary, is the same for every game.
            races.append(data["race"].iloc[0])

            number_data = data.select_dtypes(include=[np.number])
            number_data_mean = pd.Series(number_data.mean(axis=0), name=toon_race_to_update)
            number_data_std = pd.Series(number_data.std(axis=0), name=toon_race_to_update)
            number_data_std.fillna(0, inplace=True)  # If there were only 1 game std becomes NaN, swap to 0.

            # Update self._stats.
            if toon_race_to_update in self._stats["mean"].index:
                self._stats["mean"].loc[toon_race_to_update] = number_data_mean
            else:
                self._stats["mean"] = pd.concat([self._stats["mean"], pd.DataFrame(number_data_mean).T])
            if toon_race_to_update in self._stats["std"].index:
                self._stats["std"].loc[toon_race_to_update] = number_data_std
            else:
                self._stats["std"] = pd.concat([self._stats["std"], pd.DataFrame(number_data_std).T])
            self.stats_not_up_to_date_toon_races.discard(toon_race_to_update)
        assert self.stats_not_up_to_date_toon_races == set()

        # Add general stats: race + toon + n_games
        self._stats["general"] = pd.DataFrame({"race": races, "toon": toons, "n_games": n_games_list},
                                              index=[str(toon_race) for toon_race in zip(toons, races)])

        # Update self._overall_stats.
        number_data = self._stats["mean"].select_dtypes(include=[np.number])
        self._overall_stats["average_mean"] = number_data.mean().to_dict()
        number_data = self._stats["std"].select_dtypes(include=[np.number])
        self._overall_stats["average_std"] = number_data.mean().to_dict()

    def reset_files(self):
        for filename in ["replay_features.json", "player_mean_features.json", "player_std_features.json", "player_general_features.json"]:
            file_path = os.path.join(self.data_path, filename)
            with open(file_path, "w") as f:
                f.write("{}")
        with open(os.path.join(self.data_path, "overall_stats.json"), 'w') as f:
            json.dump({"average_mean": {}, "average_std": {}}, f)

    def save_to_file(self):
        self.update_stats()
        # Save features.
        with open(os.path.join(self.data_path, "replay_features.json"), "w") as outfile:
            rep_f = {}
            for key in self.features:
                rep_f[key] = json.loads(self.features[key].to_json())  # to_json() makes a string, I want dict.
            json.dump(rep_f, outfile)
        # Save player stats.
        with open(os.path.join(self.data_path, "player_mean_features.json"), "w") as outfile:
            json.dump(self._stats["mean"].to_json(), outfile)
        with open(os.path.join(self.data_path, "player_std_features.json"), "w") as outfile:
            json.dump(self._stats["std"].to_json(), outfile)
        with open(os.path.join(self.data_path, "player_general_features.json"), "w") as outfile:
            json.dump(self._stats["general"].to_json(), outfile)
        # Save overall stats.
        with open(os.path.join(self.data_path, "overall_stats.json"), "w") as outfile:
            json.dump(self._overall_stats, outfile)

    def load_from_file(self):
        # Load features.
        file_path = os.path.join(self.data_path, "replay_features.json")
        with open(file_path, "r") as infile:
            self.features = json.load(infile)
        for key, data in self.features.items():
            self.features[key] = pd.DataFrame(data)
            self.features[key].index.name = "replay_hash"
        # Load mean.
        with open(os.path.join(self.data_path, "player_mean_features.json"), "r") as f:
            json_object = json.load(f)
        if json_object == {}:  # Separate empty case since for some reason this crashes the read_json.
            self._stats["mean"] = pd.DataFrame(json_object)
        else:
            self._stats["mean"] = pd.read_json(json_object)
        # Load std.
        with open(os.path.join(self.data_path, "player_std_features.json"), "r") as f:
            json_object = json.load(f)
        if json_object == {}:  # Separate empty case since for some reason this crashes the read_json.
            self._stats["std"] = pd.DataFrame(json_object)
        else:
            self._stats["std"] = pd.read_json(json_object)
        # Load general.
        with open(os.path.join(self.data_path, "player_general_features.json"), "r") as f:
            json_object = json.load(f)
        if json_object == {}:  # Separate empty case since for some reason this crashes the read_json.
            self._stats["general"] = pd.DataFrame(json_object)
        else:
            self._stats["general"] = pd.read_json(json_object)
        # Load overall stats.
        with open(os.path.join(self.data_path, "overall_stats.json"), 'r') as f:
            self._overall_stats = json.load(f)

    def enter_replay(self, player_data):
        self.stats_not_up_to_date_toon_races.add(player_data.toon_race)
        features = player_data.features
        toon_race = player_data.toon_race
        replay_id = player_data.replay_id

        if toon_race in self.features:
            self.features[toon_race] = pd.concat(
                [self.features[toon_race], pd.DataFrame([features], index=[replay_id])]
            )
        else:
            self.features[toon_race] = pd.DataFrame([features], index=[replay_id])
        self.features[toon_race].index.name = "replay_hash"

    def remove_replay(self, toon_race, replay_id):
        self.stats_not_up_to_date_toon_races.add(toon_race)
        assert replay_id in self.features[toon_race].index
        self.features[toon_race] = self.features[toon_race].drop(replay_id)

    def get_stats(self):
        if len(self.stats_not_up_to_date_toon_races) == 0:
            return self._stats
        else:
            self.update_stats()
            return self._stats

    def get_overall_stats(self):
        if len(self.stats_not_up_to_date_toon_races) == 0:
            return self._overall_stats
        else:
            self.update_stats()
            return self._overall_stats

    def drop_columns(self, columns_to_drop):
        for stat in ["mean", "std"]:
            self._stats[stat] = self._stats[stat].drop(columns_to_drop, axis=1)
        for toon_race in self.features:
            self.features[toon_race] = self.features[toon_race].drop(columns_to_drop, axis=1)
        for d in self._overall_stats.values():
            for col in columns_to_drop:
                d.pop(col)

    def race_filter_stats(self, filter_race):
        self.update_stats()
        filtered = dict()
        for stat in self._stats:
            filtered[stat] = self._stats[stat][
                [toon_race_to_race(toon_race) == filter_race for toon_race in self._stats[stat].index]]
        return filtered
