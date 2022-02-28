
def remove_none_values_from_dict(original_dict: dict):
    return {k: v for k, v in original_dict.items() if v is not None}


def replace_dict_keys(
    original_dict: dict,
    replacement_dict: dict
) -> dict:
    return {replacement_dict.get(k, k): v for k, v in original_dict.items()}
