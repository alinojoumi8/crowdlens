"""Vector search must return a graph's own neighbours even when other graphs rank higher."""
from app.storage.search_service import SearchService


class Embedding:
    def embed(self, text):
        return [1.0, 0.0]


class SharedIndexSession:
    """One vector index shared by all graphs, best score first, as Neo4j provides it."""

    def __init__(self, rows):
        self.rows = rows
        self.vector_queries = 0

    def run(self, query, **params):
        if 'db.index.vector' not in query:
            return []
        self.vector_queries += 1
        key = 'r' if 'queryRelationships' in query else 'n'
        scanned = self.rows[:params['candidates']]
        hits = [{key: row, 'score': row['rank']} for row in scanned if row['graph_id'] == params['graph_id']]
        return [{'scanned': len(scanned), 'hits': hits[:params['limit']]}]


def shared_index(other=500, own=30):
    rows = [{'uuid': f'other-{i}', 'graph_id': 'other', 'rank': 1.0 - i / 1000} for i in range(other)]
    rows += [{'uuid': f'own-{i}', 'graph_id': 'mine', 'rank': 0.4 - i / 1000} for i in range(own)]
    return SharedIndexSession(rows)


def test_edge_search_finds_own_graph_behind_other_graphs():
    session = shared_index()

    results = SearchService(Embedding()).search_edges(session, 'mine', 'question', limit=10)

    assert [row['uuid'] for row in results] == [f'own-{i}' for i in range(10)]


def test_node_search_finds_own_graph_behind_other_graphs():
    session = shared_index()

    results = SearchService(Embedding()).search_nodes(session, 'mine', 'question', limit=10)

    assert [row['uuid'] for row in results] == [f'own-{i}' for i in range(10)]


def test_search_stops_when_the_index_is_exhausted():
    session = shared_index(other=5, own=3)

    results = SearchService(Embedding()).search_edges(session, 'mine', 'question', limit=10)

    assert [row['uuid'] for row in results] == ['own-0', 'own-1', 'own-2']
    assert session.vector_queries == 2


def test_a_short_answer_from_the_approximate_index_does_not_end_the_search():
    session = shared_index()
    complete = session.rows
    # The index returns only 30 rows for the first, narrow request.
    original = session.run
    def run(query, **params):
        session.rows = complete[:30] if params.get('candidates') == 40 else complete
        return original(query, **params)
    session.run = run

    results = SearchService(Embedding()).search_edges(session, 'mine', 'question', limit=10)

    assert [row['uuid'] for row in results] == [f'own-{i}' for i in range(10)]
