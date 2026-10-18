"""NC Wealth Base scanner pages; reads precomputed bases from Supabase, no client-side keys."""

import gzip
import io
import logging
from datetime import date
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

MIN_DATE = date(2000, 1, 1)
RANGES = list(range(5, 55, 5))

# One page layout, two stock universes. 'kp' keeps each page's widgets separate.
CONFIGS = {
    'futures': dict(
        bucket='base-breakouts', kp='base',
        title='Base Breakout Scanner',
        subtitle='Stocks trading in a tight range, and the ones that broke out',
        note='Universe: futures stocks.',
    ),
    'investing': dict(
        bucket='investing_baseformation', kp='ibase',
        title='Base Formation Scanner',
        subtitle='₹1,000–50,000 cr market-cap stocks trading in a tight range, and the ones that broke out',
        note='Universe: companies with a market cap between ₹1,000 cr and ₹50,000 cr, refreshed monthly.',
    ),
}

# Real calendar durations (dates inclusive: 18/09 -> 17/10 = 1 month).
# Order must match DURATIONS in build_bases.py (DurationRank 1..11).
DURATIONS = {
    '15 days': pd.DateOffset(days=15),
    '1 month': pd.DateOffset(months=1),
    '45 days': pd.DateOffset(days=45),
    '2 months': pd.DateOffset(months=2),
    '3 months': pd.DateOffset(months=3),
    '6 months': pd.DateOffset(months=6),
    '1 year': pd.DateOffset(years=1),
    '2 years': pd.DateOffset(years=2),
    '3 years': pd.DateOffset(years=3),
    '4 years': pd.DateOffset(years=4),
    '5 years': pd.DateOffset(years=5),
}
BASIS_FILES = {
    'Closing prices': 'bases_close.csv.gz',
    'High–Low (intraday)': 'bases_highlow.csv.gz',
}
STATUS_OPTIONS = ['Base Formation Ongoing', 'Breakout', 'Breakdown', 'Wick-out']
STATUS_HELP = {
    'Base Formation Ongoing': 'Still inside the range on the latest data day',
    'Breakout': 'Closed above the base high after the base',
    'Breakdown': 'Closed below the base low after the base',
    'Wick-out': 'High–Low basis only: poked outside intraday but closed inside',
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_bases(bucket, filename):
    url = st.secrets['SUPABASE_URL'].rstrip('/')
    key = st.secrets['SUPABASE_SERVICE_ROLE_KEY']
    endpoint = f"{url}/storage/v1/object/authenticated/{bucket}/{quote(filename)}"
    response = requests.get(endpoint, headers={
        'apikey': key, 'Authorization': f'Bearer {key}'
    }, timeout=120)
    response.raise_for_status()
    raw = gzip.decompress(response.content)
    dtypes = {'Symbol': 'category', 'Status': 'category'}
    header = pd.read_csv(io.BytesIO(raw), nrows=0).columns
    if 'Company' in header:
        dtypes['Company'] = 'category'
    return pd.read_csv(io.BytesIO(raw), dtype=dtypes,
                       parse_dates=['BaseStart', 'BaseEnd', 'ExitDate'])


def filter_bases(df, start, rng, duration_label, statuses):
    """
    Bases in the chosen range whose FULL length meets the chosen duration, and which
    are still forming or ended (breakout / breakdown / wick-out) on or after `start`.
    """
    min_rank = list(DURATIONS).index(duration_label) + 1      # same order as build_bases.py
    d = df[(df['RangePct'] == rng) & (df['Status'].isin(statuses)) &
           (df['DurationRank'] >= min_rank) & (df['BaseEnd'] >= pd.Timestamp(start))].copy()
    return d.sort_values(['BaseEnd', 'CalendarDays'], ascending=[False, False])


def _stock_list(title, symbols, key):
    st.subheader(f'{title} ({len(symbols)})')
    if symbols:
        st.write(', '.join(symbols))
    else:
        st.info('No stocks match in this category.')
    st.download_button('Download list (CSV)',
                       pd.DataFrame({'Stock': symbols}).to_csv(index=False).encode('utf-8'),
                       file_name=f'{key}.csv', mime='text/csv', key=f'dl_{key}')


def show_base_page(ist, universe='futures'):
    cfg = CONFIGS[universe]
    kp = cfg['kp']
    st.markdown(f'<div class="tagline">{cfg["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{cfg["subtitle"]}</div>', unsafe_allow_html=True)

    basis = st.radio('Range measured on', list(BASIS_FILES), horizontal=True, key=f'{kp}_basis',
                     help='Closing prices ignore intraday spikes. High–Low is stricter.')
    c1, c2, c3 = st.columns(3)
    start = c1.date_input('Active on or after', value=date(date.today().year, 1, 1), min_value=MIN_DATE,
                          max_value=date.today(), key=f'{kp}_start',
                          help='Shows bases that are still forming, or that ended (breakout / breakdown) on or after this date.')
    rng = c2.selectbox('Range (%)', RANGES, index=1, key=f'{kp}_range', format_func=lambda x: f'{x}%')
    dur = c3.selectbox('Base lasted at least', list(DURATIONS), index=2, key=f'{kp}_dur')
    statuses = st.multiselect('Show', STATUS_OPTIONS,
                              default=['Base Formation Ongoing', 'Breakout'], key=f'{kp}_status')
    st.caption('  \n'.join(f'**{k}**: {v}' for k, v in STATUS_HELP.items()))
    st.caption(cfg['note'])

    if st.button('Scan Bases', key=f'{kp}_scan'):
        try:
            data = get_bases(cfg['bucket'], BASIS_FILES[basis])
            st.session_state[f'{kp}_result'] = (
                filter_bases(data, start, rng, dur, statuses),
                dict(basis=basis, start=start, rng=rng, dur=dur),
            )
        except Exception as exc:
            logging.getLogger('base_page').error('Base load failed: %s: %s',
                                                 type(exc).__name__, str(exc).split('?')[0])
            st.error('Unable to load base data. Check Supabase access and the latest upload.')
            return

    if f'{kp}_result' not in st.session_state:
        return
    res, p = st.session_state[f'{kp}_result']
    st.markdown(f"**{p['basis']} · {p['rng']}% range · ≥ {p['dur']} · active on/after {p['start']:%d %b %Y}**")

    if res.empty:
        st.info('No bases match these filters.')
        return

    shown = [s for s in STATUS_OPTIONS if s in set(res['Status'].astype(str))]
    for i in range(0, len(shown), 2):
        cols = st.columns(2, gap='large')
        for col, status in zip(cols, shown[i:i + 2]):
            symbols = sorted(set(res.loc[res['Status'] == status, 'Symbol'].astype(str)))
            with col:
                _stock_list(status, symbols, f"{kp}_{status.lower().replace(' ', '_')}_{p['rng']}pct")

    st.subheader(f'Detailed bases ({len(res)})')
    columns = ['Symbol'] + (['Company'] if 'Company' in res.columns else []) + [
        'Status', 'BaseStart', 'BaseEnd', 'CalendarDays', 'BaseLow', 'BaseHigh', 'ActualRangePct', 'ExitDate']
    out = res[columns].copy()
    for c in ('BaseStart', 'BaseEnd', 'ExitDate'):
        out[c] = out[c].dt.strftime('%Y-%m-%d')
    for c in ('Symbol', 'Company', 'Status'):
        if c in out.columns:
            out[c] = out[c].astype(str)
    st.dataframe(out.head(2000), hide_index=True, use_container_width=True)
    st.download_button('Download detailed bases (CSV)', out.to_csv(index=False).encode('utf-8-sig'),
                       file_name=f"{kp}_bases_{p['rng']}pct_{p['dur'].replace(' ', '')}.csv",
                       mime='text/csv', key=f'{kp}_dl_detail')
    st.caption('One stock can appear several times (different base periods). '
               'Lists show unique symbols; the table and CSV keep every base. '
               'Days are calendar days of the full base. Research only; not investment advice.')
