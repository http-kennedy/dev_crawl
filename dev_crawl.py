import argparse
import ast
import astor
import os
import sys
import traceback
from collections import defaultdict
from typing import Dict, Tuple, List

DEBUG_LOG_IDENTIFIER = "--- debug.log generated using dev_crawl.py ---"


class DebugTransformer(ast.NodeTransformer):
    """
    A class to transform Python AST nodes by inserting debugging statements into a script.

    Attributes:
        script_identifier (str): Identifier of the current script being processed.
        modified_scripts (Set[str]): Set of names of scripts being modified.
        function_call_counter (defaultdict[str, int]): Tracks the call count of functions.
        current_function (Optional[str]): Name of the currently processed function, or None.
        debug_to_file (bool): Indicates if debug statements should be written to a file.
        output_file_path (str): Path to the output file for debug statements.
    """

    def __init__(
        self,
        script_identifier: str,
        modified_scripts: set,
        debug_to_file: bool,
        output_file_path: str,
    ):
        """
        Initializes the DebugTransformer.

        Args:
            script_identifier (str): The identifier of the current script.
            modified_scripts (Set[str]): Set of names of scripts being modified.
            debug_to_file (bool): If True, directs debug output to a file.
            output_file_path (str): Path to the output file for debug statements.
        """
        self.script_identifier = script_identifier
        self.modified_scripts = modified_scripts
        self.function_call_counter = defaultdict(int)
        self.current_function = None
        self.debug_to_file = debug_to_file
        self.output_file_path = output_file_path

    def create_debug_statement(self, message: str) -> ast.Expr:
        """
        Creates a debug statement AST node.

        Args:
            message (str): The debug message to be logged.

        Returns:
            ast.Expr: An AST expression representing the debug statement.
        """
        if self.debug_to_file:
            debug_code = f"with open('{self.output_file_path}', 'a') as debug_file: debug_file.write({message} + '\\n')"
        else:
            debug_code = f"print({message})"
        return ast.parse(debug_code).body[0]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """
        Visits a FunctionDef node in the AST and modifies it by inserting a debugging print statement at the beginning.

        Args:
            node (ast.FunctionDef): The function definition node in the AST.

        Returns:
            ast.FunctionDef: The modified function definition node.
        """
        original_function, self.current_function = self.current_function, node.name
        self.function_call_counter[node.name] += 1
        enter_message = f"\"[{self.function_call_counter[node.name]}] Entering '{node.name}' in '{self.script_identifier}'\""
        enter_debug = [self.create_debug_statement(enter_message)]
        node.body = enter_debug + node.body
        self.generic_visit(node)
        self.current_function = original_function
        return node

    def visit_Import(self, node: ast.Import) -> ast.Import:
        """
        Visits an Import node in the AST and modifies it if the imported module
        is one of the scripts being modified. The import will be changed to import
        the '_debug' version of the module.

        Args:
            node (ast.Import): The import node in the AST.

        Returns:
            ast.Import: The potentially modified import node.
        """
        for alias in node.names:
            relative_module_path = alias.name.replace(".", os.sep)

            for modified_script in self.modified_scripts:
                if relative_module_path.endswith(modified_script):
                    alias_name_parts = alias.name.split(".")
                    alias_name_parts[-1] += "_debug"
                    alias.name = ".".join(alias_name_parts)
                    return node
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        """
        Modifies ImportFrom nodes in the AST. If the imported module or any part
        of its path is being modified, the import is changed to import from
        the '_debug' version of the module.

        Args:
            node (ast.ImportFrom): The import-from node in the AST.

        Returns:
            ast.ImportFrom: The potentially modified import-from node.
        """
        if node.module:
            relative_module_path = node.module.replace(".", os.sep)

            for modified_script in self.modified_scripts:
                if relative_module_path.endswith(modified_script):
                    node_module_parts = node.module.split(".")
                    node_module_parts[-1] += "_debug"
                    node.module = ".".join(node_module_parts)
                    return node
        return node

    def visit_Return(self, node: ast.Return) -> ast.Return:
        """
        Visits a Return node in the AST and appends a debugging print statement before the return statement.

        Args:
            node (ast.Return): The return statement node in the AST.

        Returns:
            ast.Return: The modified return statement node with a preceding debugging print statement.
        """
        if self.current_function:
            exit_message = f"\"[{self.function_call_counter[self.current_function] - 1}] Exiting '{self.current_function}' in '{self.script_identifier}'\""
            exit_debug = [self.create_debug_statement(exit_message)]
            return exit_debug + [node]
        return node


def transform_script_ast(
    script_path: str,
    script_identifier: str,
    modified_scripts: set,
    debug_to_file: bool,
    output_file_path: str,
) -> Tuple[str, DebugTransformer]:
    """
    Modifies a Python script's AST by inserting debugging statements.

    Args:
        script_path (str): Path to the Python script to be modified.
        script_identifier (str): A unique identifier for the script, typically its filename.
        modified_scripts (Set[str]): A set containing the names of scripts that are being modified.
        debug_to_file (bool): If True, directs debug output to the specified output file.
        output_file_path (str): The path to the file where debug output should be written.

    Returns:
        Tuple[str, DebugTransformer]: A tuple containing the modified source code as a string
                                    and the DebugTransformer object used for the transformation.
    """
    absolute_output_file_path = generate_file_path(output_file_path)

    with open(script_path, "r") as file:
        script_content = file.read()

    tree = ast.parse(script_content)
    transformer = DebugTransformer(
        script_identifier, modified_scripts, debug_to_file, absolute_output_file_path
    )
    modified_tree = transformer.visit(tree)

    return astor.to_source(modified_tree), transformer


def transform_scripts(
    scripts: List[str], debug_to_file: bool, output_file_path: str
) -> Tuple[Dict[str, str], Dict[str, DebugTransformer]]:
    """
    Modifies multiple Python scripts by adding debugging statements.

    Args:
        scripts (List[str]): A list of paths to Python scripts to be modified.
        debug_to_file (bool): If True, directs debug output to the specified output file.
        output_file_path (str): Path to the output file where debug statements are directed.

    Returns:
        Tuple[Dict[str, str], Dict[str, DebugTransformer]]: A tuple containing two dictionaries.
            - The first dictionary maps original script paths to their modified versions.
            - The second dictionary maps script identifiers to their corresponding DebugTransformer instances.
    """
    modified_scripts = {
        os.path.splitext(os.path.basename(script))[0] for script in scripts
    }
    modified_paths = {}
    transformers = {}

    for script_path in scripts:
        try:
            script_identifier = os.path.basename(script_path)
            modified_content, transformer = transform_script_ast(
                script_path,
                script_identifier,
                modified_scripts,
                debug_to_file,
                output_file_path,
            )
            transformers[script_identifier] = transformer
            new_script_path = os.path.splitext(script_path)[0] + "_debug.py"
            with open(new_script_path, "w", encoding="utf-8") as new_file:
                new_file.write(modified_content)
            modified_paths[script_path] = new_script_path

        except SyntaxError as e:
            print(f"\nError modifying {script_path}: {e}")
            print("\nDetailed stack trace:")
            print(traceback.format_exc())
            print("Suspending script execution.")
            sys.exit(1)

    return modified_paths, transformers


def initialize_debug_log(output_file_path: str = "debug.log") -> None:
    """
    Initializes or resets the debug log file and writes an identifier line to it.

    Args:
        output_file_path (str): Path to the debug log file. Defaults to 'debug.log' in the
                                current directory if no path is provided.

    Returns:
        None: This function does not return anything but performs file operations and prints
            status messages to the terminal.
    """
    absolute_output_file_path = generate_file_path(output_file_path)

    directory_path = os.path.dirname(absolute_output_file_path)
    if validate_directory(directory_path) or directory_path == "":
        with open(absolute_output_file_path, "w") as debug_file:
            debug_file.write(f"{DEBUG_LOG_IDENTIFIER}\n")

        print("\n" + "=" * 30)
        print(f"Debug Log Initialized: {absolute_output_file_path}")
        print("=" * 30 + "\n")
    else:
        print(f"Error: {directory_path} is not a valid directory.")


def is_valid_debug_log(file_path: str) -> bool:
    """
    Validates if the provided file is a debug log generated by this script.

    Args:
        file_path (str): The path to the file that needs to be validated.

    Returns:
        str: An empty string if the file is a valid debug log; otherwise, an error
            message indicating either the file is not a valid debug log or the file
            could not be read.
    """
    try:
        with open(file_path, "r") as file:
            first_line = file.readline().strip()
            if first_line == DEBUG_LOG_IDENTIFIER:
                return ""
            else:
                return (
                    "Error: the file is not a valid debug log generated by this script"
                )
    except IOError:
        return "Error: Unable to read the file. Please check the path and try again."


def confirm_overwrite(file_path: str, non_interactive: bool) -> bool:
    """
    Confirms whether to overwrite an existing file, based on user input or the mode of operation.

    Args:
        file_path (str): The path of the file to be overwritten.
        non_interactive (bool): If True, the function runs in non-interactive mode and
                                automatically prevents overwriting. If False, the user
                                is prompted for confirmation.

    Returns:
        bool: True if the file does not exist, is to be overwritten (as confirmed by the user),
            or the operation is in non-interactive mode. False if the file exists and the user
            chooses not to overwrite it.
    """
    if os.path.exists(file_path) and not non_interactive:
        response = (
            input(f"Warning: {file_path} already exists. Overwrite? (y/N) ")
            .strip()
            .lower()
        )
        return response in ["y", "yes"]
    return True


def validate_directory(directory_path: str) -> bool:
    """
    Validates if the provided path is a directory.

    Args:
        directory_path (str): The path to be validated as a directory.

    Returns:
        bool: True if the specified path is a valid directory, False otherwise.
    """
    return os.path.isdir(directory_path)


def generate_file_path(file_path: str) -> str:
    """
    Generates an absolute file path from a given file path.

    Args:
        file_path (str): The file path to be converted to an absolute path.

    Returns:
        str: The absolute path corresponding to the given file path.
    """
    return os.path.abspath(file_path)


def reformat_and_output_log(log_file_path: str, output_file_path: str) -> None:
    """
    Reformats a debug log file and writes the reformatted content to a specified file and the terminal.

    Args:
        log_file_path (str): The path to the original debug log file to be reformatted.
        output_file_path (str): The path where the reformatted log content should be written.

    Returns:
        None
    """
    with open(log_file_path, "r") as file:
        lines = file.readlines()

    grouped_lines = []
    enter_count = 0

    for line in lines:
        if "Entering" in line or "Exiting" in line:
            if "Entering" in line and enter_count == 0:
                grouped_lines.append("\n>>> Starting group:\n")
            enter_count += ("Entering" in line) - ("Exiting" in line)
            indented_line = "    " * enter_count + line
            grouped_lines.append(indented_line)
            if "Exiting" in line and enter_count == 0:
                grouped_lines.append("<<< Ending group:\n")
        else:
            grouped_lines.append("    " + line)

    grouped_lines.append("\n>>> Script execution completed <<<\n")

    with open(output_file_path, "w") as out_file:
        for line in grouped_lines:
            print(line, end="")
            out_file.write(line)


def output_function_call_summary(
    function_calls: defaultdict, output_file_path: str
) -> None:
    """
    Outputs a summary of function calls to both the terminal and a specified file.

    Args:
        function_calls (defaultdict[int, int]): A dictionary mapping 'Script Name | Function Name' to the count of calls.
        output_file_path (str): The path to the file where the function call summary should be written.

    Returns:
        None
    """
    summary_lines = [
        "\n>>> Function Call Summary <<<\n",
        "------ Legend ------\n",
        "'Script Name | Function Name: Called X times' indicates how many times a function was called.\n",
        "The summary is listed in the order functions were first called.\n",
        "---------------------\n\n",
    ]

    for key, count in function_calls.items():
        summary_line = f"{key}: Called {count} times\n"
        summary_lines.append(summary_line)

    with open(output_file_path, "a") as out_file:
        for line in summary_lines:
            print(line, end="")
            out_file.write(line)


def reformat_and_output_log_md(log_file_path: str, output_file_path: str) -> None:
    """
    Reformats a debug log file into Markdown format and writes it to a specified file.

    Args:
        log_file_path (str): The path to the original debug log file to be reformatted.
        output_file_path (str): The path to the output Markdown file where the reformatted log is written.

    Returns:
        None
    """
    with open(log_file_path, "r") as file:
        lines = file.readlines()

    lines = (
        lines[1:]
        if lines[0].strip() == "--- debug.log generated using dev_crawl.py ---"
        else lines
    )

    function_calls = analyze_function_calls_in_log(log_file_path)
    total_calls = sum(function_calls.values())

    grouped_lines = [
        "# Debug Log <small>-> generated using dev_crawl.py</small>\n\n",
        f"<details><summary>Click to expand the brief summary</summary>\n\n",
        f"- Total function calls: {total_calls}\n",
        f"- Unique functions entered: {len(function_calls)}\n",
        "</details>\n\n",
        "## Execution Flow\n\n",
        "<details>\n",
        "<summary>Click to expand the execution flow details</summary>\n\n",
    ]
    enter_count = 0

    for line in lines:
        if "Entering" in line or "Exiting" in line:
            indent = "    " * enter_count
            action = "Entering" if "Entering" in line else "Exiting"
            function_name = line.split("'")[1]
            script_name = line.split()[-1].strip("'")
            formatted_line = (
                f"{indent}- **{action}** `{function_name}` in `{script_name}`\n"
            )
            grouped_lines.append(formatted_line)
            if "Exiting" in line:
                enter_count -= 1
                if enter_count == 0:
                    grouped_lines.append("\n---\n")
                    grouped_lines.append("\n---\n")
            else:
                enter_count += 1
        else:
            grouped_lines.append(line)

    grouped_lines.append("\n## Script Execution Completed\n\n</details>\n\n")
    grouped_lines.append(
        "## Function Call Summary<small> -> in order of execution</small>\n\n"
    )
    grouped_lines.append("| No. | Script | Function | Calls |\n")
    grouped_lines.append("| --- | ------ | -------- | ----- |\n")

    for i, (key, count) in enumerate(function_calls.items(), start=1):
        script, function = key.split(" | ")
        grouped_lines.append(f"| {i}   | `{script}` | `{function}` | {count} |\n")

    with open(output_file_path, "w") as out_file:
        out_file.writelines(grouped_lines)


def analyze_function_calls_in_log(debug_file_path: str) -> defaultdict:
    """
    Analyzes a debug log file and counts the occurrences of function calls.

    Args:
        debug_file_path (str): The path to the debug log file to be analyzed.

    Returns:
        defaultdict: A dictionary mapping 'script name | function name' to the count of function calls.
    """
    function_calls = defaultdict(int)

    with open(debug_file_path, "r") as file:
        for line in file:
            if "Entering" in line:
                parts = line.split("'")
                if len(parts) >= 4:
                    function_name = parts[1]
                    script_name = parts[3]
                    key = f"{script_name} | {function_name}"
                    function_calls[key] += 1
    return function_calls


def handle_arguments(args) -> bool:
    """
    Validates the provided command-line arguments for mutual exclusivity and necessary conditions.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.

    Returns:
        bool: True if the arguments are valid, False otherwise.
    """
    exclusive_args = [
        bool(args.reformat_log),
        bool(args.reformat_log_md),
        args.debug_to_file,
        args.clear_debug_log is not None,
    ]

    if sum(exclusive_args) > 1:
        print("Error: Only one argument can be specified at a time.")
        print("Use --help for more information.")
        return False

    if (args.debug_to_file or not any(exclusive_args)) and not args.scripts:
        print("Error: No scripts were provided.")
        print("Use --help for more information.")
        return False

    return True


def handle_script_modification(
    scripts: List[str],
    debug_to_file: bool,
    output_file_path: str,
    non_interactive: bool,
) -> None:
    """
    Handles the modification of Python scripts based on the provided arguments.

    Args:
        scripts (List[str]): List of paths to the Python scripts to be modified.
        debug_to_file (bool): Flag indicating if debug output should be directed to a file.
        output_file_path (str): Path for the output debug log file.
        non_interactive (bool): Flag for running the script in non-interactive mode.

    Returns:
        None
    """
    if debug_to_file:
        if not handle_debug_to_file(debug_to_file, output_file_path, non_interactive):
            return
    modified_script_paths, _ = transform_scripts(
        scripts, debug_to_file, output_file_path
    )

    print("\n" + "=" * 30)
    print("Modified Scripts:")
    print("-" * 30)
    for original, modified in modified_script_paths.items():
        print(f"  Original: {original}\n  Modified: {modified}\n")
    print("=" * 30)


def handle_debug_to_file(
    debug_to_file: bool, output_file_path: str, non_interactive: bool
) -> bool:
    """
    Handles the debug log file initialization and output file location when the debug-to-file option is enabled.

    Args:
        debug_to_file (bool): Flag indicating if debug output should be directed to a file.
        output_file_path (str): Path for the output debug log file.
        non_interactive (bool): Flag for running the script in non-interactive mode,
                                which allows overwriting without confirmation.

    Returns:
        bool: True if the debug log file is successfully initialized, False otherwise.
    """
    if debug_to_file:
        absolute_output_file_path = generate_file_path(output_file_path)

        if not confirm_overwrite(absolute_output_file_path, non_interactive):
            if not non_interactive:
                print("\nOperation cancelled by the user.")
            return False

        initialize_debug_log(absolute_output_file_path)
    return True


def handle_reformat_log(log_file_path: str) -> None:
    """
    Handles the reformatting of a debug log file.

    Args:
        log_file_path (str): The path to the debug log file to be reformatted.

    Returns:
        None
    """
    error_message = is_valid_debug_log(log_file_path)

    print("\n" + "=" * 30)
    if not error_message:
        with open(log_file_path, "r") as file:
            lines = file.readlines()

        if all(
            line.isspace() or line.strip() == DEBUG_LOG_IDENTIFIER for line in lines
        ):
            print("The debug log is empty. Please run your _debug.py script/s.")
        else:
            reformatted_log_path = generate_file_path(
                os.path.splitext(log_file_path)[0] + "_reformatted.log"
            )
            reformat_and_output_log(log_file_path, reformatted_log_path)
            function_calls = analyze_function_calls_in_log(reformatted_log_path)
            output_function_call_summary(function_calls, reformatted_log_path)
            print("\n" + "=" * 30)
            print(f"Reformatted log has been generated as {reformatted_log_path}")

    else:
        print(error_message)
    print("=" * 30 + "\n")


def handle_reformat_log_md(log_file_path: str) -> None:
    """
    Handles the reformatting of a debug log file into markdown format.

    Args:
        log_file_path (str): The path to the debug log file to be reformatted into markdown.

    Returns:
        None
    """
    error_message = is_valid_debug_log(log_file_path)

    print("\n" + "=" * 30)
    if not error_message:
        with open(log_file_path, "r") as file:
            lines = file.readlines()

        if all(
            line.isspace() or line.strip() == DEBUG_LOG_IDENTIFIER for line in lines
        ):
            print("The debug log is empty. Please run your _debug.py script/s.")
        else:
            markdown_file_path = os.path.abspath(
                os.path.splitext(log_file_path)[0] + ".md"
            )
            reformat_and_output_log_md(log_file_path, markdown_file_path)
            print(f"Markdown formatted log has been generated as {markdown_file_path}")

    else:
        print(error_message)
    print("=" * 30 + "\n")


def handle_clear_debug_log() -> None:
    """
    Clears the default debug log file.

    Returns:
        None
    """
    initialize_debug_log()


def main() -> None:
    """
    The function supports these command line arguments:
    - `scripts`: List of paths to Python scripts to be modified (optional).
    - `--reformat-log`: Path to the debug output file to reformat (optional).
    - `--reformat-log-md`: Path to the debug output file to reformat into markdown (optional).
    - `--debug-to-file`: If set, redirects debug output to a file instead of the terminal (optional).
    - `--output-file`: Specifies the output file path for the debug log (optional).
    - `--clear-debug-log`: Clears the specified debug log file, or creates a new 'debug.log' if no path is provided (optional).
    - `--non-interactive`: Runs the script in non-interactive mode for automated use (optional).

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description="Python script for adding debugging statements to other Python scripts."
    )
    parser.add_argument(
        "scripts", nargs="*", help="Paths to the Python scripts to be modified."
    )
    parser.add_argument(
        "--reformat-log",
        nargs="?",
        const="debug.log",
        default=None,
        help="Path to the debug output file to reformat; defaults to debug.log in the current directory if no path is provided.",
    )
    parser.add_argument(
        "--reformat-log-md",
        nargs="?",
        const="debug.log",
        default=None,
        help="Path to the debug output file to reformat into markdown; defaults to debug.log in the current directory if no path is provided.",
    )
    parser.add_argument(
        "--debug-to-file",
        action="store_true",
        help="Direct debug output to a file instead of the terminal.",
    )
    parser.add_argument(
        "--output-file",
        dest="output_file",
        default="debug.log",
        help="Output file path for the debug log.",
    )
    parser.add_argument(
        "--clear-debug-log",
        nargs="?",
        const="debug.log",
        default=None,
        dest="clear_debug_log",
        help="Clears the specified debug log file or creates a new debug.log in the current directory if no path is provided. ",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run the script in non-interactive mode for automated use. (Will overwrite files without confirmation.)",
    )
    args = parser.parse_args()

    if not handle_arguments(args):
        return

    if args.clear_debug_log is not None:
        initialize_debug_log(args.clear_debug_log)

    if args.reformat_log is not None:
        handle_reformat_log(args.reformat_log)

    if args.reformat_log_md is not None:
        handle_reformat_log_md(args.reformat_log_md)

    if args.scripts:
        handle_script_modification(
            args.scripts, args.debug_to_file, args.output_file, args.non_interactive
        )


if __name__ == "__main__":
    main()
