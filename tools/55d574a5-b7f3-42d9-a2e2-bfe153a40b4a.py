```python
import json

def run(inputs: dict) -> dict:
    """
    Formats JSON data to be human-readable by pretty-printing it with indentation and line breaks.

    Args:
        inputs (dict): A dictionary containing the input data.
            Expected key:
            - "json_data" (str): The JSON data string to be pretty-printed.

    Returns:
        dict: A dictionary indicating the success, output, or error.
            - "success" (bool): True if the operation was successful, False otherwise.
            - "output" (str): The pretty-printed JSON string if successful, None otherwise.
            - "error" (str): An error message if the operation failed, empty string otherwise.
    """
    json_data_str = inputs.get("json_data")

    if json_data_str is None:
        return {
            "success": False,
            "output": None,
            "error": "Input 'json_data' is missing. Please provide a JSON string."
        }

    if not isinstance(json_data_str, str):
        return {
            "success": False,
            "output": None,
            "error": f"Input 'json_data' must be a string, but received type {type(json_data_str).__name__}."
        }

    try:
        # Parse the JSON string into a Python object
        parsed_json = json.loads(json_data_str)

        # Pretty-print the Python object back into a JSON string
        # using an indent of 2 spaces for readability
        pretty_json = json.dumps(parsed_json, indent=2)

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
        # Catch any other unexpected errors during processing
        return {
            "success": False,
            "output": None,
            "error": f"An unexpected error occurred: {e}"
        }

if __name__ == '__main__':
    # Example Usage:

    # 1. Valid JSON input
    valid_json_input = {
        "json_data": '{"name": "John Doe", "age": 30, "isStudent": false, "courses": [{"title": "Math", "credits": 3}, {"title": "Science", "credits": 4}], "address": null}'
    }
    print("--- Valid JSON Input ---")
    result = run(valid_json_input)
    print(f"Success: {result['success']}")
    if result['success']:
        print("Pretty-printed JSON:\n", result['output'])
    else:
        print(f"Error: {result['error']}")
    print("\n" + "="*30 + "\n")

    # 2. Invalid JSON input
    invalid_json_input = {
        "json_data": '{"name": "Jane", "age": 25, "city": "New York",}' # Trailing comma makes it invalid
    }
    print("--- Invalid JSON Input ---")
    result = run(invalid_json_input)
    print(f"Success: {result['success']}")
    if result['success']:
        print("Pretty-printed JSON:\n", result['output'])
    else:
        print(f"Error: {result['error']}")
    print("\n" + "="*30 + "\n")

    # 3. Missing 'json_data' key
    missing_key_input = {
        "other_data": "some value"
    }
    print("--- Missing 'json_data' Key ---")
    result = run(missing_key_input)
    print(f"Success: {result['success']}")
    if result['success']:
        print("Pretty-printed JSON:\n", result['output'])
    else:
        print(f"Error: {result['error']}")
    print("\n" + "="*30 + "\n")

    # 4. 'json_data' is not a string
    non_string_input = {
        "json_data": {"key": "value"}
    }
    print("--- 'json_data' is not a string ---")
    result = run(non_string_input)
    print(f"Success: {result['success']}")
    if result['success']:
        print("Pretty-printed JSON:\n", result['output'])
    else:
        print(f"Error: {result['error']}")
    print("\n" + "="*30 + "\n")

    # 5. Empty JSON object
    empty_object_input = {
        "json_data": "{}"
    }
    print("--- Empty JSON Object Input ---")
    result = run(empty_object_input)
    print(f"Success: {result['success']}")
    if result['success']:
        print("Pretty-printed JSON:\n", result['output'])
    else:
        print(f"Error: {result['error']}")
    print("\n" + "="*30 + "\n")

    # 6. Empty JSON array
    empty_array_input = {
        "json_data": "[]"
    }
    print("--- Empty JSON Array Input ---")
    result = run(empty_array_input)
    print(f"Success: {result['success']}")
    if result['success']:
        print("Pretty-printed JSON:\n", result['output'])
    else:
        print(f"Error: {result['error']}")
    print("\n" + "="*30 + "\n")
```