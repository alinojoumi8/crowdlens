from app.services.simulation_config_generator import SimulationConfigGenerator, SimulationParameters
from app.services.simulation_manager import SimulationManager, SimulationStatus


class FakeGraphStorage:
    def get_all_nodes(self, graph_id):
        return [
            {
                "uuid": "company-1",
                "name": "Acme Robotics",
                "labels": ["Entity", "Company"],
                "summary": "Delivery robot company running a Toronto pilot.",
                "attributes": {},
            }
        ]

    def get_all_edges(self, graph_id):
        return []


def test_prepare_simulation_accepts_prediction_settings_without_profile_generator_error(tmp_path, monkeypatch):
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path))
    # Config generation is mocked; do not depend on a developer .env credential.
    monkeypatch.setattr("app.services.simulation_config_generator.Config.LLM_API_KEY", "unit-test-key")

    def fake_generate_config(self, **kwargs):
        return SimulationParameters(
            simulation_id=kwargs["simulation_id"],
            project_id=kwargs["project_id"],
            graph_id=kwargs["graph_id"],
            simulation_requirement=kwargs["simulation_requirement"],
        )

    monkeypatch.setattr(SimulationConfigGenerator, "generate_config", fake_generate_config)

    manager = SimulationManager()
    state = manager.create_simulation(
        project_id="project-1",
        graph_id="graph-1",
        prediction_settings={"agent_count": 1, "profile_parallelism": 1},
    )

    prepared = manager.prepare_simulation(
        state.simulation_id,
        simulation_requirement="Predict reaction to delivery robots.",
        document_text="Acme Robotics is piloting delivery robots in Toronto.",
        use_llm_for_profiles=False,
        storage=FakeGraphStorage(),
        prediction_settings={"agent_count": 1, "profile_parallelism": 1},
    )

    assert prepared.status == SimulationStatus.READY
    assert prepared.profiles_count == 1
    assert (tmp_path / state.simulation_id / "reddit_profiles.json").exists()
    assert (tmp_path / state.simulation_id / "simulation_config.json").exists()


def test_template_profile_generation_needs_no_llm_credentials(monkeypatch):
    from app.services.entity_reader import EntityNode
    from app.services.oasis_profile_generator import OasisProfileGenerator
    monkeypatch.setattr("app.services.oasis_profile_generator.Config.LLM_API_KEY", None)
    generator = OasisProfileGenerator()
    entity = EntityNode(uuid="entity-1", name="Acme", labels=["Entity", "Company"], summary="A company", attributes={})
    profile = generator.generate_profile_from_entity(entity, user_id=1, use_llm=False)
    assert profile.name == "Acme"


def test_legal_preparation_persists_both_party_types_under_cap(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(SimulationManager, 'SIMULATION_DATA_DIR', str(tmp_path))
    monkeypatch.setattr('app.services.simulation_config_generator.Config.LLM_API_KEY', 'unit-test-key')
    monkeypatch.setattr(SimulationConfigGenerator, 'generate_config', lambda self, **kw:
        SimulationParameters(simulation_id=kw['simulation_id'], project_id=kw['project_id'],
                             graph_id=kw['graph_id'], simulation_requirement=kw['simulation_requirement']))
    class PairedGraph(FakeGraphStorage):
        def get_all_nodes(self, graph_id):
            return [{'uuid': str(i), 'name': f'Entity {i}', 'labels': ['Entity', kind],
                     'summary': 'Synthetic participant.', 'attributes': {}}
                    for i, kind in enumerate(['Company'] * 8 + ['Defendant', 'Plaintiff'])]
    manager = SimulationManager()
    state = manager.create_simulation(project_id='project', graph_id='graph',
        prediction_settings={'agent_count': 2, 'report_mode': 'legal_case'})
    prepared = manager.prepare_simulation(state.simulation_id, simulation_requirement='Compare both parties.',
        document_text='Synthetic paired notices.', use_llm_for_profiles=False, storage=PairedGraph())
    expected = {'Plaintiff': 1, 'Defendant': 1}
    assert prepared.status == SimulationStatus.READY
    assert prepared.participant_selection['selected_by_type'] == expected
    folder = tmp_path / state.simulation_id
    config = json.loads((folder / 'simulation_config.json').read_text())
    assert config['participant_selection']['selected_by_type'] == expected
    profiles = json.loads((folder / 'reddit_profiles.json').read_text())
    assert len(profiles) == 2
    reloaded = SimulationManager().get_simulation(state.simulation_id)
    assert reloaded.participant_selection == prepared.participant_selection
