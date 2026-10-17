"""NC Wealth Base Breakout scanner; reads precomputed bases, no client-side keys."""

import gzip
import io
import logging
from datetime import date
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
import streamlit as st

BUCKET = 'base-breakouts'
MIN_DATE = date(2000, 1, 1)
RANGES = list(range(5, 55, 5))

# Real calendar durations (dates inclusive: 18/09 -> 17/10 = 1 month)
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
def get_bases(filename):
    url = st.secrets['SUPABASE_URL'].rstrip('/')
    key = st.secrets['SUPABASE_SERVICE_ROLE_KEY']
    endpoint = f"{url}/storage/v1/object/authenticated/{BUCKET}/{quote(filename)}"
    response = requests.get(endpoint, headers={
        'apikey': key, 'Authorization': f'Bearer {key}'
    }, timeout=120)
    response.raise_for_status()
    raw = gzip.decompress(response.content)
    df = pd.read_csv(io.BytesIO(raw), dtype={'Symbol': 'category', 'Status': 'category'},
                     parse_dates=['BaseStart', 'BaseEnd', 'ExitDate'])
    return df


def filter_bases(df, start, rng, duration_label, statuses):
    """
    Bases that overlap [start, today]. If a base began before `start`, only the
    part from `start` onwards is counted (a slice of a valid base is still a valid
    base inside the same range).
    """
    start = pd.Timestamp(start)
    d = df[(df['RangePct'] == rng) & (df['Status'].isin(statuses)) & (df['BaseEnd'] >= start)].copy()
    if d.empty:
        return d
    eff_start = d['BaseStart'].where(d['BaseStart'] >= start, start)
    threshold = pd.DatetimeIndex(eff_start) + DURATIONS[duration_label] - pd.Timedelta(days=1)
    ok = np.asarray(threshold <= pd.DatetimeIndex(d['BaseEnd']))
    d = d.loc[ok].copy()
    d['InRangeSince'] = eff_start[ok]
    d['DaysInRange'] = (d['BaseEnd'] - d['InRangeSince']).dt.days + 1
    return d.sort_values(['BaseEnd', 'DaysInRange'], ascending=[False, False])


def _stock_list(title, symbols, key):
    st.subheader(f'{title} ({len(symbols)})')
    if symbols:
        st.write(', '.join(symbols))
    else:
        st.info('No stocks match in this category.')
    st.download_button('Download list (CSV)',
                       pd.DataFrame({'Stock': symbols}).to_csv(index=False).encode('utf-8'),
                       file_name=f'{key}.csv', mime='text/csv', key=f'dl_{key}')


def show_base_page(ist):
    st.markdown('<div class="tagline">Base Breakout Scanner</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Stocks trading in a tight range, and the ones that broke out</div>',
                unsafe_allow_html=True)

    basis = st.radio('Range measured on', list(BASIS_FILES), horizontal=True, key='base_basis',
                     help='Closing prices ignore intraday spikes. High–Low is stricter.')
    c1, c2, c3 = st.columns(3)
    start = c1.date_input('From', value=date(date.today().year, 1, 1), min_value=MIN_DATE,
                          max_value=date.today(), key='base_start')
    rng = c2.selectbox('Range (%)', RANGES, index=1, key='base_range',
                       format_func=lambda x: f'{x}%')
    dur = c3.selectbox('Stays in range for at least', list(DURATIONS), index=2, key='base_dur')
    statuses = st.multiselect('Show', STATUS_OPTIONS,
                              default=['Base Formation Ongoing', 'Breakout'], key='base_status')
    st.caption('  \n'.join(f'**{k}**: {v}' for k, v in STATUS_HELP.items()))

    if st.button('Scan Bases', key='scan_base'):
        try:
            data = get_bases(BASIS_FILES[basis])
            st.session_state['base_result'] = (
                filter_bases(data, start, rng, dur, statuses),
                dict(basis=basis, start=start, rng=rng, dur=dur),
            )
        except Exception as exc:
            logging.getLogger('base_page').error('Base load failed: %s: %s',
                                                 type(exc).__name__, str(exc).split('?')[0])
            st.error('Unable to load base data. Check Supabase access and the latest upload.')
            return

    if 'base_result' not in st.session_state:
        return
    res, p = st.session_state['base_result']
    st.markdown(f"**{p['basis']} · {p['rng']}% range · ≥ {p['dur']} · from {p['start']:%d %b %Y}**")

    if res.empty:
        st.info('No bases match these filters.')
        return

    shown = [s for s in STATUS_OPTIONS if s in set(res['Status'].astype(str))]
    for i in range(0, len(shown), 2):
        cols = st.columns(2, gap='large')
        for col, status in zip(cols, shown[i:i + 2]):
            symbols = sorted(set(res.loc[res['Status'] == status, 'Symbol'].astype(str)))
            with col:
                _stock_list(status, symbols, f"{status.lower().replace(' ', '_')}_{p['rng']}pct")

    st.subheader(f'Detailed bases ({len(res)})')
    out = res[['Symbol', 'Status', 'InRangeSince', 'BaseEnd', 'DaysInRange',
               'BaseLow', 'BaseHigh', 'ActualRangePct', 'ExitDate']].copy()
    for c in ('InRangeSince', 'BaseEnd', 'ExitDate'):
        out[c] = out[c].dt.strftime('%Y-%m-%d')
    out['Symbol'] = out['Symbol'].astype(str)
    out['Status'] = out['Status'].astype(str)
    st.dataframe(out.head(2000), hide_index=True, use_container_width=True)
    st.download_button('Download detailed bases (CSV)', out.to_csv(index=False).encode('utf-8-sig'),
                       file_name=f"bases_{p['rng']}pct_{p['dur'].replace(' ', '')}.csv",
                       mime='text/csv', key='dl_base_detail')
    st.caption('One stock can appear several times (different base periods). '
               'Lists show unique symbols; the table and CSV keep every base. '
               'Base Low/High/Range describe the full base, which may start before your From date. '
               'Research only; not investment advice.')
