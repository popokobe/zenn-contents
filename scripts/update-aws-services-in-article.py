import requests
import json
import os

AWS_IP_RANGES_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"
MARKDOWN_FILE_PATH = '../articles/aws-ipaddresses-services.md'
START_MARKER = '<!-- AWS_SERVICES_LIST_START -->'
END_MARKER = '<!-- AWS_SERVICES_LIST_END -->'


def main():
    """
    Main function to compare the current list of AWS services in a markdown file 
    with a freshly fetched list. If the lists differ, updates the markdown file.

    Raises
    ------
    Exception
        If any error occurs during execution.
    """
    try:
        current_aws_services = extract_aws_services_from_markdown(
            MARKDOWN_FILE_PATH, START_MARKER, END_MARKER
        )
        fetched_aws_services = fetch_aws_services_from_url(AWS_IP_RANGES_URL)

        if current_aws_services != fetched_aws_services:
            print("Starting update as the content differs.")
            update_aws_services_in_markdown(
                MARKDOWN_FILE_PATH, START_MARKER, END_MARKER, fetched_aws_services)

            # Set the environment variable for GitHub Actions
            with open(os.environ['GITHUB_ENV'], 'a') as github_env:
                github_env.write("UPDATE_REQUIRED=true\n")
        else:
            print("No update needed as the content is the same.")

            # Set the environment variable for GitHub Actions when error occured
            with open(os.environ['GITHUB_ENV'], 'a') as github_env:
                github_env.write("ERROR_OCCURRED=true\n")

    except Exception as e:
        print(f"An error occurred: {e}")


def extract_aws_services_from_markdown(file_path, start_marker, end_marker):
    """
    Extracts the list of AWS services from a specified range in a markdown file.

    Parameters
    ----------
    file_path : str
        The path to the markdown file containing AWS services.
    start_marker : str
        The marker that indicates the start of the list in the file.
    end_marker : str
        The marker that indicates the end of the list in the file.

    Returns
    -------
    list
        A sorted list of AWS services extracted from the markdown file.

    Raises
    ------
    FileNotFoundError
        If the markdown file does not exist.
    ValueError
        If the start or end markers are not found in the file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"The specified file was not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    start_index = content.find(start_marker) + len(start_marker)
    end_index = content.find(end_marker)

    if start_index == -1 or end_index == -1:
        raise ValueError("Markers not found in the file")

    lines = content[start_index:end_index].strip().splitlines()
    return sorted(set(lines[1:-1])) if len(lines) > 2 else set()


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
