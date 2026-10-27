import argparse
import json
from pathlib import Path
import sys
from .audit import audit_html, MAX_BYTES


def main(argv=None):
    # Stable UTF-8 output for JSON and redirected reports, including Windows.
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Revisión estática básica de formularios HTML, sin navegador ni red.')
    parser.add_argument('file', help='Archivo HTML local; no se aceptan URLs')
    parser.add_argument('--json', action='store_true', help='Salida JSON sin copiar contenido del documento')
    parser.add_argument('--fail-on', choices=['error', 'warning'], default='error')
    args = parser.parse_args(argv)
    try:
        path = Path(args.file)
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ValueError('Archivo inválido o demasiado grande.')
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Archivo demasiado grande.')
        report = audit_html(raw.decode('utf-8-sig'))
    except (OSError, UnicodeError, ValueError, RecursionError):
        print('No se pudo analizar el archivo local. Revisa formato UTF-8, permisos y límite de un MiB.', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report['scope'])
        print(f"Controles: {report['controlCount']}; errores: {report['errorCount']}; advertencias: {report['warningCount']}.")
        for issue in report['issues']:
            print(f"{issue['severity']} {issue['code']} · línea {issue['line']} · {issue['message']}")
        print(report['notice'])
    return 1 if report['errorCount'] or (args.fail_on == 'warning' and report['warningCount']) else 0


if __name__ == '__main__':
    sys.exit(main())
