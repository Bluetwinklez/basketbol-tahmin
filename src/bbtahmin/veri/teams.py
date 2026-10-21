"""Oran arşivi / Basketball Reference açık franchise eşlemesi."""
ALIASES = {
'ATL':['Atlanta','Atlanta Hawks'],'BOS':['Boston','Boston Celtics'],
'BRK':['Brooklyn','Brooklyn Nets','New Jersey','New Jersey Nets'],
'CHO':['Charlotte','Charlotte Hornets','Charlotte Bobcats'],
'CHI':['Chicago','Chicago Bulls'],'CLE':['Cleveland','Cleveland Cavaliers'],
'DAL':['Dallas','Dallas Mavericks'],'DEN':['Denver','Denver Nuggets'],
'DET':['Detroit','Detroit Pistons'],'GSW':['GoldenState','Golden State Warriors'],
'HOU':['Houston','Houston Rockets'],'IND':['Indiana','Indiana Pacers'],
'LAC':['LAClippers','Los Angeles Clippers'],'LAL':['LALakers','Los Angeles Lakers'],
'MEM':['Memphis','Memphis Grizzlies','Vancouver Grizzlies'],
'MIA':['Miami','Miami Heat'],'MIL':['Milwaukee','Milwaukee Bucks'],
'MIN':['Minnesota','Minnesota Timberwolves'],
'NOP':['NewOrleans','New Orleans Pelicans','New Orleans Hornets'],
'NYK':['NewYork','New York Knicks'],
'OKC':['OklahomaCity','Oklahoma City Thunder','Seattle','Seattle SuperSonics'],
'ORL':['Orlando','Orlando Magic'],'PHI':['Philadelphia','Philadelphia 76ers'],
'PHO':['Phoenix','Phoenix Suns'],'POR':['Portland','Portland Trail Blazers'],
'SAC':['Sacramento','Sacramento Kings'],'SAS':['SanAntonio','San Antonio Spurs'],
'TOR':['Toronto','Toronto Raptors'],'UTA':['Utah','Utah Jazz'],
'WAS':['Washington','Washington Wizards','Washington Bullets']}
def _key(name):
    # "LA Clippers", "L.A. Clippers" ve "LAClippers" aynı anahtara iner.
    return ''.join(ch for ch in str(name).casefold() if ch.isalnum())
def team_code(name):
    key=_key(name)
    for code,names in ALIASES.items():
        if key in {_key(n) for n in names+[code]}:
            return code
    raise ValueError(f'Eşleşmeyen takım: {name}')
