from collections import defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser

MAX_BYTES = 1024 * 1024
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
CONTROLS = {'input', 'select', 'textarea', 'button'}


@dataclass(eq=False)
class Node:
    tag: str
    attrs: dict
    line: int
    parent: object = field(default=None, repr=False)
    children: list = field(default_factory=list, repr=False)


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root', {}, 1)
        self.stack = [self.root]
        self.nodes = []
        self.duplicate_attributes = []

    def handle_starttag(self, tag, attrs):
        if len(self.nodes) >= 5000 or len(self.stack) > 100:
            raise ValueError('Documento demasiado complejo para esta revisión.')
        names = [key for key, _ in attrs]
        node = Node(tag, dict(attrs), self.getpos()[0], self.stack[-1])
        if len(names) != len(set(names)):
            self.duplicate_attributes.append(node)
        self.nodes.append(node)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def ancestors(node):
    current = node.parent
    while current is not None:
        yield current
        current = current.parent


def content_text(node):
    if node.tag in {'script', 'style', 'template'}:
        return ''
    parts = [node.attrs.get('alt') or ''] if node.tag == 'img' else []
    for child in node.children:
        parts.append(child if isinstance(child, str) else content_text(child))
    return ' '.join(' '.join(parts).split())


def labelable(node):
    return node.tag in CONTROLS and not (node.tag == 'input' and (node.attrs.get('type') or '').lower() == 'hidden')


def audit_html(html):
    if not isinstance(html, str) or len(html.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Se requiere HTML de hasta un MiB.')
    document = Document()
    document.feed(html)
    document.close()
    nodes = document.nodes
    ids = defaultdict(list)
    for node in nodes:
        if node.attrs.get('id'):
            ids[node.attrs['id']].append(node)
    issues = []

    def issue(code, severity, node, message):
        # No HTML, labels, values, IDs or names are copied into the report.
        issues.append({'code': code, 'severity': severity, 'line': node.line, 'element': node.tag, 'message': message})

    def referenced_text(node):
        tokens = (node.attrs.get('aria-labelledby') or '').split()
        return ' '.join(content_text(ids[token][0]) for token in tokens if len(ids[token]) == 1).strip()

    labels = [node for node in nodes if node.tag == 'label']

    def name_of(node):
        if referenced_text(node):
            return referenced_text(node), 'aria-labelledby'
        if (node.attrs.get('aria-label') or '').strip():
            return node.attrs['aria-label'].strip(), 'aria-label'
        explicit = [label for label in labels if node.attrs.get('id') and label.attrs.get('for') == node.attrs['id'] and content_text(label)]
        if explicit:
            return ' '.join(content_text(label) for label in explicit), 'label'
        for parent in ancestors(node):
            if parent.tag == 'label' and 'for' not in parent.attrs and content_text(parent):
                descendants = [candidate for candidate in nodes if labelable(candidate) and parent in list(ancestors(candidate))]
                if descendants and descendants[0] is node:
                    return content_text(parent), 'label'
        kind = (node.attrs.get('type') or 'text').lower()
        if node.tag == 'button' and content_text(node):
            return content_text(node), 'button'
        if node.tag == 'input' and kind in {'button', 'submit', 'reset'}:
            value = (node.attrs.get('value') or '').strip()
            if value or kind in {'submit', 'reset'}:
                return value or 'Nombre predeterminado del navegador', 'button'
        if node.tag == 'input' and kind == 'image' and (node.attrs.get('alt') or '').strip():
            return node.attrs['alt'].strip(), 'alt'
        if (node.attrs.get('title') or '').strip():
            return node.attrs['title'].strip(), 'title'
        return '', ''

    html_nodes = [node for node in nodes if node.tag == 'html']
    if not html_nodes or not (html_nodes[0].attrs.get('lang') or '').strip():
        issue('DOCUMENT_LANG', 'warning', html_nodes[0] if html_nodes else document.root, 'Declara el idioma del documento y comprueba que corresponda al contenido.')
    for duplicates in ids.values():
        if len(duplicates) > 1:
            for node in duplicates:
                issue('DUPLICATE_ID', 'error', node, 'Usa un identificador único para que las referencias sean inequívocas.')
    for node in document.duplicate_attributes:
        issue('DUPLICATE_ATTRIBUTE', 'warning', node, 'Revisa atributos repetidos; el navegador puede interpretarlos de otra forma.')
    for label in labels:
        if 'for' in label.attrs:
            targets = ids.get(label.attrs['for'], [])
            if len(targets) != 1 or not labelable(targets[0]):
                issue('LABEL_TARGET', 'error', label, 'La etiqueta necesita un destino único y etiquetable.')
        else:
            contained = [node for node in nodes if labelable(node) and label in list(ancestors(node))]
            if len(contained) > 1:
                issue('MULTIPLE_LABEL_CONTROLS', 'warning', label, 'Una etiqueta implícita no debe envolver varios controles etiquetables.')
    active = []
    for node in nodes:
        if not labelable(node) or any('hidden' in candidate.attrs or 'inert' in candidate.attrs for candidate in [node, *ancestors(node)]):
            continue
        active.append(node)
        for attr in ['aria-labelledby', 'aria-describedby']:
            if attr in node.attrs:
                tokens = (node.attrs[attr] or '').split()
                if not tokens or any(len(ids.get(token, [])) != 1 for token in tokens):
                    issue('ARIA_REFERENCE', 'error' if attr == 'aria-labelledby' else 'warning', node, 'Revisa las referencias ARIA: deben apuntar a elementos existentes y únicos.')
        name, method = name_of(node)
        if not name:
            issue('CONTROL_NAME', 'error', node, 'Proporciona una etiqueta o nombre accesible; placeholder y value de texto no son sustitutos.')
        elif method == 'title':
            issue('TITLE_ONLY', 'warning', node, 'El nombre depende de title: revisa una etiqueta visible adecuada para todos los usuarios.')
        if any((candidate.attrs.get('aria-hidden') or '').lower() == 'true' for candidate in [node, *ancestors(node)]):
            issue('CONTROL_ARIA_HIDDEN', 'warning', node, 'Revisa un control oculto al árbol accesible; podría seguir recibiendo foco.')
    fieldsets = [node for node in nodes if node.tag == 'fieldset']
    for node in fieldsets:
        legends = [child for child in node.children if isinstance(child, Node) and child.tag == 'legend']
        if not legends or not content_text(legends[0]):
            issue('FIELDSET_LEGEND', 'warning', node, 'Añade una leyenda clara al grupo y revisa su propósito.')
    radios = defaultdict(list)
    for node in active:
        if node.tag != 'input' or (node.attrs.get('type') or '').lower() != 'radio' or not node.attrs.get('name'):
            continue
        owner = None
        if node.attrs.get('form') and len(ids.get(node.attrs['form'], [])) == 1 and ids[node.attrs['form']][0].tag == 'form':
            owner = ids[node.attrs['form']][0]
        if owner is None:
            owner = next((parent for parent in ancestors(node) if parent.tag == 'form'), document.root)
        radios[(owner, node.attrs['name'])].append(node)
    for group in radios.values():
        if len(group) < 2:
            continue
        containers = [next((parent for parent in ancestors(node) if parent.tag == 'fieldset' or parent.attrs.get('role') == 'radiogroup'), None) for node in group]
        container = containers[0]
        named = False
        if container is not None:
            legends = [child for child in container.children if isinstance(child, Node) and child.tag == 'legend']
            named = bool((legends and content_text(legends[0])) or (container.attrs.get('aria-label') or '').strip() or referenced_text(container))
        if container is None or not all(value is container for value in containers) or not named:
            issue('RADIO_GROUP', 'warning', group[0], 'Revisa la agrupación de opciones relacionadas y proporciona un nombre de grupo.')
    return {
        'scope': 'Revisión estática parcial de HTML; no ejecuta JavaScript ni calcula el árbol accesible del navegador.',
        'controlCount': len(active),
        'errorCount': sum(item['severity'] == 'error' for item in issues),
        'warningCount': sum(item['severity'] == 'warning' for item in issues),
        'issues': issues,
        'notice': 'Cero hallazgos no certifica accesibilidad ni cumplimiento WCAG. Revisa teclado, lector de pantalla, contraste y contenido dinámico.',
    }
