import yaml
from typing import Union, Dict, List, Any


class Helper:
    """
    A class for representing a Pydantic model in a plain text format.
    """

    @staticmethod
    def data_to_yaml(data: Union[Dict, List[Any]] = None) -> str:
        if data is None:
            return ""
        return yaml.dump(data, sort_keys=False, default_flow_style=False)
