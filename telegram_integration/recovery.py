"""Known-progress recovery. Invoked under Application execution ownership.

A saved execution intent is never evidence that starting a replacement is safe.
Only fully captured work with no external intent may enter the normal start path.
"""
import json
from pathlib import Path
from .attachments import digest, owned_directory
from .contracts import Blocked, RunResult, InputEvidence, TaskInput

class Recovery:
    def __init__(self, app):
        self.app=app

    def inputs(self, task):
        inputs=[]
        for item in task.get('inputs',[]):
            if item.get('download_status') != 'preserved':
                raise Blocked('Captured attachment is incomplete; recover the original input manually')
            value=TaskInput(**{key:value for key,value in item.items() if key not in ('download_status','reason')})
            path=Path(value.path)
            owned_directory(path.parent)
            if path.is_symlink() or not path.is_file() or digest(path)!=value.sha256:
                raise Blocked('Captured original changed; automatic recovery cannot replace it')
            inputs.append(value)
        return tuple(inputs)

    def snapshot(self, task):
        folder=Path(task['folder']); owned_directory(folder)
        saved=task.get('snapshot_sha256')
        if not saved:
            raise Blocked('Captured work lacks a verified fixed snapshot; inspect before continuing')
        for name,identity in saved.items():
            path=folder/name
            if path.parent!=folder or path.is_symlink() or not path.is_file() or digest(path)!=identity:
                raise Blocked('Captured task snapshot changed; automatic recovery cannot recapture it')
        return (folder/f"input-{task['run']}.txt").read_text()

    async def observe(self, task):
        app=self.app
        if not task.get('chat_id'):
            raise Blocked('Execution lacks a known chat identity')
        cwd=Path(task.get('cwd',task['folder']))
        if task.get('turn_id'):
            observation=await app.codex.observe_turn(task['chat_id'],cwd,task['turn_id'])
        elif task.get('client_request_id'):
            observation=await app.codex.find_turn(task['chat_id'],cwd,task['client_request_id'])
        else:
            raise Blocked('Execution lacks a known turn or durable correlation identity')
        if task.get('turn_id') and observation.turn_id!=task['turn_id']:
            raise Blocked('Codex recovered a different turn identity')
        if observation.turn_id:
            task['turn_id']=observation.turn_id; app._save(task)
        if observation.result and observation.result.turn_id!=observation.turn_id:
            raise Blocked('Recovered result has a different turn identity')
        return observation

    async def paused(self, task):
        """Read back Codex progress without restoring any revoked authority."""
        if task.get('phase')!='executing': return task
        try:
            observation=await self.observe(task)
            if observation.status=='completed':
                if observation.result:
                    self.app._store_result(task,observation.result)
                else:
                    task.update(phase='terminal_result',terminal_error=observation.reason or 'Completed turn has no recoverable structured result')
            elif observation.status in ('interrupted','failed'):
                task['phase']='terminal_'+observation.status
            task['reason']=observation.reason or 'Access remains paused; known turn is '+observation.status
        except Exception as exc:
            task['reason']=str(exc)
        task['status']='paused'; self.app._save(task)
        return task

    async def one(self, task):
        app=self.app; phase=task.get('phase')
        try:
            if phase=='complete' and task.get('status')=='finished': return task
            if task.get('status')=='paused': return await self.paused(task)
            if phase in ('reporting','complete'):
                return await app._handle({'action':'reconcile_reports','task_id':task['task_id']})
            await app._task_access(task)
            if phase == 'creating_chat' and task.get('chat_id') and not task.get('client_request_id'):
                # The create response was committed; only the known chat may run.
                task['phase']=phase='captured'; app._save(task)
            if phase == 'captured':
                if app.monitoring.has_unfinished_execution():
                    raise Blocked('Another external execution remains unresolved; captured work is retained')
                if (task.get('codex_create_intent') and not task.get('chat_id')) or task.get('client_request_id'):
                    raise Blocked('Captured work has an external intent; reconcile it before continuing')
                text=self.snapshot(task); inputs=self.inputs(task)
                app._validate_topic_binding(task)
                if task.get('project_id'):
                    project=await app._project(task['group_id'])
                    if project.get('project_id')!=task['project_id'] or project.get('cwd')!=task['cwd']:
                        raise Blocked('Captured task destination differs from its current group assignment')
                    if task.get('chat_id'):
                        placement=await app._placement(task)
                        if placement['status']=='unresolved': raise Blocked(placement['reason'])
                result=await app._start_captured(task,text,inputs)
                await app._finish_result(task,result,inputs)
            elif phase == 'terminal_result':
                if task.get('terminal_error'): raise Blocked(task['terminal_error'])
                data=json.loads((Path(task['folder'])/f"run-result-{task['run']}.json").read_text())
                data['input_evidence']=tuple(InputEvidence(**item) for item in data.get('input_evidence',[]))
                result=RunResult(**data)
                if task.get('turn_id') and result.turn_id!=task['turn_id']:
                    raise Blocked('Saved result has a different turn identity')
                await app._finish_result(task,result,self.inputs(task))
            elif phase == 'creating_chat':
                raise Blocked('Chat creation outcome is unresolved; no replacement chat will be created')
            elif phase == 'executing':
                observation=await self.observe(task)
                if observation.status=='completed':
                    # Protocol completion is final even if structured output is missing.
                    task['phase']='terminal_result'; app._save(task)
                    if observation.result is None:
                        task['terminal_error']=observation.reason or 'Completed turn has no recoverable structured result'
                        raise Blocked(task['terminal_error'])
                    if observation.result.turn_id!=observation.turn_id:
                        raise Blocked('Recovered result has a different turn identity')
                    # Keep terminal output even when original validation blocks delivery.
                    app._store_result(task,observation.result)
                    await app._finish_result(task,observation.result,self.inputs(task))
                elif observation.status in ('interrupted','failed'):
                    task['phase']='terminal_'+observation.status
                    raise Blocked(observation.reason or 'Known turn is '+observation.status+'; inspect retained progress before continuing')
                else:
                    raise Blocked(observation.reason or 'Known turn is still running or cannot be observed; no new turn was started')
            elif phase == 'capturing_inputs':
                raise Blocked('Input capture was interrupted; retain files and inspect incomplete inputs before retrying')
            else:
                raise Blocked(task.get('reason') or 'Task has no automatically recoverable progress')
        except Exception as exc:
            task.update(status='blocked',reason=str(exc)); app._save(task)
        return task

    async def recover(self, task_id=None):
        app=self.app
        app.monitoring.recover_unbound()
        tasks=[app._task(task_id)] if task_id else [json.loads(row[0]) for row in app.db.execute('SELECT data FROM tasks ORDER BY rowid')]
        outcomes=[]
        # Reconcile external intents before admitting captured work to execution.
        tasks.sort(key=lambda task: task.get('phase') not in ('creating_chat','executing'))
        for task in tasks:
            if task.get('phase') is None or task.get('status')=='linked': continue
            outcome=await self.one(task)
            app.monitoring.record_recovery_outcome(outcome)
            outcomes.append(outcome)
        return {'status':'blocked' if any(t['status'] in ('blocked','paused') for t in outcomes) else 'recovered','tasks':outcomes}
