"""One-way, stable-identity reconciliation of Codex names and topic references."""
import asyncio
from pathlib import Path
from .contracts import Blocked


def topic_name(name):
    # Telegram's MTProto limit is UTF-8 bytes, not Unicode characters.
    return name.encode('utf-8')[:128].decode('utf-8', errors='ignore')


async def synchronize(app, task):
    if not task.get('chat_id') or not task.get('project_id') or task.get('topic_id') is None:
        raise Blocked('Reference synchronization requires a linked project chat topic')
    state = task.setdefault('reference_sync', {})
    group, topic = task['group_id'], task['topic_id']
    try:
        await app._access(group)
        observed = await asyncio.wait_for(app.codex.observe_chat(task['chat_id'], Path(task['cwd'])), 10)
        if observed.get('chat_id') != task['chat_id']:
            raise Blocked('Codex metadata resolved a different chat')
        name = observed.get('name')
        if name is not None and not isinstance(name, str):
            raise Blocked('Codex returned an invalid chat name')
        # Null is an absent title, never an instruction to overwrite a known one.
        if name and name.strip():
            state['name'] = name
        state['observation'] = {'status':'current' if name and name.strip() else 'pending'}
    except Exception as exc:
        state['observation'] = {'status':'failed','reason':str(exc)}
        # Metadata availability must not stall independent status/reference work.
        app._save(task)
    name = state.get('name')
    state['title'] = {'status':'pending'}
    if name:
        desired = topic_name(name)
        state['title'] = {'status':'pending','desired':desired}
        app._save(task)
        try:
            await app._access(group)
            current = await app.telegram.topic_title(group, topic)
            if current != desired:
                state['title']['status'] = 'uncertain'
                app._save(task)
                await app._access(group)
                await app.telegram.rename_topic(group, topic, desired)
                await app._access(group)
                if await app.telegram.topic_title(group, topic) != desired:
                    raise Blocked('Topic rename was not confirmed')
            state['title']['status'] = 'current'
        except Exception as exc:
            state['title'].update(status='failed',reason=str(exc))
    app._save(task)
    try:
        projects = await asyncio.to_thread(app.catalog.refresh)
        project = next((p for p in projects if p.id == task['project_id']), None)
        if project is None:
            raise Blocked('Linked project is absent from the current catalog')
        text = (f'Project: {project.name}\nChat: {name or "Title pending"}\n'
                f'Status: {task["status"]}\nCodex: codex://threads/{task["chat_id"]}\n'
                f'Chat ID: {task["chat_id"]}')
        state['desired_text'] = text
        reference = state.setdefault('reference', {'status':'pending'})
        identity = reference.get('message_id')
        if identity is None:
            if reference['status'] == 'uncertain':
                raise Blocked('Reference creation outcome is uncertain; inspect Telegram before retrying')
            await app._access(group)
            reference['status'] = 'uncertain'
            app._save(task)  # Crash/lost acknowledgment cannot blindly duplicate a reference.
            identity = await app.telegram.create_reference(group, topic, text)
            reference['message_id'] = str(identity)
            app._save(task)
        await app._access(group)
        current = await app.telegram.reference(group, topic, identity)
        if current['text'] != text:
            reference['status'] = 'uncertain'
            app._save(task)
            await app._access(group)
            await app.telegram.edit_reference(group, topic, identity, text)
            await app._access(group)
            current = await app.telegram.reference(group, topic, identity)
            if current['text'] != text:
                raise Blocked('Reference edit was not confirmed')
        reference.update(status='current',reason=None)
        app._save(task)
    except Exception as exc:
        reference = state.setdefault('reference', {})
        # Keep an uncertain create distinguishable from a known-ID recoverable failure.
        if reference.get('status') != 'uncertain' or reference.get('message_id') is not None:
            reference['status'] = 'failed'
        reference['reason'] = str(exc)
        state['pin'] = {'status':'pending','reason':'Reference has not been confirmed'}
        app._save(task)
        return task
    state['pin'] = {'status':'pending'}
    app._save(task)
    try:
        if not current.get('pinned'):
            await app._access(group)
            await app.telegram.pin_reference(group, topic, identity)
            await app._access(group)
            current = await app.telegram.reference(group, topic, identity)
            if not current.get('pinned'):
                raise Blocked('Reference pin was not confirmed')
        state['pin'] = {'status':'current'}
    except Exception as exc:
        state['pin'] = {'status':'failed','reason':str(exc)}
    app._save(task)
    return task
