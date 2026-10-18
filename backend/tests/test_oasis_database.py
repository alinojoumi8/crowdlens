import asyncio
import importlib.util
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_prompt_reads_its_platform_database_and_restores_context(tmp_path, monkeypatch):
    from oasis.social_agent import agent_environment

    def unwritable_default():
        raise PermissionError('package directory is read-only')

    monkeypatch.setattr(agent_environment, 'get_db_path', unwritable_default)
    spec = importlib.util.spec_from_file_location(
        'oasis_database_under_test', Path(__file__).parents[1] / 'scripts' / 'oasis_database.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async def run():
        prompts = []
        for platform, followers in [('twitter', 7), ('reddit', 19)]:
            path = tmp_path / f'{platform}.db'
            with sqlite3.connect(path) as connection:
                connection.execute('CREATE TABLE user (agent_id, num_followers, num_followings)')
                connection.execute('INSERT INTO user VALUES (0, ?, ?)', (followers, followers + 1))
            env = agent_environment.SocialEnvironment(SimpleNamespace(agent_id=0))
            with pytest.raises(PermissionError):
                await env.get_followers_env()

            async def prompt(env=env):
                await asyncio.sleep(0)
                return await env.get_followers_env(), await env.get_follows_env()

            env.to_text_prompt = prompt
            agent = SimpleNamespace(env=env)
            graph = SimpleNamespace(get_agents=lambda agent=agent: [(0, agent)])
            module.bind_agent_database(graph, path)
            prompts.append(env.to_text_prompt)
        results = await asyncio.gather(*(prompt() for prompt in prompts))
        assert results == [('I have 7 followers.', 'I have 8 follows.'),
                           ('I have 19 followers.', 'I have 20 follows.')]
        with pytest.raises(PermissionError):
            agent_environment.get_db_path()

        async def failing_prompt():
            raise ValueError('prompt failed')

        env = SimpleNamespace(to_text_prompt=failing_prompt)
        module.bind_agent_database(SimpleNamespace(get_agents=lambda: [(0, SimpleNamespace(env=env))]), path)
        with pytest.raises(ValueError, match='prompt failed'):
            await env.to_text_prompt()
        with pytest.raises(PermissionError):
            agent_environment.get_db_path()

    asyncio.run(run())
