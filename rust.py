from rustplus import RustSocket
from rustplus import ServerDetails
from rustplus import EntityEventPayload, TeamEventPayload, ChatEventPayload, ProtobufEvent, ChatEvent, EntityEvent, TeamEvent

class rust_client():
    server_details = None
    def create_session(self, ip:str, port:str, player_id:str, player_token:str) -> ServerDetails:
        self.server_details = ServerDetails(ip=ip, port=port, player_id=player_id, player_token=player_token)
        self.rust_socket = RustSocket(server_details=self.server_details)
    
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

    talk_buffer = []
    @ChatEvent(server_details)
    async def chat(self, event: ChatEventPayload):
        data = {
            "name": event.message.name,
            "message": event.message.message
        }
        self.talk_buffer.append(data)
        
    def get_talk_buffer(self):
        talk_buffer = self.talk_buffer
        self.talk_buffer = []
        return talk_buffer