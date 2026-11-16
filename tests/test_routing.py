import tempfile
import unittest
from pathlib import Path
from telegram_integration.application import Application
from telegram_integration.catalog import CodexProject
from telegram_integration.contracts import Context, Message, RunResult, GroupMetadata

class Telegram:
    name = 'help'
    group = 10
    async def allowed_groups(self, folder): return {10}
    async def group_metadata(self, group): return GroupMetadata(self.group, self.name)
    async def message(self, group, message): return Message(group,message,'Write a greeting',topic_id=2)
    async def context(self, group, message, scope):
        return Context((Message(group,message,'Write a greeting',topic_id=2),))
    async def send_text(self,*args): return '1'
    async def send_document(self,*args): return '2'

class Codex:
    def __init__(self): self.created=[]; self.runs=[]
    async def aclose(self): pass
    async def create_chat(self,cwd,project_id=None):
        self.created.append((cwd,project_id)); return 'actual-chat'
    async def run(self,chat,cwd,prompt,**kwargs):
        self.runs.append((chat,cwd)); return RunResult('Done','Hello','turn')
    async def observe_chat(self,chat,cwd):
        return {'chat_id':chat,'cwd':str(cwd),'project_id':'server-help'}

class Catalog:
    def __init__(self,root): self.projects=(CodexProject('server-help','help',(root,)),)
    def refresh(self): return self.projects

class RoutingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.project=self.root/'real'; self.project.mkdir()
        self.telegram=Telegram(); self.codex=Codex(); self.catalog=Catalog(self.project)
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        await self.app.handle({'action':'configure','folder_id':8})
    async def asyncTearDown(self): await self.app.close(); self.tmp.cleanup()
    async def task(self,**extra):
        return await self.app.handle(dict(action='task',group_id=10,message_id=3,destination='project',**extra))
    async def test_exact_project_and_same_topic_continue_actual_chat_across_restart_and_rename(self):
        first=await self.task()
        self.assertEqual(first['status'],'finished',first)
        self.assertEqual(self.codex.created,[(self.project,'server-help')])
        self.assertEqual(first['placement']['status'],'server_verified_desktop_unverified')
        self.telegram.name='renamed group'
        self.catalog.projects=(CodexProject('server-help','renamed project',(self.project,)),)
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        second=await self.task()
        self.assertEqual((second['task_id'],second['chat_id'],second['folder']),(first['task_id'],'actual-chat',first['folder']))
        self.assertEqual(self.codex.runs,[('actual-chat',self.project)]*2)
        self.assertEqual(len(self.codex.created),1)
    async def test_ambiguous_names_require_current_explicit_choice_and_survive_rename(self):
        self.catalog.projects+=(CodexProject('other-help','help',(self.root,)),)
        choices=await self.task()
        self.assertEqual(choices['status'],'project_choice')
        self.assertEqual(self.codex.runs,[])
        selected=await self.app.handle({'action':'project','group_id':10,'choice_id':choices['choice_id'],'choice':1})
        self.assertEqual(selected['project_id'],'server-help')
        self.telegram.name='different'
        result=await self.task()
        self.assertEqual(result['project_id'],'server-help')

    async def test_missing_name_never_uses_test_destination_and_stale_choice_is_rejected(self):
        self.telegram.name='missing'
        choices=await self.task()
        self.assertEqual(choices['status'],'project_choice')
        self.catalog.projects=()
        result=await self.app.handle({'action':'project','group_id':10,'choice_id':choices['choice_id'],'choice':1})
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(self.codex.created,[])

    async def test_wrong_group_metadata_blocks_before_execution(self):
        self.telegram.group=20
        result=await self.task()
        self.assertEqual(result['status'],'blocked')
        self.assertIn('different group',result['reason'])
        self.assertEqual(self.codex.runs,[])

    async def test_removed_identity_cannot_redirect_to_same_name_replacement(self):
        first=await self.task()
        self.catalog.projects=(CodexProject('replacement','help',(self.project,)),)
        second=await self.task()
        self.assertEqual(second['status'],'project_choice')
        self.assertEqual(len(self.codex.runs),1)

    async def test_wrong_placement_is_visible_and_cannot_execute_followup(self):
        async def wrong(chat,cwd): return {'chat_id':chat,'project_id':'wrong','cwd':str(cwd)}
        self.codex.observe_chat=wrong
        first=await self.task()
        self.assertEqual(first['status'],'blocked')
        self.assertEqual(first['placement']['status'],'unresolved')
        second=await self.task()
        self.assertEqual(second['status'],'blocked')
        self.assertEqual(len(self.codex.runs),1)

    async def test_followup_cannot_move_to_other_topic(self):
        first=await self.task()
        async def context(group,message,scope): return Context((Message(group,message,'Other task',topic_id=99),))
        self.telegram.context=context
        result=await self.app.handle({'action':'followup','task_id':first['task_id'],'message_id':5})
        self.assertEqual(result['status'],'blocked')
        self.assertIn('same topic',result['reason'])
        self.assertEqual(len(self.codex.runs),1)
    async def test_project_cwd_change_requires_choice_and_does_not_move_existing_chat(self):
        first=await self.task()
        self.catalog.projects=(CodexProject('server-help','help',(self.root,)),)
        choices=await self.task()
        self.assertEqual(choices['status'],'project_choice')
        await self.app.handle({'action':'project','group_id':10,'choice_id':choices['choice_id'],'choice':1})
        second=await self.task()
        self.assertEqual(second['status'],'blocked')
        self.assertIn('differs',second['reason'])
        self.assertEqual(len(self.codex.runs),1)

    async def test_delayed_canonical_assignment_reconciles_same_chat(self):
        pending=[None,None,'server-help']
        async def delayed(chat,cwd): return {'chat_id':chat,'project_id':pending.pop(0),'cwd':str(cwd)}
        self.codex.observe_chat=delayed
        result=await self.task()
        self.assertEqual(result['status'],'finished')
        self.assertEqual(result['placement']['status'],'server_verified_desktop_unverified')
        self.assertEqual(len(result['placement']['observations']),3)

    async def test_routed_wire_protocol_keeps_first_chat_and_inherited_permissions(self):
        import sys
        from test_codex import SERVER
        from telegram_integration.codex import CodexAppServer
        server=SERVER.replace("result={'thread':{'id':'chat-actual'}}", "result={'thread':{'id':'chat-actual'}}\n        if method=='thread/start' and p.get('projectId')!='server-help': raise RuntimeError('wrong project')")
        server=server.replace("    elif method=='turn/start':", "    elif method=='thread/read':\n        result={'thread':{'id':'chat-actual','projectId':'server-help','cwd':str(Path.cwd())}}\n    elif method=='turn/start':")
        script=self.root/'wire.py'; script.write_text(server)
        await self.app.close()
        self.codex=CodexAppServer([sys.executable,str(script),'success'])
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        first=await self.task()
        self.assertEqual(first['status'],'finished',first)
        self.assertEqual(first['chat_id'],'chat-actual')
        second=await self.task()
        self.assertEqual(second['status'],'finished',second)
        self.assertEqual((second['task_id'],second['folder'],second['chat_id']),(first['task_id'],first['folder'],'chat-actual'))
    async def test_context_cannot_reconcile_a_selected_topic_to_different_topic(self):
        async def context(group,message,scope): return Context((Message(group,message,'Wrong topic',topic_id=9),))
        self.telegram.context=context
        result=await self.task()
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(self.codex.runs,[])

    async def test_observer_cannot_confirm_another_chat_in_same_project(self):
        async def wrong(chat,cwd): return {'chat_id':'different-chat','project_id':'server-help','cwd':str(cwd)}
        self.codex.observe_chat=wrong
        result=await self.task()
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['chat_id'],'actual-chat')
        self.assertEqual(result['placement']['status'],'unresolved')
