import matplotlib.pyplot as plt
import pandas as pd


def plot_all_features(replay_features, green_player_toon_race="most_common"):
    """
    Plot for a single player all the features, just to get a visual of how consistent the player is for each feature
    @param green_player_toon_handle: the toon handle of the player to be plotted as green. If 'most_common' then
        automatically find the most common player and make that one green
    @return: None
    """
    # get the most common player in the list of replays
    if green_player_toon_race == "most_common":
        most_games = 0
        most_toon_race = ""
        for toon_race, features in replay_features.items():
            n_games = len(features)
            if n_games > most_games:
                most_games = n_games
                most_toon_race = toon_race
        green_player_toon_handle = most_toon_race

    df = replay_features[most_toon_race]
    # make sure the type of the numerics are correct
    for col in df:
        # transform the column to numerics if possible
        try:
            df[col] = pd.to_numeric(df[col])
        except ValueError:
            continue
        plt.figure()
        plt.title(col)
        ax = df[col].plot(c="g", style="o")
        plt.show()
