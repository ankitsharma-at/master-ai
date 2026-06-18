
import json

def run(inputs: dict) -> dict:
    """
    A tool that pretty-prints JSON data.

    Args:
        inputs (dict): A dictionary containing the following keys:
            - json_data (str): The JSON data string to be formatted.

    Returns:
        dict: A dictionary with the following keys:
            - success (bool): True if the JSON was successfully formatted, False otherwise.
            - output (str or None): The pretty-printed JSON string if successful, None otherwise.
            - error (str or None): An error message if an error occurred, None otherwise.
    """
    if 'json_data' not in inputs:
        return {
            "success": False,
            "output": None,
            "error": "Missing 'json_data' in inputs."
        }

    json_data_str = inputs['json_data']

    if not isinstance(json_data_str, str):
        return {
            "success": False,
            "output": None,
            "error": f"Invalid type for 'json_data'. Expected string, got {type(json_data_str).__name__}."
        }

    try:
        # Parse the JSON string into a Python object
        parsed_json = json.loads(json_data_str)
        
        # Pretty-print the Python object back into a JSON string
        pretty_json = json.dumps(parsed_json, indent=2)
        
        return {
            "success": True,
            "output": pretty_json,
            "error": None
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "output": None,
            "error": f"JSON decoding error: {e}"
        }
    except Exception as e:
        # Catch any other unexpected errors
        return {
            "success": False,
            "output": None,
            "error": f"An unexpected error occurred: {e}"
        }

