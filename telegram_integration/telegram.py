"""Telethon capabilities; every resolved peer remains inside the selected folder."""
from datetime import datetime, timezone
from pathlib import Path
import secrets
from telethon import utils
from telethon.tl import functions, types
from .contracts import Blocked, Message

class TelethonAdapter:
    def __init__(self, client):
        self.client = client
        self.folder_id = None

    async def folders(self):
        result = await self.client(functions.messages.GetDialogFiltersRequest())
        return [{'id':f.id,'title':getattr(f.title,'text',str(f.title))}
                for f in result.filters if hasattr(f,'title')]

    async def allowed_groups(self, folder_id: int) -> set[int]:
        result = await self.client(functions.messages.GetDialogFiltersRequest())
        selected = next((f for f in result.filters if getattr(f,'id',None)==folder_id), None)
        if selected is None or not hasattr(selected,'include_peers'):
            raise Blocked('Selected Telegram folder is missing or unsupported; choose its stable ID')
        self.folder_id = folder_id
        included = {utils.get_peer_id(p) for p in selected.include_peers + selected.pinned_peers}
        excluded = {utils.get_peer_id(p) for p in getattr(selected,'exclude_peers',[])}
        allowed=set()
        async for dialog in self.client.iter_dialogs():
            if not dialog.is_group or dialog.id in excluded:
                continue
            if dialog.id in included:
                allowed.add(dialog.id)
                continue
            if not getattr(selected,'groups',False):
                continue
            archived = getattr(dialog.dialog,'folder_id',None)==1
            mentions = getattr(dialog.dialog,'unread_mentions_count',0)
            if getattr(selected,'exclude_archived',False) and archived:
                continue
            if getattr(selected,'exclude_read',False) and not (dialog.unread_count or mentions):
                continue
            if getattr(selected,'exclude_muted',False):
                settings = getattr(dialog.dialog,'notify_settings',None)
                mute_until = getattr(settings,'mute_until',None)
                # Unspecified peer settings inherit account defaults. Without those
                # defaults, dynamic muted membership cannot be established safely.
                if mute_until is None:
                    raise Blocked('Folder uses inherited mute settings; effective membership needs verification')
                now=datetime.now(timezone.utc)
                muted = mute_until > now if isinstance(mute_until,datetime) else mute_until > now.timestamp()
                if muted and not (mentions and not archived):
                    continue
            allowed.add(dialog.id)
        return allowed

    async def _peer(self, group_id):
        if self.folder_id is None or group_id not in await self.allowed_groups(self.folder_id):
            raise Blocked('Group is outside the selected Telegram folder')
        peer=await self.client.get_input_entity(group_id)
        if utils.get_peer_id(peer)!=group_id:
            raise Blocked('Resolved Telegram peer differs from the allowed group')
        return peer

    async def message(self, group_id, message_id):
        peer=await self._peer(group_id)
        message=await self.client.get_messages(peer,ids=message_id)
        if message is None:
            raise Blocked('Selected Telegram message is missing or inaccessible')
        if message.chat_id != group_id:
            raise Blocked('Selected message belongs to a different group')
        header=message.reply_to
        topic_id=None
        if header and getattr(header,'forum_topic',False):
            topic_id=getattr(header,'reply_to_top_id',None) or header.reply_to_msg_id
        if isinstance(message.action,types.MessageActionTopicCreate):
            topic_id=message.id
        # Web previews enrich the selected URL's text; even a preview containing
        # a photo/document is not a separately selected attachment. Other media
        # (including unsupported types) must still block this text-only slice.
        has_attachment = message.media is not None and not isinstance(
            message.media, (types.MessageMediaWebPage, types.MessageMediaEmpty))
        return Message(message.chat_id,message.id,message.raw_text or '',has_attachment,topic_id)

    @staticmethod
    def _message_id(result):
        if isinstance(result,types.UpdateShortSentMessage):
            return str(result.id)
        for update in getattr(result,'updates',[]):
            if isinstance(update,types.UpdateMessageID):
                return str(update.id)
        raise Blocked('Telegram send outcome lacks a message identity; inspect source before retrying')

    async def send_text(self, group_id, message_id, text, topic_id):
        peer=await self._peer(group_id)
        # Explanation is intentionally short; result body goes into the Markdown file.
        if len(text)>4000:
            raise Blocked('Explanation is too long for Telegram; inspect local result')
        result=await self.client(functions.messages.SendMessageRequest(peer=peer,message=text,
            random_id=secrets.randbits(63),reply_to=types.InputReplyToMessage(message_id,top_msg_id=topic_id)))
        return self._message_id(result)

    async def send_document(self, group_id, message_id, document: Path, topic_id):
        await self._peer(group_id)
        uploaded=await self.client.upload_file(str(document))
        peer=await self._peer(group_id)  # Membership can change during upload.
        result=await self.client(functions.messages.SendMediaRequest(peer=peer,
            media=types.InputMediaUploadedDocument(file=uploaded,mime_type='text/markdown',
                attributes=[types.DocumentAttributeFilename(document.name)]),message='',
            random_id=secrets.randbits(63),reply_to=types.InputReplyToMessage(message_id,top_msg_id=topic_id)))
        return self._message_id(result)
