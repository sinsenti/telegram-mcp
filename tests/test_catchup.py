import unittest
import test_monitoring
from telegram_integration.application import Application

class CatchupTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=test_monitoring.MonitoringTests.asyncSetUp
    asyncTearDown=test_monitoring.MonitoringTests.asyncTearDown
    self_id=test_monitoring.MonitoringTests.self_id
    latest=test_monitoring.MonitoringTests.latest
    event=test_monitoring.MonitoringTests.event
    async def test_bounded_catchup_survives_restart_and_keeps_prior_admission_order(self):
        groups={10,20}
        async def allowed(folder): return groups.copy()
        self.telegram.allowed_groups=allowed
        history={10:[self.observation(10,101,'2026-01-02T00:00:00+00:00'), self.observation(10,102,'2026-01-04T00:00:00+00:00')],
                 20:[self.observation(20,101,'2026-01-01T00:00:00+00:00'),self.observation(20,102,'2026-01-03T00:00:00+00:00')]}
        async def page(group,after,limit): return [e for e in history[group] if e['message_id']>after][:limit]
        self.telegram.history_page=page
        await self.app.handle({'action':'monitor_enable'})
        await self.event(110)
        result=await self.app.handle({'action':'monitor_catch_up','page_size':1})
        self.assertEqual(result['status'],'caught_up',result)
        state=await self.app.handle({'action':'monitor_status'})
        self.assertEqual([(r['group_id'],r['message_id']) for r in state['requests']],[(10,110),(20,101),(10,101)])
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        await self.app.handle({'action':'monitor_catch_up','page_size':1})
        await self.app.handle({'action':'monitor_catch_up','page_size':1})
        state=await self.app.handle({'action':'monitor_status'})
        self.assertEqual([(r['group_id'],r['message_id']) for r in state['requests']],[(10,110),(20,101),(10,101),(20,102),(10,102)])
        self.assertEqual([g['cutoff'] for g in state['groups']],[100,100])

    @staticmethod
    def observation(group,message,date,**extra):
        return dict(dict(kind='history_message',group_id=group,message_id=message,sender_id=77,text='#codex greeting',created_at=date,edited=False,forwarded=False),**extra)

    async def test_edited_offline_history_excluded_but_known_pristine_event_survives(self):
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101)
        async def page(group,after,limit):
            return [self.observation(group,k,'2026-01-02T00:00:00+00:00',edited=True) for k in (101,102) if k>after]
        self.telegram.history_page=page
        result=await self.app.handle({'action':'monitor_catch_up'})
        self.assertEqual([u['message_id'] for u in result['uncertainties']],[101,102])
        self.assertEqual([r['message_id'] for r in (await self.app.handle({'action':'monitor_status'}))['requests']],[101])
        self.assertEqual(self.codex.created,[])

    async def test_failed_batch_rolls_back_admissions_and_retries_eligible_boundary(self):
        await self.app.handle({'action':'monitor_enable'})
        fail=True
        async def page(group,after,limit):
            return [self.observation(group,101,'2026-01-02T00:00:00+00:00'),
                    self.observation(group,102,'2026-01-02T00:00:00+00:00',kind='forged_new' if fail else 'history_message')] if after<102 else []
        self.telegram.history_page=page
        self.assertEqual((await self.app.handle({'action':'monitor_catch_up'}))['status'],'blocked')
        self.assertEqual((await self.app.handle({'action':'monitor_status'}))['requests'],[])
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        fail=False
        result=await self.app.handle({'action':'monitor_catch_up'})
        self.assertEqual(result['admitted'],2)
        self.assertEqual((await self.app.handle({'action':'monitor_catch_up'}))['admitted'],0)

    async def test_completed_request_never_replays_and_readded_group_gets_fresh_cutoff(self):
        groups={10}
        async def allowed(folder): return groups.copy()
        self.telegram.allowed_groups=allowed
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101)
        from telegram_integration.contracts import Message
        async def message(group,identity): return Message(group,identity,'#codex greeting',topic_id=2)
        self.telegram.message=message
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'finished')
        async def page(group,after,limit): return [self.observation(group,k,'2026-01-02T00:00:00+00:00') for k in (101,102,301) if k>after][:limit]
        self.telegram.history_page=page
        await self.app.handle({'action':'monitor_catch_up','page_size':1})
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'idle')
        groups.clear(); await self.app.handle({'action':'monitor_refresh'})
        groups.add(10)
        async def latest(group): return 300
        self.telegram.latest_message_id=latest
        await self.app.handle({'action':'monitor_refresh'})
        result=await self.app.handle({'action':'monitor_catch_up'})
        self.assertEqual(result['admitted'],1)
        self.assertEqual([r['message_id'] for r in (await self.app.handle({'action':'monitor_status'}))['requests']],[101,301])
        self.assertEqual(len(self.codex.runs),1)

    async def test_listener_startup_uses_application_discovery_after_sdk_catchup(self):
        from telegram_integration.listener import listen
        sdk_caught_up=False
        pages=[]
        async def page(group,after,limit):
            self.assertTrue(sdk_caught_up)
            pages.append((group,after))
            return []
        self.telegram.history_page=page
        class Client:
            def add_event_handler(self,*args): pass
            def remove_event_handler(self,*args): pass
            async def catch_up(self):
                nonlocal sdk_caught_up
                sdk_caught_up=True
            async def run_until_disconnected(self): pass
        await listen(self.app,Client())
        self.assertEqual(pages,[(10,100)])
