"""Keep OASIS prompt database reads scoped to their agent's platform."""
import os
from contextvars import ContextVar
from functools import wraps

from oasis.social_agent import agent_environment


_database_path = ContextVar('crowdlens_oasis_database_path', default=None)
_default_get_db_path = agent_environment.get_db_path


def _get_db_path():
    path = _database_path.get()
    return path if path is not None else _default_get_db_path()


def _bind_prompt(prompt, database_path):
    @wraps(prompt)
    async def scoped_prompt(*args, **kwargs):
        token = _database_path.set(database_path)
        try:
            return await prompt(*args, **kwargs)
        finally:
            _database_path.reset(token)
    return scoped_prompt


def bind_agent_database(agent_graph, database_path):
    # OASIS's prompt reader imports a global getter instead of using the
    # database passed to oasis.make. Context-local paths also isolate parallel
    # Twitter/Reddit tasks and later interviews without changing process env.
    database_path = os.path.abspath(os.fspath(database_path))
    agent_environment.get_db_path = _get_db_path
    for _, agent in agent_graph.get_agents():
        agent.env.to_text_prompt = _bind_prompt(agent.env.to_text_prompt, database_path)
