from os import path
from sys import exit as sys_exit

from environs import Env, EnvError

from core.config import ENV_FILE
from core.logger import logger


class Environment:

    def __init__(self, path_to_env_file: str) -> None:
        if not path.exists(path_to_env_file):
            logger.critical("Env file not found", path_to_env_file)
            sys_exit(1)

        self._env: Env = Env()
        self._env.read_env(path=path_to_env_file, recurse=False)

    def _get_env_var(self, var_name: str) -> str:
        try:
            return self._env.str(var_name)
        except EnvError as exc:
            logger.critical(f"{var_name} not found", repr(exc))
            sys_exit(repr(exc))

    def get_openai_api(self) -> str:
        return self._get_env_var("OPENAI_API_KEY")

    def get_token_or_exit(self) -> str:
        """
        Returns the bot token or terminates the program in case of an error

        :return: bot token
        :rtype: str
        """
        try:
            return str(self._env.str("BOT_TOKEN"))
        except EnvError as exc:
            logger.critical("BOT_TOKEN not found: %s", repr(exc))
            sys_exit(repr(exc))


env: Environment = Environment(path_to_env_file=ENV_FILE)
