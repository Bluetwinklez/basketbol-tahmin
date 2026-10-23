"""Venue-to-venue schedule proxies; never an assertion of actual team itineraries."""
import json, math
from pathlib import Path
from .quality import timestamp


def distance(a,b):
    points=[]
    for p in (a,b):
        lat,lon=float(p['latitude']),float(p['longitude'])
        if not math.isfinite(lat+lon) or not -90<=lat<=90 or not -180<=lon<=180:
            raise ValueError('Invalid venue coordinates')
        points.append((math.radians(lat),math.radians(lon)))
    (x,y),(u,v)=points
    h=math.sin((u-x)/2)**2+math.cos(x)*math.cos(u)*math.sin((v-y)/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1.,max(0.,h))))


def context(snapshot,registry,event_id,as_of):
    cutoff=timestamp(as_of)
    if timestamp(snapshot['captured_at_utc'])>cutoff or timestamp(registry['captured_at_utc'])>cutoff:
        raise ValueError('Venue observations unavailable at requested cutoff')
    choices=[r for r in snapshot['games'] if r['event_id']==event_id]
    if len(choices)!=1:raise ValueError('Unknown or ambiguous fixture')
    f=choices[0];start=timestamp(f['start_utc'])
    if cutoff>=start:raise ValueError('Pregame context requires a pretipoff cutoff')
    venues=registry['venues'];destination=venues.get(f['venue_id']);teams={}
    for team in (f['home'],f['away']):
        past=[r for r in snapshot['games'] if r.get('played') and team in (r['home'],r['away'])
              and timestamp(r['start_utc'])<cutoff.floor('D')]
        previous=max(past,key=lambda r:timestamp(r['start_utc'])) if past else None
        origin=venues.get(previous['venue_id']) if previous else None
        value=dict(known=bool(origin and destination),previous_event_id=previous['event_id'] if previous else None,
            previous_venue_id=previous['venue_id'] if previous else None,
            elapsed_tipoff_hours=(start-timestamp(previous['start_utc'])).total_seconds()/3600 if previous else None,
            scheduled_leg_km=distance(origin,destination) if origin and destination else None,
            timezone_shift_hours=None)
        if origin and destination:
            a=start.tz_convert(origin['timezone']).utcoffset().total_seconds()/3600
            b=start.tz_convert(destination['timezone']).utcoffset().total_seconds()/3600
            value['timezone_shift_hours']=b-a
        teams[team]=value
    return dict(event_id=event_id,as_of_utc=cutoff.isoformat(),venue_id=f['venue_id'],teams=teams,
        source_url=snapshot['source_url'],source_freshness_verified=snapshot.get('source_freshness_verified',False),
        used_in_default_model=False,
        note='Straight-line distance from last observed venue to scheduled venue, not actual travel, flights or full recovery time. Unknown coordinates remain null. Cached schedules require current confirmation. No accuracy gain established.')


def local_context(event_id,as_of):
    return context(json.loads(Path('data/context/venue_schedule.json').read_text()),
        json.loads(Path('data/context/venues.json').read_text()),event_id,as_of)
