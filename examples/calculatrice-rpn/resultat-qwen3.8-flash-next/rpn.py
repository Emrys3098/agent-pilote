"""Évaluateur d'expressions en notation polonaise inverse (RPN).

Les éléments (nombres et opérateurs) sont séparés par des espaces, par
exemple ``"3 4 + 2 *"`` vaut ``14.0``.

Opérateurs pris en charge : ``+``, ``-``, ``*``, ``/``.
Nombres : entiers ou décimaux, éventuellement signés (``-2.5``, ``+.5``).

Depuis un interpreter ::

    >>> import rpn
    >>> rpn.evaluate("3 4 + 2 *")
    14.0

En ligne de commande ::

    $ python3 rpn.py "3 4 +"
    7.0
    $ python3 rpn.py "3 0 /"
    Erreur : Division par zéro.
    $ echo $?
    1

Les erreurs sont écrites sur ``stderr`` (préfixées par ``Erreur : ``) et le
programme renvoie le code de sortie ``1`` ; le succès affiche le résultat
sur ``stdout`` et renvoie ``0``.
"""

from __future__ import annotations

import re
import sys

__all__ = ["evaluate", "OPERATORS", "main"]

# Opérateurs binaires supportés : symbole -> nom (pour les messages d'erreur).
OPERATORS = {
    "+": "addition",
    "-": "soustraction",
    "*": "multiplication",
    "/": "division",
}

# Nombre littéral : entier ou décimal, avec signe optionnel.
# Volontairement strict : "nan", "inf" ou "1_0" ne sont pas acceptés.
_NUMBER_RE = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$")

USAGE = 'usage : python3 rpn.py "3 4 + 2 *"   (opérateurs : + - * /)'


def _to_number(token: str) -> float:
    """Convertit un jeton en nombre, lève ``ValueError`` si invalide."""
    if not _NUMBER_RE.match(token):
        raise ValueError(f"Élément inconnu : {token!r} (attendu un nombre ou un opérateur)")
    return float(token)


def _apply(operator: str, left: float, right: float) -> float:
    """Applique un opérateur binaire à deux opérandes."""
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    # operator == "/"
    if right == 0:
        raise ValueError("Division par zéro.")
    return left / right


def evaluate(expression: str) -> float:
    """Évalue une expression RPN et renvoie le résultat en ``float``.

    Lève ``ValueError`` avec un message clair si :

    * l'expression est vide (ou uniquement des espaces) ;
    * un opérateur manque d'opérandes ;
    * il reste plusieurs valeurs sur la pile à la fin ;
    * un jeton n'est ni un nombre ni un opérateur connu ;
    * une division par zéro est tentée.

    Lève ``TypeError`` si ``expression`` n'est pas une chaîne.
    """
    if not isinstance(expression, str):
        raise TypeError("L'expression doit être une chaîne de caractères.")

    tokens = expression.split()
    if not tokens:
        raise ValueError("Expression vide : donnez une expression RPN, par exemple \"3 4 +\".")

    stack: list[float] = []
    for index, token in enumerate(tokens, start=1):
        if token in OPERATORS:
            if len(stack) < 2:
                raise ValueError(
                    f"Opérande manquante avant l'opérateur {token!r} "
                    f"(position {index}) : il faut deux nombres avant « {token} »."
                )
            right = stack.pop()
            left = stack.pop()
            stack.append(_apply(token, left, right))
        else:
            stack.append(_to_number(token))

    if len(stack) > 1:
        raise ValueError(
            f"Opérande(s) en trop : il reste {len(stack)} valeurs au lieu d'une seule "
            f"({', '.join(repr(value) for value in stack)})."
        )

    return stack[0]


def main(argv: "list[str] | None" = None) -> int:
    """Point d'entrée CLI. Renvoie le code de sortie (0 = succès, 1 = erreur).

    ``argv`` est la liste des arguments (sans le nom du script) ; ``sys.argv[1:]``
    est utilisé si ``argv`` vaut ``None``. Plusieurs arguments sont joints par des
    espaces, ce qui rend ``python3 rpn.py "3 4 +"`` et ``python3 rpn.py 3 4 +``
    équivalents.
    """
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        print("Erreur : il manque l'expression RPN.", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    if args[0] in ("-h", "--help"):
        print(USAGE)
        return 0

    expression = " ".join(args)
    try:
        result = evaluate(expression)
    except (ValueError, TypeError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # ex. sortie pipée vers `head`
        sys.exit(1)
