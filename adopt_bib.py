#!/usr/bin/env python3
"""adopt_bib.py LOCAL.bib [--apply] [--map OUT.json]

Adopt the entries of a consumer's local bibliography file into the master references.bib, following the master conventions:
  * an entry that is already in the master (same title+year, same arXiv id, or same DOI) is NOT duplicated: its local key is mapped to the
    master key;
  * a new entry gets a house-style key (Author-Author:YYYY from the author field; hyphen only between authors; suffix a/b/... on a clash — an
    existing unsuffixed key with the same author+year is renamed to ...a, recorded in the map), is formatted with bibtex-tidy using
    .bibtex-tidy-args (needs `bibtex-tidy` on PATH), and is inserted in key order.
Writes (with --apply) references.bib and a JSON map {old key -> new key} (default rekey-adopted-<name>.json) that the consumer applies to its TeX
sources (`texfix.py cites --map ...`). Dry run by default: prints what would be matched / added / renamed.
"""
import sys, os, re, json, subprocess, importlib.util, unicodedata, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('g', os.path.join(HERE, 'generate_rekey_map.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
OMIT = {'coden', 'mrreviewer', 'bdsk-url-1', 'bdsk-url-2', 'bdsk-url-3', 'keywords', 'date-added', 'date-modified', 'owner', 'timestamp', 'abstract', 'file'}


def clean_value(v):
    """Collapse whitespace and strip; drop a control space left dangling at the end ('Lett.\\ ' -> 'Lett.'),
    which stripping would otherwise turn into a stray backslash before the closing brace ('{Lett.\\}')."""
    v = re.sub(r'\s+', ' ', v).strip()
    while re.search(r'(?<!\\)(?:\\\\)*\\$', v):
        v = v[:-1].rstrip()
    return v


def read_braced(s, i):
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '\\':
            continue
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
    return s[i + 1:], len(s)


def parse(text):
    ents = {}
    order = []
    for m in re.finditer(r'^@(\w+)\s*\{\s*([^,\s]+)\s*,', text, re.M):
        typ, key = m.group(1).lower(), m.group(2)
        if typ in ('comment', 'preamble', 'string'):
            continue
        start = text.index('{', m.start())
        body, end = read_braced(text, start)
        fields = {}
        for fm in re.finditer(r'(\w+)\s*=\s*', body):
            k, i = fm.group(1).lower(), fm.end()
            if i >= len(body):
                continue
            if body[i] == '{':
                v, _ = read_braced(body, i)
            elif body[i] == '"':
                v = body[i + 1:body.index('"', i + 1)]
            else:
                mm = re.match(r'[^,\s}]+', body[i:])
                v = mm.group(0) if mm else ''
            fields.setdefault(k, clean_value(v))
        ents[key] = dict(type=typ, fields=fields, raw=text[m.start():end])
        order.append(key)
    return ents, order


def norm_title(t):
    t = g.strip_tex_and_unicode(t).lower()
    return re.sub(r'[^a-z0-9]+', '', t)


def arxiv(f):
    for k in ('eprint', 'note', 'url', 'journal'):
        m = re.search(r'(?:arXiv[:.]\s*|abs/)((?:[a-z\-]+/)?\d{4}\.?\d{3,5})', f.get(k, ''), re.I)
        if m:
            return m.group(1)
    return None


def find_match(e, master, by_title, by_arxiv, by_doi):
    f = e['fields']
    if f.get('doi') and f['doi'].lower() in by_doi:
        return by_doi[f['doi'].lower()]
    a = arxiv(f)
    if a and a in by_arxiv:
        return by_arxiv[a]
    t = norm_title(f.get('title', ''))
    if t and t in by_title:
        c = by_title[t]
        yr = [k for k in c if master[k]['fields'].get('year', '') == f.get('year', '')]
        return (yr or c)[0]
    return None


def house_key(f, fallback):
    names = g.parse_names(f.get('author') or f.get('editor') or '')
    year = g.extract_year(f.get('year', '')) or '0000'
    return g.canonical_base(names, year) if names else (re.sub(r'[^A-Za-z0-9]', '', fallback) + ':' + year)


def protect_accents(v):
    return re.sub(r"(?<!\{)\\(['\"`^~=.])([A-Za-z])|(?<!\{)\\([vcuHkrdb])\{([A-Za-z])\}", lambda m: '{\\%s%s}' % (m.group(1), m.group(2)) if m.group(1) else '{\\%s{%s}}' % (m.group(3), m.group(4)), v)


def fmt(key, typ, f):
    order = ['author', 'editor', 'title', 'booktitle', 'journal', 'fjournal', 'series', 'volume', 'number', 'publisher', 'address', 'school', 'institution', 'edition', 'year', 'pages', 'doi', 'url', 'eprint', 'archiveprefix', 'primaryclass', 'issn', 'isbn', 'mrclass', 'mrnumber', 'note']
    names = [k for k in order if k in f] + sorted(k for k in f if k not in order)
    lines = [f'@{typ}{{{key},']
    for k in names:
        v = clean_value(str(f[k]))
        if not v or k in OMIT:
            continue
        if k in ('author', 'editor'):
            v = protect_accents(v)
        lines.append(f'  {k} = {{{v}}},')
    lines.append('}')
    return '\n'.join(lines)


def tidy(text):
    args = [l.strip() for l in open(os.path.join(HERE, '.bibtex-tidy-args')).read().split('\n') if l.strip()]
    r = subprocess.run(['bibtex-tidy', *args], input=text.encode(), capture_output=True)
    if r.returncode:
        sys.exit('bibtex-tidy failed: ' + r.stderr.decode(errors='replace'))
    return r.stdout.decode()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    local_path = sys.argv[1]
    apply_ = '--apply' in sys.argv
    mp = os.path.join(HERE, f'rekey-adopted-{os.path.splitext(os.path.basename(local_path))[0]}.json')
    if '--map' in sys.argv:
        mp = sys.argv[sys.argv.index('--map') + 1]
    mtext = open(os.path.join(HERE, 'references.bib'), errors='replace').read()
    master, morder = parse(mtext)
    loc, lorder = parse(open(local_path, errors='replace').read())
    by_title, by_arxiv, by_doi = {}, {}, {}
    for k, e in master.items():
        by_title.setdefault(norm_title(e['fields'].get('title', '')), []).append(k)
        a = arxiv(e['fields'])
        if a:
            by_arxiv[a] = k
        if e['fields'].get('doi'):
            by_doi[e['fields']['doi'].lower()] = k
    keymap, matched, new = {}, [], []
    for k in lorder:
        m = find_match(loc[k], master, by_title, by_arxiv, by_doi)
        if m:
            keymap[k] = m
            matched.append((k, m))
        else:
            new.append(k)
    # keys for the new entries
    by_base = {}
    for k in master:
        by_base.setdefault(re.sub(r'(?<=\d)[a-z]$', '', k), []).append(k)
    groups = {}
    for k in new:
        groups.setdefault(house_key(loc[k]['fields'], k), []).append(k)
    renames, newkeys = {}, {}
    for base, ks in groups.items():
        existing = sorted(by_base.get(base, []))
        if not existing and len(ks) == 1:
            newkeys[ks[0]] = base
            continue
        used = {re.search(r'(?<=\d)([a-z])$', e).group(1) for e in existing if re.search(r'(?<=\d)[a-z]$', e)}
        for e in existing:
            if not re.search(r'(?<=\d)[a-z]$', e):
                l = next(c for c in 'abcdefghijklmnopqrstuvwxyz' if c not in used)
                renames[e] = base + l
                used.add(l)
        for k in sorted(ks, key=lambda x: norm_title(loc[x]['fields'].get('title', ''))):
            l = next(c for c in 'abcdefghijklmnopqrstuvwxyz' if c not in used)
            newkeys[k] = base + l
            used.add(l)
    keymap.update(newkeys)
    print(f'{local_path}: {len(loc)} entries; {len(matched)} already in the master; {len(new)} new; {len(renames)} existing master key(s) renamed to make room')
    for k, m in matched:
        print(f'  = {k} -> {m}' + ('' if k == m else '   (key differs)'))
    for k in new:
        print(f'  + {k} -> {newkeys[k]}')
    for o, n in renames.items():
        print(f'  ~ master {o} -> {n}')
    if not apply_:
        print('(dry run; add --apply)')
        return
    # apply: rename existing keys, add tidied new entries in key order
    text = mtext
    for o, n in renames.items():
        text = re.sub(r'(^@\w+\s*\{\s*)' + re.escape(o) + r'(\s*,)', lambda m: m.group(1) + n + m.group(2), text, count=1, flags=re.M)
    tidy_in = '\n\n'.join(fmt(newkeys[k], loc[k]['type'], loc[k]['fields']) for k in new)
    blocks = tidy(tidy_in).strip('\n').split('\n\n') if new else []
    mats = list(re.finditer(r'^@\w+\s*\{\s*([^,\s]+)\s*,', text, re.M))
    inserts = []
    for b in blocks:
        key = re.match(r'@\w+\s*\{\s*([^,\s]+)', b).group(1)
        pos = next((m.start() for m in mats if m.group(1).lower() > key.lower()), len(text))
        inserts.append((pos, b))
    for pos, b in sorted(inserts, key=lambda x: -x[0]):
        text = text[:pos] + b.strip('\n') + '\n\n' + text[pos:]
    open(os.path.join(HERE, 'references.bib'), 'w').write(text)
    full = {k: v for k, v in keymap.items() if k != v}
    full.update(renames)
    json.dump(full, open(mp, 'w'), indent=2, sort_keys=True)
    open(mp, 'a').write('\n')
    print(f'references.bib updated; key map written to {mp} (apply it to the consumer\'s TeX files)')


main()
