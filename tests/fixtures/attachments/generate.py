"""Generate synthetic attachment originals using only the Python standard library.

These files exercise orchestration and later controlled real interpretation. They
are not parsers or evidence that the connector can interpret document contents.
"""
import argparse
import binascii
from pathlib import Path
import struct
import zipfile
import zlib


def png():
    width, height = 320, 200
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            color = (255, 255, 255)
            if any(left <= x < left + 45 and 25 <= y < 70 for left in (30, 135, 240)):
                color = (220, 30, 40)
            if any((x - cx) ** 2 + (y - 140) ** 2 <= 26 ** 2 for cx in (100, 220)):
                color = (30, 80, 220)
            row.extend(color)
        rows.append(b'\0' + row)
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', binascii.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))


def pdf():
    streams = [b'BT /F1 20 Tf 72 720 Td (Attachment acceptance fixture) Tj ET',
               b'BT /F1 18 Tf 72 720 Td (Checkpoint: amber bridge 47) Tj ET']
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for stream in streams:
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    result = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(result)
    result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        result.extend(f'{offset:010d} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(result)


def archive(path, files):
    # Fixed ZIP timestamps keep generated originals byte-for-byte reproducible.
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for name, value in files.items():
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, value)


def generate(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'note.txt').write_bytes(b'Attachment acceptance fixture\nDelivery token: copper-otter-73\n')
    (destination / 'shapes.png').write_bytes(png())
    (destination / 'checkpoint.pdf').write_bytes(pdf())
    content_start = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    archive(destination / 'brief.docx', {
        '[Content_Types].xml': content_start + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        '_rels/.rels': content_start + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        'word/document.xml': content_start + '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Attachment acceptance fixture</w:t></w:r></w:p><w:p><w:r><w:t>Meeting phrase: silver meadow 29.</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>',
    })
    archive(destination / 'inventory.xlsx', {
        '[Content_Types].xml': content_start + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        '_rels/.rels': content_start + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': content_start + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Inventory" sheetId="1" r:id="rId1"/></sheets><calcPr calcId="124519" fullCalcOnLoad="1"/></workbook>',
        'xl/_rels/workbook.xml.rels': content_start + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        'xl/styles.xml': content_start + '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Arial"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
        'xl/worksheets/sheet1.xml': content_start + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cols><col min="1" max="1" width="35" customWidth="1"/><col min="2" max="2" width="16" customWidth="1"/></cols><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Synthetic item</t></is></c><c r="B1" t="inlineStr"><is><t>Quantity</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Blue notebooks (fixture constant)</t></is></c><c r="B2"><v>7</v></c></row><row r="3"><c r="A3" t="inlineStr"><is><t>Red notebooks (fixture constant)</t></is></c><c r="B3"><v>11</v></c></row><row r="4"><c r="A4" t="inlineStr"><is><t>Total notebooks</t></is></c><c r="B4"><f>SUM(B2:B3)</f><v>18</v></c></row></sheetData></worksheet>',
    })
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', nargs='?', type=Path, default=Path(__file__).parent / 'originals')
    print(generate(parser.parse_args().destination).resolve())
