#!/usr/bin/env python3
"""Extract public UI strings for a portable, pretranslated Chinese dictionary."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
strings = set()
skip_files = ('react-', 'tanstack-', 'maplibre', 'marked.esm-', 'rolldown-runtime-', 'ui-', 'FloatingRootStore-', 'composite-', 'select-', 'dropdown-menu-', 'DirectionContext-', 'use', 'DialogTitle-', 'Composite', 'safePolygon-', 'store-')
for file in (root / 'public/assets').glob('*.js'):
    if file.name.startswith(skip_files):
        continue
    source = file.read_text()
    # Rolldown outputs nearly all visible text as template literals.
    for match in re.finditer(r'`((?:[^`\\]|\\.)*)`|"((?:[^"\\]|\\.)*)"', source):
        value = match.group(1) if match.group(1) is not None else match.group(2)
        if '${' in value:
            # Translate literal fragments as React renders them independently.
            values = re.split(r'\$\{[^}]*\}', value)
        else:
            values = [value]
        for value in values:
            value = value.replace('\\n', ' ').replace('\\"', '"').replace("\\'", "'").strip()
            value = re.sub(r'\s+', ' ', value)
            if not re.search('[a-zA-Z]{2}', value) or len(value) < 3 or len(value) > 14000:
                continue
            if value.startswith(('http', '/', '.', '#', 'assets/', 'data:', 'queries/', 'image/', 'application/', 'text/', 'M0', 'M1', 'M2')):
                continue
            if re.search(r'\b(?:className|queryKey|function|=>|useEffect|data-slot)\b|\\[a-z]|[{}<>]|--|rgba?\(|hsl\(|[a-z]+-[a-z]+(?:-|/|\[)|[a-z][A-Z]|^\w+[.:/]\w+|^#[A-Fa-f0-9]+$', value):
                continue
            if re.fullmatch(r'[a-z0-9_:-]+', value):
                continue
            if not (' ' in value or re.match(r'^[A-Z][a-z]+(?:[.!?…])?$', value)):
                continue
            strings.add(value)
target = root / 'ui-strings.json'
target.write_text(json.dumps(sorted(strings), ensure_ascii=False, indent=2))
print(len(strings), 'strings;', sum(len(s) for s in strings), 'characters')
