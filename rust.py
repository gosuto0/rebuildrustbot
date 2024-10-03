from rustplus import RustSocket
from rustplus import ServerDetails
from rustplus import EntityEventPayload, TeamEventPayload, ChatEventPayload, ProtobufEvent, ChatEvent, EntityEvent, TeamEvent

class rust_client:    
    def __init__(self, ip:str, port:str, player_id:str, player_token:str):
        self.talk_buffer = []
        server_details = ServerDetails(ip=ip, port=port, player_id=player_id, player_token=player_token)
        self.rust_socket = RustSocket(server_details=server_details)
    
        @ChatEvent(server_details)
        async def chat(event: ChatEventPayload):
            data = {
                "name": event.message.name,
                "message": event.message.message
            }
            if "[DISCORD]" not in event.message.message:
                self.talk_buffer.append(data)
            
    async def connect_session(self) -> bool:
        if self.rust_socket:
            await self.rust_socket.connect()
            return True
        else: return False

    async def disconnect_session(self) -> bool:
        if self.rust_socket:
            await self.rust_socket.disconnect()
            return True
        else: return False

    async def get_server_info(self):
        return await self.rust_socket.get_info()
    
    async def get_server_time(self):
        return await self.rust_socket.get_time()
    
    async def get_server_markers(self):
        return await self.rust_socket.get_markers()

    async def get_team_info(self):
        return await self.rust_socket.get_team_info()
    
    async def send_team_chat(self, content):
        await self.rust_socket.send_team_message(content)
        
    #保存しているbufferを返します。
    #またこの際bufferの中身はすべて削除されます。
    def get_talk_buffer(self):
        talk_buffer = self.talk_buffer
        self.talk_buffer = []
        return talk_buffer