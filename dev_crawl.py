import argparse
import ast
import astor
import os
from collections import defaultdict
from typing import Dict, Tuple, List

DEBUG_LOG_IDENTIFIER = "--- debug.log generated using dev_crawl.py ---"


class DebugTransformer(ast.NodeTransformer):
    """
    Transforms Python AST nodes to insert debugging statements into a script.

    Attributes:
        script_identifier (str): Identifier of the current script being processed.
        modified_scripts (set): Set of script names that are modified.
        function_call_counter (defaultdict[int, int]): Tracks the call count of functions.
        current_function (str or None): Name of the currently processed function.
        debug_to_file (bool): Flag to indicate if debug statements should be written to a file.
    """

    def __init__(
        self, script_identifier: str, modified_scripts: set, debug_to_file: bool
    ):
        """
        Initializes the DebugTransformer with the script identifier, modified scripts, and debug mode.

        Args:
            script_identifier (str): The identifier of the current script.
            modified_scripts (set): Set of names of scripts being modified.
            debug_to_file (bool): If True, debug statements will be directed to 'debug.log'.
        """
        self.script_identifier = script_identifier
        self.modified_scripts = modified_scripts
        self.function_call_counter = defaultdict(int)
        self.current_function = None
        self.debug_to_file = debug_to_file

    def create_debug_statement(self, message: str) -> ast.Expr:
        """
        Creates a debug statement. If self.debug_to_file is True, it writes to 'debug.log'.
        Otherwise, it simply prints the message.

        Args:
            message (str): The debug message to be logged.

        Returns:
            ast.Expr: An AST expression representing the debug statement.
        """
        if self.debug_to_file:
            debug_code = f"""with open('debug.log', 'a') as debug_file: debug_file.write({message} + '\\n')"""
        else:
            debug_code = f"print({message})"
        return ast.parse(debug_code).body[0]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """
        Visits a FunctionDef (function definition) node in the AST and modifies it
        by inserting a debugging print statement at the beginning.

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
        Visits a Return node in the AST and appends a debugging print statement
        before the return statement. This is used to indicate when the function
        is exiting.

        Args:
            node (ast.Return): The return statement node in the AST.

        Returns:
            ast.Return: The modified return statement node, now preceded by a
            debugging print statement.
        """
        if self.current_function:
            exit_message = f"\"[{self.function_call_counter[self.current_function] - 1}] Exiting '{self.current_function}' in '{self.script_identifier}'\""
            exit_debug = [self.create_debug_statement(exit_message)]
            return exit_debug + [node]
        return node


def transform_script_ast(
    script_path: str, script_identifier: str, modified_scripts: set, debug_to_file: bool
) -> Tuple[str, DebugTransformer]:
    """
    Modifies a Python script in memory using AST.

    Args:
        script_path (str): The path to the script to be modified.
        script_identifier (str): The identifier of the script.
        modified_scripts (set): A set of scripts that are being modified.
        debug_to_file (bool): If True, direct debug output to a file instead of the terminal.

    Returns:
        Tuple[str, DebugTransformer]: The modified source code and the transformer used.
    """
    with open(script_path, "r") as file:
        script_content = file.read()

    tree = ast.parse(script_content)
    transformer = DebugTransformer(script_identifier, modified_scripts, debug_to_file)
    modified_tree = transformer.visit(tree)

    return astor.to_source(modified_tree), transformer


def transform_scripts(
    scripts: List[str], debug_to_file: bool
) -> Tuple[Dict[str, str], Dict[str, DebugTransformer]]:
    """
    Modifies a list of Python scripts by adding debugging statements.

    Args:
        scripts (List[str]): List of paths to the Python scripts to be modified.
        debug_to_file (bool): If True, direct debug output to a file instead of terminal.

    Returns:
        Tuple[Dict[str, str], Dict[str, DebugTransformer]]: Dictionary mapping original script paths to modified script paths, and their associated transformers.
    """
    modified_scripts = {
        os.path.splitext(os.path.basename(script))[0] for script in scripts
    }
    modified_paths = {}
    transformers = {}
    for script_path in scripts:
        script_identifier = os.path.basename(script_path)
        modified_content, transformer = transform_script_ast(
            script_path, script_identifier, modified_scripts, debug_to_file
        )
        transformers[script_identifier] = transformer
        new_script_path = os.path.splitext(script_path)[0] + "_debug.py"
        with open(new_script_path, "w", encoding="utf-8") as new_file:
            new_file.write(modified_content)
        modified_paths[script_path] = new_script_path
    return modified_paths, transformers


def initialize_debug_log() -> None:
    """
    Initializes or clears the debug.log file and adds a unique identifier line to it.

    This function creates a new debug.log file or overwrites the existing one,
    starting it with a unique identifier line to validate its origin.
    """
    with open("debug.log", "w") as debug_file:
        debug_file.write(f"{DEBUG_LOG_IDENTIFIER}\n")
    print("debug.log has been initialized.")


def is_valid_debug_log(file_path: str) -> bool:
    """
    Checks if a debug.log file was generated by this script.

    Args:
        file_path (str): The path to the debug.log file.

    Returns:
        bool: True if the file is a valid debug.log created by this script, False otherwise.
    """
    try:
        with open(file_path, "r") as file:
            first_line = file.readline().strip()
            return first_line == DEBUG_LOG_IDENTIFIER
    except IOError:
        return False


def reformat_and_output_log(log_file_path: str, output_file_path: str) -> None:
    """
    Reformats the debug log file and writes the output to both the terminal and a specified file.

    Args:
        log_file_path (str): The path to the original debug log file.
        output_file_path (str): The path to the output file for the reformatted log.
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
    Prints and writes a summary of function calls to the terminal and a file.

    Args:
        function_calls (defaultdict): A dictionary with counts of function calls.
        output_file_path (str): The path to the output file for writing the summary.
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
    Reformats the debug log file into a markdown format and writes the output to a specified file.

    Args:
        log_file_path (str): The path to the original debug log file.
        output_file_path (str): The path to the output markdown file.
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
    Analyzes the debug output file and counts function calls.

    Args:
        debug_file_path (str): The path to the debug output file.

    Returns:
        defaultdict: A dictionary with counts of function calls.
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


def main() -> None:
    """
    Main function handling script arguments to modify Python scripts, reformat,
    and analyze debug logs, and also reformat logs into markdown format.

    Command Line Arguments:
    - scripts (list of str, optional): Paths to Python scripts to be modified.
    - --reformat-log (str, optional): Path to the debug output file to reformat.
    - --reformat-log-md (str, optional): Path to the debug output file to reformat into markdown.
    - --debug-to-file (bool, optional): If set, directs debug output to 'debug.log'.
    - --clear-debug-log (bool, optional): If set, clears the existing 'debug.log'.
    """
    parser = argparse.ArgumentParser(
        description="Python script for adding debugging statements to other Python scripts."
    )
    parser.add_argument(
        "scripts", nargs="*", help="Paths to the Python scripts to be modified."
    )
    parser.add_argument(
        "--reformat-log",
        dest="log_file",
        help="Path to the debug output file to reformat.",
    )
    parser.add_argument(
        "--reformat-log-md",
        dest="log_file_md",
        help="Path to the debug output file to reformat into markdown.",
    )
    parser.add_argument(
        "--debug-to-file",
        action="store_true",
        help="Direct debug output to a file instead of the terminal.",
    )
    parser.add_argument(
        "--clear-debug-log",
        action="store_true",
        help="Clears the existing debug.log and creates a new one.",
    )
    args = parser.parse_args()

    if not os.path.exists("debug.log"):
        initialize_debug_log()

    if args.clear_debug_log:
        initialize_debug_log()
        return

    if args.log_file:
        if is_valid_debug_log(args.log_file):
            reformatted_log_path = args.log_file
            reformat_and_output_log(args.log_file, reformatted_log_path)
            function_calls = analyze_function_calls_in_log(reformatted_log_path)
            output_function_call_summary(function_calls, reformatted_log_path)
        else:
            print("Error: The specified debug.log file is not valid.")
            return

    if args.log_file_md:
        if is_valid_debug_log(args.log_file_md):
            reformat_and_output_log_md(args.log_file_md, "debug_log.md")
            print("Markdown formatted log has been generated as debug_log.md")
        else:
            print("Error: The specified debug.log file is not valid.")
            return

    if not args.log_file and not args.log_file_md:
        modified_script_paths, _ = transform_scripts(args.scripts, args.debug_to_file)
        print("\nModified scripts:")
        for original, modified in modified_script_paths.items():
            print(f"{original} -> {modified}")


if __name__ == "__main__":
    main()
