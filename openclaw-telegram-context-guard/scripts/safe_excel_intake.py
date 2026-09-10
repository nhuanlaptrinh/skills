#!/usr/bin/env python3
"""Read-only CSV/XLSX intake. Default: headers only. One JSON, <=2000 chars.

Standard library only. XLSX values use cached formula results and raw Excel date
serials (no formula execution, formatting, external links or macros).
"""
import argparse
import csv
import json
import math
import posixpath
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_OUTPUT = 2000
MAX_COLUMNS = 80
MAX_SHEETS = 10
MAX_XML_BYTES = 64 * 1024 * 1024
MAX_SHARED_STRINGS = 100000
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


class IntakeError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise IntakeError('invalid_arguments')


def dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def emit(result):
    """Trim JSON structurally, never slice serialized output."""
    clipped = False

    def normalize(value):
        nonlocal clipped
        if isinstance(value, dict):
            return {str(k): normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        if isinstance(value, str) and len(value) > 120:
            clipped = True
            return value[:119] + '…'
        return value

    result = normalize(result)
    if clipped:
        result['output_truncated'] = True
    while len(dump(result)) + 1 > MAX_OUTPUT:
        result['output_truncated'] = True
        candidates = []
        samples = []

        def collect(value):
            if isinstance(value, dict):
                sample = value.get('matches_sample')
                if isinstance(sample, list) and sample:
                    samples.append(sample)
                for key, child in value.items():
                    if key != 'matches_sample':
                        collect(child)
            elif isinstance(value, list) and value:
                candidates.append(value)
                for child in value:
                    collect(child)

        collect(result)
        if samples:
            max(samples, key=lambda value: len(dump(value))).pop()
            continue
        if not candidates:
            result = {'ok': False, 'error': 'output_budget_exceeded'}
            break
        max(candidates, key=lambda value: len(dump(value))).pop()
    sys.stdout.write(dump(result) + '\n')


def parse_args(argv):
    parser = Parser(add_help=False)
    parser.add_argument('file', nargs='?')
    parser.add_argument('--help', action='store_true')
    parser.add_argument('--sheet')
    parser.add_argument('--contains', nargs=2, metavar=('COLUMN', 'TEXT'))
    parser.add_argument('--columns', nargs='+', default=[])
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--max-scan-rows', type=int, default=10000)
    args = parser.parse_args(argv)
    if args.help:
        return args
    if not args.file or not 1 <= args.limit <= 5 or not 1 <= args.max_scan_rows <= 100000:
        raise IntakeError('invalid_arguments')
    if args.contains and any(not part.strip() for part in args.contains):
        raise IntakeError('empty_filter_not_allowed')
    if args.columns and not args.contains:
        raise IntakeError('columns_require_filter')
    return args


class XMLReader:
    """Limit decompressed reads and reject DTD/entity declarations, including splits."""
    def __init__(self, stream):
        self.stream = stream
        self.total = 0
        self.tail = b''

    def read(self, size=-1):
        data = self.stream.read(min(size if size >= 0 else 65536, 65536))
        self.total += len(data)
        if self.total > MAX_XML_BYTES:
            raise IntakeError('xlsx_xml_size_limit')
        check = (self.tail + data).upper()
        if b'\x00' in check or b'<!DOCTYPE' in check or b'<!ENTITY' in check:
            raise IntakeError('xlsx_dtd_not_allowed')
        self.tail = check[-16:]
        return data


class Workbook:
    def __init__(self, path):
        self.archive = zipfile.ZipFile(path)
        infos = self.archive.infolist()
        if len(infos) > 2000 or sum(i.file_size for i in infos) > 256 * 1024 * 1024:
            self.close()
            raise IntakeError('xlsx_archive_size_limit')
        self.names = set(i.filename for i in infos)
        if len(self.names) != len(infos):
            self.close()
            raise IntakeError('xlsx_duplicate_zip_entry')
        for item in infos:
            if item.flag_bits & 1 or item.file_size > MAX_XML_BYTES or item.file_size > max(1, item.compress_size) * 250:
                self.close()
                raise IntakeError('xlsx_unsafe_zip_entry')
        self.strings = {}

    def close(self):
        self.archive.close()

    def events(self, name):
        if name not in self.names:
            raise IntakeError('xlsx_required_part_missing')
        with self.archive.open(name) as stream:
            yield from ET.iterparse(XMLReader(stream), events=('start', 'end'))

    def document(self, name):
        root = None
        for event, element in self.events(name):
            if root is None:
                root = element
        return root

    def sheets(self):
        relationships = self.document('xl/_rels/workbook.xml.rels')
        mapping = {}
        for rel in relationships:
            if rel.get('TargetMode') == 'External':
                continue
            target = rel.get('Target', '')
            part = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
            if not part.startswith('xl/') or part.startswith('xl/../'):
                raise IntakeError('xlsx_invalid_relationship')
            mapping[rel.get('Id')] = part
        root = self.document('xl/workbook.xml')
        return [(sheet.get('name', ''), mapping.get(sheet.get(RID))) for sheet in root.findall(NS + 'sheets/' + NS + 'sheet')]

    def read_strings(self, needed=None):
        if 'xl/sharedStrings.xml' not in self.names:
            if needed:
                raise IntakeError('xlsx_shared_strings_missing')
            return
        if needed is not None and not needed:
            return
        index = 0
        stored_chars = 0
        root = None
        for event, element in self.events('xl/sharedStrings.xml'):
            if root is None:
                root = element
            if event != 'end' or element.tag != NS + 'si':
                continue
            if index >= MAX_SHARED_STRINGS:
                raise IntakeError('xlsx_shared_strings_limit')
            if needed is None or index in needed:
                value = ''.join(node.text or '' for node in element.iter(NS + 't'))
                stored_chars += len(value)
                if stored_chars > 16 * 1024 * 1024:
                    raise IntakeError('xlsx_shared_strings_size_limit')
                self.strings[index] = value
            index += 1
            element.clear()
            root.clear()
            if needed is not None and needed.issubset(self.strings):
                return
        if needed is not None and not needed.issubset(self.strings):
            raise IntakeError('xlsx_shared_string_index_missing')

    def rows(self, name, metadata, header_only=False):
        root = None
        for event, element in self.events(name):
            if root is None:
                root = element
            if header_only and event == 'start' and element.tag == NS + 'row' and int(element.get('r', '1')) != 1:
                return
            if event == 'end' and element.tag == NS + 'dimension':
                metadata['dimension_metadata'] = element.get('ref')
            if event != 'end' or element.tag != NS + 'row':
                continue
            cells = {}
            for cell in element.findall(NS + 'c'):
                ref = cell.get('r', '')
                letters = ''.join(c for c in ref if 'A' <= c <= 'Z')
                col = 0
                for letter in letters:
                    col = col * 26 + ord(letter) - 64
                if not 1 <= col <= MAX_COLUMNS:
                    continue
                kind = cell.get('t', '')
                if kind == 'inlineStr':
                    value = ''.join(t.text or '' for t in cell.iter(NS + 't'))
                else:
                    value = cell.findtext(NS + 'v')
                cells[col - 1] = (kind, value)
            row_number = int(element.get('r', '1'))
            yield row_number, cells
            if header_only:
                return
            element.clear()
            root.clear()

    def values(self, cells):
        values = []
        for index in range(max(cells, default=-1) + 1):
            kind, value = cells.get(index, ('', None))
            if value is not None:
                if kind == 's':
                    if int(value) not in self.strings:
                        raise IntakeError('xlsx_shared_string_index_missing')
                    value = self.strings[int(value)]
                elif kind == 'b':
                    value = value == '1'
                elif kind not in ('str', 'inlineStr', 'e', 'd'):
                    try:
                        numeric = float(value)
                        value = int(numeric) if math.isfinite(numeric) and numeric.is_integer() else numeric if math.isfinite(numeric) else str(value)
                    except ValueError:
                        pass
            values.append(value)
        return values


def column_index(header, name):
    matches = [i for i, value in enumerate(header) if value == name]
    if not matches:
        raise IntakeError('column_not_found_in_first_80_columns')
    if len(matches) != 1:
        raise IntakeError('column_name_ambiguous')
    return matches[0]


def filtered_rows(rows, header, args):
    where = column_index(header, args.contains[0])
    names = list(dict.fromkeys(args.columns or [args.contains[0]]))
    indexes = [column_index(header, name) for name in names]
    needle = args.contains[1].casefold()
    sample, scanned, stop = [], 0, 'end_of_file'
    for row in rows:
        scanned += 1
        cell = row[where] if where < len(row) else None
        if needle in ('' if cell is None else str(cell)).casefold():
            sample.append([row[i] if i < len(row) else None for i in indexes])
        if len(sample) >= args.limit:
            stop = 'sample_limit'
            break
        if scanned >= args.max_scan_rows:
            stop = 'scan_limit'
            break
    return {'columns': names, 'matches_sample': sample, 'rows_scanned': scanned,
            'stop_reason': stop, 'matches_are_sample_not_total': True}


def inspect_file(args):
    path = Path(args.file)
    if not path.is_file():
        raise IntakeError('file_not_found')
    suffix = path.suffix.lower()
    if suffix not in ('.csv', '.xlsx', '.xlsm'):
        raise IntakeError('unsupported_file_type_use_csv_xlsx_xlsm')
    if suffix == '.csv' and args.sheet:
        raise IntakeError('sheet_not_applicable_to_csv')
    if suffix != '.csv' and args.contains and not args.sheet:
        raise IntakeError('sheet_required_for_filtered_workbook')
    result = {'ok': True, 'file': path.name, 'bytes': path.stat().st_size,
              'suffix': suffix, 'mode': 'filtered_sample' if args.contains else 'headers_only'}
    if suffix == '.csv':
        with path.open(newline='', encoding='utf-8-sig') as stream:
            rows = csv.reader(stream)
            raw_header = next(rows, [])
            header = raw_header[:MAX_COLUMNS]
            result.update(headers=header, header_columns_omitted=max(0, len(raw_header) - MAX_COLUMNS))
            if args.contains:
                result.update(filtered_rows(rows, header, args))
        return result
    workbook = Workbook(path)
    try:
        sheets = workbook.sheets()
        if args.sheet and args.sheet not in [name for name, _ in sheets]:
            raise IntakeError('sheet_not_found')
        chosen = [(name, part) for name, part in sheets if name == args.sheet] if args.sheet else sheets[:MAX_SHEETS]
        result.update(sheet_count=len(sheets), sheets_omitted=len(sheets) - len(chosen), sheets=[],
                      xlsx_values='cached_formula_values; dates_may_be_excel_serials')
        if args.contains:
            workbook.read_strings()
        for name, part in chosen:
            if not part:
                raise IntakeError('xlsx_sheet_relationship_missing')
            item = {'sheet': name}
            rows = workbook.rows(part, item, header_only=not args.contains)
            try:
                number, cells = next(rows, (1, {}))
                if number != 1:
                    cells = {}  # Do not guess a later data row as the header.
                if not args.contains:
                    workbook.read_strings({int(v) for kind, v in cells.values() if kind == 's' and v is not None})
                header = ['' if value is None else str(value) for value in workbook.values(cells)]
                item['headers'] = header
                item['headers_limited_to_columns'] = MAX_COLUMNS
                if args.contains:
                    item.update(filtered_rows((workbook.values(c) for _, c in rows), header, args))
            finally:
                rows.close()
            result['sheets'].append(item)
    finally:
        workbook.close()
    return result


def main(argv=None):
    try:
        args = parse_args(argv)
        result = {'ok': True, 'usage': 'safe_excel_intake.py FILE [--sheet NAME] [--contains COLUMN TEXT --columns COL ... --limit 1..5 --max-scan-rows 1..100000]',
                  'default': 'Headers only; standard library; UTF-8 CSV or XLSX/XLSM.',
                  'output': 'One JSON <=2000 characters including newline; no source writes.'} if args.help else inspect_file(args)
    except IntakeError as error:
        emit({'ok': False, 'error': str(error)})
        return 2
    except Exception as error:
        emit({'ok': False, 'error': 'file_read_failed', 'error_type': type(error).__name__})
        return 1
    emit(result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
