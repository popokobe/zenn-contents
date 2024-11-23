import requests
import json
from datetime import datetime

AWS_IP_RANGES_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"
MARKDOWN_FILE_PATH = '../articles/aws-ipaddresses-services.md'
AWS_START_MARKER = '<!-- AWS_SERVICES_LIST_START -->'
AWS_END_MARKER = '<!-- AWS_SERVICES_LIST_END -->'
DATE_START_MARKER = '<!-- LAST_CHECK_DATE_START -->'
DATE_END_MARKER = '<!-- LAST_CHECK_DATE_END -->'


def main():
    """
    Main function to update AWS services and execution time in a markdown file

    Raises
    ------
    Exception
        If any error occurs during execution.
    """
    try:
        fetched_aws_services = fetch_aws_services_from_url(AWS_IP_RANGES_URL)

        print("Starting update")
        update_last_check_datetime_in_markdown(
            MARKDOWN_FILE_PATH, DATE_START_MARKER, DATE_END_MARKER)
        update_aws_services_in_markdown(
            MARKDOWN_FILE_PATH, AWS_START_MARKER, AWS_END_MARKER, fetched_aws_services)

    except Exception as e:
        print(f"An error occurred: {e}")


def fetch_aws_services_from_url(url):
    """
    Fetches the list of AWS services from a specified URL that provides AWS IP address ranges.

    Parameters
    ----------
    url : str
        The URL to fetch the AWS IP address ranges from.

    Returns
    -------
    list
        A sorted list of AWS services

    Raises
    ------
    ConnectionError
        If there is an error connecting to the URL.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = json.loads(response.text)

        fetched_aws_services = set()

        for prefix in data['prefixes']:
            fetched_aws_services.add(prefix['service'])

        fetched_aws_services = sorted(fetched_aws_services)

    except requests.RequestException as e:
        raise ConnectionError(f"Failed to retrieve data from URL: {e}")

    return fetched_aws_services


def update_last_check_datetime_in_markdown(file_path, start_marker, end_marker):
    """
    Updates the last check date and time in the markdown file.

    Parameters
    ----------
    file_path : str
        The path to the markdown file to update.
    start_marker : str
        The marker that indicates the start of the date in the file.
    end_marker : str
        The marker that indicates the end of the date in the file.
    """
    current_time = datetime.now().strftime("%Y/%m/%d %H:%M")

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    start_index = content.find(start_marker) + len(start_marker)
    end_index = content.find(end_marker)

    if start_index == -1 or end_index == -1:
        raise ValueError("Date markers not found in the file")

    new_content = content[:start_index] + " " + \
        current_time + " " + content[end_index:]

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    print(f"Updated the last check date to {current_time}.")


def update_aws_services_in_markdown(file_path, start_marker, end_marker, aws_services):
    """
    Replaces the existing AWS services list in a markdown file with a new list.

    Parameters
    ----------
    file_path : str
        The path to the markdown file to update.
    start_marker : str
        The marker that indicates the start of the list in the file.
    end_marker : str
        The marker that indicates the end of the list in the file.
    aws_services : list
        A sorted list of AWS services to insert into the file.

    Raises
    ------
    ValueError
        If the start or end markers are not found in the file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    start_index = content.find(start_marker) + len(start_marker)
    end_index = content.find(end_marker)

    if start_index == -1 or end_index == -1:
        raise ValueError("Markers not found in the file")

    replacement_text = "\n" + "```\n" + \
        "\n".join(aws_services) + "\n" + "```\n"
    new_content = content[:start_index] + \
        replacement_text + content[end_index:]

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    print(f"Updated the AWS services list in {file_path}.")


if __name__ == "__main__":
    main()
