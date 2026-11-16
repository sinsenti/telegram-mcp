"""Bound and freeze generated files before any Telegram delivery.

Headers establish the promised container type, not document correctness or safety.
Local provenance checks are not an isolation boundary against hostile same-user code.
"""
import hashlib
import io
import os
from pathlib import Path
import stat
import zipfile

from .attachments import owned_directory
from .contracts import Blocked, ResultArtifact

MAX_FILES = 10
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_TOTAL_SIZE = 100 * 1024 * 1024
SUPPORTED = {'.pdf', '.docx', '.xlsx', '.csv', '.tsv', '.png', '.jpg', '.jpeg',
             '.webp', '.gif', '.md', '.txt'}


def _directory(path):
    """Open every ancestor without following links, retaining the final descriptor."""
    absolute = Path(os.path.abspath(path))
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read(directory, parts, limit):
    descriptor = os.dup(directory)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=descriptor)
        with os.fdopen(file, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise Blocked('Generated artifact must be a regular file without hardlinks')
            if before.st_size > limit:
                raise Blocked('Generated artifact exceeds its file size or total size limit')
            content = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(content) > limit:
                raise Blocked('Generated artifact exceeds its file size or total size limit')
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns) or len(content) != after.st_size:
                raise Blocked('Generated artifact changed while being read; regenerate and retry')
            return content
    finally:
        os.close(descriptor)


def _format(name, content):
    extension = Path(name).suffix.lower()
    if extension not in SUPPORTED:
        raise Blocked(f'{name}: unsupported generated format; choose PDF, DOCX, XLSX, text or an image')
    valid = True
    if extension == '.pdf':
        valid = content.startswith(b'%PDF-')
    elif extension == '.png':
        valid = content.startswith(b'\x89PNG\r\n\x1a\n')
    elif extension in {'.jpg', '.jpeg'}:
        valid = content.startswith(b'\xff\xd8\xff')
    elif extension == '.webp':
        valid = content.startswith(b'RIFF') and content[8:12] == b'WEBP'
    elif extension == '.gif':
        valid = content.startswith((b'GIF87a', b'GIF89a'))
    elif extension in {'.docx', '.xlsx'}:
        # Bound central-directory allocation before ZipFile constructs entry objects.
        tail = content[-65557:]
        offset = tail.rfind(b'PK\x05\x06')
        if offset < 0 or offset + 22 > len(tail):
            valid = False
        else:
            end = tail[offset:offset + 22]
            entries = int.from_bytes(end[10:12], 'little')
            directory_size = int.from_bytes(end[12:16], 'little')
            valid = 0 < entries <= 10000 and directory_size <= 4 * 1024 * 1024
        if valid:
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as bundle:
                    names = bundle.namelist()
                    required = {'[Content_Types].xml', 'word/document.xml' if extension == '.docx' else 'xl/workbook.xml'}
                    valid = all(names.count(item) == 1 and not bundle.getinfo(item).is_dir()
                                and bundle.getinfo(item).file_size > 0 for item in required)
            except (zipfile.BadZipFile, ValueError, OverflowError):
                valid = False
    if not valid:
        raise Blocked(f'{name}: contents do not match the requested file format; regenerate the file')


def freeze_artifacts(output_directory: Path, artifacts: tuple[ResultArtifact, ...],
                     destination_directory: Path) -> list[dict]:
    """Validate the whole manifest, then freeze exact bytes under stable filenames."""
    if len(artifacts) > MAX_FILES:
        raise Blocked(f'Generated artifact limit is {MAX_FILES} files; reduce the manifest')
    if not artifacts:
        return []
    validated = []
    seen = set()
    total = 0
    try:
        root = _directory(output_directory)
        try:
            for artifact in artifacts:
                raw = artifact.path
                if not isinstance(raw, str) or not raw or '\x00' in raw:
                    raise Blocked('Generated artifact path must name a file relative to the run output directory')
                path = Path(raw)
                if path.is_absolute() or '..' in path.parts or not path.parts:
                    raise Blocked('Generated artifact path must stay inside the run output directory')
                if path in seen:
                    raise Blocked(f'Duplicate generated artifact path: {raw}')
                seen.add(path)
                content = _read(root, path.parts, min(MAX_FILE_SIZE, MAX_TOTAL_SIZE - total))
                _format(path.name, content)
                total += len(content)
                validated.append((path.name, content))
        finally:
            os.close(root)
        destination = Path(os.path.abspath(destination_directory))
        owned_directory(destination)
        results = []
        for index, (name, content) in enumerate(validated):
            folder = owned_directory(destination / str(index))
            folder_fd = _directory(folder)
            try:
                try:
                    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                         0o600, dir_fd=folder_fd)
                except FileExistsError:
                    if _read(folder_fd, (name,), MAX_FILE_SIZE) != content:
                        raise Blocked(f'{name}: frozen snapshot differs; restore the original or start a new run')
                else:
                    with os.fdopen(descriptor, 'wb') as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                results.append({'path': str(folder / name), 'name': name,
                                'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)})
            finally:
                os.close(folder_fd)
        return results
    except OSError as exc:
        raise Blocked(f'Cannot freeze generated artifact: {exc.strerror}; check the run output files and retry') from exc
