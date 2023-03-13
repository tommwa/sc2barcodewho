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

    self._mean: pd.DataFrame with toon_race as index and features as columns.

    self.means_not_up_to_date_toon_races: This variable states which toon_races have un-updated mean data.
    The purpose is to allow changing the data multiple times without updating the mean, but we also
    guarantee than whenever the "get_means()" method is called then the means will first be updated if necessary.
    This is why direct access to the "_means" variable should be considered private, since it might not be up to date.
    """

    def __init__(self, data_path):
        self.data_path = data_path
        self.features = {}
        self._mean = pd.DataFrame()
        self.means_not_up_to_date_toon_races = set()

    def update_mean(self, toon_races_to_update):
        """
        @param toon_races_to_update: Either specify a toon_race to update and leave others untouched, or set to "all"
        or "changed". Changed will only update the ones that have changed since the last update,
        "all" will update all.
        """
        if len(self.means_not_up_to_date_toon_races) == 0 and toon_races_to_update != "all":
            return

        if toon_races_to_update == "changed":
            toon_races_to_update = copy.copy(self.means_not_up_to_date_toon_races)

        if toon_races_to_update == "all":
            self._mean = pd.DataFrame()
            for toon_race, data in self.features.items():
                if len(data) == 0:
                    continue
                number_data = data.select_dtypes(include=[np.number])
                number_data_mean = pd.Series(number_data.mean(axis=0), name=toon_race).to_frame().T
                number_data_mean["toon"] = data["toon"].iloc[0]  # The 0 is arbitrary, is the same for every game.
                number_data_mean["race"] = data["race"].iloc[0]
                self._mean = pd.concat([self._mean, number_data_mean])
            self.means_not_up_to_date_toon_races = set()
        else:
            for toon_race_to_update in toon_races_to_update:
                # If this player no longer exist in the database.
                if toon_race_to_update not in self.features:
                    if toon_race_to_update in self._mean.index:
                        self._mean.drop(toon_race_to_update, inplace=True)
                    self.means_not_up_to_date_toon_races.discard(toon_race_to_update)
                    continue

                data = self.features[toon_race_to_update]
                # If this player has features from 0 games (if all added were removed), remove from the mean df.
                if len(data) == 0:
                    if toon_race_to_update in self._mean.index:
                        self._mean.drop(toon_race_to_update, inplace=True)
                    self.means_not_up_to_date_toon_races.discard(toon_race_to_update)
                    continue

                # Calculate mean for this player
                number_data = data.select_dtypes(include=[np.number])
                number_data_mean = pd.Series(number_data.mean(axis=0), name=toon_race_to_update)
                number_data_mean["toon"] = data["toon"].iloc[0]  # The 0 is arbitrary, is the same for every game.
                number_data_mean["race"] = data["race"].iloc[0]
                if toon_race_to_update in self._mean.index:
                    self._mean.loc[toon_race_to_update] = number_data_mean
                else:
                    self._mean = pd.concat([self._mean, pd.DataFrame(number_data_mean).T])
                self.means_not_up_to_date_toon_races.discard(toon_race_to_update)
            if toon_races_to_update == "changed":
                assert self.means_not_up_to_date_toon_races == set()

    def reset_files(self):
        for filename in ["replay_features.json", "player_mean_features.json"]:
            file_path = os.path.join(self.data_path, filename)
            with open(file_path, "w") as f:
                f.write("{}")

    def save_to_file(self):
        self.update_mean("changed")
        # Save features.
        with open(os.path.join(self.data_path, "replay_features.json"), "w") as outfile:
            rep_f = {}
            for key in self.features:
                rep_f[key] = json.loads(self.features[key].to_json())  # to_json() makes a string, I want dict.
            json.dump(rep_f, outfile)
        # Save mean.
        with open(os.path.join(self.data_path, "player_mean_features.json"), "w") as outfile:
            json.dump(self._mean.to_json(), outfile)

    def load_from_file(self):
        # Load features.
        file_path = os.path.join(self.data_path, "replay_features.json")
        with open(file_path, "r") as infile:
            self.features = json.load(infile)
        for key, data in self.features.items():
            self.features[key] = pd.DataFrame(data)
            self.features[key].index.name = "replay_hash"
        # Load mean.
        load_path = os.path.join(self.data_path, "player_mean_features.json")
        with open(load_path, "r") as f:
            json_object = json.load(f)
        if json_object == {}:  # Separate empty case since for some reason this crashes the read_json.
            self._mean = pd.DataFrame(json_object)
        else:
            self._mean = pd.read_json(json_object)

    def enter_replay(self, player_data):
        self.means_not_up_to_date_toon_races.add(player_data.toon_race)
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
        self.means_not_up_to_date_toon_races.add(toon_race)
        assert replay_id in self.features[toon_race].index
        self.features[toon_race] = self.features[toon_race].drop(replay_id)

    def get_mean(self):
        if len(self.means_not_up_to_date_toon_races) == 0:
            return self._mean
        else:
            self.update_mean("changed")
            return self._mean

    def drop_columns(self, columns_to_drop):
        self._mean = self._mean.drop(columns_to_drop, axis=1)
        for toon_race in self.features:
            self.features[toon_race] = self.features[toon_race].drop(columns_to_drop, axis=1)

    def race_filter_mean(self, filter_race):
        self.update_mean("changed")
        return self._mean[[toon_race_to_race(toon_race) == filter_race for toon_race in self._mean.index]]
