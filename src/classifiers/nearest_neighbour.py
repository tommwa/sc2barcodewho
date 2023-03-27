import numpy as np
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

from utils.utils import get_toon_dict, is_barcode, toon_race_to_toon
from features.feature_normalizing import scale_df
from features.utils_features import add_name_to_toon_dict
from database.DBMS import DBMS
from features.player_dataclass import PlayerData


def find_nearest_neighbour(toon_dict, player_data: PlayerData, dbms: DBMS, to_visualize=True):
    """
    @param player_data: PlayerData instance.
    @param dbms: DBMS instance
    @return:
    """
    toon_race = player_data.toon_race
    player_mean_features = dbms.rep_feats.get_stats()["mean"]

    # sort out players of other races from df
    barcode_race = player_mean_features.loc[toon_race]["race"]
    player_mean_features = player_mean_features.drop(
        player_mean_features[player_mean_features["race"] != barcode_race].index
    )

    # first scale the data to mean 1 (only suitable as long as all the features are positive)
    player_mean_features = scale_df(player_mean_features)
    # TODO: the test data is not being scaled now, need to either scale with it or without it and then save the scaling coefficients to scale the test data too..

    # separate text data
    text_data = player_mean_features.select_dtypes(exclude=[np.number])
    player_mean_features = player_mean_features.select_dtypes(include=[np.number])
    # find nearest neighbour
    # first calculate square distances to the barcode
    diff = player_mean_features - player_data.features.select_dtypes(include=[np.number])
    sq_dist = pd.Series((diff * diff).sum(axis=1), name="sq_dist")
    player_mean_features = pd.concat([player_mean_features, sq_dist], axis=1)
    player_mean_features = player_mean_features.sort_values("sq_dist")
    # add back text data
    player_mean_features = pd.concat([player_mean_features, text_data], axis=1)
    player_mean_features_with_sq = player_mean_features.copy()

    # we also want to return the toon of our guess
    nearest_toon_race = player_mean_features.index[0]  # take second value because the first is the barcode itself.

    # We also want the nearest non-barcode. Eg if someone has multiple barcodes it's useless to classify a barcode as a barcode.
    nearest_non_barcode_toon_race = nearest_toon_race
    i = 1
    all_barcodes = True
    while all_barcodes:
        toon = toon_race_to_toon(nearest_non_barcode_toon_race)
        names = toon_dict[toon]  # keep in mind each toon saves a list of the history of all their names.
        for name in names:
            if not is_barcode(name):
                all_barcodes = False
        if all_barcodes:
            i += 1
            nearest_non_barcode_toon_race = player_mean_features.index[
                i
            ]  # will crash if there's only barcodes in the database which I don't mind for this test function

    # save only top neightbours
    player_mean_features = player_mean_features.iloc[: options["neighbours_to_print"]]
    # make a return list of top people, where we list [[names, sq_dist], ...]
    return_list = []
    for key in player_mean_features.index:
        toon = player_mean_features["toon"][key]
        names = toon_dict[toon]
        sq_dist = player_mean_features.loc[key]["sq_dist"]
        return_list.append([names, sq_dist])

    # finally visualize the result if requested to
    if to_visualize:
        print("Nearest Neighbours (+sq dist):")
        for e in return_list:
            print(e)
        print("----------------------")
    return return_list, player_mean_features_with_sq, nearest_toon_race, nearest_non_barcode_toon_race


def get_accuracy_of_nearest_neighbour(
    program_path, replay_features, player_mean_features, n_games_known, n_sample_games
):
    """
    calculates the accuracy (and some other test measures) of nearest_neighbour. The idea is to loop over each player
    and keep n_games_known games of theirs to set the mean features, and then perform n_single_barcode_trials by
    anonymizing some of their other replays and checking if they are correctly classified by the nearest_neighbour
    classifier.
    @param replay_features: dict of pandas DataFrames. key = "(player-race)"
    @param player_mean_features: pandas DataFrame, rows = "(player-race)", columns = mean features.
    @param n_games_known: number of games that are used to set the player mean.
    If there are noot enough replays the player-race is skipped.
    @param n_sample_games: number of anonymized games to test the accuracy, need to be separate from the games
    from n_games_known. If there are not enough games the player-race is skipped.
    @return: acc, n_trials, goal_distances, closest_sq_distances. n_trials is the number of tests that were able to be
    made. goal_distances is a list of the square distances estimated by the classifier between the mean features and the
    test. closest_sq_distances is the distance to the closest neighbour, this will equal goal_distance if the
    classification was correct.
    """
    # prep
    toon_dict = get_toon_dict(program_path)
    min_games_required_to_test = n_games_known + n_sample_games
    n_correct = 0
    n_incorrect = 0
    goal_distances = []
    closest_sq_distances = []
    for toon_race, feature_df in replay_features.items():
        # sort out barcodes, this helps combat the issue of accuracy never getting above ~50% if people have a barcode and real account
        toon = toon_race_to_toon(toon_race)
        names = toon_dict[toon]
        any_barcodes = False
        for name in names:
            if is_barcode(name):
                any_barcodes = True
        if any_barcodes:
            continue

        # calculate length of feature_df
        n_games = feature_df.shape[0]
        if n_games >= min_games_required_to_test:
            # update the mean values pretending we only have these n_known_games known features
            temp_player_mean_features = player_mean_features.copy()
            known_features = feature_df.iloc[0:n_games_known]
            known_features_mean = known_features.select_dtypes(include=[np.number]).mean()
            for feature in known_features_mean.index:
                temp_player_mean_features.at[toon_race, feature] = known_features_mean[feature]
            # add each of the test datapoints to the mean dict with a fake test toon.
            unknown_features = feature_df.iloc[n_games_known : (n_games_known + n_sample_games)]
            for idx, row in unknown_features.iterrows():
                fake_toon = "FakeTestToonRace645734545"  # random-ish number.. why not.
                add_name_to_toon_dict(program_path, fake_toon, name="FakeName39343466762346346")
                row["toon"] = fake_toon
                temp_player_mean_features.loc[fake_toon] = row.loc[
                    [f for f in row.index if f in temp_player_mean_features.columns]
                ]
                # now use this temporary fake data to find nearest neighbour of the fake one.
                (
                    return_list,
                    player_mean_features_with_sq,
                    nearest_toon_race,
                    nearest_non_barcode_toon_race,
                ) = find_nearest_neighbour(program_path, temp_player_mean_features, fake_toon, to_visualize=False)
                if nearest_non_barcode_toon_race == toon_race:
                    n_correct += 1
                else:
                    n_incorrect += 1
                # TODO: also calculate goal_distances and root_sq dist for histogram plots
                goal_distances.append(player_mean_features_with_sq.at[toon_race, "sq_dist"])
                closest_sq_distances.append(player_mean_features_with_sq.iloc[1]["sq_dist"])

    acc = n_correct / (n_correct + n_incorrect)
    return acc, (n_correct + n_incorrect)
