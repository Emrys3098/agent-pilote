# Calculatrice en notation polonaise inverse (RPN)

Crée un petit projet Python 3 (bibliothèque standard uniquement) :

1. Un module `rpn.py` avec une fonction `evaluate(expression: str) -> float` qui évalue une
   expression RPN dont les éléments sont séparés par des espaces, par exemple `"3 4 + 2 *"` → `14.0`.
   - Opérateurs : `+`, `-`, `*`, `/`.
   - Nombres entiers ou décimaux, éventuellement négatifs (`-2.5`).
   - Erreurs : lève `ValueError` avec un message clair si l'expression est vide, s'il manque
     des opérandes, s'il reste plusieurs valeurs à la fin, si un élément est inconnu,
     ou en cas de division par zéro.
2. Une interface en ligne de commande : `python3 rpn.py "3 4 +"` affiche `7.0` ;
   en cas d'erreur, affiche `Erreur : <message>` et renvoie le code de sortie 1.
3. Des tests `test_rpn.py` (module `unittest`) couvrant les cas normaux, chaque cas d'erreur
   et l'interface en ligne de commande. `python3 -m unittest -q` doit réussir.
