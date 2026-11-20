# Rapport Pilote

- Résultat : **succès**
- Durée totale : 596 s
- Bac à sable : bwrap (réseau coupé, système en lecture seule)
- Modèle rapide : halogen-qwen3.8-flash-next (32 appels, 23987 jetons générés, 40.6 jetons/s)

| # | Étape | Statut | Tentatives | Modèle | Durée |
|---|---|---|---|---|---|
| 1 | Implémenter l'évaluateur RPN | réussie | 1 | halogen-qwen3.8-flash-next | 84 s |
| 2 | Ajouter l'interface en ligne de commande | réussie | 1 | halogen-qwen3.8-flash-next | 123 s |
| 3 | Ajouter les tests unittest | réussie | 1 | halogen-qwen3.8-flash-next | 138 s |

## Résumés de passation

**1. Implémenter l'évaluateur RPN** — Étape 1 terminée : création de `rpn.py` avec `evaluate(expression: str) -> float`.

Détails :
- Pile RPN classique ; opérateurs binaires `+ - * /` via un dict `OPERATORS` (+ table `_apply`).
- Nombres validés par regex stricte `^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)$` → accepte `-2.5`, `+.5`, `3.` ; refuse `nan`, `inf`, `1e3`, `1_0` (donc pas de valeurs magiques silencieuses).
- `ValueError` avec messages clairs (en français) pour : expression vide/espaces, opérande manquante avant un opérateur (avec position), élément inconnu, opérandes en trop (reste >1 valeur), division par zéro. `TypeError` si l'argument n'est pas une str.
- Le contrôle demandé passe (exit 0) ; tests manuels supplémentaires OK (`5`, `2 3 4 * +`, `10 4 - 2 2 + /`, `+`, `3 4 * *`, `nan`, `3 4 + 5 6`).

Points d'attention pour la suite :
- Aucun bloc `__main__` n'a été ajouté (réservé à l'étape 2 : CLI `python3 rpn.py "3 4 +"` → `7.0`, `Erreur : <message>` + code 1).
- `evaluate` renvoie toujours un `float` ; l'affichage `7.0` se fera donc naturellement via `print(resultat)`.
- `PLAN.json` n'a pas été modifié.

**2. Ajouter l'interface en ligne de commande** — Étape 2 terminée : CLI ajoutée dans `rpn.py` (aucun nouveau fichier, `evaluate` inchangée).

Fichier modifié : `rpn.py` (+ docstring CLI, import `sys`, constante `USAGE`, fonction `main`, bloc `__main__`).

Choix faits :
- `main(argv=None) -> int` renvoie le code de sortie (0/1) au lieu d'appeler `sys.exit` → testable sans subprocess ; `argv=None` ⇒ `sys.argv[1:]`.
- Arguments multiples joints par `" "` : `python3 rpn.py "3 4 +"` ≡ `python3 rpn.py 3 4 +` → `7.0` sur stdout, code 0.
- Erreur : `Erreur : <message>` sur **stderr**, code 1 (capture `ValueError` et `TypeError`).
- Sans argument : `Erreur : il manque l'expression RPN.` + usage sur stderr, code 1 ; `-h/--help` → usage sur stdout, code 0.
- Garde `BrokenPipeError` dans `__main__`.

Vérifications : contrôle de l'étape → `FINAL_CONTROL_OK` (exit 0) ; non-régression étape 1 (`STEP1_OK`) et `py_compile` OK ; codes de sortie testés pour succès/vide/inconnu/opérandes en trop/division par zéro/sans argument. `PASSATION.md` mis à jour ; `PLAN.json` non modifié ; `__pycache__` nettoyé.

Points d'attention pour l'étape 3 (tests) : le message d'erreur va sur stderr (en subprocess, lire `result.stderr`) ; `main` ne lève pas d'exception, elle retourne 1.

**3. Ajouter les tests unittest** — Étape 3 terminée : création de `test_rpn.py` (unittest, 48 tests, aucun fichier existant modifié).

Structure (4 classes) :
- `TestCasNormaux` : exemple du cahier (`3 4 + 2 *` → 14.0), 4 opérateurs, division non entière, décimaux (`1.5`, `.5`, `3.`), négatifs/signés (`-2.5`, `+3`, `2 -3 *`), nombre seul, pile profonde, espaces/tab/NL, type de retour `float`, résultat nul.
- `TestErreurs` : un test par cas + variantes — vide / espaces, opérande manquante (`+`, `3 +`, `* 3 4`, `3 4 * *`, mention de position), opérandes en trop (`3 4 + 5 6`, `3 4`), élément inconnu (`x`, `abc`, `%`, `nan`, `inf`, `1e3`, `1_0`, `++`, `--3`, `.`), division par zéro (`3 0 /`, `4 5 5 - /`, `0.0`, `-0`), `TypeError` pour entrées non-texte.
- `TestInterfaceLigneCommande` : `rpn.main(argv)` + `redirect_stdout/stderr` (helper `run_main`) → codes 0/1, `7.0\n` sur stdout, stderr vide en succès, préfixe exact `Erreur : `, tableau de tous les cas d'erreur via CLI, `main([])` (message « il manque » + usage), `-h/--help` → 0, et `main` ne lève jamais.
- `TestSousProcessus` : vrai `subprocess.run([sys.executable, "rpn.py", ...])` (chemin absolu via `__file__`) pour succès, div. par zéro, inconnu, sans argument, arguments multiples.

Comportements réels notés (tests alignés dessus) : `5 5 - 4 /` n'est pas une division par zéro (RPN = `5 - 5/4`) → test avec `4 5 5 - /` ; `-3` étant un nombre, `5 -3` donne « Opérande(s) en trop » ; le message liste des flottants (`3.0`) → assertion sur « 3 valeurs ».

Vérifs : `python3 -m unittest test_rpn -v` → `Ran 48 tests ... OK` ; `python3 -m unittest -q` → OK ; contrôle de l'étape → `FINAL_CONTROL_OK` (exit 0) ; non-régression étape 1 (`STEP1_OK`) et 2 (`STEP2_OK`). `PASSATION.md` mis à jour ; `PLAN.json` non modifié ; `__pycache__` nettoyé.

