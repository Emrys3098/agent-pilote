## Étape 1 — Implémenter l'évaluateur RPN
Étape 1 terminée : création de `rpn.py` avec `evaluate(expression: str) -> float`.

Détails :
- Pile RPN classique ; opérateurs binaires `+ - * /` via un dict `OPERATORS` (+ table `_apply`).
- Nombres validés par regex stricte `^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)$` → accepte `-2.5`, `+.5`, `3.` ; refuse `nan`, `inf`, `1e3`, `1_0` (donc pas de valeurs magiques silencieuses).
- `ValueError` avec messages clairs (en français) pour : expression vide/espaces, opérande manquante avant un opérateur (avec position), élément inconnu, opérandes en trop (reste >1 valeur), division par zéro. `TypeError` si l'argument n'est pas une str.
- Le contrôle demandé passe (exit 0) ; tests manuels supplémentaires OK (`5`, `2 3 4 * +`, `10 4 - 2 2 + /`, `+`, `3 4 * *`, `nan`, `3 4 + 5 6`).

Points d'attention pour la suite :
- Aucun bloc `__main__` n'a été ajouté (réservé à l'étape 2 : CLI `python3 rpn.py "3 4 +"` → `7.0`, `Erreur : <message>` + code 1).
- `evaluate` renvoie toujours un `float` ; l'affichage `7.0` se fera donc naturellement via `print(resultat)`.
- `PLAN.json` n'a pas été modifié.

## Étape 2 — Ajouter l'interface en ligne de commande
Étape 2 terminée : CLI ajoutée **dans `rpn.py`** (pas de fichier séparé), `evaluate` inchangée.

Détails :
- Nouvelle fonction `main(argv: list[str] | None = None) -> int` : renvoie le code de sortie (0/1) au lieu d'appeler `sys.exit`, donc testable avec `contextlib.redirect_stdout/stderr` sans subprocess. `argv=None` → `sys.argv[1:]`.
- Les arguments supplémentaires sont joints par `" "` : `python3 rpn.py "3 4 +"` et `python3 rpn.py 3 4 +` donnent `7.0`.
- Succès : `print(resultat)` sur **stdout** (ex. `7.0`), code 0.
- Erreur : `Erreur : <message>` sur **stderr** (préfixe exact `Erreur : `), code 1 ; capture `ValueError` **et** `TypeError`.
- Cas sans argument : `Erreur : il manque l'expression RPN.` + ligne d'usage sur stderr, code 1. `-h`/`--help` : usage sur stdout, code 0 (constante `USAGE`).
- Garde `BrokenPipeError` dans le bloc `__main__` (sortie pipée vers `head`).
- Contrôle de l'étape : `CONTROL_OK` (exit 0). Non-régression étape 1 : `STEP1_OK`, `py_compile` OK.
- `PLAN.json` non modifié.

Points d'attention pour l'étape 3 (tests) :
- Tester la CLI soit via `rpn.main([...])` + `redirect_stdout/redirect_stderr` (assertRaises n'est pas nécessaire : `main` ne lève pas, elle renvoie 1), soit via `subprocess.run([sys.executable, "rpn.py", "3 4 +"])`.
- Attention : le message d'erreur est sur **stderr**, donc un test subprocess doit lire `result.stderr` (et `2>&1` en shell).
- `main([])` → 1, `main(["--help"])` → 0 ; `main` n'écrit rien sur stdout en cas d'erreur.
## Étape 2 — Ajouter l'interface en ligne de commande
Étape 2 terminée : CLI ajoutée dans `rpn.py` (aucun nouveau fichier, `evaluate` inchangée).

Fichier modifié : `rpn.py` (+ docstring CLI, import `sys`, constante `USAGE`, fonction `main`, bloc `__main__`).

Choix faits :
- `main(argv=None) -> int` renvoie le code de sortie (0/1) au lieu d'appeler `sys.exit` → testable sans subprocess ; `argv=None` ⇒ `sys.argv[1:]`.
- Arguments multiples joints par `" "` : `python3 rpn.py "3 4 +"` ≡ `python3 rpn.py 3 4 +` → `7.0` sur stdout, code 0.
- Erreur : `Erreur : <message>` sur **stderr**, code 1 (capture `ValueError` et `TypeError`).
- Sans argument : `Erreur : il manque l'expression RPN.` + usage sur stderr, code 1 ; `-h/--help` → usage sur stdout, code 0.
- Garde `BrokenPipeError` dans `__main__`.

Vérifications : contrôle de l'étape → `FINAL_CONTROL_OK` (exit 0) ; non-régression étape 1 (`STEP1_OK`) et `py_compile` OK ; codes de sortie testés pour succès/vide/inconnu/opérandes en trop/division par zéro/sans argument. `PASSATION.md` mis à jour ; `PLAN.json` non modifié ; `__pycache__` nettoyé.

Points d'attention pour l'étape 3 (tests) : le message d'erreur va sur stderr (en subprocess, lire `result.stderr`) ; `main` ne lève pas d'exception, elle retourne 1.


## Étape 3 — Ajouter les tests unittest
Étape 3 terminée : création de `test_rpn.py` (module `unittest`, 48 tests, aucun fichier existant modifié).

Contenu (4 classes) :
- `TestCasNormaux` : exemple du cahier (`3 4 + 2 *` → 14.0), les 4 opérateurs, division non entière, décimaux (`1.5`, `.5`, `3.`), négatifs/signés (`-2.5`, `+3`, `2 -3 *`), nombre seul, pile profonde (`2 3 4 * +`, `10 4 - 2 2 + /`), espaces multiples/tabulations/NL, retour de type `float`, résultat nul.
- `TestErreurs` : un test par cas d'erreur + variantes — vide / espaces seuls, opérande manquante (`+`, `3 +`, `* 3 4`, `3 4 * *`, position mentionnée), opérandes en trop (`3 4 + 5 6` → « 3 valeurs », `3 4`), élément inconnu (`x`, `abc`, `%`, `nan`, `inf`, `1e3`, `1_0`, `++`, `--3`, `.`), division par zéro (`3 0 /`, `4 5 5 - /`, `0.0`, `-0`), `TypeError` pour les entrées non-texte (None, int, float, list, bytes).
- `TestInterfaceLigneCommande` : `rpn.main(argv)` + `contextlib.redirect_stdout/stderr` via l'helper `run_main` → codes 0/1, `7.0\n` sur stdout, stderr vide en succès, préfixe exact `Erreur : `, tableau de tous les cas d'erreur via CLI, `main([])` (message « il manque » + usage), `-h/--help` → 0 sur stdout, et vérification que `main` ne lève jamais.
- `TestSousProcessus` : vrai `subprocess.run([sys.executable, "rpn.py", ...])` (chemin absolu via `__file__`, `cwd=HERE`) → stdout/stderr/codes pour succès, division par zéro, élément inconnu, absence d'argument, arguments multiples.

Points notés pendant l'écriture (comportement réel de `rpn.py`, tests corrigés en conséquence) :
- `5 5 - 4 /` n'est **pas** une division par zéro : RPN = `5 - (5/4)` ; le test utilise `4 5 5 - /`.
- `-3` est un nombre, donc `5 -3` lève « Opérande(s) en trop » (et non un calcul).
- Le message « opérandes en trop » affiche les flottants (`3.0`), d'où l'assertion sur « 3 valeurs ».

Vérifications : `python3 -m unittest test_rpn -v` → `Ran 48 tests ... OK` ; `python3 -m unittest -q` → OK ; contrôle de l'étape → `CONTROL_OK` (exit 0) ; non-régression étapes 1 (`STEP1_OK`) et 2 (`STEP2_OK`). `__pycache__` nettoyé ; `PLAN.json` non modifié.
## Étape 3 — Ajouter les tests unittest
Étape 3 terminée : création de `test_rpn.py` (unittest, 48 tests, aucun fichier existant modifié).

Structure (4 classes) :
- `TestCasNormaux` : exemple du cahier (`3 4 + 2 *` → 14.0), 4 opérateurs, division non entière, décimaux (`1.5`, `.5`, `3.`), négatifs/signés (`-2.5`, `+3`, `2 -3 *`), nombre seul, pile profonde, espaces/tab/NL, type de retour `float`, résultat nul.
- `TestErreurs` : un test par cas + variantes — vide / espaces, opérande manquante (`+`, `3 +`, `* 3 4`, `3 4 * *`, mention de position), opérandes en trop (`3 4 + 5 6`, `3 4`), élément inconnu (`x`, `abc`, `%`, `nan`, `inf`, `1e3`, `1_0`, `++`, `--3`, `.`), division par zéro (`3 0 /`, `4 5 5 - /`, `0.0`, `-0`), `TypeError` pour entrées non-texte.
- `TestInterfaceLigneCommande` : `rpn.main(argv)` + `redirect_stdout/stderr` (helper `run_main`) → codes 0/1, `7.0\n` sur stdout, stderr vide en succès, préfixe exact `Erreur : `, tableau de tous les cas d'erreur via CLI, `main([])` (message « il manque » + usage), `-h/--help` → 0, et `main` ne lève jamais.
- `TestSousProcessus` : vrai `subprocess.run([sys.executable, "rpn.py", ...])` (chemin absolu via `__file__`) pour succès, div. par zéro, inconnu, sans argument, arguments multiples.

Comportements réels notés (tests alignés dessus) : `5 5 - 4 /` n'est pas une division par zéro (RPN = `5 - 5/4`) → test avec `4 5 5 - /` ; `-3` étant un nombre, `5 -3` donne « Opérande(s) en trop » ; le message liste des flottants (`3.0`) → assertion sur « 3 valeurs ».

Vérifs : `python3 -m unittest test_rpn -v` → `Ran 48 tests ... OK` ; `python3 -m unittest -q` → OK ; contrôle de l'étape → `FINAL_CONTROL_OK` (exit 0) ; non-régression étape 1 (`STEP1_OK`) et 2 (`STEP2_OK`). `PASSATION.md` mis à jour ; `PLAN.json` non modifié ; `__pycache__` nettoyé.

