def expected(home,away,advantage=0):
    return 1/(1+10**(-(home-away+advantage)/400))
def update(home,away,home_score,away_score,k,advantage=0,mov=False):
    probability=expected(home,away,advantage)
    multiplier=1.
    if mov:
        signed=(home-away+advantage)*(1 if home_score>away_score else -1)
        denominator=7.5+.006*signed
        if denominator<=0:
            raise ValueError('MOV denominator is nonpositive: unsupported Elo gap')
        multiplier=(abs(home_score-away_score)+3)**.8/denominator
    delta=k*multiplier*((home_score>away_score)-probability)
    return home+delta,away-delta
