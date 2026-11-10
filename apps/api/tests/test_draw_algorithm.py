"""Tests del algoritmo de sorteo, sin base de datos. Los de propiedades usan Hypothesis:
generan cientos de grupos y exclusiones al azar y comprueban que las reglas se cumplen siempre."""

import itertools
import time
from random import Random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.draw import DrawImpossible, draw_assignments


def names(n: int) -> dict[str, str]:
    return {f"p{i}": f"Persona {i}" for i in range(n)}


@st.composite
def groups(draw, min_size: int = 3, max_size: int = 15):
    """Un grupo de personas, un conjunto cualquiera de exclusiones y una semilla."""
    people = names(draw(st.integers(min_size, max_size)))
    pairs = [frozenset(pair) for pair in itertools.combinations(people, 2)]
    # Se decide pareja por pareja si está excluida: así salen también grupos con muchas
    # exclusiones, que son los que obligan al algoritmo a deshacer pasos.
    excluded = draw(st.lists(st.booleans(), min_size=len(pairs), max_size=len(pairs)))
    exclusions = {pair for pair, is_excluded in zip(pairs, excluded, strict=True) if is_excluded}
    seed = draw(st.integers(0, 2**32))
    return people, exclusions, seed


def assert_valid(people: dict[str, str], exclusions: set[frozenset[str]], result: dict) -> None:
    assert set(result) == set(people)  # todos regalan
    assert set(result.values()) == set(people)  # todos reciben (con lo anterior: biyección)
    for giver, receiver in result.items():
        assert giver != receiver
        assert frozenset((giver, receiver)) not in exclusions


def solution_exists(people: dict[str, str], exclusions: set[frozenset[str]]) -> bool:
    """Fuerza bruta: prueba todas las permutaciones. Solo vale para grupos pequeños."""
    ids = list(people)
    return any(
        all(g != r and frozenset((g, r)) not in exclusions for g, r in zip(ids, perm, strict=True))
        for perm in itertools.permutations(ids)
    )


@given(groups())
@settings(max_examples=300)
def test_result_follows_the_rules(group) -> None:
    people, exclusions, seed = group
    try:
        result = draw_assignments(people, exclusions, Random(seed))
    except DrawImpossible:
        return  # que solo falle cuando es imposible lo comprueba el test siguiente
    assert_valid(people, exclusions, result)


@given(groups(max_size=7))
@settings(max_examples=300)
def test_finds_a_solution_if_and_only_if_one_exists(group) -> None:
    people, exclusions, seed = group
    try:
        draw_assignments(people, exclusions, Random(seed))
        found = True
    except DrawImpossible:
        found = False
    assert found == solution_exists(people, exclusions)


def test_error_names_who_cannot_give_to_anyone() -> None:
    people = {"ana": "Ana", "luis": "Luis", "marta": "Marta", "pablo": "Pablo"}
    exclusions = {frozenset(("ana", other)) for other in ("luis", "marta", "pablo")}

    with pytest.raises(DrawImpossible, match="Ana no puede regalar a nadie"):
        draw_assignments(people, exclusions, Random(0))


def test_impossible_without_anyone_isolated() -> None:
    # Ana y Luis no pueden tocarse: los dos tendrían que regalar a Marta.
    people = {"ana": "Ana", "luis": "Luis", "marta": "Marta"}
    exclusions = {frozenset(("ana", "luis"))}

    with pytest.raises(DrawImpossible, match="no hay ningún reparto posible"):
        draw_assignments(people, exclusions, Random(0))


def test_backtracks_when_a_first_choice_leads_nowhere() -> None:
    # Hay solución, pero con algunas semillas la primera elección deja a alguien sin opciones
    # y hay que deshacerla. Un algoritmo voraz (sin deshacer) falla aquí con la semilla 0.
    people = names(5)
    exclusions = {frozenset(("p0", "p2")), frozenset(("p1", "p2")), frozenset(("p3", "p4"))}

    for seed in range(30):
        assert_valid(people, exclusions, draw_assignments(people, exclusions, Random(seed)))


def test_different_seeds_give_different_results() -> None:
    # Con 3 personas hay exactamente 2 repartos válidos (los dos ciclos); deben salir ambos.
    people = names(3)
    results = {
        tuple(sorted(draw_assignments(people, set(), Random(seed)).items())) for seed in range(50)
    }
    assert len(results) == 2


def test_fifty_people_is_fast() -> None:
    people = names(50)
    rng = Random(1)
    pairs = [frozenset(pair) for pair in itertools.combinations(people, 2)]
    exclusions = set(rng.sample(pairs, 25))

    start = time.perf_counter()
    result = draw_assignments(people, exclusions, rng)

    assert time.perf_counter() - start < 1
    assert_valid(people, exclusions, result)
