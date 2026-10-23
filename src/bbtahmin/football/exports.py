"""Full-report exports; browser filters never alter frozen forecasts."""
import csv
import io


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'"+value
    return value


def export_csv(report):
    stream = io.StringIO(newline=''); writer = csv.writer(stream)
    fields = ('league','date','home','away','status','model','home_probability','draw_probability',
              'away_probability','over_1.5','over_2.5','over_3.5','both_teams_score',
              'actual_home','actual_away','winner_correct','total_absolute_error','margin_absolute_error')
    writer.writerow(fields)
    for item in report['forecasts']:
        f, p, r = item['fixture'], item['prediction'], item.get('result') or {}
        values = [f['league'], f['date'], f['home_name'], f['away_name'], item['status'], p['model'],
                  *[p['probabilities'][k] for k in ('home','draw','away')],
                  *[p['over'][k] for k in ('1.5','2.5','3.5')], p['both_teams_score'],
                  *[r.get(k) for k in fields[-5:]]]
        writer.writerow([safe_cell(v) for v in values])
    return stream.getvalue().encode('utf-8-sig')


def markdown(report):
    def clean(value):
        return str(value).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')
    lines = ['# Football research', '', 'Community-source finals; official accuracy unavailable.',
             'Full report; display filters do not restrict this export.', '',
             '| Date | League | Fixture | Home / draw / away | Over 2.5 | Status |',
             '|---|---|---|---|---|---|']
    for item in report['forecasts']:
        f, p = item['fixture'], item['prediction']
        probabilities = ' / '.join(f"{100*p['probabilities'][k]:.1f}%" for k in ('home','draw','away'))
        lines.append('| '+' | '.join(map(clean, [f['date'], f['league'], f"{f['home_name']} - {f['away_name']}",
                                                probabilities, f"{100*p['over']['2.5']:.1f}%", item['status']]))+' |')
    return ('\n'.join(lines)+'\n').encode('utf8')
