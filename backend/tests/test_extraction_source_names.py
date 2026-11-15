import pytest

from app.storage.ner_extractor import NERExtractor


ONTOLOGY = {'entity_types': ['JudicialOfficer', 'Person'], 'edge_types': ['PRESIDES_OVER']}


@pytest.mark.parametrize('reference', ['The Walsh review is discussed.',
    'Use: Walsh — correction of the application record.'])
def test_doctrine_name_and_invented_person_are_not_case_participants(reference):
    class LLM:
        def chat_json(self, **kwargs):
            return {'entities': [
                {'name': 'Walsh', 'type': 'JudicialOfficer'},
                {'name': 'Judge Rowan', 'type': 'JudicialOfficer'},
                {'name': 'Invented Person', 'type': 'Person'}],
                'relations': [{'source': 'Walsh', 'target': 'Judge Rowan', 'type': 'PRESIDES_OVER'}]}
    extractor = NERExtractor(llm_client=LLM())
    result = extractor.extract(reference + ' Judge Rowan signed the order.', ONTOLOGY)
    assert [e['name'] for e in result['entities']] == ['Judge Rowan']
    assert result['relations'] == []  # A relation must not resurrect rejected endpoints.


def test_doctrine_filter_keeps_a_person_explicitly_acting_in_the_source():
    class LLM:
        def chat_json(self, **kwargs):
            return {'entities': [{'name': 'Walsh', 'type': 'JudicialOfficer'}], 'relations': []}
    result = NERExtractor(llm_client=LLM()).extract(
        'The Walsh review was discussed. Justice Walsh signed this order.', ONTOLOGY)
    assert result['entities'][0]['name'] == 'Walsh'


def test_batch_validation_uses_each_chunks_source_and_rejects_unknown_types():
    class LLM:
        def chat_json(self, **kwargs):
            return {'chunks': [
                {'chunk_index': 0, 'entities': [{'name': 'Rowan', 'type': 'Person'},
                    {'name': 'Lane', 'type': 'Person'}], 'relations': []},
                {'chunk_index': 1, 'entities': [{'name': 'Lane', 'type': 'InventedType'}], 'relations': []}]}
    result = NERExtractor(llm_client=LLM()).extract_batch(['Rowan wrote.', 'Lane answered.'], ONTOLOGY)
    assert [e['name'] for e in result[0]['entities']] == ['Rowan']
    assert result[1]['entities'] == []


def test_rejected_type_does_not_hide_a_valid_entity_with_the_same_name():
    class LLM:
        def chat_json(self, **kwargs):
            return {'entities': [{'name': 'Rowan', 'type': 'InventedType'},
                                 {'name': 'Rowan', 'type': 'Person'}], 'relations': []}
    result = NERExtractor(llm_client=LLM()).extract('Rowan wrote the letter.', ONTOLOGY)
    assert result['entities'] == [{'name': 'Rowan', 'type': 'Person', 'attributes': {}}]


def test_names_in_text_without_word_separators_are_found_in_the_source():
    class LLM:
        def chat_json(self, **kwargs):
            return {'entities': [{'name': '张三', 'type': 'Person'}, {'name': '李四', 'type': 'Person'},
                                 {'name': '王五', 'type': 'Person'}], 'relations': []}
    result = NERExtractor(llm_client=LLM()).extract('张三向李四支付了款项。', ONTOLOGY)
    assert [e['name'] for e in result['entities']] == ['张三', '李四']
