import os
import re
import shutil
import argparse
import logging
import datetime
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define regular expressions for common credentials
CREDENTIAL_REGEXES = [
    re.compile(r"(?i)api_key\s*=\s*['\"]?([a-zA-Z0-9_-]+)['\"]?"),
    re.compile(r"(?i)password\s*=\s*['\"]?([a-zA-Z0-9!@#$%^&*()_+=-]+)['\"]?"),
    re.compile(r"(?i)secret\s*=\s*['\"]?([a-zA-Z0-9_-]+)['\"]?"),
    re.compile(r"(?i)access_token\s*=\s*['\"]?([a-zA-Z0-9_-]+)['\"]?"),
    re.compile(r"(?i)bearer\s*([a-zA-Z0-9._-]+)") #added bearer token detection
    # Add more regex patterns as needed
]

# Define file types to sanitize
FILE_TYPES = {
    "bash": "~/.bash_history",
    "zsh": "~/.zsh_history",
    "powershell": "~/Documents/WindowsPowerShell/PSReadLine/ConsoleHost_history.txt",
    "jupyter": ".ipynb"  # Will search recursively for .ipynb files
}


def _redact_text(content):
    """Replace the captured credential value in each match with REDACTED.

    The first version of this substituted the whole match back in with
    the word REDACTED appended, so "api_key=abc123" came out as
    "api_key=abc123REDACTED": the file was marked sanitized and the
    secret was still in it, readable by anyone. Only group 1, the value,
    is replaced; the key name stays so the line still shows what was
    there. A pattern with no capture group (possible in a custom regex
    file) has its whole match replaced instead.
    """
    def _replace(match):
        if match.lastindex:
            # Keep what surrounds the value (an opening quote before it,
            # a closing quote after it) so the line stays well formed.
            start = match.start(1) - match.start(0)
            end = match.end(1) - match.start(0)
            return match.group(0)[:start] + "REDACTED" + match.group(0)[end:]
        return "REDACTED"

    for regex in CREDENTIAL_REGEXES:
        content = regex.sub(_replace, content)
    return content


def _make_backup(filepath):
    """Write a timestamped backup, owner read and write only (0600).

    A backup holds the original content, so it holds every removed
    secret in clear. It is credential material and is logged as such.
    """
    backup_filepath = filepath + "." + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".bak"
    shutil.copy2(filepath, backup_filepath)  # copy2 preserves metadata
    os.chmod(backup_filepath, 0o600)
    logging.warning(f"Backup written to: {backup_filepath}. This backup contains the removed secrets in clear text and must be handled as credential material.")
    return backup_filepath


def sanitize_file(filepath, backup=False):
    """
    Sanitizes a file by removing credentials matching the defined regular expressions.

    Args:
        filepath (str): The path to the file to sanitize.
        backup (bool): Write a timestamped .bak copy of the original
            first. Off by default, because the backup holds the removed
            secrets in clear.

    Returns:
        bool: True if the file was successfully sanitized, False otherwise.
    """
    try:
        if backup:
            _make_backup(filepath)

        # Read the file content
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        sanitized_content = _redact_text(content)
        # Write the sanitized content back to the file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sanitized_content)

        logging.info(f"Successfully sanitized file: {filepath}")
        return True

    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return False
    except Exception as e:
        logging.error(f"An error occurred while sanitizing file {filepath}: {e}")
        return False


def _redact_text_field(value):
    """Redact a notebook text field, keeping its string or list shape."""
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        joined = "".join(item for item in value if isinstance(item, str))
        return _redact_text(joined).splitlines(keepends=True)
    return value


def sanitize_jupyter_notebook(filepath, backup=False):
    """
    Sanitizes a Jupyter Notebook file by removing credentials from code
    and markdown cell sources and from code cell outputs.

    Args:
        filepath (str): The path to the Jupyter Notebook file.
        backup (bool): Write a timestamped .bak copy of the original
            first. Off by default, because the backup holds the removed
            secrets in clear.

    Returns:
        bool: True if the file was successfully sanitized, False otherwise.
    """
    try:
        import json  # Import here to avoid dependency if not using Jupyter functionality

        if backup:
            _make_backup(filepath)

        # Read the JSON content of the Jupyter Notebook
        with open(filepath, "r", encoding="utf-8") as f:
            notebook_data = json.load(f)

        # Iterate through the cells and sanitize code and markdown
        # cell sources, plus code cell outputs. Outputs and markdown
        # used to be skipped, so a secret pasted into a printed result
        # or a note survived a run that logged success.
        for cell in notebook_data["cells"]:
            if cell["cell_type"] in ("code", "markdown"):
                source = cell.get("source", "")
                # A notebook cell source is either one string or a list
                # of lines depending on the notebook's age; both shapes
                # go through the same redaction and keep their shape.
                if isinstance(source, (list, str)):
                    cell["source"] = _redact_text_field(source)
                else:
                    logging.warning(f"Unexpected format for cell source: {type(source)}")
            if cell["cell_type"] == "code":
                for output in cell.get("outputs", []):
                    if "text" in output:
                        output["text"] = _redact_text_field(output["text"])
                    if isinstance(output.get("data"), dict):
                        for mime, data_value in output["data"].items():
                            output["data"][mime] = _redact_text_field(data_value)
                    if isinstance(output.get("traceback"), list):
                        output["traceback"] = [_redact_text(line) for line in output["traceback"]]


        # Write the sanitized content back to the file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(notebook_data, f, indent=1)  # indent for readability

        logging.info(f"Successfully sanitized Jupyter Notebook: {filepath}")
        return True

    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return False
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON in {filepath}: {e}")
        return False
    except ImportError:
        logging.error("The 'json' module is required to sanitize Jupyter Notebooks.  Please install it (e.g., 'pip install json').")
        return False
    except Exception as e:
        logging.error(f"An error occurred while sanitizing Jupyter Notebook {filepath}: {e}")
        return False


def find_and_sanitize_jupyter_notebooks(directory, backup=False):
    """
    Recursively finds and sanitizes Jupyter Notebook files within a directory.

    Args:
        directory (str): The directory to search in.
        backup (bool): Passed through to each notebook sanitize.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".ipynb"):
                filepath = os.path.join(root, file)
                sanitize_jupyter_notebook(filepath, backup=backup)


def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(description="cma-Credential-Sanitizer: Removes secrets from command history files and Jupyter Notebooks.")
    parser.add_argument(
        "--filetype",
        "-t",
        choices=FILE_TYPES.keys(),
        help="The type of file to sanitize (bash, zsh, powershell, jupyter).",
    )
    parser.add_argument(
        "--filepath",
        "-f",
        help="The specific file path to sanitize.  Overrides --filetype if provided.",
    )
    parser.add_argument(
        "--directory",
        "-d",
        help="The directory to recursively search for Jupyter Notebooks (.ipynb files).  Only applies when --filetype is jupyter.",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Sanitize all supported file types (bash, zsh, powershell, Jupyter). Jupyter Notebooks will be searched recursively in the current directory.",
    )
    parser.add_argument(
        "--regex_file",
        "-r",
        help="Path to a file containing custom regular expressions (one per line).",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Write a timestamped .bak copy of each original file before sanitizing, with owner only permissions (0600). Off by default. A backup contains the removed secrets in clear text and must be handled as credential material.",
    )

    return parser


def main():
    """
    The main function of the script.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    global CREDENTIAL_REGEXES

    # Load custom regexes from file if provided
    if args.regex_file:
        try:
            with open(args.regex_file, "r") as f:
                custom_regexes = [re.compile(line.strip()) for line in f if line.strip()]
                CREDENTIAL_REGEXES.extend(custom_regexes)
            logging.info(f"Loaded {len(custom_regexes)} custom regexes from {args.regex_file}")
        except FileNotFoundError:
            logging.error(f"Regex file not found: {args.regex_file}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error reading regex file {args.regex_file}: {e}")
            sys.exit(1)

    # Input validation:  Make sure at least one action is specified
    if not any([args.filetype, args.filepath, args.directory, args.all]):
        parser.print_help()
        sys.exit(1)

    # -d only searches for Jupyter notebooks. Without -t jupyter it
    # used to fall through every branch, do nothing, and exit 0.
    if args.directory and args.filetype != "jupyter":
        logging.error("--directory (-d) requires --filetype jupyter (-t jupyter): no file type was given, so nothing was sanitized.")
        sys.exit(1)

    if args.filepath:
        # A missing or unreadable target is a failed run. Exiting 0 here
        # let cleanup scripts report success over files never touched.
        if sanitize_file(args.filepath, backup=args.backup):
            logging.info("Sanitization complete.")
            sys.exit(0)
        logging.error("Sanitization failed.")
        sys.exit(1)

    if args.filetype == "jupyter" and args.directory:
      find_and_sanitize_jupyter_notebooks(args.directory, backup=args.backup)
      sys.exit(0)


    if args.filetype:
        # Sanitize based on file type
        if args.filetype == "jupyter":
            if args.directory:
                find_and_sanitize_jupyter_notebooks(args.directory, backup=args.backup)
            else:
                find_and_sanitize_jupyter_notebooks(os.getcwd(), backup=args.backup) # Default to current directory
        else:
            filepath = os.path.expanduser(FILE_TYPES[args.filetype])
            if sanitize_file(filepath, backup=args.backup):
                logging.info("Sanitization complete.")
            else:
                logging.error("Sanitization failed.")
                sys.exit(1)
    elif args.all:
        # Sanitize all supported file types
        for filetype, filepath in FILE_TYPES.items():
            if filetype == "jupyter":
                find_and_sanitize_jupyter_notebooks(os.getcwd(), backup=args.backup) # Default to current directory for Jupyter
            else:
                filepath = os.path.expanduser(filepath)
                sanitize_file(filepath, backup=args.backup)
        logging.info("Sanitization complete for all supported file types.")

    # Example usages (these won't actually execute in the script, but serve as documentation)
    r"""
    Example Usages:

    1. Sanitize bash history:
       python cma-Credential-Sanitizer.py -t bash

    2. Sanitize a specific file:
       python cma-Credential-Sanitizer.py -f /path/to/my/file.txt

    3. Sanitize all supported file types:
       python cma-Credential-Sanitizer.py -a

    4. Recursively sanitize Jupyter Notebooks in a directory:
       python cma-Credential-Sanitizer.py -t jupyter -d /path/to/notebooks

    5. Use a custom regex file:
       python cma-Credential-Sanitizer.py -t bash -r custom_regexes.txt

    custom_regexes.txt (example):
    (?i)database_password\s*=\s*['\"]?([a-zA-Z0-9!@#$%^&*()_+=-]+)['\"]?
    """


if __name__ == "__main__":
    main()