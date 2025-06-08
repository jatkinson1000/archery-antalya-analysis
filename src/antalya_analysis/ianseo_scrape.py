"""General routines used to extract data from ianseo."""

from io import StringIO
from itertools import product

import pandas as pd
import requests
from bs4 import BeautifulSoup


def get_cat(
    url_main: str,
    url_suffix: str,
    div: str,
    gen: str,
) -> pd.DataFrame:
    """
    Fetch data from an ianseo link - handles new and old table formats.

    Parameters
    ----------
    url_main : str
        the main competition url to pull data from
    url_suffix : str
        suffix to apply to the competition url to get to specific results page
    div : str
        division (bowstyle) suffix to apply to get specific results
    gen : str
        gender suffix to apply to get specific results

    Returns
    -------
    pd.DataFrame
        A pandas DataFrame generated from the html table read from the ianseo webpage
    """
    # Old IANSEO Table layout
    try:
        page = requests.get(f"{url_main}/{url_suffix}", timeout=20)
        soup = BeautifulSoup(page.text, "lxml")
        table1 = soup.find("table", {"class": "Griglia"})

        table = pd.read_html(StringIO(str(table1)))[0]

    # New IANSEO Table layout
    except ImportError:
        page = requests.get(f"{url_main}/{url_suffix}", timeout=20)
        soup = BeautifulSoup(page.text, "lxml")
        table = table_to_2d(soup.find("table"))

        # Remove excess headers/rows without useful data
        del table[0]
        del table[2::3]
        del table[2::2]

        table = pd.DataFrame(table[1:], columns=table[0])

    # Add columns relevant for our usage
    table["Event"] = f"{div}{gen}"
    table["Division"] = div
    table["Class"] = gen
    table = table.rename(columns={"Tot.": "Score", "Pos.": "Category Rank"})
    table = table.rename(columns={"Rank": "Category Rank"})

    # Remove disqualified athletes (messes up pandas import and no effect on analysis)
    table[table["Score"] == "DSQ"] = 0

    return table


def table_to_2d(table_tag):
    """
    Take 'new' stye ianseo table html and process to remove empty cells.

    Parameters
    ----------
    table_tag : str
        string of html table returned by soup.find()

    Returns
    -------
    list[str]
        the html table from beautiful soup processed to remove columns
    """
    # Credit: Martijn Pieters
    # https://stackoverflow.com/questions/48393253/how-to-parse-table-with-rowspan-and-colspan
    rowspans = []  # track pending rowspans
    rows = table_tag.find_all("tr")

    # first scan, see how many columns we need
    colcount = 0
    for r, row in enumerate(rows):
        cells = row.find_all(["td", "th"], recursive=False)
        # count columns (including spanned).
        # add active rowspans from preceding rows
        # we *ignore* the colspan value on the last cell, to prevent
        # creating 'phantom' columns with no actual cells, only extended
        # colspans. This is achieved by hardcoding the last cell width as 1.
        # a colspan of 0 means “fill until the end” but can really only apply
        # to the last cell; ignore it elsewhere.
        colcount = max(
            colcount,
            sum(int(c.get("colspan", 1)) or 1 for c in cells[:-1])
            + len(cells[-1:])
            + len(rowspans),
        )
        # update rowspan bookkeeping; 0 is a span to the bottom.
        rowspans += [int(c.get("rowspan", 1)) or len(rows) - r for c in cells]
        rowspans = [s - 1 for s in rowspans if s > 1]

    # It doesn't matter if there are still rowspan numbers 'active'; no extra
    # rows to show in the table means the larger than 1 rowspan numbers in the
    # last table row are ignored.

    # build an empty matrix for all possible cells
    table = [[None] * colcount for row in rows]

    # fill matrix from row data
    rowspans = {}  # track pending rowspans, column number mapping to count
    for row, row_elem in enumerate(rows):
        span_offset = 0  # how many columns are skipped due to row and colspans
        for col, cell in enumerate(row_elem.find_all(["td", "th"], recursive=False)):
            # adjust for preceding row and colspans
            col += span_offset  # noqa: PLW2901 intetionally skip columns in loop
            while rowspans.get(col, 0):
                span_offset += 1
                col += 1  # noqa: PLW2901 intetionally skip columns in loop

            # fill table data
            rowspan = rowspans[col] = int(cell.get("rowspan", 1)) or len(rows) - row
            colspan = int(cell.get("colspan", 1)) or colcount - col
            # next column is offset by the colspan
            span_offset += colspan - 1
            value = cell.get_text()
            for drow, dcol in product(range(rowspan), range(colspan)):
                try:
                    table[row + drow][col + dcol] = value
                    rowspans[col + dcol] = rowspan
                except IndexError:
                    # rowspan or colspan outside the confines of the table
                    pass

        # update rowspan bookkeeping
        rowspans = {c: s - 1 for c, s in rowspans.items() if s > 1}

    return table
