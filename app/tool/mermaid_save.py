import os
from app.tool import BaseTool
import logging # Optional: for better logging within the tool

# Configure logging if you haven't already at the app level
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MermaidDiagramSaver(BaseTool):
    """
    A tool specifically designed to save Mermaid diagram code into a file.
    """

    # --- Tool Configuration ---
    name: str = "mermaid_diagram_saver"
    description: str = """Saves the provided Mermaid diagram code to the specified file.
Use this tool when you have generated Mermaid syntax and need to persist it to a file system location.
You must provide the full absolute path for the destination file and the Mermaid code itself.
"""
    parameters: dict = {
        "type": "object",
        "required": ["filename", "mermaid_code"], # Both parameters are mandatory
        "properties": {
            "filename": {
                "type": "string",
                "description": "(required) The absolute path (including filename and extension) where the Mermaid diagram file should be saved.",
            },
            "mermaid_code": {
                "type": "string",
                "description": "(required) The string containing the complete and valid Mermaid diagram syntax generated previously.",
            }
        },
    }

    # No default work_path needed unless you want a fallback,
    # but the requirement is an absolute path input.

    async def execute(self, filename: str, mermaid_code: str, **kwargs) -> str :
        """
        Executes the file saving operation for the Mermaid diagram.

        Args:
            filename (str): The absolute path to save the file to.
            mermaid_code (str): The Mermaid code content.
            **kwargs: Catches any unexpected extra arguments passed by the framework.

        Returns:
            str: A message indicating success or failure.
        """
        if not filename or not isinstance(filename, str):
            return "Error: 'filename' parameter is missing or invalid."
        if not isinstance(mermaid_code, str):
             return "Error: 'mermaid_code' parameter must be a string."
        try:
            filename = os.path.normpath(filename)
            dir_path = os.path.dirname(filename)

            if dir_path and not os.path.exists(dir_path):
                if not os.path.isabs(filename):
                     return f"Error: 'filename' must be an absolute path, received: {filename}"

                logging.info(f"Directory '{dir_path}' does not exist. Creating it.")
                os.makedirs(dir_path, exist_ok=True) # exist_ok=True prevents error if dir exists race condition

            file_exists = os.path.exists(filename)
            file_mode = 'a' if file_exists else 'w'
            with open(filename, file_mode, encoding='utf-8') as f:
                if file_mode == 'a' and os.path.getsize(filename) > 0:
                    f.write("\n\n")
                f.write(mermaid_code)

            success_message = f"Successfully saved Mermaid diagram to: {filename}"
            return success_message

        except OSError as e:
            error_message = f"Error saving Mermaid diagram to {filename}. OS Error: {e}"
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred while saving Mermaid diagram to {filename}: {str(e)}"
            return error_message

