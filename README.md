![The knife edge close up lifting a curled shaving from the vellum, the scraped area ahead of it smooth and blank and the faded manuscript strokes soft behind](intro-banner.png)

> Common name first: credential sanitizer. Latin where honest: the starling is Sturnus vulgaris. A field guide entry, Baloo Tammudu 2 in hive wood on a sky plate, with a murmuration drawn once as a header plate under this block.

# cma-credential-sanitizer

![One cream vellum sheet straight on, its upper half scraped smooth and completely blank and its lower half carrying only blurred ink strokes that form no letters, a scraping knife with a wooden handle resting across the boundary between them, the heading plate](logo.png)

![A binder's bench with vellum sheets at different stages of scraping laid along it, a scraper lifting curled shavings from one sheet, a pumice stone and a water bowl beside it and finished blank sheets stacked at the bench end](banner.png)

![A field at dusk in three depths: a distant scatter drifts across the far sky, the main murmuration ribbon turns between a wide ribbon and a tighter knot above the hedgerow, and grass heads sway at the near edge](scene.svg)

# cma-Credential-Sanitizer
Removes secrets from command history files (bash, zsh, powershell) and Jupyter Notebooks. Identifies and redacts API keys, passwords, and other credentials using regular expressions. In Jupyter Notebooks it redacts code cell sources, markdown cell sources, and code cell outputs. No backup is written by default. With `--backup` it writes a timestamped .bak copy of each original file first, with owner only permissions (0600): that backup contains the removed secrets in clear text and must be handled as credential material. Passing `--directory` without `--filetype jupyter` is rejected with exit 1, because the directory search only applies to notebooks. Uses `os` for file system access, `re` for regex, and `shutil` for backups when `--backup` is given.


![A major divider](sep-heavy.svg)

## Install

> Hedgerow notice board: Unhyphenated Name in the Source. The clone line above reads ShadowGuardAI with no hyphen, the wrong organisation name. It is preserved verbatim and flagged here rather than corrected silently. This repository lives under ShadowGuard-AI.
`git clone https://github.com/ShadowGuardAI/cma-credential-sanitizer`


![A major divider](sep-heavy.svg)

## Usage

> Hedgerow notice board: the usage line above is a placeholder and runs nothing. The true run lines are given in the flagged plate at the end of this document.
`./cma-credential-sanitizer [params]`


![A major divider](sep-heavy.svg)

## Parameters

> Hedgerow notice board: Directory Means Notebooks Only. Passing --directory without --filetype jupyter is rejected with exit 1, because the directory search only applies to notebooks.
- `-h`: Show help message and exit
- `--filetype`: No description provided
- `--filepath`: The specific file path to sanitize.  Overrides --filetype if provided.
- `--directory`: No description provided
- `--all`: No description provided
- `--regex_file`: No description provided
- `--backup`: Write a timestamped .bak copy of each original file before sanitizing, with owner only permissions (0600). Off by default. A backup contains the removed secrets in clear text and must be handled as credential material.


![A major divider](sep-heavy.svg)

## License

> Hedgerow notice board: Unhyphenated Name in the Source. The licence line above reads Copyright (c) ShadowGuardAI, the same unhyphenated wrong name, while the LICENSE file itself carries the MIT License.
Copyright (c) ShadowGuardAI

![A major divider](sep-heavy.svg)

## Flagged completion from the parser and the code

The entries in this section come from the argument parser and the code in main.py. They are added here in their own flagged plate, never blended into the preserved list above. Every example value here is a plainly fictional placeholder.

- The worked examples preserved in the code, retargeted to the repository's real entry point main.py and labelled as retargeted, are: `python3 main.py -t bash`, `python3 main.py -f /path/to/my/file.txt`, `python3 main.py -a`, `python3 main.py -t jupyter -d /path/to/notebooks`, and `python3 main.py -t bash -r custom_regexes.txt`.
- `-t`, `--filetype` chooses the type of file to sanitize, with choices bash, zsh, powershell, and jupyter.
- `-f`, `--filepath` gives the specific file path to sanitize and overrides --filetype if provided.
- `-d`, `--directory` gives the directory to recursively search for Jupyter Notebooks, and only applies when --filetype is jupyter.
- `-a`, `--all` sanitizes all supported file types, with notebooks searched recursively in the current directory.
- `-r`, `--regex_file` gives the path to a file containing custom regular expressions, one per line.
- Default places looked: bash history at ~/.bash_history, zsh history at ~/.zsh_history, PowerShell history at ~/Documents/WindowsPowerShell/PSReadLine/ConsoleHost_history.txt, and notebooks found by recursive search for .ipynb files.
- The built in patterns match assignments for api_key, password, secret, and access_token, and bearer tokens following the word bearer. Only the captured value is replaced, with the word REDACTED, while the key name stays and any quotes around the value stay. One worked line, a fictional placeholder and nothing else: a line reading api_key = "fictional-example-value" comes back reading api_key = "REDACTED". A pattern with no capture group has its whole match replaced instead.
- For notebooks, cell sources keep their shape, whether one string or a list of lines, and code cell outputs are redacted in their text, in their data values, and in their tracebacks.
- With no action flag at all, the tool prints its help and exits with code 1. A --filepath run that fails exits with code 1, while an --all run does not check the per file results, so a missing history file in that mode is logged inside the run and then covered by a closing line saying sanitization is complete.
- Every file is rewritten whether anything matched or not, and reading drops bytes that are not valid UTF-8, so a history file with damaged or foreign encoding comes back normalised and silently shorter.
- Sanitizing a live history file races the shell that is still appending to it, and the caller should close that session first.
- A sanitized notebook is reserialised at indent 1 whatever its original formatting was, so a diff of the result shows a whole file rewrite and cannot show what was actually redacted.
- A backup holds the removed secrets in clear text and is credential material.
