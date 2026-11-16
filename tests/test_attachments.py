"""Application orchestration contracts; fake Codex findings do not prove interpretation."""
import unittest
from pathlib import Path
import test_application
from telegram_integration.contracts import Attachment, Context, Message, RunResult, InputEvidence

class AttachmentTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_application.ApplicationTests.asyncSetUp
    asyncTearDown = test_application.ApplicationTests.asyncTearDown
    async def test_originals_and_evidence_survive_followup(self):
        async def context(group, message, scope):
            return Context((Message(group,message,'Read the original',True,2,
                attachment=Attachment('doc-7','../../AGENTS.md','text/plain',19)),))
        async def download(group,message,attachment,file):
            file.write(b'The blue code: 731.')
        async def run(chat,cwd,prompt,inputs=(),**kwargs):
            self.assertEqual(Path(inputs[0].path).read_bytes(),b'The blue code: 731.')
            self.assertEqual(inputs[0].original_name,'../../AGENTS.md')
            return RunResult('Read original.','# Finding\nBlue code is 731.','turn',
                             (InputEvidence(inputs[0].input_id,'interpreted','Line 1: blue code 731'),))
        self.telegram.context=context
        self.telegram.download=download
        self.codex.run=run
        result=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'finished',result)
        self.assertEqual(result['inputs'][0]['source_message_id'],42)
        original=Path(result['inputs'][0]['path'])
        self.assertTrue(original.is_relative_to(Path(result['folder'])/'inputs'))
        self.assertEqual(result['input_evidence'][0]['evidence'],'Line 1: blue code 731')
        again=await self.app.handle({'action':'followup','task_id':result['task_id'],'message_id':43})
        self.assertEqual(again['status'],'finished',again)
        self.assertNotEqual(again['inputs'][0]['path'],str(original))
        self.assertEqual(original.read_bytes(),b'The blue code: 731.')

    async def test_unknown_unsupported_blocks_after_preserving_partial_downloads(self):
        async def context(group,message,scope):
            return Context((Message(group,message,'Use inputs',True,2,attachment=Attachment('a','same.txt')),
                            Message(group,message+1,'',True,2,attachment=Attachment('b','same.bin')),
                            Message(group,message+2,'',True,2,attachment=Attachment('c','missing.pdf'))))
        async def download(group,message,attachment,file):
            if attachment.media_id=='c':
                raise RuntimeError('Original was deleted')
            file.write(b'preserved source')
        self.telegram.context=context;self.telegram.download=download
        result=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'blocked')
        self.assertIn('unsupported',result['reason']);self.assertIn('Original was deleted',result['reason'])
        self.assertEqual([item['download_status'] for item in result['inputs']],['preserved','preserved','failed'])
        self.assertEqual(Path(result['inputs'][0]['path']).read_bytes(),b'preserved source')
        self.assertEqual(self.codex.chats,[])
        self.assertEqual((await self.app.handle({'action':'status','task_id':result['task_id']}))['inputs'],result['inputs'])

    async def test_supported_unreadable_and_missing_or_forged_evidence_block(self):
        async def context(group,message,scope):
            return Context((Message(group,message,'Read',True,2,attachment=Attachment('a','broken.pdf')),))
        async def download(group,message,attachment,file):
            file.write(b'corrupt PDF')
        self.telegram.context=context;self.telegram.download=download
        cases=[(),(InputEvidence('wrong','interpreted','Content'),),
               (InputEvidence('10:42:a','interpreted',''),),
               (InputEvidence('10:42:a','explicitly_unnecessary','Model guessed irrelevant'),),
               (InputEvidence('10:42:a','unreadable','Invalid PDF structure'),)]
        for evidence in cases:
            async def run(*args,inputs=(),**kwargs):
                return RunResult('Done','# Result','turn',evidence)
            self.codex.run=run
            result=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
            self.assertEqual(result['status'],'blocked',result)
            self.assertNotIn('document',result)
        self.assertIn('Invalid PDF structure',result['reason'])
        self.assertEqual(result['input_evidence'][0]['outcome'],'unreadable')

    async def test_explicit_caller_exclusion_allows_preserved_unsupported(self):
        async def context(group,message,scope):
            return Context((Message(group,message,'Prepare a summary; archive is unnecessary',True,2,
                attachment=Attachment('archive','extras.zip')),))
        async def download(group,message,attachment,file): file.write(b'opaque archive')
        async def run(*args,inputs=(),**kwargs):
            return RunResult('extras.zip preserved; explicitly unnecessary.','# Summary\nExcluded extras.zip.','turn',
                (InputEvidence(inputs[0].input_id,'explicitly_unnecessary','Explicit caller exclusion'),))
        self.telegram.context=context;self.telegram.download=download;self.codex.run=run
        blocked=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(blocked['status'],'blocked')
        result=await self.app.handle({'action':'followup','task_id':blocked['task_id'],'message_id':42,
                                      'unnecessary_input_ids':['10:42:archive']})
        self.assertEqual(result['status'],'finished',result)
        self.assertEqual(result['folder'],blocked['folder'])
        self.assertEqual(result['run'],2)
        self.assertTrue(Path(blocked['inputs'][0]['path']).exists())
        self.assertEqual(Path(result['inputs'][0]['path']).read_bytes(),b'opaque archive')

    async def test_five_format_findings_are_orchestration_only(self):
        originals=Path(__file__).parent/'fixtures'/'attachments'/'originals'
        names=['note.txt','shapes.png','checkpoint.pdf','brief.docx','inventory.xlsx']
        findings=['copper-otter-73','3 red squares above 2 blue circles','Page 2: amber bridge 47',
                  'Paragraph 2: silver meadow 29','Inventory!B4 = 18 (7 + 11)']
        async def context(group,message,scope):
            return Context(tuple(Message(group,message+i,'Summarize originals' if i==0 else '',True,2,
                attachment=Attachment(str(i),name)) for i,name in enumerate(names)))
        async def download(group,message,attachment,file): file.write((originals/attachment.original_name).read_bytes())
        async def run(*args,inputs=(),**kwargs):
            self.assertEqual([item.family for item in inputs],['text','image','pdf','word','spreadsheet'])
            for item in inputs:
                self.assertEqual(Path(item.path).read_bytes(),(originals/item.original_name).read_bytes())
            # Fixed findings are an orchestration fake, never actual tool interpretation.
            return RunResult('Five originals read by fixture fake.','\n'.join(findings),'turn',
                tuple(InputEvidence(item.input_id,'interpreted',finding) for item,finding in zip(inputs,findings)))
        self.telegram.context=context;self.telegram.download=download;self.codex.run=run
        result=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'finished',result)
        for finding in findings: self.assertIn(finding,Path(result['document']).read_text())

    async def test_symlink_workspace_blocks_without_writing_outside(self):
        outside=self.root/'outside';outside.mkdir()
        self.app.workspace.symlink_to(outside,target_is_directory=True)
        result=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'blocked')
        self.assertIn('symlink',result['reason'])
        self.assertEqual(list(outside.iterdir()),[])

    async def test_mime_fallback_and_filename_collisions_keep_distinct_originals(self):
        async def context(group,message,scope):
            return Context((Message(group,message,'Read both',True,2,attachment=Attachment('a','original','application/pdf')),
                            Message(group,message+1,'',True,2,attachment=Attachment('b','original','text/plain'))))
        async def download(group,message,attachment,file): file.write(attachment.media_id.encode())
        async def run(*args,inputs=(),**kwargs):
            self.assertEqual([item.family for item in inputs],['pdf','text'])
            self.assertNotEqual(inputs[0].path,inputs[1].path)
            return RunResult('Read both','# Summary','turn',tuple(InputEvidence(i.input_id,'interpreted','Fixture finding') for i in inputs))
        self.telegram.context=context;self.telegram.download=download;self.codex.run=run
        result=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'finished',result)
        self.assertEqual([Path(item['path']).read_bytes() for item in result['inputs']],[b'a',b'b'])

    async def test_modifying_original_is_a_blocker(self):
        async def context(group,message,scope):
            return Context((Message(group,message,'Read',True,2,attachment=Attachment('a','note.txt')),))
        async def download(group,message,attachment,file): file.write(b'original')
        async def run(*args,inputs=(),**kwargs):
            Path(inputs[0].path).write_bytes(b'modified')
            return RunResult('Done','# Result','turn',(InputEvidence(inputs[0].input_id,'interpreted','Read content'),))
        self.telegram.context=context;self.telegram.download=download;self.codex.run=run
        result=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'blocked')
        self.assertIn('changed during execution',result['reason'])

    async def test_usable_replacement_keeps_existing_chat_without_stale_run_evidence(self):
        async def context(group,message,scope):
            name='extras.zip' if message==43 else 'note.txt'
            return Context((Message(group,message,'Use original',True,2,
                attachment=Attachment('a',name)),))
        async def download(group,message,attachment,file): file.write(b'original')
        async def run(*args,inputs=(),**kwargs):
            return RunResult('Read original','# Result','turn-'+str(inputs[0].source_message_id),
                (InputEvidence(inputs[0].input_id,'interpreted','Line 1: original'),))
        self.telegram.context=context;self.telegram.download=download;self.codex.run=run
        first=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(first['status'],'finished',first)
        blocked=await self.app.handle({'action':'followup','task_id':first['task_id'],'message_id':43})
        self.assertEqual(blocked['status'],'blocked',blocked)
        for key in ('turn_id','input_evidence','result_status','document','explanation','report_ids'):
            self.assertNotIn(key,blocked)
        again=await self.app.handle({'action':'followup','task_id':first['task_id'],'message_id':44})
        self.assertEqual(again['status'],'finished',again)
        self.assertEqual(again['folder'],first['folder'])
        self.assertEqual(again['chat_id'],first['chat_id'])
        self.assertEqual(len(self.codex.chats),1)
        self.assertEqual(again['turn_id'],'turn-44')
        self.assertTrue(Path(first['inputs'][0]['path']).exists())
        self.assertTrue(Path(blocked['inputs'][0]['path']).exists())
        self.assertTrue(Path(first['document']).exists())
        self.assertTrue((Path(first['folder'])/'evidence-1.json').exists())

    async def test_lost_blocker_report_ack_prevents_continuation(self):
        async def context(group,message,scope):
            return Context((Message(group,message,'Use original',True,
                attachment=Attachment('a','extras.zip')),))
        async def download(group,message,attachment,file): file.write(b'original')
        async def uncertain(*args): raise TimeoutError('Telegram acknowledgment lost')
        self.telegram.context=context;self.telegram.download=download;self.telegram.send_text=uncertain
        blocked=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(blocked['phase'],'capturing_inputs')
        again=await self.app.handle({'action':'followup','task_id':blocked['task_id'],'message_id':43})
        self.assertEqual(again['status'],'blocked')
        self.assertEqual(await self.app.handle({'action':'status','task_id':blocked['task_id']}),blocked)
        self.assertEqual(self.codex.chats,[])
