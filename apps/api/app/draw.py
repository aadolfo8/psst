"""Sorteo del amigo invisible con exclusiones. Función pura: no sabe nada de la base de datos.

Es un backtracking aleatorizado: se asigna destinatario a una persona cada vez, probando los
candidatos en orden aleatorio, y si alguien se queda sin opciones se deshace el último paso.
Para que casi nunca haga falta deshacer, en cada paso se elige a quien menos opciones libres
le quedan (la heurística de "lo más difícil primero").

Límite honesto: no todos los repartos válidos salen con exactamente la misma probabilidad.
Para un amigo invisible da igual; lo que importa es que nadie pueda predecir el resultado,
y eso lo garantiza el generador aleatorio que se le pasa (SystemRandom en producción).
"""

from collections.abc import Iterable, Mapping
from random import Random

# Tope de pasos para que un caso patológico no deje colgada la petición. Con grupos de hasta
# 50 personas y exclusiones normales se usan unas decenas de pasos.
MAX_STEPS = 100_000

NO_SOLUTION = "no hay ningún reparto posible con estas exclusiones; prueba a quitar alguna"


class DrawImpossible(Exception):
    """No existe (o no se ha encontrado) ningún reparto que cumpla las reglas."""


def draw_assignments[T](
    participants: Mapping[T, str],
    exclusions: Iterable[frozenset[T]],
    rng: Random,
) -> dict[T, T]:
    """Devuelve {quien regala: a quien regala}.

    `participants` va de id a nombre (el nombre solo se usa en los mensajes de error).
    Cada exclusión es un par {a, b}: a no regala a b ni b regala a a.
    """
    excluded = set(exclusions)
    options = {
        giver: [r for r in participants if r != giver and frozenset((giver, r)) not in excluded]
        for giver in participants
    }
    for giver, receivers in options.items():
        if not receivers:
            raise DrawImpossible(
                f"{participants[giver]} no puede regalar a nadie con estas exclusiones"
            )

    # Orden aleatorio de partida: así los empates de la heurística también son aleatorios.
    givers = list(participants)
    rng.shuffle(givers)

    assignment: dict[T, T] = {}
    taken: set[T] = set()
    steps = 0

    def free_options(giver: T) -> list[T]:
        return [r for r in options[giver] if r not in taken]

    def assign_next() -> bool:
        nonlocal steps
        steps += 1
        if steps > MAX_STEPS:
            raise DrawImpossible(NO_SOLUTION)

        pending = [g for g in givers if g not in assignment]
        if not pending:
            return True

        giver = min(pending, key=lambda g: len(free_options(g)))
        candidates = free_options(giver)
        rng.shuffle(candidates)
        for receiver in candidates:
            assignment[giver] = receiver
            taken.add(receiver)
            if assign_next():
                return True
            del assignment[giver]
            taken.remove(receiver)
        return False  # nadie libre para esta persona: el paso anterior tiene que cambiar

    if not assign_next():
        raise DrawImpossible(NO_SOLUTION)
    return assignment


def close_gap[T](
    gives_to: Mapping[T, T],
    leaving: T,
    exclusions: Iterable[frozenset[T]],
    rng: Random,
) -> dict[T, T]:
    """Quita a `leaving` de un sorteo ya hecho tocando lo mínimo. Devuelve el reparto nuevo.

    Al irse Ana quedan dos huecos: quien le regalaba (Pepe) se queda sin destinatario y a
    quien regalaba Ana (Xavi) se queda sin nadie que le regale. Lo normal es cerrarlos
    juntos: Pepe pasa a regalar a Xavi y nadie más cambia.

    Si no se puede (Pepe y Xavi están excluidos, o son la misma persona porque Ana y Xavi
    se regalaban entre sí), se abre otra pareja P -> Q al azar y se cruza: Pepe regala a Q y
    P regala a Xavi. Cambian dos personas más, pero sigue siendo un reparto válido.
    """
    excluded = set(exclusions)

    def allowed(giver: T, receiver: T) -> bool:
        return giver != receiver and frozenset((giver, receiver)) not in excluded

    # Con dos personas cada una sabría quién le regala: hacen falta al menos tres.
    if len(gives_to) - 1 < 3:
        raise DrawImpossible("con una persona menos no quedan suficientes para el sorteo")

    orphan_giver = next(g for g, r in gives_to.items() if r == leaving)  # Pepe
    orphan_receiver = gives_to[leaving]  # Xavi
    result = {g: r for g, r in gives_to.items() if leaving not in (g, r)}

    if allowed(orphan_giver, orphan_receiver):
        result[orphan_giver] = orphan_receiver
        return result

    pairs = list(result.items())
    rng.shuffle(pairs)
    for giver, receiver in pairs:
        if allowed(orphan_giver, receiver) and allowed(giver, orphan_receiver):
            result[orphan_giver] = receiver
            result[giver] = orphan_receiver
            return result
    raise DrawImpossible(
        "no hay forma de recolocar el sorteo sin esta persona con estas exclusiones"
    )
