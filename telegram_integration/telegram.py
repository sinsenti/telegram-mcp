"""Telethon capabilities; every resolved peer remains inside the selected folder."""
from datetime import datetime, timezone
from pathlib import Path
import secrets
from urllib.parse import urlparse, parse_qs
from dataclasses import replace
from telethon import utils
from telethon.tl import functions, types
from .contracts import Blocked, Context, Message, Attachment, GroupMetadata

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
        if isinstance(selected,(types.DialogFilter,types.DialogFilterChatlist)) and not getattr(selected,'groups',False):
            # Explicit folders need only their selected peers. Re-read the filter
            # and entity metadata each time; enumerating all dialogs per operation
            # triggers unrelated account reads and Telegram flood waits.
            peers={utils.get_peer_id(p):p for p in selected.include_peers + selected.pinned_peers}
            allowed=set()
            for identity, peer in peers.items():
                if identity in excluded:
                    continue
                entity=await self.client.get_entity(peer)
                if utils.get_peer_id(entity) != identity:
                    raise Blocked('Resolved folder peer differs from the included peer')
                if isinstance(entity,types.Chat) or isinstance(entity,types.Channel) and (entity.megagroup or entity.gigagroup):
                    allowed.add(identity)
            return allowed
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

    async def group_metadata(self, group_id):
        peer = await self._peer(group_id)
        entity = await self.client.get_entity(peer)
        if utils.get_peer_id(entity) != group_id:
            raise Blocked('Telegram resolved a different group metadata destination')
        await self._peer(group_id)
        return GroupMetadata(group_id, entity.title)

    async def message(self, group_id, message_id):
        peer=await self._peer(group_id)
        message=await self.client.get_messages(peer,ids=message_id)
        if message_id == 1 and (message is None or not getattr(message,'reply_to',None)):
            entity=await self.client.get_entity(peer)
            if getattr(entity,'forum',False):
                return Message(group_id,1,'',topic_id=1,is_topic_root=True)
        if message is None:
            raise Blocked('Selected Telegram message is missing or inaccessible')
        if message.chat_id != group_id:
            raise Blocked('Selected message belongs to a different group')
        selected=self._normalize(message)
        if selected.topic_id is None:
            peer=await self._peer(group_id)
            entity=await self.client.get_entity(peer)
            if getattr(entity,'forum',False):
                selected=replace(selected,topic_id=1)
        return selected

    async def resolve_link(self, link):
        parsed=urlparse(link)
        query=parse_qs(parsed.query,keep_blank_values=True)
        if parsed.scheme not in ('https','http') or parsed.netloc not in ('t.me','telegram.me') or parsed.fragment:
            raise Blocked('Unsupported Telegram message/topic link')
        if set(query)-{'thread','single'} or any(len(values)!=1 for values in query.values()):
            raise Blocked('Unsupported or ambiguous Telegram link parameters; comment redirects are not supported')
        parts=parsed.path.strip('/').split('/')
        private=parts[0]=='c'
        if private:
            if len(parts) not in (3,4) or not parts[1].isdigit() or int(parts[1]) <= 0:
                raise Blocked('Invalid private Telegram link')
            group=utils.get_peer_id(types.PeerChannel(int(parts[1])))
            numbers=parts[2:]
        else:
            if len(parts) not in (2,3) or not parts[0] or not all(ch.isalnum() or ch=='_' for ch in parts[0]):
                raise Blocked('Invalid public Telegram link')
            peer=await self.client.get_input_entity(parts[0])
            group=utils.get_peer_id(peer)
            numbers=parts[1:]
        if any(not value.isdigit() or int(value)<=0 for value in numbers):
            raise Blocked('Invalid Telegram message/topic identity')
        thread=int(numbers[0]) if len(numbers)==2 else None
        if 'thread' in query:
            value=query['thread'][0]
            if not value.isdigit() or int(value)<=0 or thread not in (None,int(value)):
                raise Blocked('Inconsistent Telegram thread identity')
            thread=int(value)
        selected=await self.message(group,int(numbers[-1]))
        if thread is not None and selected.topic_id != thread:
            raise Blocked('Telegram link thread differs from the actual message topic')
        return selected

    async def download(self, group_id, message_id, attachment, file):
        peer=await self._peer(group_id)
        raw=await self.client.get_messages(peer,ids=message_id)
        if raw is None or raw.chat_id!=group_id or self._normalize(raw).attachment!=attachment:
            raise Blocked('Selected attachment changed or disappeared before download')
        await self._peer(group_id)
        # Exact exclusively-created file handle; Telegram's untrusted filename is
        # metadata only. No thumbnails, conversions, or downloader-chosen paths.
        result=await self.client.download_media(raw,file=file)
        if result is None:
            raise Blocked('Telegram returned no original attachment')
        if result is not file:
            raise Blocked('Telegram returned an unexpected download destination')

    @staticmethod
    def _normalize(message):
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
        attachment=None
        document=getattr(message,'document',None)
        photo=getattr(message,'photo',None)
        if document is None and isinstance(message.media,types.MessageMediaDocument):
            document=message.media.document
        if photo is None and isinstance(message.media,types.MessageMediaPhoto):
            photo=message.media.photo
        if isinstance(document,types.Document):
            name=next((a.file_name for a in document.attributes if isinstance(a,types.DocumentAttributeFilename)), 'unnamed.bin')
            attachment=Attachment(f'document-{document.id}',name,document.mime_type,document.size)
        elif isinstance(photo,types.Photo):
            attachment=Attachment(f'photo-{photo.id}','photo.jpg','image/jpeg')
        return Message(message.chat_id,message.id,message.raw_text or '',has_attachment,topic_id,
                       getattr(header,'reply_to_msg_id',None),isinstance(message.action,types.MessageActionTopicCreate),attachment)

    async def context(self, group_id, message_id, scope):
        if scope not in ('message','topic'):
            raise Blocked('Selection scope must be message or topic')
        selected=await self.message(group_id,message_id)
        topic=selected.topic_id
        general=topic == 1
        if topic is None and scope == 'topic':
            peer=await self._peer(group_id)
            entity=await self.client.get_entity(peer)
            if not getattr(entity,'forum',False):
                raise Blocked('Whole-topic selection requires a Telegram forum topic')
            topic=1
            general=True
        candidates={selected.message_id:selected}
        if topic is not None and not general:
            root=await self.message(group_id,topic)
            candidates[root.message_id]=root
        # Explicit page RPCs revalidate access before every remote fetch, without
        # refetching the complete folder and dialog list for each buffered item.
        async for raw in self._history(group_id,None if general else topic or selected.message_id):
            item=self._normalize(raw)
            if general:
                if item.topic_id not in (None,1):
                    continue
            elif topic and item.topic_id != topic and item.message_id != topic:
                raise Blocked('History returned a message outside the selected topic')
            candidates.setdefault(item.message_id,item)
        ordered=sorted(candidates.values(),key=lambda item:item.message_id)
        if scope == 'topic':
            return Context(tuple(ordered))
        included={selected.message_id}
        for item in ordered:
            if item.reply_to_id in included:
                included.add(item.message_id)
        # A missing intermediate parent can hide a descendant. Expose the gap;
        # execution must never assume that such a subset is the whole discussion.
        missing={item.reply_to_id for item in ordered if item.reply_to_id and
                 item.reply_to_id not in candidates and item.reply_to_id != topic and
                 item.message_id > selected.message_id}
        return Context(tuple(item for item in ordered if item.message_id in included),not missing,
                       'Reply ancestry is missing; descendants cannot be classified completely' if missing else None)

    async def search(self, group_id, query):
        found={}
        async for raw in self._history(group_id,query=query):
            item=self._normalize(raw)
            found[item.message_id]=item
        return tuple(found[key] for key in sorted(found))

    async def _history(self, group_id, reply_to=None, query=None):
        offset=0
        while True:
            peer=await self._peer(group_id)
            arguments=dict(peer=peer,offset_id=offset,offset_date=None,add_offset=0,limit=100,max_id=0,min_id=0,hash=0)
            if query is not None:
                arguments.pop('offset_date')
                request=functions.messages.SearchRequest(q=query,filter=types.InputMessagesFilterEmpty(),
                    min_date=None,max_date=None,**arguments)
            elif reply_to is not None:
                request=functions.messages.GetRepliesRequest(msg_id=reply_to,**arguments)
            else:
                request=functions.messages.GetHistoryRequest(**arguments)
            result=await self.client(request)
            if not hasattr(result,'messages'):
                raise Blocked('Telegram history response has no complete page')
            if not result.messages:
                return
            next_offset=min(item.id for item in result.messages)
            if next_offset <= 0 or offset and next_offset >= offset:
                raise Blocked('Telegram history pagination did not advance')
            for raw in result.messages:
                if getattr(raw,'chat_id',None) != group_id:
                    raise Blocked('History contains a missing message or a different destination')
                yield raw
            offset=next_offset

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
            random_id=secrets.randbits(63),reply_to=types.InputReplyToMessage(message_id,top_msg_id=None if topic_id == 1 else topic_id)))
        return self._message_id(result)

    async def send_document(self, group_id, message_id, document: Path, topic_id):
        await self._peer(group_id)
        uploaded=await self.client.upload_file(str(document))
        peer=await self._peer(group_id)  # Membership can change during upload.
        result=await self.client(functions.messages.SendMediaRequest(peer=peer,
            media=types.InputMediaUploadedDocument(file=uploaded,mime_type='text/markdown',
                attributes=[types.DocumentAttributeFilename(document.name)]),message='',
            random_id=secrets.randbits(63),reply_to=types.InputReplyToMessage(message_id,top_msg_id=None if topic_id == 1 else topic_id)))
        return self._message_id(result)
