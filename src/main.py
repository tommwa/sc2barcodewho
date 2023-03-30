import os
import tkinter as tk
from tkinter import messagebox
import time
import threading

import sc2reader
from sc2reader.engine.plugins.apm import APMTracker

from features.evaluate_features import get_feature_relevances
from classifiers.eval_classificatiton import test_classification_accuracy
from database.DBMS import DBMS
from utils.utils import (
    get_toon_dict,
    load_config,
    get_most_recent_replay_filename,
    try_load_replay,
    get_replays_recursively,
    set_config,
)
from classifiers.classify import classify_replay_filepath
from tkinter.filedialog import askopenfilename


class MainApplication:
    def __init__(self, config, program_path, data_path):
        # Set Event = shared info between threads so that we can stop loading replays when the stop button is pressed
        self.stop_event = threading.Event()
        self.user_quit_event = threading.Event()

        self.dbms = False
        self.data_path = data_path
        self.config = config
        self.program_path = program_path

        # GUI button stuff
        self.root = tk.Tk()
        self.frame_main = tk.Frame(self.root)
        self.button_dir = tk.Button(
            self.frame_main,
            text="Set replay folder",
            font=("Arial", 14),
            command=self.set_replay_dir,
        )
        self.button_dir.pack(padx=10, pady=5)
        self.button_load = tk.Button(
            self.frame_main,
            text="Load all unloaded replays",
            font=("Arial", 14),
            command=self.load_all_unloaded_replays,
        )
        self.button_load.pack(padx=10, pady=5)
        self.button_classify_recent = tk.Button(
            self.frame_main,
            text="Classify the most recent game",
            font=("Arial", 14),
            command=self.classify_most_recent_replay,
        )
        self.button_classify_recent.pack(padx=10, pady=20)
        self.button_classify_choose = tk.Button(
            self.frame_main,
            text="Choose a replay to classify",
            font=("Arial", 14),
            command=self.select_replay_then_classify,
        )
        self.button_classify_choose.pack(padx=10, pady=20)
        self.button_find_toons = tk.Button(
            self.frame_main, text="Find Toons", font=("Arial", 14), command=self.find_toons
        )
        self.button_find_toons.pack(padx=10, pady=20)
        self.button_reset = tk.Button(
            self.frame_main, text="Reset Database", font=("Arial", 14), command=self.reset_database
        )
        self.button_reset.pack(padx=10, pady=150)

        self.frame_stop = tk.Frame()
        self.button_stop = tk.Button(
            self.frame_stop, text="Stop loading into database", font=("Arial", 14), command=self.stop_loading
        )
        self.button_stop.pack(padx=10, pady=20)

        self.frame_main.pack()
        self.root.protocol("WM_DELETE_WINDOW", self.when_closing_window)
        self.root.mainloop()

    def set_replay_dir(self):
        replay_dir = tk.filedialog.askdirectory()
        print(f"You selected the directory: {replay_dir}")
        # Check how many replays there are in the dir.
        list_of_replay_paths, latest_replay_time = get_replays_recursively(folder_path=replay_dir)
        print(f"There are {len(list_of_replay_paths)} replays in this directory and it's sub-folders.")
        # Set it
        self.config = load_config(self.program_path)
        if messagebox.askyesno(
            "Set path?",
            f"{replay_dir}\nIs this the path that you want to load replays from? All sub-folders will be included.",
        ):
            self.config["options"]["REPLAY_FOLDER_PATH"] = replay_dir
            if self.dbms is not False:
                self.dbms.config["options"]["REPLAY_FOLDER_PATH"] = replay_dir
            set_config(self.program_path, config=self.config)
        else:
            print("Not setting the replay path.")

    def when_closing_window(self):
        print("--------------------")
        print("Closing program, please wait...")
        self.user_quit_event.set()
        self.stop_event.set()
        self.root.destroy()
        print("Program closed.")

    def stop_loading(self):
        self.stop_event.set()

    def load_all_unloaded_replays(self):
        """Start a new thread to load all replays."""

        def process_all_replays():
            """Load all replays."""
            self.stop_event.clear()
            self.frame_main.pack_forget()
            self.frame_stop.pack()
            # Actually do the loading
            if not self.dbms:
                self.dbms = DBMS(self.config, program_path, reset_before_loading=False)
            self.dbms.enter_all_replays_into_db(self.stop_event, False)
            # Put GUI back when it is finished.
            if not self.user_quit_event.is_set():
                self.frame_stop.pack_forget()
                self.frame_main.pack()

        threading.Thread(target=process_all_replays).start()

    def classify_most_recent_replay(self):
        if not self.dbms:
            self.dbms = DBMS(self.config, program_path, reset_before_loading=False)
        # Classify most recent.
        most_recent_replay_path = get_most_recent_replay_filename(self.config)[0]
        classify_replay_filepath(
            self.config, most_recent_replay_path, dbms=self.dbms, to_visualize=True, data_path=self.data_path
        )
        if self.config["options"]["UPDATE_DB_AFTER_CLASSIFYING"]:
            self.load_all_unloaded_replays()
        return

    def select_replay_then_classify(self):
        if not self.dbms:
            self.dbms = DBMS(self.config, program_path, reset_before_loading=False)
        filename = askopenfilename()
        print(f"Will classify replay {filename}")
        classify_replay_filepath(self.config, filename, dbms=self.dbms, to_visualize=True, data_path=self.data_path)
        return

    @staticmethod
    def find_toons():
        filename = askopenfilename()
        print(f"Looking for toons in replay {filename}")
        replay = try_load_replay(filename)
        if replay is False:
            return
        for player in replay.players:
            print(f"Player {player} has toon {player.toon_handle}.")

    def reset_database(self):
        if messagebox.askyesno(
            "Reset?",
            "Are you sure you want to reset this programs database? This means you will need to load all your replays again to use it.",
        ):
            self.dbms = DBMS(self.config, program_path, reset_before_loading=True)
            self.dbms.save_to_file()
            print("Database reset.")
        else:
            print("Not resetting.")


if __name__ == "__main__":
    # some prep
    program_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(program_path, "database", "data")
    sc2reader.engine.register_plugin(APMTracker())
    config = load_config(program_path)

    # main code
    # most_recent_replay_path = get_most_recent_replay_filename(config)[0]
    app = MainApplication(config, program_path, data_path)
    time.sleep(5)

    # test
    if config["options"]["RUN_TESTS"]:
        dbms = DBMS(config, program_path, reset_before_loading=False)
        toon_dict = get_toon_dict(data_path)
        feature_relevances = get_feature_relevances(dbms.rep_feats.features)
        print("Feature relevances:\n", feature_relevances, "-----------------------")

        features_to_drop = [
            "average_chain_length_earlygame",
            "distances_side_scrolls_mean_earlygame",
            "percentage_side_scrolls_earlygame",
            "non_zero_jumps_earlygame",
        ]

        acc, n_trials = test_classification_accuracy(
            config,
            toon_dict,
            dbms,
            n_sample_games=1,
            columns_to_remove=features_to_drop,
            profile_mode=False,
            max_games_to_use=5,
        )
        print(f"acc: {acc} over {n_trials} trials")

    # replay_features = load_replay_features(program_path)
    # plot_all_features(replay_features)

    # df = dbms.get_replay_mean_copy()
    # scaled_features = scale_df(df)
