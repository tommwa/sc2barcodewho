import copy
import os
import json
from collections import defaultdict

import pandas as pd
from tqdm.auto import tqdm

from database.replay_features_class import ReplayFeatures
from database.n_grams_class import NGrams
from features.player_dataclass import PlayerData
from utils.utils import get_replays_recursively, replay_is_relevant, try_load_replay
from database.replay_hash import ReplayHash

class DBMS:
    def __init__(self, config, program_path, reset_before_loading):
        # Basic variables
        self.program_path = program_path
        self.data_path = os.path.join(self.program_path, "database", "data")
        self.config = config
        # These will be set up when calling self.load_data().
        self.rep_hash = ReplayHash(self.data_path)
        self.rep_feats = ReplayFeatures(self.data_path)
        self.n_grams = NGrams(config, self.data_path)
        self.latest_update_time = None
        # Load data from file.
        if reset_before_loading:
            self.reset_database()
        self.load_data()

    def load_data(self):
        """Simply load data from file."""
        self.rep_feats.load_from_file()
        self.n_grams.load_from_file()
        self.rep_hash.load_from_file()
        fn = os.path.join(self.data_path, "latest_update_time.txt")
        with open(fn, "r") as f:
            self.latest_update_time = float(f.read())

    def save_to_file(self):
        """
        Updates all means and save everything to file.
        Replay hashes and toon dict are both updated and saved to file for every replay by the replay loader,
        so they do not need to be saved again here.
        """
        print("saving to file...")
        self.rep_feats.save_to_file()
        self.n_grams.save_to_file()
        self.rep_hash.save_to_file()
        fn = os.path.join(self.data_path, "latest_update_time.txt")
        with open(fn, "w") as f:
            f.write(str(self.latest_update_time))
        print("Saved to file.")

    def reset_database(self):
        """Removes all data from file (except toon_handle_to_names)."""
        self.rep_hash.reset_file()
        self.rep_feats.reset_files()
        self.n_grams.reset_files()

    def enter_into_db(self, player_datas):
        """Takes the extracted features + n_grams from the replay and adds to the database variables."""
        for player_data in player_datas:
            self.rep_feats.enter_replay(player_data)
            self.n_grams.enter_replay(player_data)

    def enter_all_replays_into_db(self, stop_event, exception_replay):
        """Find list of replay paths -> parse them -> enter features etc. into database in memory and save to file."""
        list_of_replay_paths, latest_replay_time = get_replays_recursively(
            config=self.config, filter_update_time=self.latest_update_time
        )
        for i in tqdm(range(len(list_of_replay_paths)), desc="loading replays"):
            if stop_event.is_set():
                # Stop event is set if the user clicks the stop button or closes the GUI.
                print("Manually stopping loading of replays.")
                break
            replay_path = list_of_replay_paths[i]
            if exception_replay:
                if replay_path == exception_replay:
                    continue
            replay_hash = self.rep_hash.hash_replay(replay_path)
            if self.rep_hash.in_db(replay_hash):
                continue
            self.rep_hash.add_hash(replay_hash)
            replay = try_load_replay(replay_path)
            if replay is False:
                continue
            if not replay_is_relevant(replay):
                continue
            _update_toon_dict(replay, self.program_path)
            player_datas = []
            for player in replay.players:
                player_datas.append(PlayerData(self.config, player=player, replay_id=replay_hash))
            self.enter_into_db(player_datas)
        self.latest_update_time = latest_replay_time
        self.save_to_file()

    def get_replay_features_copy(self):
        return copy.deepcopy(self.rep_feats.features)

    def get_replay_mean_copy(self):
        return copy.deepcopy(self.rep_feats.get_mean())

    def update_means(self, toon_races_to_update, max_games_to_use=1000000):
        self.n_grams.update_means(toon_races_to_update, max_games_to_use=max_games_to_use)
        self.rep_feats.update_mean(toon_races_to_update)

    def get_race_filter_means(self, filter_race):
        return_dict = dict()
        return_dict["n_gram"] = self.n_grams.race_filter_mean(filter_race)
        return_dict["features"] = self.rep_feats.race_filter_mean(filter_race)
        return return_dict

    def remove_from_db(self, toon_race, replay_id):
        """If the replay is in the db, remove the features for this player. Note that not all features of this player
         are removed; only from a single game given by the replay_id.
         Requires quite a bit of computation since n_grams as well as replay_mean_features needs to be re-computed for
         this player.
        @param replay_id: The replay hash.
        """
        # Do nothing if the replay is not in the database to begin with.
        if not self.rep_hash.in_db(replay_id):
            return
        self.rep_feats.remove_replay(toon_race, replay_id)
        self.n_grams.remove_replay(toon_race, replay_id)

    def get_test_replay_db_pairs(self, n_sample_games, max_games_to_use):
        """
        Method used for testing only, will for each replay pretend that it is an unknown barcode replay and remove
        it from the database so that other functions can test accuracy.

        @param max_games_to_use: The max number of n_gram training data to use, just limiting n_grams for speedup.
        @param n_sample_games: The number of barcode samples to test from a single player.
        @return yields tuples of the replay's PlayerData and a copy of the dbms with this specific replay's data removed.
        """
        self.update_means("changed")
        for toon_race, df in self.rep_feats.features.items():
            # Verify that this player has enough games in database.
            if len(df) < max(n_sample_games, 2):
                continue

            n_replays_tested_for_toon_race = 0
            for replay_id in df.index:
                n_replays_tested_for_toon_race += 1
                if n_replays_tested_for_toon_race > n_sample_games:
                    break
                # Create a PlayerData instance using the current dbms data.
                player_data_dict = dict()
                player_data_dict["replay_id"] = replay_id
                player_data_dict["toon_race"] = toon_race
                player_n_grams = []
                for i in range(self.n_grams.HIGHEST_N):
                    n_gram_df = self.n_grams.n_grams[i]
                    n_gram_df = n_gram_df[(n_gram_df["replay_id"] == replay_id) & (n_gram_df["toon_race"] == toon_race)]
                    player_n_grams.append(n_gram_df[n_gram_df["replay_id"] == replay_id])
                player_data_dict["n_grams"] = player_n_grams
                feat_series = self.rep_feats.features[toon_race].loc[replay_id]
                player_data_dict["features"] = pd.DataFrame([feat_series], index=[toon_race])
                player_data = PlayerData(self.config, complete_data=player_data_dict)

                # Create a copy of the dbms and remove the current player's data.
                copy_dbms = copy.deepcopy(self)
                copy_dbms.remove_from_db(toon_race, replay_id)
                copy_dbms.update_means(set([toon_race]), max_games_to_use=max_games_to_use)
                # TODO: check if this still works after changing n_grams
                yield player_data, copy_dbms


def _update_toon_dict(replay, program_path):
    """simply adds the toons from the replay to the toon dict, also reads and saves to file."""
    # load toon_dict from file
    dict_path = os.path.join(program_path, "database", "data", "toon_handle_to_names.txt")
    with open(dict_path, "r") as infile:
        toon_dict = json.load(infile)
    toon_dict = defaultdict(list, toon_dict)
    # update the variable
    for player in replay.players:
        if player.name in toon_dict[player.toon_handle]:
            continue
        else:
            toon_dict[player.toon_handle].append(player.name)
    # update the file
    with open(dict_path, "w") as outfile:
        json.dump(toon_dict, outfile)
