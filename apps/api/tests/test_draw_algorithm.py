"""Tests del algoritmo de sorteo, sin base de datos. Los de propiedades usan Hypothesis:
generan cientos de grupos y exclusiones al azar y comprueban que las reglas se cumplen siempre."""

import itertools
import time
from random import Random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.draw import DrawImpossible, close_gap, draw_assignments


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


# --- baja después del sorteo (close_gap) ---------------------------------------------------


@settings(max_examples=300, deadline=None)
@given(groups(min_size=4, max_size=12), st.data())
def test_close_gap_keeps_a_valid_draw_without_the_leaving_person(group, data) -> None:
    people, exclusions, seed = group
    try:
        gives_to = draw_assignments(people, exclusions, Random(seed))
    except DrawImpossible:
        return
    leaving = data.draw(st.sampled_from(sorted(people)))
    rest = {p: n for p, n in people.items() if p != leaving}

    try:
        result = close_gap(gives_to, leaving, exclusions, Random(seed))
    except DrawImpossible:
        return  # puede no haber forma tocando solo dos parejas: lo comprueba el test siguiente

    assert_valid(rest, exclusions, result)
    # Como mucho cambian dos personas que ya estaban: quien regalaba al que se va y otra.
    changed = [g for g in result if gives_to[g] != result[g]]
    assert len(changed) <= 2


@settings(max_examples=300, deadline=None)
@given(groups(min_size=4, max_size=12), st.data())
def test_close_gap_without_exclusions_always_works(group, data) -> None:
    people, _, seed = group
    gives_to = draw_assignments(people, set(), Random(seed))
    leaving = data.draw(st.sampled_from(sorted(people)))

    result = close_gap(gives_to, leaving, set(), Random(seed))

    assert_valid({p: n for p, n in people.items() if p != leaving}, set(), result)


def test_close_gap_joins_the_two_ends_when_possible() -> None:
    gives_to = {"ana": "xavi", "xavi": "luis", "luis": "pepe", "pepe": "ana"}

    result = close_gap(gives_to, "ana", set(), Random(0))

    assert result == {"xavi": "luis", "luis": "pepe", "pepe": "xavi"}


def test_close_gap_when_the_leaving_person_was_a_pair_of_two() -> None:
    # Ana y Xavi se regalaban entre sí: Xavi se queda sin destinatario y sin quien le regale.
    gives_to = {"ana": "xavi", "xavi": "ana", "luis": "pepe", "pepe": "marta", "marta": "luis"}

    result = close_gap(gives_to, "ana", set(), Random(0))

    rest = {p: p for p in ["xavi", "luis", "pepe", "marta"]}
    assert_valid(rest, set(), result)


def test_close_gap_needs_three_people_left() -> None:
    gives_to = {"ana": "luis", "luis": "pepe", "pepe": "ana"}

    with pytest.raises(DrawImpossible):
        close_gap(gives_to, "ana", set(), Random(0))
