import json
from pathlib import Path
import subprocess
import sys
import unittest
from audita_formularios import audit_html


def page(body):
    return '<html lang="es"><body>' + body + '</body></html>'


def codes(body):
    return {item['code'] for item in audit_html(page(body))['issues']}


class AuditTests(unittest.TestCase):
    def test_explicit_label(self):
        self.assertNotIn('CONTROL_NAME', codes('<label for="a">Zona</label><input id="a">'))

    def test_implicit_label(self):
        self.assertNotIn('CONTROL_NAME', codes('<label>Zona <input></label>'))

    def test_aria_label(self):
        self.assertNotIn('CONTROL_NAME', codes('<textarea aria-label="Descripción general"></textarea>'))

    def test_labelledby_can_reference_hidden_text(self):
        self.assertNotIn('CONTROL_NAME', codes('<span id="a" hidden>Zona</span><input aria-labelledby="a">'))

    def test_broken_aria_reference(self):
        result = codes('<input aria-labelledby="missing">')
        self.assertIn('ARIA_REFERENCE', result)
        self.assertIn('CONTROL_NAME', result)

    def test_duplicate_ids(self):
        self.assertIn('DUPLICATE_ID', codes('<label for="a">Zona</label><input id="a"><input id="a">'))

    def test_placeholder_and_value_are_not_labels(self):
        self.assertIn('CONTROL_NAME', codes('<input placeholder="Zona" value="Dato ficticio">'))

    def test_empty_label(self):
        self.assertIn('CONTROL_NAME', codes('<label for="a"> </label><input id="a">'))

    def test_button_and_image_alt(self):
        self.assertNotIn('CONTROL_NAME', codes('<button><img alt="Revisar"></button><input type="image" alt="Continuar">'))

    def test_submit_default_name(self):
        self.assertNotIn('CONTROL_NAME', codes('<input type="submit">'))

    def test_unnamed_button(self):
        self.assertIn('CONTROL_NAME', codes('<button></button><input type="button">'))

    def test_hidden_controls_excluded(self):
        report = audit_html(page('<input type="hidden"><div hidden><input></div>'))
        self.assertEqual(report['controlCount'], 0)

    def test_aria_hidden_control_warns(self):
        self.assertIn('CONTROL_ARIA_HIDDEN', codes('<input aria-label="Zona" aria-hidden="true">'))

    def test_title_only_warns(self):
        result = codes('<input title="Zona">')
        self.assertIn('TITLE_ONLY', result)
        self.assertNotIn('CONTROL_NAME', result)

    def test_broken_label_target(self):
        self.assertIn('LABEL_TARGET', codes('<label for="missing">Zona</label>'))

    def test_multiple_controls_in_label(self):
        self.assertIn('MULTIPLE_LABEL_CONTROLS', codes('<label>Zona<input><input></label>'))

    def test_fieldset_without_legend(self):
        self.assertIn('FIELDSET_LEGEND', codes('<fieldset><input aria-label="Zona"></fieldset>'))

    def test_radio_group_with_legend(self):
        html = '<fieldset><legend>Tipo</legend><label>A<input type="radio" name="x"></label><label>B<input type="radio" name="x"></label></fieldset>'
        self.assertNotIn('RADIO_GROUP', codes(html))

    def test_radio_group_without_container(self):
        html = '<label>A<input type="radio" name="x"></label><label>B<input type="radio" name="x"></label>'
        self.assertIn('RADIO_GROUP', codes(html))

    def test_same_radio_name_in_different_forms_is_separate(self):
        html = '<form><input type="radio" name="x" aria-label="A"></form><form><input type="radio" name="x" aria-label="B"></form>'
        self.assertNotIn('RADIO_GROUP', codes(html))

    def test_missing_describedby_is_warning(self):
        report = audit_html(page('<input aria-label="Zona" aria-describedby="missing">'))
        self.assertEqual(report['errorCount'], 0)
        self.assertGreater(report['warningCount'], 0)

    def test_no_source_values_in_report(self):
        report = json.dumps(audit_html(page('<input value="FICTICIO_PRIVADO" id="ID_PRIVADO">')))
        self.assertNotIn('FICTICIO_PRIVADO', report)
        self.assertNotIn('ID_PRIVADO', report)

    def test_size_depth_and_types(self):
        for value in [None, 'x' * (1024 * 1024 + 1), '<div>' * 102]:
            with self.assertRaises(ValueError):
                audit_html(value)

    def test_cli_valid_document(self):
        folder = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, '-m', 'audita_formularios', 'examples/correcto.html', '--json'], cwd=folder, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['errorCount'], 0)

    def test_cli_findings_and_missing_file(self):
        folder = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, '-m', 'audita_formularios', 'examples/con-problemas.html'], cwd=folder, capture_output=True)
        self.assertEqual(result.returncode, 1)
        missing = subprocess.run([sys.executable, '-m', 'audita_formularios', 'missing-ficticio.html'], cwd=folder, capture_output=True)
        self.assertEqual(missing.returncode, 2)


if __name__ == '__main__':
    unittest.main()
