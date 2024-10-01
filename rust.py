from rustplus import RustSocket
from rustplus import ServerDetails

class rust_client:
    rust_socket = None

    def create_session(self, ip:str, port:str, steamid:str, player_token:str) -> ServerDetails:
        server_details = ServerDetails(ip=ip, port=port, steamid=steamid, player_token=player_token)
        self.rust_socket = RustSocket(server_details=server_details)
        return ServerDetails
    
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