"""NC Wealth RSI Divergence dashboard; reads published signals, no client-side keys."""
import io
import logging
from datetime import date, datetime, timedelta
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st


@st.cache_data(ttl=300, show_spinner=False)
def get_signals():
    url = st.secrets['SUPABASE_URL'].rstrip('/')
    key = st.secrets['SUPABASE_SERVICE_ROLE_KEY']
    endpoint = f"{url}/storage/v1/object/authenticated/rsi-divergence/{quote('signals.csv')}"
    response = requests.get(endpoint, headers={
        'apikey': key, 'Authorization': f'Bearer {key}'
    }, timeout=40)
    response.raise_for_status()
    return pd.read_csv(io.BytesIO(response.content), dtype={'Stock': str})


def show_rsi_page(navigate, ist):
    st.markdown('<div class="tagline">Triple RSI Divergence</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Bullish and bearish confirmed daily divergence</div>', unsafe_allow_html=True)
    today = datetime.now(ist).date()
    minimum = date(2025, 1, 1)
    if 'rsi_start' not in st.session_state:
        st.session_state.rsi_start = today - timedelta(days=29) if today - timedelta(days=29) >= minimum else minimum
    if 'rsi_end' not in st.session_state:
        st.session_state.rsi_end = today

    c1, c2 = st.columns(2)
    if c1.button('Last 15 days', key='rsi15'):
        st.session_state.rsi_start = max(minimum, today - timedelta(days=14))
        st.session_state.rsi_end = today
    if c2.button('Last 30 days', key='rsi30'):
        st.session_state.rsi_start = max(minimum, today - timedelta(days=29))
        st.session_state.rsi_end = today

    d1, d2 = st.columns(2)
    start = d1.date_input('From', key='rsi_start', min_value=minimum, max_value=today)
    end = d2.date_input('To', key='rsi_end', min_value=minimum, max_value=today)
    if start > end:
        st.warning('Start must be on or before end.')
        return
    st.caption('Dates refer to the confirmation candle, one trading session after Point C.')
    if not st.button('Scan Divergence', key='scan_rsi'):
        return

    try:
        df = get_signals()
        required = {'Divergence Type', 'Confirmation Date', 'Stock', 'A Date', 'B Date', 'C Date'}
        if not required.issubset(df.columns):
            if 'Divergence Type' not in df.columns:
                st.warning('Supabase still contains bullish-only signals. Run the updated RSI GitHub Action once, then scan again.')
                return
            raise ValueError('Missing columns: ' + ', '.join(sorted(required - set(df.columns))))
        df['Divergence Type'] = df['Divergence Type'].astype(str).str.strip().str.title()
        df['Stock'] = df['Stock'].fillna('').astype(str).str.strip().str.upper()
        dates = pd.to_datetime(df['Confirmation Date'], errors='coerce')
        df = df.loc[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end)) &
                    df['Divergence Type'].isin(['Bullish', 'Bearish'])].copy()
        df = df.sort_values(['Confirmation Date', 'Stock'], ascending=[False, True])

        st.subheader('Divergence stock lists')
        bullish = sorted(set(df.loc[df['Divergence Type'] == 'Bullish', 'Stock']) - {'', 'NAN'})
        bearish = sorted(set(df.loc[df['Divergence Type'] == 'Bearish', 'Stock']) - {'', 'NAN'})
        left, right = st.columns(2, gap='large')
        with left:
            st.subheader(f'📈 Bullish Divergence ({len(bullish)} stocks)')
            if bullish:
                st.write(', '.join(bullish))
            else:
                st.info('No bullish signals in this date range.')
            st.download_button('Download Bullish Stock List (CSV)',
                               pd.DataFrame({'Stock': bullish}).to_csv(index=False).encode('utf-8'),
                               file_name=f'bullish_rsi_stocks_{start}_{end}.csv',
                               mime='text/csv', key='rsi_bullish_download')
        with right:
            st.subheader(f'📉 Bearish Divergence ({len(bearish)} stocks)')
            if bearish:
                st.write(', '.join(bearish))
            else:
                st.info('No bearish signals in this date range.')
            st.download_button('Download Bearish Stock List (CSV)',
                               pd.DataFrame({'Stock': bearish}).to_csv(index=False).encode('utf-8'),
                               file_name=f'bearish_rsi_stocks_{start}_{end}.csv',
                               mime='text/csv', key='rsi_bearish_download')

        st.subheader(f'Detailed confirmed signals ({len(df)})')
        if df.empty:
            st.info('No confirmed divergence signals in this date range.')
            return
        st.caption('Latest confirmation in selected range: ' + str(df['Confirmation Date'].max()))
        visible = ['Divergence Type', 'Confirmation Date', 'Stock', 'A Date', 'B Date', 'C Date']
        st.dataframe(df[visible], hide_index=True, use_container_width=True)
        st.download_button('Download Detailed Signals (CSV)',
                           df.to_csv(index=False).encode('utf-8-sig'),
                           file_name=f'rsi_bullish_bearish_{start}_{end}.csv',
                           mime='text/csv', key='rsi_detail_download')
        st.caption('One stock can have multiple confirmations in the chosen range. Stock lists show unique symbols; the detailed table and CSV retain every signal. Research only; not investment advice.')
    except Exception as exc:
        logging.getLogger('rsi_page').error('RSI signals load failed: %s: %s', type(exc).__name__, str(exc).split('?')[0])
        st.error('Unable to load RSI signals. Check Supabase access and the GitHub Actions update.')
