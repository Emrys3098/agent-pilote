"""Tests unitaires pour le module `rpn` (évaluateur RPN + interface en ligne de commande).

Lancement ::

    python3 -m unittest -q
    python3 -m unittest test_rpn -v
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

import rpn

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "rpn.py")


def run_main(argv):
    """Exécute `rpn.main(argv)` et renvoie `(code, stdout, stderr)`."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = rpn.main(argv)
    return code, out.getvalue(), err.getvalue()


def run_cli(*args):
    """Exécute réellement `python3 rpn.py ...` en sous-processus."""
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        cwd=HERE,
    )


class TestCasNormaux(unittest.TestCase):
    """Expressions valides : opérateurs, nombres entiers/décimaux/négatifs."""

    def test_exemple_du_cahier_des_charges(self):
        self.assertEqual(rpn.evaluate("3 4 + 2 *"), 14.0)

    def test_quatre_operateurs(self):
        self.assertEqual(rpn.evaluate("3 4 +"), 7.0)
        self.assertEqual(rpn.evaluate("3 4 -"), -1.0)
        self.assertEqual(rpn.evaluate("3 4 *"), 12.0)
        self.assertEqual(rpn.evaluate("8 2 /"), 4.0)

    def test_division_non_entiere(self):
        self.assertAlmostEqual(rpn.evaluate("10 4 /"), 2.5)
        self.assertAlmostEqual(rpn.evaluate("1 3 /"), 1 / 3)

    def test_nombres_decimaux(self):
        self.assertEqual(rpn.evaluate("1.5 2 +"), 3.5)
        self.assertEqual(rpn.evaluate("0.5 0.25 +"), 0.75)
        self.assertEqual(rpn.evaluate(".5 1 +"), 1.5)
        self.assertEqual(rpn.evaluate("3. 2 *"), 6.0)

    def test_nombres_negatifs_et_signes(self):
        self.assertEqual(rpn.evaluate("-2.5 2 *"), -5.0)
        self.assertEqual(rpn.evaluate("-2 -3 +"), -5.0)
        self.assertEqual(rpn.evaluate("+3 4 -"), -1.0)
        self.assertEqual(rpn.evaluate("2 -3 *"), -6.0)

    def test_nombre_negatif_pas_pris_pour_operateur(self):
        # `-3` est un nombre négatif, pas l'opérateur « moins » :
        # deux valeurs restent donc sur la pile (opérandes en trop).
        with self.assertRaises(ValueError) as ctx:
            rpn.evaluate("5 -3")
        self.assertIn("Opérande(s) en trop", str(ctx.exception))
        # Avec un opérateur explicite, le nombre négatif est bien une opérande.
        self.assertEqual(rpn.evaluate("5 -3 -"), 8.0)

    def test_expression_d_un_seul_nombre(self):
        self.assertEqual(rpn.evaluate("5"), 5.0)
        self.assertEqual(rpn.evaluate("-2.5"), -2.5)

    def test_pile_plus_profonde(self):
        self.assertEqual(rpn.evaluate("2 3 4 * +"), 14.0)
        self.assertEqual(rpn.evaluate("10 4 - 2 2 + /"), 1.5)
        self.assertEqual(rpn.evaluate("1 2 + 3 4 + *"), 21.0)

    def test_espaces_multiples_et_bordures(self):
        self.assertEqual(rpn.evaluate("  3   4  +  "), 7.0)
        self.assertEqual(rpn.evaluate("3\t4\n+"), 7.0)

    def test_type_de_retour_est_float(self):
        resultat = rpn.evaluate("2 3 +")
        self.assertIsInstance(resultat, float)
        self.assertEqual(resultat, 5.0)

    def test_zero_comme_resultat(self):
        self.assertEqual(rpn.evaluate("5 5 -"), 0.0)
        self.assertEqual(rpn.evaluate("0 5 /"), 0.0)


class TestErreurs(unittest.TestCase):
    """Chaque cas d'erreur doit lever `ValueError` avec un message clair."""

    def assertMessage(self, expression, attendu):
        with self.assertRaises(ValueError) as ctx:
            rpn.evaluate(expression)
        message = str(ctx.exception)
        self.assertTrue(message, "le message d'erreur ne doit pas être vide")
        if attendu:
            self.assertIn(attendu, message)
        return message

    # --- expression vide -------------------------------------------------
    def test_expression_vide(self):
        self.assertMessage("", "vide")

    def test_expression_espaces_uniquement(self):
        self.assertMessage("   ", "vide")
        self.assertMessage("\t\n ", "vide")

    # --- opérandes manquantes -------------------------------------------
    def test_operateur_sans_operande(self):
        message = self.assertMessage("+", "Opérande manquante")
        self.assertIn("+", message)

    def test_operateur_une_seule_operande(self):
        self.assertMessage("3 +", "Opérande manquante")

    def test_operateur_trop_peu_d_operandes(self):
        self.assertMessage("3 4 * *", "Opérande manquante")

    def test_operateur_debut_expression(self):
        self.assertMessage("* 3 4", "Opérande manquante")

    def test_message_position_indiquee(self):
        message = self.assertMessage("3 4 + +", "Opérande manquante")
        self.assertIn("position", message)

    # --- opérandes en trop ----------------------------------------------
    def test_valeurs_restantes_sur_la_pile(self):
        message = self.assertMessage("3 4 + 5 6", "Opérande(s) en trop")
        self.assertIn("3 valeurs", message)

    def test_deux_nombres_seuls(self):
        self.assertMessage("3 4", "Opérande(s) en trop")

    # --- élément inconnu -------------------------------------------------
    def test_element_inconnu(self):
        message = self.assertMessage("3 x", "inconnu")
        self.assertIn("'x'", message)

    def test_element_inconnu_apres_calcul_valide(self):
        self.assertMessage("3 4 + abc", "inconnu")

    def test_operateur_inconnu(self):
        self.assertMessage("3 4 %", "inconnu")

    def test_nan_refuse(self):
        self.assertMessage("nan 1 +", "inconnu")

    def test_inf_refuse(self):
        self.assertMessage("inf 1 +", "inconnu")

    def test_notation_scientifique_refusee(self):
        self.assertMessage("1e3 1 +", "inconnu")

    def test_separateur_millier_refuse(self):
        self.assertMessage("1_0 1 +", "inconnu")

    def test_contenu_non_numerique(self):
        self.assertMessage("3 4 ++", "inconnu")
        self.assertMessage("--3 4 +", "inconnu")
        self.assertMessage("3 . 4 +", "inconnu")

    # --- division par zéro ----------------------------------------------
    def test_division_par_zero(self):
        self.assertMessage("3 0 /", "Division par zéro")

    def test_division_par_zero_resultat_de_soustraction(self):
        self.assertMessage("4 5 5 - /", "Division par zéro")

    def test_division_par_zero_decimal(self):
        self.assertMessage("5 0.0 /", "Division par zéro")

    def test_division_par_zero_negatif(self):
        self.assertMessage("5 -0 /", "Division par zéro")

    # --- type d'argument -------------------------------------------------
    def test_argument_non_texte(self):
        for valeur in (None, 3, 3.5, ["3", "4", "+"], b"3 4 +"):
            with self.subTest(valeur=valeur):
                with self.assertRaises(TypeError):
                    rpn.evaluate(valeur)

    def test_error_est_valueerror(self):
        # `ValueError` (et non une autre exception) pour tous les cas d'erreur.
        for expression in ("", "3 +", "3 4 + 5", "3 x", "3 0 /"):
            with self.subTest(expression=expression):
                self.assertRaises(ValueError, rpn.evaluate, expression)


class TestInterfaceLigneCommande(unittest.TestCase):
    """Comportement de `rpn.main` : codes de sortie, stdout/stderr."""

    def test_succes_affiche_le_resultat(self):
        code, out, err = run_main(["3 4 +"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "7.0\n")
        self.assertEqual(err, "")

    def test_exemple_du_cahier_des_charges(self):
        code, out, _ = run_main(["3 4 + 2 *"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "14.0")

    def test_arguments_multiples_joints(self):
        code, out, _ = run_main(["3", "4", "+"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "7.0")

    def test_erreur_sur_stderr_et_code_1(self):
        code, out, err = run_main(["3 0 /"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("Erreur : "), err)
        self.assertIn("Division par zéro", err)

    def test_tous_les_cas_d_erreur_via_cli(self):
        cas = {
            "": "vide",
            "3 +": "Opérande manquante",
            "3 4 + 5": "Opérande(s) en trop",
            "3 x": "inconnu",
            "3 0 /": "Division par zéro",
        }
        for expression, attendu in cas.items():
            with self.subTest(expression=expression):
                code, out, err = run_main([expression])
                self.assertEqual(code, 1)
                self.assertEqual(out, "")
                self.assertTrue(err.startswith("Erreur : "), err)
                self.assertIn(attendu, err)

    def test_argument_unique_vide(self):
        code, out, err = run_main([""])
        self.assertEqual(code, 1)
        self.assertIn("vide", err)

    def test_sans_argument(self):
        code, out, err = run_main([])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("il manque l'expression RPN", err)
        self.assertIn("usage", err)

    def test_aide(self):
        for drapeau in ("-h", "--help"):
            with self.subTest(drapeau=drapeau):
                code, out, err = run_main([drapeau])
                self.assertEqual(code, 0)
                self.assertIn("usage", out)
                self.assertEqual(err, "")

    def test_main_ne_leve_pas_d_exception(self):
        # `main` convertit les erreurs en code de sortie, ne propage rien.
        for argv in ([], [""], ["3 0 /"], ["nan"], ["3 4 + 5"], ["--help"]):
            with self.subTest(argv=argv):
                self.assertIn(run_main(argv)[0], (0, 1))


class TestSousProcessus(unittest.TestCase):
    """Vérification « bout en bout » du vrai appel `python3 rpn.py ...`."""

    def test_script_affiche_resultat(self):
        result = run_cli("3 4 +")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "7.0")
        self.assertEqual(result.stderr, "")

    def test_script_division_par_zero(self):
        result = run_cli("3 0 /")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith("Erreur : "), result.stderr)
        self.assertEqual(result.stdout, "")

    def test_script_element_inconnu(self):
        result = run_cli("3 4 w")
        self.assertEqual(result.returncode, 1)
        self.assertIn("inconnu", result.stderr)

    def test_script_sans_argument(self):
        result = subprocess.run(
            [sys.executable, SCRIPT], capture_output=True, text=True, cwd=HERE
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Erreur :", result.stderr)

    def test_script_arguments_multiples(self):
        result = run_cli("3", "4", "+")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "7.0")


if __name__ == "__main__":
    unittest.main()
