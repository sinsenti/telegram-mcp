import hashlib
import io
import os
from pathlib import Path
import zipfile
import unittest
import tempfile
from unittest.mock import patch
from telegram_integration.artifacts import freeze_artifacts
from telegram_integration.contracts import Blocked, ResultArtifact

def archive(member):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as bundle:
        bundle.writestr('[Content_Types].xml', '<Types/>')
        bundle.writestr(member, '<document/>')
    return buffer.getvalue()

class ArtifactTests(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        output = Path(self.temporary.name) / 'output'
        output.mkdir()
        self.roots = (output, Path(self.temporary.name) / 'snapshot')

    def set_limit(self, module, name, value):
        patcher = patch.object(module, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_freezes_verified_bytes_and_preserves_names_0(self):
        roots = self.roots
        name, content = ('Report.pdf', b'%PDF-1.7\nbody')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_1(self):
        roots = self.roots
        name, content = ('Report.docx', archive('word/document.xml'))
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_2(self):
        roots = self.roots
        name, content = ('Budget.xlsx', archive('xl/workbook.xml'))
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_3(self):
        roots = self.roots
        name, content = ('rows.csv', b'a,b\n1,2')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_4(self):
        roots = self.roots
        name, content = ('rows.tsv', b'a\tb')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_5(self):
        roots = self.roots
        name, content = ('notes.md', b'# Notes')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_6(self):
        roots = self.roots
        name, content = ('notes.txt', b'Notes')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_7(self):
        roots = self.roots
        name, content = ('Picture.png', b'\x89PNG\r\n\x1a\nbody')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_8(self):
        roots = self.roots
        name, content = ('Picture.jpeg', b'\xff\xd8\xffbody')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_9(self):
        roots = self.roots
        name, content = ('Picture.jpg', b'\xff\xd8\xffbody')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_10(self):
        roots = self.roots
        name, content = ('Picture.webp', b'RIFF\x04\x00\x00\x00WEBP')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_freezes_verified_bytes_and_preserves_names_11(self):
        roots = self.roots
        name, content = ('Picture.gif', b'GIF89abody')
        output, destination = roots
        (output / 'nested').mkdir()
        source = output / 'nested' / name
        source.write_bytes(content)
        result = freeze_artifacts(output, (ResultArtifact('nested/' + name),), destination)
        frozen = destination / '0' / name
        assert result == [{'path': str(frozen.absolute()), 'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}]
        source.write_bytes(b'changed')
        assert frozen.read_bytes() == content

    def test_rejects_unsafe_paths_0(self):
        roots = self.roots
        path = ''
        with self.assertRaises(Blocked):
            freeze_artifacts(roots[0], (ResultArtifact(path),), roots[1])

    def test_rejects_unsafe_paths_1(self):
        roots = self.roots
        path = '.'
        with self.assertRaises(Blocked):
            freeze_artifacts(roots[0], (ResultArtifact(path),), roots[1])

    def test_rejects_unsafe_paths_2(self):
        roots = self.roots
        path = '../secret.txt'
        with self.assertRaises(Blocked):
            freeze_artifacts(roots[0], (ResultArtifact(path),), roots[1])

    def test_rejects_unsafe_paths_3(self):
        roots = self.roots
        path = 'nested/../report.txt'
        with self.assertRaises(Blocked):
            freeze_artifacts(roots[0], (ResultArtifact(path),), roots[1])

    def test_rejects_unsafe_paths_4(self):
        roots = self.roots
        path = '/tmp/report.txt'
        with self.assertRaises(Blocked):
            freeze_artifacts(roots[0], (ResultArtifact(path),), roots[1])

    def test_rejects_duplicate_paths_before_writing(self):
        roots = self.roots
        output, destination = roots
        (output / 'report.txt').write_text('report')
        with self.assertRaisesRegex(Blocked, 'duplicate|Duplicate'):
            freeze_artifacts(output, (ResultArtifact('report.txt'), ResultArtifact('./report.txt')), destination)
        assert not (destination / '0' / 'report.txt').exists()

    def test_rejects_untrusted_sources_0(self):
        roots = self.roots
        kind = 'file_symlink'
        output, destination = roots
        source = output / 'report.txt'
        target = output.parent / 'original.txt'
        target.write_text('secret')
        path = 'report.txt'
        if kind == 'file_symlink':
            source.symlink_to(target)
        elif kind == 'ancestor_symlink':
            (output / 'nested').symlink_to(output.parent, target_is_directory=True)
            path = 'nested/original.txt'
        elif kind == 'hardlink':
            os.link(target, source)
        elif kind == 'directory':
            source.mkdir()
        elif kind == 'fifo':
            os.mkfifo(source)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(path),), destination)

    def test_rejects_untrusted_sources_1(self):
        roots = self.roots
        kind = 'ancestor_symlink'
        output, destination = roots
        source = output / 'report.txt'
        target = output.parent / 'original.txt'
        target.write_text('secret')
        path = 'report.txt'
        if kind == 'file_symlink':
            source.symlink_to(target)
        elif kind == 'ancestor_symlink':
            (output / 'nested').symlink_to(output.parent, target_is_directory=True)
            path = 'nested/original.txt'
        elif kind == 'hardlink':
            os.link(target, source)
        elif kind == 'directory':
            source.mkdir()
        elif kind == 'fifo':
            os.mkfifo(source)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(path),), destination)

    def test_rejects_untrusted_sources_2(self):
        roots = self.roots
        kind = 'hardlink'
        output, destination = roots
        source = output / 'report.txt'
        target = output.parent / 'original.txt'
        target.write_text('secret')
        path = 'report.txt'
        if kind == 'file_symlink':
            source.symlink_to(target)
        elif kind == 'ancestor_symlink':
            (output / 'nested').symlink_to(output.parent, target_is_directory=True)
            path = 'nested/original.txt'
        elif kind == 'hardlink':
            os.link(target, source)
        elif kind == 'directory':
            source.mkdir()
        elif kind == 'fifo':
            os.mkfifo(source)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(path),), destination)

    def test_rejects_untrusted_sources_3(self):
        roots = self.roots
        kind = 'directory'
        output, destination = roots
        source = output / 'report.txt'
        target = output.parent / 'original.txt'
        target.write_text('secret')
        path = 'report.txt'
        if kind == 'file_symlink':
            source.symlink_to(target)
        elif kind == 'ancestor_symlink':
            (output / 'nested').symlink_to(output.parent, target_is_directory=True)
            path = 'nested/original.txt'
        elif kind == 'hardlink':
            os.link(target, source)
        elif kind == 'directory':
            source.mkdir()
        elif kind == 'fifo':
            os.mkfifo(source)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(path),), destination)

    def test_rejects_untrusted_sources_4(self):
        roots = self.roots
        kind = 'fifo'
        output, destination = roots
        source = output / 'report.txt'
        target = output.parent / 'original.txt'
        target.write_text('secret')
        path = 'report.txt'
        if kind == 'file_symlink':
            source.symlink_to(target)
        elif kind == 'ancestor_symlink':
            (output / 'nested').symlink_to(output.parent, target_is_directory=True)
            path = 'nested/original.txt'
        elif kind == 'hardlink':
            os.link(target, source)
        elif kind == 'directory':
            source.mkdir()
        elif kind == 'fifo':
            os.mkfifo(source)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(path),), destination)

    def test_rejects_untrusted_sources_5(self):
        roots = self.roots
        kind = 'missing'
        output, destination = roots
        source = output / 'report.txt'
        target = output.parent / 'original.txt'
        target.write_text('secret')
        path = 'report.txt'
        if kind == 'file_symlink':
            source.symlink_to(target)
        elif kind == 'ancestor_symlink':
            (output / 'nested').symlink_to(output.parent, target_is_directory=True)
            path = 'nested/original.txt'
        elif kind == 'hardlink':
            os.link(target, source)
        elif kind == 'directory':
            source.mkdir()
        elif kind == 'fifo':
            os.mkfifo(source)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(path),), destination)

    def test_rejects_unsupported_or_mislabeled_formats_0(self):
        roots = self.roots
        name, content = ('bad.exe', b'program')
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_rejects_unsupported_or_mislabeled_formats_1(self):
        roots = self.roots
        name, content = ('bad.pdf', b'not pdf')
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_rejects_unsupported_or_mislabeled_formats_2(self):
        roots = self.roots
        name, content = ('bad.png', b'not png')
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_rejects_unsupported_or_mislabeled_formats_3(self):
        roots = self.roots
        name, content = ('bad.jpg', b'not jpeg')
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_rejects_unsupported_or_mislabeled_formats_4(self):
        roots = self.roots
        name, content = ('bad.webp', b'RIFFxxxxWAVE')
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_rejects_unsupported_or_mislabeled_formats_5(self):
        roots = self.roots
        name, content = ('bad.gif', b'GIF00a')
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_rejects_unsupported_or_mislabeled_formats_6(self):
        roots = self.roots
        name, content = ('bad.docx', archive('xl/workbook.xml'))
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_rejects_unsupported_or_mislabeled_formats_7(self):
        roots = self.roots
        name, content = ('bad.xlsx', archive('word/document.xml'))
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_rejects_unsupported_or_mislabeled_formats_8(self):
        roots = self.roots
        name, content = ('bad.docx', b'not zip')
        output, destination = roots
        (output / name).write_bytes(content)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact(name),), destination)
        assert not (destination / '0' / name).exists()

    def test_validates_entire_manifest_before_freezing(self):
        roots = self.roots
        output, destination = roots
        (output / 'good.txt').write_text('good')
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact('good.txt'), ResultArtifact('missing.pdf')), destination)
        assert not (destination / '0' / 'good.txt').exists()

    def test_limits_manifest_file_and_total_sizes(self):
        roots = self.roots
        import telegram_integration.artifacts as module
        output, destination = roots
        (output / 'one.txt').write_bytes(b'1234')
        (output / 'two.txt').write_bytes(b'5678')
        with self.assertRaisesRegex(Blocked, '10'):
            freeze_artifacts(output, tuple((ResultArtifact(f'{i}.txt') for i in range(11))), destination)
        self.set_limit(module, 'MAX_FILE_SIZE', 3)
        with self.assertRaisesRegex(Blocked, 'size|limit'):
            freeze_artifacts(output, (ResultArtifact('one.txt'),), destination)
        self.set_limit(module, 'MAX_FILE_SIZE', 8)
        self.set_limit(module, 'MAX_TOTAL_SIZE', 7)
        with self.assertRaisesRegex(Blocked, 'total|limit'):
            freeze_artifacts(output, (ResultArtifact('one.txt'), ResultArtifact('two.txt')), destination)

    def test_restart_requires_identical_snapshot(self):
        roots = self.roots
        output, destination = roots
        (output / 'report.txt').write_text('original')
        artifact = (ResultArtifact('report.txt'),)
        first = freeze_artifacts(output, artifact, destination)
        assert freeze_artifacts(output, artifact, destination) == first
        (output / 'report.txt').write_text('changed')
        with self.assertRaisesRegex(Blocked, 'snapshot|frozen'):
            freeze_artifacts(output, artifact, destination)
        assert Path(first[0]['path']).read_text() == 'original'

    def test_rejects_snapshot_symlink_and_output_root_symlink(self):
        roots = self.roots
        output, destination = roots
        (output / 'report.txt').write_text('original')
        destination.symlink_to(output, target_is_directory=True)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact('report.txt'),), destination)
        alias = output.parent / 'alias'
        alias.symlink_to(output, target_is_directory=True)
        with self.assertRaises(Blocked):
            freeze_artifacts(alias, (ResultArtifact('report.txt'),), output.parent / 'other')

    def test_rejects_tampered_snapshot_links(self):
        output, destination = self.roots
        (output / 'report.txt').write_text('original')
        artifact = (ResultArtifact('report.txt'),)
        frozen = Path(freeze_artifacts(output, artifact, destination)[0]['path'])
        frozen.unlink()
        frozen.symlink_to(output / 'report.txt')
        with self.assertRaises(Blocked):
            freeze_artifacts(output, artifact, destination)
        frozen.unlink()
        os.link(output / 'report.txt', frozen)
        with self.assertRaises(Blocked):
            freeze_artifacts(output, artifact, destination)

    def test_rejects_office_archive_without_content_types(self):
        output, destination = self.roots
        with zipfile.ZipFile(output / 'bad.docx', 'w') as bundle:
            bundle.writestr('word/document.xml', '<document/>')
        with self.assertRaises(Blocked):
            freeze_artifacts(output, (ResultArtifact('bad.docx'),), destination)

    def test_no_artifacts_needs_no_output_directory(self):
        output, destination = self.roots
        assert freeze_artifacts(output / 'absent', (), destination) == []
        assert not destination.exists()
