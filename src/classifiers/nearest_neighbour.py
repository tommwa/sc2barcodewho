import copy

import numpy as np
import pandas as pd

from utils.utils import get_toon_dict, is_barcode, toon_race_to_toon, is_toon_barcode
from features.utils_features import add_name_to_toon_dict
from features.player_dataclass import PlayerData


def mean_feature_classify(config, toon_dict, player_data: PlayerData, features_mean: pd.DataFrame, feature_relevances,
                          to_visualize=True):
    """
    Classifies a barcode by finding the player with mean features closest in L2-space to the barcode's.
    Scales the features to min 0 and max 1.

    Only uses a single game from the barcode given by PlayerData.

    @return: toon_estimate, non_barcode_toon_estimate
    """
    # check that there are at least 2 players with feature mean.
    n_players = len(features_mean)
    if n_players < 2:
        print("You're trying to classify between less than 2 players in the database. Load more replays.")
        return False, False

    # Break apart the barcode's player_data into race / toon / numeric features.
    bc_toon = player_data.features["toon"]
    bc_race = player_data.features["race"]
    bc_toon_race = str((bc_toon, bc_race))
    bc_features = pd.Series(player_data.features)
    bc_features.drop(["toon", "race"], inplace=True)
    bc_features = pd.to_numeric(bc_features)

    # Create results_df, a copy of features_mean that will be scaled and get some columns added to help with the result.
    results_df = copy.copy(features_mean)

    # First scale data to have min 0 and max 1.
    min_feat = features_mean.min()
    max_feat = features_mean.max()
    std = features_mean.std()
    # Also remove any columns with standard deviation 0, should typically not happen, but maybe I will e.g. use a rare feature that is almost always 0.
    results_df = features_mean.loc[:, std != 0]
    min_feat = min_feat.loc[std != 0]
    max_feat = max_feat.loc[std != 0]
    bc_features = bc_features.loc[std != 0]
    std = std[std != 0]
    results_df = (results_df - min_feat) / (max_feat - min_feat)
    # Scale the barcode's player_data with the same scaling factors.
    bc_features = (bc_features - min_feat) / (max_feat - min_feat)
    bc_features.clip(lower=-0.2, upper=1.2, inplace=True)  # Clipping because we never want 1 extreme value of a feature to completely dominate the classification result.

    # Re-scale according to square root of feature relevances to put extra emphasis on the better features.
    feature_relevances_sqrt = np.sqrt(feature_relevances)
    bc_features = bc_features / feature_relevances_sqrt
    results_df = results_df / feature_relevances_sqrt

    # Add the distance to the barcode as a column to the mean df.
    dist = results_df - bc_features
    sq_dist = pd.Series((dist * dist).sum(axis=1), name="sq_dist")
    results_df = pd.concat([results_df, sq_dist], axis=1)

    # Sort the dataframe.
    results_df.sort_values("sq_dist", inplace=True)

    # Get the closest player (could be a barcode).
    results_df["toon"] = results_df.index.map(toon_race_to_toon)
    toon_estimate = results_df.index[0]
    toon_estimate_dist = results_df.iloc[0]["sq_dist"]

    # Remove all barcodes from the df.
    results_df["is_barcode"] = [is_toon_barcode(toon, toon_dict) for toon in results_df["toon"]]
    results_df.drop(results_df[results_df["is_barcode"] == True].index, inplace=True)
    non_barcode_toon_estimate = results_df.index[0]

    # Visualize the top of this df.
    results_df["names"] = results_df["toon"].map(toon_dict)
    if to_visualize:
        print("--------------------")
        print("Simple feature classification result:")
        print(f"closest non-barcode: {toon_dict[toon_race_to_toon(non_barcode_toon_estimate)]}")
        print(f"closest distance INCLUDING other barcodes: {toon_estimate_dist:.6f}")
        print("Table results:")
        print(results_df[["names", "sq_dist"]].head(config["options"]["NEIGHBOURS_TO_PRINT"]))
        print("--------------------")

    # Return both the nearest and non-barcode nearest.
    return toon_estimate, non_barcode_toon_estimate

