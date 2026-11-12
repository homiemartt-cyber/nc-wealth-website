"""Historical Nifty 500 price-high breakout and relative-strength page."""
from datetime import date
from io import BytesIO
from urllib.parse import quote
import pandas as pd
import requests
import streamlit as st

BUCKET = 'historical-rs-screener'
PRICE_LABELS = {'ATH': 'All-time high', 'FIVE_YEAR_HIGH': '5-year high', 'WEEK_52_HIGH': '52-week high'}

@st.cache_data(ttl=3600, show_spinner=False)
def load_year(year: int) -> pd.DataFrame:
    url = st.secrets['SUPABASE_URL'].rstrip('/')
    key = st.secrets['SUPABASE_SERVICE_ROLE_KEY']
    path = quote(f'calculations/{year}.parquet', safe='/')
    endpoint = f'{url}/storage/v1/object/authenticated/{BUCKET}/{path}'
    r = requests.get(endpoint, headers={'apikey': key, 'Authorization': f'Bearer {key}'}, timeout=180)
    r.raise_for_status()
    df = pd.read_parquet(BytesIO(r.content))
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df

def _bool_col(df, name):
    if name not in df:
        raise ValueError(f'Missing calculated column: {name}')
    s = df[name]
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False)
    return s.astype('string').str.lower().isin(['true', '1'])

def scan(df, start, end, price_types, price_logic, periods, rs_logic, min_rs):
    if not price_types:
        raise ValueError('Select at least one price-high condition.')
    df = df.loc[df['Date'].between(pd.Timestamp(start), pd.Timestamp(end))].copy()
    if df.empty:
        return df
    price_tests = [_bool_col(df, f'{p}_Breakout') for p in price_types]
    p = pd.concat(price_tests, axis=1)
    mask = p.all(axis=1) if price_logic == 'ALL' else p.any(axis=1)
    if periods:
        rs_tests = []
        for months in periods:
            col = f'RS_{months}M_pp'
            if col not in df:
                raise ValueError(f'Missing calculated column: {col}')
            rs_tests.append(pd.to_numeric(df[col], errors='coerce').ge(min_rs))
        r = pd.concat(rs_tests, axis=1)
        mask &= r.all(axis=1) if rs_logic == 'ALL' else r.any(axis=1)
    return df.loc[mask].sort_values(['Date', 'Symbol'], ascending=[False, True])

def show_historical_rs_page():
    st.markdown('<div class="tagline">Historical ATH & Relative Strength Screener</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Historical Nifty 500 constituents · Intraday High breakouts · RS vs Nifty 500</div>', unsafe_allow_html=True)
    st.caption('Fixed rules: daily intraday High ≥ the previous reference High. Near-high stocks are excluded. ATH refers to available downloaded price history.')
    today = date.today()
    with st.form('historical_rs_form'):
        a, b = st.columns(2)
        start = a.date_input('From date', value=date(2026, 1, 1), min_value=date(2023, 1, 1), max_value=today)
        end = b.date_input('To date', value=today, min_value=date(2023, 1, 1), max_value=today)
        price_types = st.multiselect('Price-high breakout conditions', list(PRICE_LABELS), default=['ATH'], format_func=lambda x: PRICE_LABELS[x])
        price_logic = st.radio('When multiple high conditions are selected', ['ANY', 'ALL'], horizontal=True, help='ANY = one selected high type; ALL = every selected high type.')
        periods = st.multiselect('RS periods (months)', [12, 6, 3, 1], default=[6, 3], format_func=lambda x: f'{x}M')
        rs_logic = st.radio('RS combination', ['ALL', 'ANY'], horizontal=True)
        min_rs = st.number_input('Minimum RS (percentage points)', value=0.0, step=0.5)
        submitted = st.form_submit_button('Run Scanner', use_container_width=True, type='primary')
    if submitted:
        if start > end:
            st.error('From date must not be after To date.')
            return
        if not price_types:
            st.error('Select at least one price-high condition.')
            return
        try:
            with st.spinner('Loading historical calculations from Supabase...'):
                frames = [load_year(y) for y in range(start.year, end.year + 1)]
                result = scan(pd.concat(frames, ignore_index=True), start, end, price_types, price_logic, periods, rs_logic, min_rs)
            st.session_state['historical_rs_result'] = result
            st.session_state['historical_rs_filters'] = (start, end)
        except Exception as exc:
            st.error(f'Unable to run scanner: {type(exc).__name__}: {exc}')
            return
    if 'historical_rs_result' not in st.session_state:
        return
    result = st.session_state['historical_rs_result']
    if result.empty:
        st.info('No matching signals for these conditions and dates.')
        return
    x, y, z = st.columns(3)
    x.metric('Signals', f'{len(result):,}')
    y.metric('Unique stocks', f'{result["Symbol"].nunique():,}')
    z.metric('Signal dates', f'{result["Date"].nunique():,}')
    dates = sorted(result['Date'].dt.date.dropna().unique(), reverse=True)
    chosen = st.selectbox('View stock list for date', dates, format_func=lambda d: d.strftime('%d %b %Y'))
    daily = result.loc[result['Date'].dt.date == chosen]
    symbols = sorted(daily['Symbol'].dropna().astype(str).unique().tolist())
    st.subheader(f'Stocks on {chosen:%d %b %Y} ({len(symbols)})')
    st.write(', '.join(symbols))
    st.download_button('Download date-wise stock list (CSV)', pd.DataFrame({'Symbol': symbols}).to_csv(index=False).encode('utf-8-sig'), file_name=f'historical_rs_{chosen}.csv', mime='text/csv')
    st.subheader('Detailed signals')
    columns = ['Date', 'Symbol', 'Company', 'Industry', 'Industry Group', 'Open', 'High', 'Low', 'Close', 'ATH_Previous_High', 'FIVE_YEAR_HIGH_Previous_High', 'WEEK_52_HIGH_Previous_High', 'ATH_Breakout', 'FIVE_YEAR_HIGH_Breakout', 'WEEK_52_HIGH_Breakout', 'RS_12M_pp', 'RS_6M_pp', 'RS_3M_pp', 'RS_1M_pp']
    view = result[[c for c in columns if c in result.columns]].copy()
    view['Date'] = view['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(view.head(5000), hide_index=True, use_container_width=True)
    st.caption('The on-screen table displays up to 5,000 rows; the CSV includes all matches. One stock can appear on multiple dates.')
    st.download_button('Download all matching signals (CSV)', view.to_csv(index=False).encode('utf-8-sig'), file_name='historical_ath_rs_matches.csv', mime='text/csv')
    st.caption('For research and education only. Price history may be incomplete, and historical constituents depend on the supplied membership files.')
