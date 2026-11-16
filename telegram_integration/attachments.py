"""Preserve opaque originals. Interpretation belongs to Codex's existing tools."""
import hashlib
import os
from pathlib import Path
from .contracts import Blocked

FAMILIES = {
    'text': {'.txt','.md','.csv','.tsv','.json','.xml','.html','.log'},
    'image': {'.png','.jpg','.jpeg','.webp','.gif'},
    'pdf': {'.pdf'}, 'word': {'.docx','.doc'},
    'spreadsheet': {'.xlsx','.xls','.xlsm','.ods'},
}

def family(name,mime_type=None):
    suffix=Path(name).suffix.lower()
    extension_family=next((key for key,extensions in FAMILIES.items() if suffix in extensions),None)
    if extension_family:
        return extension_family
    mime=(mime_type or '').lower().split(';',1)[0].strip()
    if mime.startswith('text/') or mime in {'application/json','application/xml'}:
        return 'text'
    return {'image/png':'image','image/jpeg':'image','image/webp':'image','image/gif':'image',
            'application/pdf':'pdf','application/msword':'word',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document':'word',
            'application/vnd.ms-excel':'spreadsheet',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'spreadsheet',
            'application/vnd.oasis.opendocument.spreadsheet':'spreadsheet'}.get(mime,'unsupported')

def owned_directory(path):
    """Reject pre-existing symlink ancestors before placing local artifacts."""
    for parent in reversed((path,*path.parents)):
        if parent.is_symlink():
            raise Blocked('Task/input path contains a symlink')
    path.mkdir(parents=True,exist_ok=True)
    if not path.is_dir():
        raise Blocked('Task/input path is not a directory')
    return path

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def validate_evidence(inputs,evidence):
    expected={item.input_id:item for item in inputs}
    if len(evidence)!=len(expected) or {item.input_id for item in evidence}!=set(expected):
        raise Blocked('Codex must provide interpretation evidence for every selected input exactly once')
    for item in evidence:
        source=expected[item.input_id]
        if not isinstance(item.evidence,str) or not item.evidence.strip():
            raise Blocked('Codex input evidence is empty')
        if source.explicitly_unnecessary:
            if item.outcome != 'explicitly_unnecessary':
                raise Blocked('Excluded unsupported input must be reported as explicitly unnecessary')
        elif item.outcome != 'interpreted' or source.family == 'unsupported':
            raise Blocked(f'{source.original_name}: {item.outcome}: {item.evidence}')
