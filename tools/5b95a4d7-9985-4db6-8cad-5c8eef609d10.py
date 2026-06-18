
import json

def run(inputs: dict) -> dict:
    """
    A tool that formats JSON data to be human-readable and pretty-printed.

    Args:
        inputs (dict): A dictionary containing the following keys:
            json_data (str): The JSON data string to be formatted.

    Returns:
        dict: A dictionary with the following keys:
            success (bool): True if the operation was successful, False otherwise.
            output (any): The pretty-printed JSON string if successful, None otherwise.
            error (str): An error message if the operation failed, empty string otherwise.
    """
    json_data_string = inputs.get("json_data")

    if not isinstance(json_data_string, str):
        return {
            "success": False,
            "output": None,
            "error": "Input 'json_data' must be a string."
        }
    
    if not json_data_string.strip():
        return {
            "success": False,
            "output": None,
            "error": "Input 'json_data' cannot be empty."
        }

    try:
        # Load the JSON string into a Python object
        json_object = json.loads(json_data_string)

        # Pretty-print the Python object back into a JSON string
        # indent=4 specifies 4 spaces for indentation
        pretty_json = json.dumps(json_object, indent=4)

        return {
            "success": True,
            "output": pretty_json,
            "error": ""
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "output": None,
            "error": f"Invalid JSON data: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": f"An unexpected error occurred: {e}"
        }
