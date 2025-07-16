import argparse
import ast
import logging
import os
import sys
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Removes unused import statements from Python code to reduce code clutter and improve readability."
    )
    parser.add_argument("filepath", help="Path to the Python file to be processed.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without modifying the file.",
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Aggressively remove imports, even if they might be used indirectly (use with caution).",
    )
    return parser

def find_unused_imports(filepath, aggressive=False):
    """
    Finds unused import statements in a Python file.

    Args:
        filepath (str): The path to the Python file.
        aggressive (bool):  Aggressively remove imports, even if they might be used indirectly.

    Returns:
        tuple: A tuple containing:
            - A list of tuples, where each tuple represents an unused import statement
              in the form (line_number, import_statement_string).
            - The parsed AST of the Python file.
    """
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return [], None
    except IOError as e:
        logging.error(f"Error reading file: {filepath} - {e}")
        return [], None

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logging.error(f"Syntax error in file: {filepath} - {e}")
        return [], None

    all_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            all_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Handle attributes like obj.attribute
            name = ""
            current_node = node
            while isinstance(current_node, ast.Attribute):
                name = "." + current_node.attr + name
                current_node = current_node.value

            if isinstance(current_node, ast.Name):
                name = current_node.id + name
                all_names.add(name)

    unused_imports = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                imported_name = alias.asname or alias.name
                if imported_name not in all_names:
                    lineno = node.lineno
                    end_col_offset = node.end_col_offset
                    start_col_offset = node.col_offset
                    
                    import_statement = content[content.rfind('\n', 0, node.lineno -1) + 1:content.find('\n', node.lineno -1)] if node.lineno > 1 else content[:content.find('\n', node.lineno -1)]
                    unused_imports.append((lineno, import_statement))
    return unused_imports, tree

def remove_unused_imports(filepath, unused_imports, dry_run=False):
    """
    Removes the specified unused import statements from the Python file.

    Args:
        filepath (str): The path to the Python file.
        unused_imports (list): A list of tuples, where each tuple represents an unused
            import statement in the form (line_number, import_statement_string).
        dry_run (bool): If True, perform a dry run without modifying the file.
    """
    if not unused_imports:
        logging.info("No unused imports found.")
        return

    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except IOError as e:
        logging.error(f"Error reading file: {filepath} - {e}")
        return

    lines_to_remove = set()
    for line_number, import_statement in unused_imports:
        lines_to_remove.add(line_number)

    new_lines = [
        line for i, line in enumerate(lines, 1) if i not in lines_to_remove
    ]

    if dry_run:
        logging.info("Dry run: The following import statements would be removed:")
        for line_number, import_statement in unused_imports:
            logging.info(f"Line {line_number}: {import_statement.strip()}")
    else:
        try:
            with open(filepath, "w") as f:
                f.writelines(new_lines)
            logging.info(f"Removed unused imports from {filepath}")
            for line_number, import_statement in unused_imports:
                logging.info(f"Removed: Line {line_number}: {import_statement.strip()}")


        except IOError as e:
            logging.error(f"Error writing to file: {filepath} - {e}")
            

def main():
    """
    Main function to execute the unused import removal process.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    filepath = args.filepath
    dry_run = args.dry_run
    aggressive = args.aggressive

    # Input Validation
    if not os.path.exists(filepath):
        logging.error(f"Error: File '{filepath}' does not exist.")
        sys.exit(1)

    if not filepath.endswith(".py"):
        logging.warning(f"Warning: File '{filepath}' does not have a '.py' extension. Proceeding anyway.")
    
    try:
        unused_imports, _ = find_unused_imports(filepath, aggressive)
        remove_unused_imports(filepath, unused_imports, dry_run)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.error(traceback.format_exc()) # Log the full traceback for debugging
        sys.exit(1)


if __name__ == "__main__":
    main()