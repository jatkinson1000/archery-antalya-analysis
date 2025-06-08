"""General routines used in processing antalya data."""

import pandas as pd


def read_from_files(
    flist: list[str],
    datapath="./data/",
    fname_fmt=".csv",
    f_pref="",
    f_suff="Scores",
) -> pd.DataFrame:
    """
    Read in data from csv files generated from ianseo results into a single dataset.

    Parameters
    ----------
    flist : list[str]
        list of strings of filenames to be read in. " " will be replaced by "_"
    datapath : str
        location of the data files
    fname_fmt : str
        file extension to apply to the data files
    f_pref : str
        prefix to be applied to the filenames
    f_suff : str
        suffix to be applied to the filenames

    Returns
    -------
    pd.DataFrame
        A pandas dataframe of the combined results read from file
    """
    li_df = []
    fields = ["Division", "Class", "Score", "10", "9", "Category Rank"]
    for f_id in flist:
        dataset = pd.read_csv(
            f"{datapath}{f_pref}{f_id.replace(' ', '_')}{f_suff}{fname_fmt}",
            usecols=fields,
        )
        # Drop any zero/DNS scores as cause issues with analysis.
        dataset = dataset.drop(dataset[dataset.Score == 0].index)
        dataset["Event"] = f_id
        li_df.append(dataset)
    # Combine all events into a single dataset
    df_comb = pd.concat(li_df, axis=0, ignore_index=True)

    return df_comb
