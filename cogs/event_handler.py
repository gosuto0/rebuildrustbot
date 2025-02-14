from dataclasses import dataclass
from typing import List, Optional, Callable


@dataclass
class ServerEvent:
    type: str
    location: str


class EventHandler:
    def __init__(self):
        self.events: List[ServerEvent] = []
        self.dead_players: List[str] = []

    def handle_death_event(self, member, grid_position) -> Optional[str]:
        if not member.is_alive and member.steam_id not in self.dead_players:
            self.dead_players.append(member.steam_id)
            return f"{member.name} is dead ({grid_position})"
        elif member.is_alive and member.steam_id in self.dead_players:
            self.dead_players.remove(member.steam_id)
        return None

    def handle_server_events(self, markers, get_grid_fn: Callable) -> List[ServerEvent]:
        events = []
        for marker in markers:
            event = self._create_event(marker, get_grid_fn)
            if event:
                events.append(event)
        return events

    def _create_event(self, marker, get_grid_fn: Callable) -> Optional[ServerEvent]:
        from .constants import EVENT_TYPES
        if marker.type in EVENT_TYPES:
            return ServerEvent(
                type=EVENT_TYPES[marker.type],
                location=get_grid_fn(marker.x, marker.y)
            )
        return None
