import json


def _codelist_helper(filename: str) -> (list[tuple[str, str]], dict[str, str]):
    """Helper to load a codelist JSON file and generate a choice list and lookup

    Parameters
    ----------
    filename : str
        JSON codelist filename.

    Returns
    -------
    list[tuple[str,str]]
        Choice list for use in forms.
    dict[str, str]
        Lookup mapping codes to names.
    """

    choice_list = [("", "--")]
    lookup = {}
    if filename is not None:
        with open(filename, "r") as fh:
            data = json.load(fh)

            choice_list += [(x["code"], x["name"]) for x in data.get("data", [])]
            choice_list.sort(key=lambda x: x[1])

            lookup = {x["code"]: x["name"] for x in data.get("data", [])}

    return choice_list, lookup
