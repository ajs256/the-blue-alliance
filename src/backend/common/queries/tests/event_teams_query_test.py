from typing import List, Optional

from google.appengine.ext import ndb

from backend.common.models.event import Event
from backend.common.models.event_team import EventTeam
from backend.common.models.keys import EventKey
from backend.common.models.team import Team
from backend.common.queries.team_query import EventTeamsQuery


def preseed_teams(start_team: int, end_team: Optional[int] = None) -> List[ndb.Key]:
    end_team = end_team or start_team
    stored = ndb.put_multi(
        [
            Team(
                id=f"frc{i}",
                team_number=i,
            )
            for i in range(start_team, end_team + 1)
        ]
    )
    assert len(stored) == (end_team - start_team + 1)
    return stored


def preseed_event_teams(team_keys: List[ndb.Key], event_key: EventKey) -> None:
    event_teams = [
        EventTeam(
            id=f"{event_key}_{t.id()}",
            event=ndb.Key(Event, event_key),
            team=t,
            year=int(event_key[:4]),
        )
        for t in team_keys
    ]
    ndb.put_multi(event_teams)


def test_no_data() -> None:
    teams = EventTeamsQuery(event_key="2020ct").fetch()
    assert teams == []


def test_get_data() -> None:
    stored_teams = preseed_teams(1, 10)
    preseed_event_teams(stored_teams, "2020ct")

    teams = EventTeamsQuery(event_key="2020ct").fetch()
    assert len(teams) == len(stored_teams)
