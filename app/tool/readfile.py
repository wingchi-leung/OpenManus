import os
from typing import Union, List

from app.config import config
from app.tool import BaseTool
from app.logger import logger
import fitz  # PyMuPDF


class ReadFileTool(BaseTool):
    name: str = "ReadFile"
    description: str = """read local file,use this if you want to read a file or check out directory,
    after reading the file, it's might be splited into chunk for smaller size,you can use `readchunk` to checkout all the chunk
    you must provide an absoulte file path for the tool the navigate  
    """
    max_chunk_size: int = 10000
    chunk_overlap: int = 100
    base_path: str = config.workspace_root
    chunk_state :dict = {
        'loaded_chunks': None,
        'current_chunk_index': 0,
    }
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "(required) The commands to run. Allowed options are: `listfile`, `readfile`",
                "enum": ["listfile", "readfile", "readchunk"],
                "type": "string"
            },
            "file_path": {
                "type": "string",
                "description": "(required) absoulte file path or directory",
            },
        }
    }



    def _validate_directory_path(self, dir_path: str) -> Union[str, None]:
        """
        Resolves the directory path relative to base_path and checks safety and type.

        Args:
            dir_path (str): The relative or absolute directory path provided.

        Returns:
            str: The absolute, normalized, and validated directory path if safe and valid.
            None: If the path is outside base_path, doesn't exist, or isn't a directory.
        """
        try:
            # Resolve path similar to how _is_path_safe does for files

            absolute_path = os.path.normpath(dir_path)


            # Security Check: Ensure the resolved path is within the base_path
            # if not absolute_path.startswith(self.base_path):
            #     logger.warning(
            #         f"Access denied: Directory path '{absolute_path}' is outside the allowed base directory '{self.base_path}'.")
            #     return None

            # Check if it exists
            if not os.path.exists(absolute_path):
                logger.warning(f"Directory path not found: '{absolute_path}'")
                return None

            # Check if it's actually a directory
            if not os.path.isdir(absolute_path):
                logger.warning(f"Path is not a directory: '{absolute_path}'")
                return None

            return absolute_path
        except Exception as e:
            logger.error(f"Error resolving or validating directory path '{dir_path}': {e}")
            return None

    def list_files(self, dir_path: str) -> List[str]:
        """
        Lists the names of files (not directories) directly within the specified directory.

        Args:
            dir_path (str): The path to the directory (relative to the workspace
                            or absolute but within the workspace) to list files from.

        Returns:
            Union[List[str], str]: A list of filenames found directly in the
                                   directory on success, or a string containing
                                   an error message on failure.
        """
        validated_dir_path = self._validate_directory_path(dir_path)
        if not validated_dir_path:
            # Error message generated within _validate_directory_path or from its logic flow
            return [f"Error: Invalid or unsafe directory path provided: '{dir_path}'."]

        try:
            logger.info(f"Listing files in directory: '{validated_dir_path}'")
            items_in_dir = os.listdir(validated_dir_path)
            file_list = []
            for item_name in items_in_dir:
                item_full_path = os.path.join(validated_dir_path, item_name)
                if os.path.isfile(item_full_path):
                    file_list.append(item_name)  # Append only the filename

            logger.info(f"Found {len(file_list)} file(s) in '{validated_dir_path}'.")
            return file_list

        except PermissionError:
            error_msg = [f"Error: Permission denied when trying to list files in '{validated_dir_path}'."]

            return error_msg
        except Exception as e:
            error_msg =[f"An unexpected error occurred while listing files in '{validated_dir_path}': {e}"]

            return error_msg

    def _read_text_file(self, file_path: str) -> str:
        """Reads content from a plain text file (like .md, .py)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try a fallback encoding if UTF-8 fails
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    logger.warning(f"Decoded '{file_path}' using latin-1 fallback.")
                    return f.read()
            except Exception as e:
                raise IOError(f"Could not decode file '{file_path}' with UTF-8 or latin-1: {e}")
        except Exception as e:
            raise IOError(f"Error reading text file '{file_path}': {e}")

    def _read_pdf_file(self, file_path: str) -> str:
        """Extracts text content from a PDF file."""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text("text") + "\n"  # Add newline between pages
            doc.close()
            return text
        except Exception as e:
            raise IOError(f"Error reading PDF file '{file_path}': {e}")

        # Inside AdvancedFileReaderTool class...

    def _chunk_content(self, content: str) -> List[str]:
        """Splits the content into raw text chunks based on max_chunk_size and overlap."""
        if not content:
            return []
        if len(content) <= self.max_chunk_size:
            return [content]

        chunks = []
        start_index = 0
        content_len = len(content)

        while start_index < content_len:
            end_index = min(start_index + self.max_chunk_size, content_len)
            chunk = content[start_index:end_index]
            chunks.append(chunk)

            if end_index == content_len:
                break

            start_index = max(start_index + 1, end_index - self.chunk_overlap)
            # No need for >= content_len check here as the while condition handles it

        return chunks  # Return raw chunks

    def read_and_chunk(self, file_path: str) ->   str:

        try:
            file_path = os.path.normpath(file_path)

            _, extension = os.path.splitext(file_path)
            extension = extension.lower()
            content = ""
            if extension in ['.md', '.py', '.txt', '.json', '.yaml', '.yml', '.html', '.css', '.js', '.ts', '.java',
                             '.c', '.cpp', '.h', '.hpp', '.sh']:
                content = self._read_text_file(file_path)
            elif extension == '.pdf':
                content = self._read_pdf_file(file_path)
            else:
                # ... (处理不支持的文件类型) ...
                logger.warning(
                    f"Unsupported file extension '{extension}' for file '{file_path}'. Attempting to read as text.")
                try:
                    content = self._read_text_file(file_path)
                except Exception:
                    return f"Error: Unsupported file type '{extension}' and could not read as text: '{file_path}'."

            if not isinstance(content, str):
                return "Error: Internal issue reading file content."

            logger.info(f"Successfully read {len(content)} characters from '{file_path}'. Now chunking...")
            raw_chunks = self._chunk_content(content)  # Get raw chunks
            logger.info(f"Content split into {len(raw_chunks)} chunk(s).")

            # Add headers/footers with filename context here
            final_chunks = []
            for i, chunk_text in enumerate(raw_chunks):
                final_chunks.append(chunk_text)
            self.chunk_state['loaded_chunks'] = final_chunks
            return f"Successfully readfrom from {file_path}, content is split into {len(final_chunks)} due tosize. the fist of chunk is {final_chunks[0]}. you can call `readchunk` command to read the rest content"

        except IOError as e:
            error_msg = [f"Error processing file '{file_path}': {e}"]
            return error_msg
        except Exception as e:
            error_msg = [f"An unexpected error occurred while processing file '{file_path}': {e}"]
            return error_msg


    def read_next_chunk(self, file_path: str):
        chunk_state = self.chunk_state
        if chunk_state is None:
            error_msg = "Error: chunk state is not available to the GetNextChunkTool."
            return error_msg
        loaded_chunks = chunk_state.get("loaded_chunks")
        current_chunk_index = chunk_state.get('current_chunk_index', 0)
        if not loaded_chunks or not isinstance(loaded_chunks, list):
            message = "No file chunks are currently loaded. Use 'AdvancedFileReaderTool' first to read and chunk a file."
            return message
        next_chunk_index = current_chunk_index + 1
        if 0 <= next_chunk_index < len(loaded_chunks):
            # There is a next chunk
            next_chunk_content = loaded_chunks[next_chunk_index]

            # Update the state for the *next* call
            chunk_state['current_chunk_index'] = next_chunk_index
            logger.info(f"Returning chunk {next_chunk_index + 1}/{len(loaded_chunks)}.")

            # The chunk content already contains headers/footers from AdvancedFileReaderTool
            return next_chunk_content
        else:
            # No more chunks available
            message = "No more chunks available for the previously loaded file."
            logger.info(message)

            # Clean up state (optional but good practice)
            if 'loaded_chunks' in chunk_state:
                del chunk_state['loaded_chunks']
            if 'current_chunk_index' in chunk_state:
                del chunk_state['current_chunk_index']

            return message




    async def execute(self, file_path: str, command: str, **kwargs) -> List[str]:
        """
       Reads a file, extracts text content based on its type, and splits
       it into manageable chunks.

       Args:
           command:
           file_path (str): The relative or absolute path to the file to read.

       Returns:
           Union[List[str], str]: A list of text chunks if successful, or a
                                  single string containing an error message.
        """
        if command == "readfile":
            return self.read_and_chunk(file_path)
        if command == "listfile":
            return self.list_files(file_path)
        if command == "readchunk":
            return self.read_next_chunk(file_path)
        else:
            return ["command is not recognized."]

