import os
from app.tool import BaseTool
from git import Repo
from app.config import config


class GitOperator(BaseTool):

    work_path :str = config.workspace_root
    name: str = "gitoperator"
    description: str = """Interact with GitHub/GitLab website. Use this if you want to download git repositories from GitHub repositories URL.
    you must provide a url for the tool.
    """
    parameters: dict = {
        "type": "object",
        "required": ["url","name"],
        "properties": {
            "url": {
                "type": "string",
                "description": "(required) the url to download github from",
            }

        },
    }

    async def execute(self, url: str,   branch = "main", local_path =work_path, **kwargs) -> str :
        """interactor whit git repository"""
        try:
            path = local_path / url.split("/")[-1]
            if os.path.exists(path):
                Repo(path).remotes.origin.pull()
            else:
                Repo.clone_from(url, path, branch=branch)
        except Exception as e :
            return f"Error Downloading Git Repository: {str(e)}"
        return f"successfully download repo {url}  in localpath {path}"
