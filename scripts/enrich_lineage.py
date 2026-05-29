#!/usr/bin/env python3
"""
Resolve CTE aliases → upstream tables in YAML lineage files.

Reads each model's SQL, extracts CTE definitions and table aliases,
resolves column-level lineage to actual upstream models, and enriches the YAML files.
"""
import json, re, os, sys, yaml
from collections import OrderedDict

dbt_root = '/home/ubuntu/smile_dbt_model/smile_dbt_model'
yml_dir = '/home/ubuntu/neo4j/config/model_lineage'

with open(f'{dbt_root}/target/manifest.json') as f:
    manifest = json.load(f)
nodes = manifest.get('nodes', {})
name_to_node = {n.get('name',''): n for n in nodes.values()}
alias_to_name = {}
for uid, n in nodes.items():
    alias_to_name[n.get('alias','')] = n.get('name','')

def read_sql(name):
    n = name_to_node.get(name)
    if not n: return ''
    p = n.get('original_file_path','')
    fp = os.path.join(dbt_root, p) if p else ''
    if os.path.exists(fp):
        with open(fp) as f:
            return f.read()
    return ''

def strip_jinja(s):
    s = re.sub(r'{{.*?}}', '', s, flags=re.DOTALL)
    s = re.sub(r'{%.*?%}', '', s, flags=re.DOTALL)
    return s

def resolve_refs(s):
    s = re.sub(r"\{\{\s*ref\s*\(\s*'([^']+)'\s*\)\s*\}\}", r'\1', s)
    s = re.sub(r"\{\{\s*source\s*\(\s*'[^']+'\s*,\s*'([^']+)'\s*\)\s*\}\}", r'\1', s)
    return s

def find_cte_boundary(lines, start_idx):
    """Find the closing paren of a CTE definition by tracking depth."""
    depth = 0; i = start_idx
    started = False
    while i < len(lines):
        for ch in lines[i]:
            if ch == '(':
                started = True; depth += 1
            elif ch == ')':
                depth -= 1
                if started and depth == 0:
                    return i
        i += 1
    return -1

def parse_cte_definitions(sql):
    """Extract CTE names -> (upstream_table, alias) mapping by tracking paren depth."""
    s = resolve_refs(sql)       # resolve {{ ref('name') }} → name FIRST
    s = strip_jinja(s)          # then strip remaining Jinja
    s = re.sub(r"--.*?\n", "\n", s)
    s = re.sub(r"'[^']*'", "''", s)

    lines = s.split('\n')
    cte_map = {}

    # Find WITH keyword — could be on its own line or same line as first CTE
    with_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'\s*WITH\b', line, re.IGNORECASE):
            with_idx = i
            break
    if with_idx == -1:
        return cte_map

    # Scan from WITH to find CTE definitions
    i = with_idx
    current_cte_lines = []
    depth = 0
    in_cte_body = False
    cte_name = ''

    while i < len(lines):
        line = lines[i]

        if not in_cte_body:
            # Check if THIS line starts with WITH (first CTE)
            with_prefix = ''
            if i == with_idx:
                with_prefix = r'^.*?\bWITH\b\s+'

            # Looking for "cte_name AS (" — possibly after WITH
            m = re.match(with_prefix + r'(\w+)\s+AS\s*\(', line, re.IGNORECASE)
            if not m and i > with_idx:
                m = re.match(r'\s*(\w+)\s+AS\s*\(', line, re.IGNORECASE)

            if m:
                cte_name = m.group(1).lower()
                in_cte_body = True
                # Everything after '(' goes into current_cte_lines
                paren_pos = line.index('(')
                after_paren = line[paren_pos+1:]
                current_cte_lines = [after_paren]
                depth = 1
            elif re.match(r'\s*SELECT\b', line, re.IGNORECASE):
                # This is the final SELECT — CTEs are done
                break
        else:
            current_cte_lines.append(line)
            for ch in line:
                if ch == '(': depth += 1
                elif ch == ')': depth -= 1

            if depth == 0:
                cte_body = '\n'.join(current_cte_lines)
                cte_body = cte_body.strip().rstrip(',')

                for ref_m in re.finditer(
                    r'(?:FROM|JOIN)\s+(?:ONLY\s+)?(?:"?(\w+)"?\.)?(?:"?(\w+)"?)(?:\s+(?:AS\s+)?(?:"?(\w+)"?))?',
                    cte_body, re.IGNORECASE
                ):
                    tbl = ref_m.group(2) or ''
                    alias = (ref_m.group(3) or tbl).lower()
                    upstream_name = ''
                    if tbl in name_to_node:
                        upstream_name = tbl
                    elif tbl in alias_to_name:
                        upstream_name = alias_to_name[tbl]
                    if upstream_name:
                        cte_map[cte_name] = upstream_name
                        cte_map[alias] = upstream_name
                        break

                in_cte_body = False
                current_cte_lines = []
                cte_name = ''

        i += 1

    return cte_map

def extract_table_aliases(sql):
    """Extract alias -> table_name from FROM/JOIN clauses (non-CTE)."""
    s = resolve_refs(sql)
    s = strip_jinja(s)
    refs = {}
    for m in re.finditer(
        r'(?:FROM|JOIN)\s+(?:ONLY\s+)?(?:"?(\w+)"?\.)?(?:"?(\w+)"?)(?:\s+(?:AS\s+)?(?:"?(\w+)"?))?',
        s, re.IGNORECASE
    ):
        tbl = m.group(2) or ''
        alias = (m.group(3) or tbl).lower()
        upstream = ''
        if tbl in name_to_node: upstream = tbl
        elif tbl in alias_to_name: upstream = alias_to_name[tbl]
        if upstream: refs[alias] = upstream
    return refs

def extract_join_conditions(sql):
    """Extract JOIN ON conditions that reveal column-level keys."""
    s = resolve_refs(sql); s = strip_jinja(s)
    s = re.sub(r"--.*?\n", "\n", s); s = re.sub(r"'[^']*'", "''", s)
    joins = []
    for m in re.finditer(
        r'JOIN\s+.*?ON\s+(.*?)(?=\s+(?:LEFT|RIGHT|INNER|OUTER|CROSS|FULL|JOIN|WHERE|GROUP|ORDER|LIMIT|$))',
        s, re.IGNORECASE | re.DOTALL
    ):
        cond = m.group(1).strip()
        for eq in re.findall(r'(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)', cond):
            joins.append({
                'left_alias': eq[0].lower(), 'left_col': eq[1],
                'right_alias': eq[2].lower(), 'right_col': eq[3],
            })
    return joins

def extract_column_refs(expr):
    """Extract all table_alias.column references from an expression."""
    return re.findall(r'(?:\b)(\w+)\.(\w+)\b', expr)

def resolve_column(col_entry, cte_map, table_refs, upstreams):
    """
    Try to resolve a column entry to its upstream table.
    Returns (upstream_name, upstream_column) or ('', '').
    """
    expr = col_entry.get('expression', '')
    existing_src = col_entry.get('source_table', '')

    # If already resolved to a real upstream model, keep it
    if existing_src and existing_src in name_to_node:
        return existing_src, col_entry.get('source_column', '')

    # If source_table is a CTE alias, resolve it
    if existing_src and existing_src.lower() in cte_map:
        resolved = cte_map[existing_src.lower()]
        return resolved, col_entry.get('source_column', '')

    # If source_table is a table alias, resolve it
    if existing_src and existing_src.lower() in table_refs:
        return table_refs[existing_src.lower()], col_entry.get('source_column', '')

    # Extract table.column references from expression
    refs = extract_column_refs(expr)
    if refs:
        for tbl_alias, col_name in refs:
            tbl_alias = tbl_alias.lower()
            if tbl_alias in cte_map:
                return cte_map[tbl_alias], col_name
            if tbl_alias in table_refs:
                return table_refs[tbl_alias], col_name
            # Try direct match with upstream names
            for up in upstreams:
                if tbl_alias == up.lower():
                    return up, col_name

    return '', ''

# Process each model YAML
TARGET_NAMES = sorted([f.replace('.yml','') for f in os.listdir(yml_dir)
                       if f.endswith('.yml') and not f.startswith('_')])

total_before = 0; total_after = 0

for model_name in TARGET_NAMES:
    yml_path = os.path.join(yml_dir, f'{model_name}.yml')
    with open(yml_path) as f:
        data = yaml.safe_load(f)

    m = data.get('model', {})
    if not m: continue

    sql = read_sql(model_name)
    cte_map = parse_cte_definitions(sql)
    table_refs = extract_table_aliases(sql)
    join_conditions = extract_join_conditions(sql)
    upstreams = [u['name'] for u in m.get('upstreams', [])]

    columns = m.get('columns', [])
    before_resolved = sum(1 for c in columns if c.get('source_table','') in name_to_node or
                          any(c.get('source_table','') == u for u in upstreams))

    # Resolve each column
    col_lineage_map = {}  # col_name -> (upstream_table, upstream_col)
    for col in columns:
        up_table, up_col = resolve_column(col, cte_map, table_refs, upstreams)
        if up_table:
            # Check if table exists in upstreams
            normalized_table = up_table
            for u in upstreams:
                if up_table.lower() == u.lower() or up_table == u:
                    normalized_table = u
                    break

            col['source_table'] = normalized_table
            if up_col:
                col['source_column'] = up_col
            col_lineage_map[col['name']] = (normalized_table, up_col)

    # Also add join condition-based lineage
    for jc in join_conditions:
        # Find which side of the join belongs to this model vs upstream
        for col in columns:
            col_name = col.get('name', '')
            if col_name in col_lineage_map:
                continue
            expr = col.get('expression', '')
            # Check if the expression references a join key
            for side_name, side_alias_key, side_col_key in [
                ('left', 'left_alias', 'left_col'),
                ('right', 'right_alias', 'right_col'),
            ]:
                side_alias = jc.get(side_alias_key, '')
                side_col = jc.get(side_col_key, '')
                # Check if this column matches
                if f'.{side_col}' in expr or f' {side_alias}.' in expr:
                    other_alias = jc.get('right_alias' if side_name == 'left' else 'left_alias', '')
                    other_col = jc.get('right_col' if side_name == 'left' else 'left_col', '')
                    resolved_table = cte_map.get(other_alias, '') or table_refs.get(other_alias, '')
                    if resolved_table:
                        # Normalize to upstream name
                        for u in upstreams:
                            if resolved_table.lower() == u.lower():
                                resolved_table = u
                                break
                        col_lineage_map[col_name] = (resolved_table, other_col)
                        col['source_table'] = resolved_table
                        col['source_column'] = other_col
                    break

    after_resolved = sum(1 for c in columns if c.get('source_table','') in name_to_node or
                         any(c.get('source_table','') == u for u in upstreams))
    total_before += before_resolved
    total_after += after_resolved

    # Update upstreams with column_lineage
    upstream_cols = {}
    for col_name, (up_table, up_col) in col_lineage_map.items():
        if up_table not in upstream_cols:
            upstream_cols[up_table] = []
        if up_col:
            upstream_cols[up_table].append({'column': col_name, 'from_column': up_col})

    for up_entry in m.get('upstreams', []):
        uname = up_entry['name']
        if uname in upstream_cols:
            up_entry['column_lineage'] = upstream_cols[uname]

    # Write updated YAML
    with open(yml_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    delta = after_resolved - before_resolved
    flag = " ✓" if delta > 0 else ""
    print(f"  {model_name:50s} resolved: {before_resolved:3d} → {after_resolved:3d} ({delta:+d}) "
          f"CTEs={len(cte_map)} joins={len(join_conditions)}{flag}")

print(f"\nTotal resolved columns: {total_before} → {total_after}")
print(f"Newly resolved: {total_after - total_before}")
