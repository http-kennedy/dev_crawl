# dev_crawl.py - Python Debugging Automation Tool

## Introduction
`dev_crawl.py` is a lightweight Python automation tool designed to streamline the debugging process by generating an output of logic flow during _debug script execution. It performs this by injecting debugging statements, managing debug logs, and intelligently handles nested scripts and their imports.

  - **Main use of this tool is to create a visual representation of the logic flow of a python script, including the order in which functions were called and the number of times each function was called.**
  - This can be useful for identifying performance bottlenecks or other issues.

## Key Features
- **Automated Debugging Statement Injection:** Automates the insertion of logic flow statements into Python scripts, extending support to nested and interdependent scripts.
- **Selective Import Modification:** Dynamically modifies import statements in scripts to include their debug-enhanced versions, but only for scripts specified in the same run.
- **Simultaneous Multiple Script Handling:** Efficiently processes multiple scripts in a single run, respecting their dependencies and nesting.
- **Versatile Debug Log Management:** Offers options for terminal output, debug.log output, custom debug log file, and log reformatting for enhanced readability or markdown conversion.

## Requirements
- Python 3.6 or later
- `astor` library

## Installation
Clone the repository from GitHub and install the dependency:

```bash
git clone https://github.com/http-kennedy/dev_crawl
cd dev_crawl
pip install -r requirements.txt
```

## Workflow and Usage
  ```bash
  python dev_crawl.py --h
  ```

### Single and Multiple Script Modification
- **Single Script:**
  ```bash
  python dev_crawl.py script1.py
  ```
- **Multiple Scripts:**
  ```bash
  python dev_crawl.py script1.py script2.py
  ```
- **Hierarchical Dependencies:**
  ```bash
  python dev_crawl.py script1.py script2.py /utils/script3.py
  ```

### Output Options
- **Default (Print to Terminal):**
  - Outputs debug information to the terminal.
  ```bash
  python dev_crawl.py script1.py
  ```
- **Using `--debug-to-file`:**
  - Directs debug outputs to `debug.log` in the current working directory.
  ```bash
  python dev_crawl.py --debug-to-file script1.py
  ```
  - **Custom Log Location with `--output-file`:**
    - Specifies a custom file path for the debug log.
    ```bash
    python dev_crawl.py --debug-to-file --output-file /path/to/custom_log.log script1.py
    ```
  - **Reformatting `debug.log`:**
    - Converts `debug.log` to a readable format.
    ```bash
    python dev_crawl.py --reformat-log /path/to/debug.log
    ```
  - **Markdown Conversion:**
    - Transforms `debug.log` into markdown format.
    ```bash
    python dev_crawl.py --reformat-log-md /path/to/debug.log
    ```

### Overwrite Confirmation and Non-Interactive Mode
  - **Overwrite Confirmation:**
    - Prompts for confirmation before overwriting existing files.
  - **Non-Interactive Mode with `--non-interactive`:**
    - Automatically overwrites existing files without confirmation.
    ```bash
    python dev_crawl.py --non-interactive --debug-to-file --output-file /path/to/debug.log script1.py
    ```

### Resetting `debug.log`
  - **Default Reset:**
    - Re-initializes `debug.log` in the current directory.
    ```bash
    python dev_crawl.py --clear-debug-log
    ```
  - **Custom Log Location**
    - Resets a custom debug log file at the specified path.
    ```bash
    python dev_crawl.py --clear-debug-log /path/to/debug.log
    ```

## Defaults for `debug.log`
  - The following arguments default to current working directory for `debug.log`
  - `--debug-to-file`
  - `--reformat-log`
  - `--reformat-log-md`
  - `--clear-debug-log`

## Screenshots

<details>
  <summary>Basic Debug Log (Click to Expand)</summary>
  <a href="screenshots/debug_log.png">
    <img src="screenshots/debug_log.png" alt="Basic Debug Log" width="500"/>
  </a>
</details>

<details>
  <summary>Basic Markdown Output (Click to Expand)</summary>
  <a href="screenshots/markdown_log_basic.png">
    <img src="screenshots/markdown_log_basic.png" alt="Basic Markdown Output" width="500"/>
  </a>
</details>

<details>
  <summary>Full Markdown View (Click to Expand)</summary>
  <a href="screenshots/markdown_log_full.png">
    <img src="screenshots/markdown_log_full.png" alt="Full Markdown View" width="500"/>
  </a>
</details>

<details>
  <summary>Detailed Execution Flow (Click to Expand)</summary>
  <a href="screenshots/markdown_detailed.png">
    <img src="screenshots/markdown_detailed.png" alt="Full Markdown View" width="500"/>
  </a>
</details>


## Intelligent Import Handling
`dev_crawl.py` intelligently adjusts import statements in scripts to refer to their debug versions, but only when an import name matches the script name passed to dev_crawl.py at the same modification execution. This ensures that debug modifications are applied consistently across interrelated scripts.

## Contributing
I welcome contributions to improve `dev_crawl.py`. Please submit pull requests or open issues for discussion.

## License
`dev_crawl.py` is released under the CC0-1.0 License. Please see the LICENSE file for full license details.

## Contact
For questions or feedback, please open an issue in the GitHub repository.
