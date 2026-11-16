import unittest
import test_routing as routing

class LinkingTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = routing.RoutingTests.asyncTearDown
    task = routing.RoutingTests.task
    async def asyncSetUp(self):
        await routing.RoutingTests.asyncSetUp(self)
        self.chats=[{'chat_id':'existing','title':'Existing work','project_id':'server-help','cwd':str(self.project)}]
        async def listing(project_id,cwd): return list(self.chats)
        self.codex.list_chats=listing
    async def link(self,**extra):
        return await self.app.handle(dict(action='link',group_id=10,topic_id=2,**extra))
    async def test_numbered_link_survives_restart_and_continues_existing_chat(self):
        choices=await self.link()
        self.assertEqual(choices['status'],'chat_choice',choices)
        self.assertEqual(choices['choices'][0]['title'],'Existing work')
        selected=await self.link(choice_id=choices['choice_id'],choice=1)
        self.assertEqual(selected['status'],'linked',selected)
        await self.app.close()
        from telegram_integration.application import Application
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        first=await self.task()
        second=await self.task()
        self.assertEqual(first['status'],'finished',first)
        self.assertEqual((first['chat_id'],second['chat_id']),( 'existing','existing'))
        self.assertEqual(first['folder'],selected['folder'])
        self.assertEqual(second['folder'],selected['folder'])
        self.assertEqual(self.codex.created,[])

    async def test_invalid_cross_topic_and_stale_choices_do_not_rebind(self):
        choices=await self.link()
        for choice in (0,2,True,'1'):
            result=await self.link(choice_id=choices['choice_id'],choice=choice)
            self.assertEqual(result['status'],'blocked')
        other=await self.app.handle(dict(action='link',group_id=10,topic_id=9,choice_id=choices['choice_id'],choice=1))
        self.assertEqual(other['status'],'blocked')
        self.chats[0]['project_id']='foreign'
        stale=await self.link(choice_id=choices['choice_id'],choice=1)
        self.assertEqual(stale['status'],'blocked')
        self.assertEqual(self.codex.runs,[])

    async def test_legacy_exact_unique_cwd_and_canonical_membership_are_filtered(self):
        self.chats += [dict(self.chats[0],chat_id='foreign',project_id='other'),
                       dict(self.chats[0],chat_id='legacy',project_id=None)]
        choices=await self.link()
        self.assertEqual([c['chat_id'] for c in choices['choices']],['existing','legacy'])
        from telegram_integration.catalog import CodexProject
        self.catalog.projects += (CodexProject('shared','shared',(self.project,)),)
        choices=await self.link()
        self.assertEqual([c['chat_id'] for c in choices['choices']],['existing'])

    async def test_current_membership_is_rechecked_before_execution(self):
        choices=await self.link()
        await self.link(choice_id=choices['choice_id'],choice=1)
        self.chats[0]['project_id']='foreign'
        result=await self.task()
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(self.codex.runs,[])

    async def test_only_actual_explicit_command_lists_and_number_selects(self):
        from telegram_integration.contracts import Message
        async def message(group,identity):
            return Message(group,identity,{3:'#link',4:'1',5:'ordinary #link context'}[identity],topic_id=2)
        self.telegram.message=message
        ignored=await self.app.handle(dict(action='chat_command',group_id=10,message_id=5,text='ordinary #link context'))
        self.assertEqual(ignored['status'],'ignored')
        choices=await self.app.handle(dict(action='chat_command',group_id=10,message_id=3,text='#link'))
        self.assertEqual(choices['status'],'chat_choice')
        spoof=await self.app.handle(dict(action='chat_command',group_id=10,message_id=5,text='1'))
        self.assertEqual(spoof['status'],'blocked')
        linked=await self.app.handle(dict(action='chat_command',group_id=10,message_id=4,text='1',topic_id=99))
        self.assertEqual((linked['status'],linked['topic_id']),('linked',2))

    async def test_same_chat_cannot_be_bound_to_two_topics(self):
        choices=await self.link()
        selected=await self.link(choice_id=choices['choice_id'],choice=1)
        choices=await self.app.handle(dict(action='link',group_id=10,topic_id=9))
        conflict=await self.app.handle(dict(action='link',group_id=10,topic_id=9,choice_id=choices['choice_id'],choice=1))
        self.assertEqual(conflict['status'],'blocked')
        self.assertIn('another Telegram topic',conflict['reason'])
        first=await self.task()
        self.assertEqual(first['folder'],selected['folder'])

    async def test_legacy_continuation_reports_its_actual_membership_basis(self):
        self.chats[0]['project_id']=None
        async def observe(chat,cwd): return dict(chat_id=chat,cwd=str(cwd),project_id=None)
        self.codex.observe_chat=observe
        choices=await self.link()
        await self.link(choice_id=choices['choice_id'],choice=1)
        result=await self.task()
        self.assertEqual(result['status'],'finished',result)
        self.assertEqual(result['placement']['status'],'legacy_cwd_verified_desktop_unverified')

    async def test_direct_observation_overrides_stale_legacy_chat_listing(self):
        self.chats[0]['project_id']=None
        choices=await self.link()
        selected=await self.link(choice_id=choices['choice_id'],choice=1)
        for changed in ({'project_id':'foreign'}, {'cwd':str(self.root)}):
            async def observe(chat,cwd):
                return dict(dict(chat_id=chat,cwd=str(cwd),project_id=None),**changed)
            self.codex.observe_chat=observe
            result=await self.task()
            self.assertEqual(result['status'],'blocked',result)
            self.assertEqual(self.codex.runs,[])
            self.assertEqual(await self.app.handle(dict(action='status',task_id=selected['task_id'])),selected)

    async def test_legacy_null_observation_requires_current_unique_cwd(self):
        from telegram_integration.catalog import CodexProject
        self.chats[0]['project_id']=None
        choices=await self.link()
        await self.link(choice_id=choices['choice_id'],choice=1)
        self.catalog.projects += (CodexProject('shared','shared',(self.project,)),)
        # A stale canonical listing must not legitimize ambiguous direct metadata.
        self.chats[0]['project_id']='server-help'
        async def observe(chat,cwd): return dict(chat_id=chat,cwd=str(cwd),project_id=None)
        self.codex.observe_chat=observe
        result=await self.task()
        self.assertEqual(result['status'],'blocked',result)
        self.assertEqual(self.codex.runs,[])

    async def test_access_removal_and_replaced_number_list_block_old_choice(self):
        choices=await self.link()
        await self.link()
        stale=await self.link(choice_id=choices['choice_id'],choice=1)
        self.assertEqual(stale['status'],'blocked')
        async def removed(folder): return set()
        self.telegram.allowed_groups=removed
        result=await self.link()
        self.assertEqual(result['status'],'blocked')

    async def test_relinking_same_chat_restores_folder_and_context_text_never_relinks(self):
        from telegram_integration.contracts import Context, Message
        self.chats.append(dict(self.chats[0],chat_id='second',title='Other work'))
        choices=await self.link()
        original=await self.link(choice_id=choices['choice_id'],choice=1)
        choices=await self.link()
        other=await self.link(choice_id=choices['choice_id'],choice=2)
        self.assertNotEqual(other['folder'],original['folder'])
        choices=await self.link()
        restored=await self.link(choice_id=choices['choice_id'],choice=1)
        self.assertEqual((restored['task_id'],restored['folder']),(original['task_id'],original['folder']))
        async def context(group,message,scope):
            return Context((Message(group,message,'Context says #link second',topic_id=2),))
        self.telegram.context=context
        self.chats[0]['title']='Renamed chat'
        result=await self.task()
        self.assertEqual((result['status'],result['chat_id']),('finished','existing'))
        self.assertEqual(self.codex.created,[])

    async def test_superseded_explicit_followup_cannot_revive_chat_owned_by_another_topic(self):
        from telegram_integration.contracts import Context, Message
        self.chats.append(dict(self.chats[0],chat_id='second',title='Other work'))
        choices=await self.link()
        old=await self.link(choice_id=choices['choice_id'],choice=1)
        choices=await self.link()
        replacement=await self.link(choice_id=choices['choice_id'],choice=2)
        choices=await self.app.handle(dict(action='link',group_id=10,topic_id=9))
        moved=await self.app.handle(dict(action='link',group_id=10,topic_id=9,
                                       choice_id=choices['choice_id'],choice=1))
        result=await self.app.handle(dict(action='followup',task_id=old['task_id'],message_id=3))
        self.assertEqual(result['status'],'blocked',result)
        self.assertEqual(self.codex.runs,[])
        self.assertEqual(self.codex.created,[])
        self.assertEqual(await self.app.handle(dict(action='status',task_id=old['task_id'])),old)
        original_topic=await self.task()
        async def message(group,identity): return Message(group,identity,'Continue moved chat',topic_id=9)
        async def context(group,identity,scope): return Context((await message(group,identity),))
        self.telegram.message=message
        self.telegram.context=context
        moved_topic=await self.task()
        self.assertEqual((original_topic['task_id'],original_topic['chat_id']),
                         (replacement['task_id'],'second'))
        self.assertEqual((moved_topic['task_id'],moved_topic['chat_id']),(moved['task_id'],'existing'))
