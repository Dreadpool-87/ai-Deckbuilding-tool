"""Conservative CSV/TSV ownership import. Never infer quantities from Oracle."""
import csv
import hashlib
import io
import re

NAME = {'name', 'card name', 'cardname', 'card'}
TOTAL = {'quantity', 'qty', 'count', 'amount', 'total', 'copies', 'owned', 'quantityx'}
REGULAR = {'regular', 'normal', 'nonfoil', 'non foil', 'regular quantity'}
FOIL = {'foil', 'foils', 'foil quantity'}


def quantity(value):
    value = value.strip()
    if not re.fullmatch(r'(?:[0-9]+(?:\.0+)?|[xX][0-9]+|[0-9]+[xX])', value):
        raise ValueError('INVALID_OR_AMBIGUOUS_QUANTITY')
    number = int(value.lower().strip('x').split('.')[0])
    if number > 1000000:
        raise ValueError('QUANTITY_TOO_LARGE')
    return number


def normalize(raw):
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('COLLECTION_TOO_LARGE')
    try:
        text = raw.decode('utf-8-sig')
        header = text.splitlines()[0]
        if ',' in header and '\t' in header:
            raise ValueError('AMBIGUOUS_COLLECTION_DELIMITER')
        delimiter = '\t' if '\t' in header else ','
        legacy_text_export = delimiter == '\t' and header.split('\t') == ['QuantityX', 'Name', 'Edition', 'Foil', 'Card Text', 'Card Type', 'Rarity']
        # Only this known export tolerates quotes in unused descriptive fields.
        rows = csv.reader(io.StringIO(text), delimiter=delimiter, strict=not legacy_text_export)
        fields = next(rows)
        keys = [re.sub(r'[_-]+', ' ', f.strip().lower()) for f in fields]
        if len(keys) != len(set(keys)):
            raise ValueError('DUPLICATE_COLLECTION_COLUMN')
        names = [i for i, k in enumerate(keys) if k in NAME]
        totals = [i for i, k in enumerate(keys) if k in TOTAL]
        regular = [i for i, k in enumerate(keys) if k in REGULAR]
        foil = [i for i, k in enumerate(keys) if k in FOIL]
        if len(names) != 1 or len(regular) > 1 or len(foil) > 1 or not (totals or regular or foil):
            raise ValueError('UNSUPPORTED_OR_AMBIGUOUS_COLLECTION_COLUMNS')
        out = io.StringIO(newline='')
        writer = csv.writer(out, lineterminator='\n')
        writer.writerow(['Name', 'Quantity'])
        count = 0
        for row in rows:
            if not row:
                continue
            if len(row) != len(fields) or not row[names[0]].strip():
                raise ValueError('MALFORMED_COLLECTION_ROW')
            if any(any(c in row[i] for c in ('\n', '\r', '\t', '"')) for i in names + totals):
                raise ValueError('AMBIGUOUS_OWNERSHIP_FIELD')
            values = [quantity(row[i]) for i in totals]
            if values and len(set(values)) != 1:
                raise ValueError('CONTRADICTORY_COLLECTION_QUANTITIES')
            parts_columns = regular + foil
            if totals and not regular and all(row[i].strip().lower() in ('', 'yes', 'no', 'true', 'false', 'x') for i in foil):
                parts_columns = []  # Export finish marker, not an ownership quantity.
            parts = [quantity(row[i]) for i in parts_columns]
            if parts and values and sum(parts) != values[0]:
                raise ValueError('CONTRADICTORY_COLLECTION_QUANTITIES')
            total = values[0] if values else sum(parts)
            writer.writerow([row[names[0]].strip(), total])
            count += 1
        if not count:
            raise ValueError('EMPTY_COLLECTION')
    except (UnicodeError, csv.Error, IndexError, StopIteration):
        raise ValueError('INVALID_COLLECTION_EXPORT') from None
    result = out.getvalue().encode()
    return result, dict(original_sha256=hashlib.sha256(raw).hexdigest(),
                        normalized_sha256=hashlib.sha256(result).hexdigest(),
                        delimiter='TSV' if delimiter == '\t' else 'CSV', rows=count,
                        ownership_source='CURRENT_INPUT_ONLY')
