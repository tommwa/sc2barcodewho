import pandas as pd
import numpy as np


def scale_df(df):
    """
    scale to make the average value of each column 1. Only suitable when all the features have only positive values.
    Exception is for data with all 0, then it is kept at 0.
    """
    text_data = df.select_dtypes(exclude=[np.number])
    number_data = df.select_dtypes(include=[np.number])
    non_zero_data = number_data.loc[:, np.sum(number_data) != 0]
    zero_data = number_data.loc[:, np.sum(number_data) == 0]
    scaled_number_data = non_zero_data / np.sum(non_zero_data) * len(non_zero_data.index)
    return pd.concat([scaled_number_data, zero_data, text_data], axis=1)
