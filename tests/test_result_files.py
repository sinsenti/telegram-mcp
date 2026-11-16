"""Result files cross the shared Application boundary with restart-safe delivery."""
import tempfile
import unittest
from pathlib import Path

from telegram_integration.application import Application
from telegram_integration.contracts import Context, FrozenDocument, GroupMetadata, Message, ResultArtifact, RunResult
from tests.test_application import Telegram, Codex


class FileTelegram(Telegram):
    def __init__(self):
        super().__init__()
        self.remote = {}
        self.attempts = []
        self.lose_name = None
        self.after_send = None

    async def send_text(self, group, message, text, topic, *, random_id=None):
        return await self.send(group, message, 'text', text, random_id)

    async def send_document(self, group, message, document, topic, *, random_id=None):
        assert isinstance(document, FrozenDocument), 'arbitrary path reached Telegram'
        return await self.send(group, message, document.name, document.content, random_id)

    async def send(self, group, message, name, payload, random_id):
        self.attempts.append((group, message, name, payload, random_id))
        key = (group, random_id)
        self.remote.setdefault(key, (str(500 + len(self.remote)), message, name, payload))
        if self.after_send:
            await self.after_send(name)
        if name == self.lose_name:
            self.lose_name = None
            raise TimeoutError('accepted remotely; acknowledgment lost')
        return self.remote[key][0]


class FileCodex(Codex):
    payloads = {'chart.png': b'\x89PNG\r\n\x1a\n\x00\xff', 'report.pdf': b'%PDF-1.7\x00\xfe'}

    async def create_chat(self, cwd, project_id=None):
        return await super().create_chat(cwd)

    async def observe_chat(self, chat_id, cwd):
        return dict(chat_id=chat_id, cwd=str(cwd), project_id='server-help')

    async def run(self, chat_id, cwd, prompt, inputs=(), *, client_request_id=None,
                  on_turn_accepted=None, output_directory=None):
        self.runs.append((chat_id, cwd, prompt, output_directory))
        assert output_directory is not None
        # The directory and its identity must be committed before external work.
        task = self.app._task(next(iter(self.app.db.execute('SELECT id FROM tasks')))[0])
        assert task['output_directory'] == str(output_directory)
        assert task['phase'] == 'executing' and task['client_request_id']
        for name, content in self.payloads.items():
            (output_directory / name).write_bytes(content)
        if on_turn_accepted:
            await on_turn_accepted('turn-' + str(len(self.runs)))
        return RunResult('Files prepared.', '# Result', 'turn-' + str(len(self.runs)),
                         artifacts=tuple(ResultArtifact(name) for name in self.payloads))


class ResultFilesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.telegram = FileTelegram()
        self.codex = FileCodex()
        await self.open_app()
        await self.app.handle({'action': 'configure', 'folder_id': 7})

    async def open_app(self):
        self.app = Application(self.root / 'db', self.root / 'tasks', self.telegram, self.codex)
        self.codex.app = self.app

    async def asyncTearDown(self):
        await self.app.close()
        self.tmp.cleanup()

    async def task(self):
        return await self.app.handle({'action': 'task', 'group_id': 10, 'message_id': 42, 'destination': 'test'})

    async def test_later_binary_lost_ack_restarts_without_repeating_known_files_or_turn(self):
        self.telegram.lose_name = 'report.pdf'
        first = await self.task()
        self.assertEqual(first['status'], 'blocked', first)
        self.assertEqual(len(first['report_ids']), 3)
        self.assertEqual(first['reporting_version'], 2)
        self.assertEqual([item['name'] for item in first['result_files']], ['result-1.md', 'chart.png', 'report.pdf'])
        await self.app.close()
        await self.open_app()
        recovered = await self.app.handle({'action': 'recover', 'task_id': first['task_id']})
        final = self.app._task(first['task_id'])
        self.assertEqual(final['status'], 'finished', recovered)
        self.assertEqual(len(final['report_ids']), 4)
        self.assertEqual(len(self.codex.runs), 1)
        self.assertEqual([value[2] for value in self.telegram.remote.values()], ['text', 'result-1.md', 'chart.png', 'report.pdf'])
        self.assertEqual([value[3] for value in self.telegram.remote.values()][2:], list(self.codex.payloads.values()))
        self.assertEqual([value[2] for value in self.telegram.attempts], ['text', 'result-1.md', 'chart.png', 'report.pdf', 'report.pdf'])
        operations = [row[0] for row in self.app.db.execute('SELECT id FROM outgoing_operations')]
        self.assertTrue(any(value.endswith(':document') for value in operations))
        self.assertTrue(any(value.endswith(':artifact:0') for value in operations))
        await self.app.handle({'action': 'reconcile_reports', 'task_id': first['task_id']})
        self.assertEqual(len(self.telegram.attempts), 5)

    async def test_manifest_validation_happens_before_result_explanation(self):
        original = self.codex.run
        async def escaped(*args, **kwargs):
            result = await original(*args, **kwargs)
            return RunResult(result.explanation, result.markdown, result.turn_id,
                             artifacts=(ResultArtifact('../../outside.pdf'),))
        self.codex.run = escaped
        first = await self.task()
        self.assertEqual(first['status'], 'blocked', first)
        self.assertNotIn('Files prepared.', [value[3] for value in self.telegram.remote.values()])
        self.assertFalse(any(value[2] != 'text' for value in self.telegram.remote.values()))

    async def test_delivery_uses_frozen_files_after_codex_output_is_changed(self):
        async def mutate_sources(name):
            if name == 'text':
                for source in (self.root/'tasks').glob('*/artifacts/1/*'):
                    source.write_bytes(b'Changed generated source after completion')
        self.telegram.after_send=mutate_sources
        result=await self.task()
        self.assertEqual(result['status'],'finished',result)
        self.assertEqual([value[3] for value in self.telegram.remote.values()][2:],list(self.codex.payloads.values()))
        for record in result['result_files'][1:]:
            self.assertEqual(Path(record['path']).read_bytes(),self.codex.payloads[record['name']])

    async def test_mutating_later_file_during_text_blocks_all_uploads(self):
        async def mutate(name):
            if name == 'text':
                next((self.root / 'tasks').glob('*/deliverables/1/*/report.pdf')).write_bytes(b'changed')
        self.telegram.after_send = mutate
        first = await self.task()
        self.assertEqual(first['status'], 'blocked', first)
        self.assertEqual([value[2] for value in self.telegram.remote.values()], ['text'])
        self.telegram.after_send = None
        await self.app.close()
        await self.open_app()
        result = await self.app.handle({'action': 'reconcile_reports', 'task_id': first['task_id']})
        self.assertEqual(result['status'], 'blocked', result)
        self.assertEqual(len(self.telegram.remote), 1)

    async def test_revocation_between_files_retains_batch_until_explicit_reconcile(self):
        async def revoke(name):
            if name == 'chart.png':
                self.telegram.allowed.clear()
        self.telegram.after_send = revoke
        first = await self.task()
        self.assertEqual(first['status'], 'paused', first)
        self.assertEqual([value[2] for value in self.telegram.remote.values()], ['text', 'result-1.md', 'chart.png'])
        self.assertEqual(len(first['report_ids']), 3)
        self.telegram.after_send = None
        self.telegram.allowed.add(10)
        self.app.folder_access.enable(10)
        result = await self.app.handle({'action': 'reconcile_reports', 'task_id': first['task_id']})
        self.assertEqual(result['status'], 'finished', result)
        self.assertEqual(len(self.telegram.remote), 4)
        self.assertEqual(len(self.codex.runs), 1)

    async def test_terminal_result_reconstructs_artifact_dataclasses_without_new_turn(self):
        original = self.app._finish_result
        async def store_only(task, result, inputs):
            self.app._store_result(task, result)
            raise RuntimeError('crashed after persisting structured result')
        self.app._finish_result = store_only
        first = await self.task()
        self.assertEqual(first['phase'], 'terminal_result', first)
        self.app._finish_result = original
        # The synthetic blocker is an acknowledged separate status reply.
        self.telegram.remote.clear()
        await self.app.close()
        await self.open_app()
        result = await self.app.handle({'action': 'recover', 'task_id': first['task_id']})
        self.assertEqual(self.app._task(first['task_id'])['status'], 'finished', result)
        self.assertEqual(len(self.codex.runs), 1)
        self.assertEqual([value[2] for value in self.telegram.remote.values()], ['text', 'result-1.md', 'chart.png', 'report.pdf'])

    async def test_followup_uses_new_directory_and_clears_old_manifest(self):
        first = await self.task()
        self.assertEqual(first['status'], 'finished', first)
        self.codex.payloads = {}
        second = await self.app.handle({'action': 'followup', 'task_id': first['task_id'], 'message_id': 43})
        self.assertEqual(second['status'], 'finished', second)
        self.assertNotEqual(first['output_directory'], second['output_directory'])
        self.assertEqual(second['artifacts'], [])
        self.assertEqual([item['name'] for item in second['result_files']], ['result-2.md'])
        self.assertTrue(Path(first['result_files'][1]['path']).is_file())
        self.assertEqual([value[2] for value in self.telegram.remote.values()], ['text', 'result-1.md', 'chart.png', 'report.pdf', 'text', 'result-2.md'])

    async def test_legacy_version_one_batch_stays_two_reports(self):
        from telegram_integration.attachments import digest
        document = self.root / 'old.md'
        document.write_text('Saved legacy report')
        task = dict(task_id='legacy', group_id=10, message_id=42, topic_id=None, run=1,
                    status='blocked', phase='reporting', explanation='Saved legacy work',
                    document=str(document), document_sha256=digest(document), reporting_version=1,
                    report_ids=[])
        self.app._save(task)
        await self.app.close()
        await self.open_app()
        result = await self.app.handle({'action': 'reconcile_reports', 'task_id': 'legacy'})
        self.assertEqual(result['status'], 'finished', result)
        self.assertEqual(result['reporting_version'], 1)
        self.assertEqual(len(result['report_ids']), 2)
        self.assertEqual(self.codex.runs, [])

    async def test_same_routed_topic_followup_has_new_outputs_only(self):
        from tests.test_routing import Catalog
        project=self.root/'project'
        project.mkdir()
        self.app.catalog=Catalog(project)
        async def metadata(group):
            return GroupMetadata(group,'help')
        async def context(group,message,scope):
            return Context((Message(group,message,'Generate result files',topic_id=2),))
        async def message(group,identity):
            return Message(group,identity,'Generate result files',topic_id=2)
        self.telegram.group_metadata=metadata
        self.telegram.context=context
        self.telegram.message=message
        first=await self.app.handle(dict(action='task',group_id=10,message_id=42,destination='project'))
        self.assertEqual(first['status'],'finished',first)
        self.codex.payloads={'next.txt':b'New followup only'}
        second=await self.app.handle(dict(action='task',group_id=10,message_id=43,destination='project'))
        self.assertEqual(second['status'],'finished',second)
        self.assertEqual(first['task_id'],second['task_id'])
        self.assertEqual(second['run'],2)
        self.assertEqual(second['chat_id'],first['chat_id'])
        self.assertEqual([item['name'] for item in second['result_files']],['result-2.md','next.txt'])
        self.assertEqual(self.codex.runs[0][1],project)
        self.assertEqual(self.codex.runs[1][1],project)
        self.assertNotEqual(self.codex.runs[0][3],self.codex.runs[1][3])
        followup_reports=[value for value in self.telegram.remote.values() if value[1]==43]
        self.assertEqual([value[2] for value in followup_reports],['text','result-2.md','next.txt'])

    async def test_preexisting_hardlinked_summary_cannot_modify_outside_file(self):
        outside=self.root/'outside.md'
        outside.write_bytes(b'Unrelated original bytes')
        original=self.codex.run
        async def hardlink(*args,**kwargs):
            result=await original(*args,**kwargs)
            (kwargs['output_directory'].parent.parent/'result-1.md').hardlink_to(outside)
            return result
        self.codex.run=hardlink
        result=await self.task()
        self.assertEqual(result['status'],'blocked',result)
        self.assertEqual(outside.read_bytes(),b'Unrelated original bytes')
        self.assertNotIn('Files prepared.',[value[3] for value in self.telegram.remote.values()])
        self.assertFalse(any(value[2]!='text' for value in self.telegram.remote.values()))

    async def test_preexisting_summary_mismatch_is_retained_and_blocks_reporting(self):
        original=self.codex.run
        async def existing(*args,**kwargs):
            result=await original(*args,**kwargs)
            (kwargs['output_directory'].parent.parent/'result-1.md').write_bytes(b'Unexpected prior content')
            return result
        self.codex.run=existing
        result=await self.task()
        self.assertEqual(result['status'],'blocked',result)
        self.assertEqual((Path(result['folder'])/'result-1.md').read_bytes(),b'Unexpected prior content')
        self.assertFalse(any(value[2]!='text' for value in self.telegram.remote.values()))

    async def test_terminal_result_recovery_accepts_identical_existing_summary(self):
        original=self.app._deliver_reports
        async def crash(task):
            raise RuntimeError('stopped after freezing files before delivery')
        self.app._deliver_reports=crash
        first=await self.task()
        self.assertEqual(first['status'],'blocked',first)
        first['phase']='terminal_result'
        self.app._save(first)
        self.app._deliver_reports=original
        await self.app.close()
        await self.open_app()
        result=await self.app.handle({'action':'recover','task_id':first['task_id']})
        self.assertEqual(self.app._task(first['task_id'])['status'],'finished',result)
        self.assertEqual(len(self.codex.runs),1)
        self.assertEqual([value[2] for value in self.telegram.remote.values()],['text','result-1.md','chart.png','report.pdf'])
