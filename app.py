import io
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title='NC Wealth Corporation', page_icon='📈', layout='wide', initial_sidebar_state='collapsed')
SCREENER_URL = 'https://ema-stock-screener.streamlit.app/'
BUCKET = 'momentum-trading'
FILES = ('01&16_Review_Date_Wise_Active_Stocks.csv', 'Expiry_Review_Date_Wise_Active_Stocks.csv')
IST = ZoneInfo('Asia/Kolkata')

st.markdown('''<style>
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden;}
.stApp {background:radial-gradient(circle at 50% 10%,#182d44 0%,#0b1625 55%,#080f19 100%);color:#f5f2ea;}
.block-container {max-width:1060px;padding-top:5rem;padding-bottom:5rem;}
h1,h2,h3,p {color:#f5f2ea!important;}
.brand {text-align:center;color:#d8bb80;letter-spacing:.34em;font-size:clamp(1rem,2vw,1.5rem);font-weight:700;margin-top:3.5rem;}
.tagline {text-align:center;font-size:clamp(2.5rem,5vw,4.6rem);font-family:Georgia,serif;line-height:1.15;margin:1.5rem auto 1rem;}
.subtitle {text-align:center;color:#aeb9c8;font-size:1rem;letter-spacing:.09em;margin-bottom:3rem;}
.card {background:linear-gradient(135deg,#192d43,#112136);border:1px solid #3b4e63;border-radius:18px;padding:2.2rem 1.8rem;min-height:190px;}
.card-title {font-size:1.65rem;font-family:Georgia,serif;color:#f6f0e5;margin-bottom:.7rem;}
.card-text {color:#b3c0cf;line-height:1.7;}
.gold {color:#d8bb80!important;}
.stButton>button {width:100%;background:#d8bb80;color:#0d1826;border:0;border-radius:10px;padding:.75rem 1rem;font-weight:700;}
.stButton>button:hover {background:#ecd3a3;color:#0d1826;}
.stDownloadButton>button {background:#d8bb80!important;color:#0d1826!important;border:0!important;border-radius:10px!important;font-weight:700!important;}
.stDownloadButton>button:hover {background:#ecd3a3!important;color:#0d1826!important;}
.stDownloadButton>button p {color:#0d1826!important;}
.stLinkButton>a {background:#d8bb80!important;color:#0d1826!important;border:0!important;border-radius:10px!important;font-weight:700!important;}
.back .stButton>button {background:transparent;color:#d8bb80;border:1px solid #5d6774;}
</style>''', unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_snapshot(filename):
    # Credentials stay on Streamlit's server and are never sent to the browser.
    url = st.secrets['SUPABASE_URL'].rstrip('/')
    key = st.secrets['SUPABASE_SERVICE_ROLE_KEY']
    object_path = quote(f'historical-watchlists/{filename}', safe='/')
    endpoint = f'{url}/storage/v1/object/authenticated/{BUCKET}/{object_path}'
    response = requests.get(endpoint, headers={'apikey': key, 'Authorization': f'Bearer {key}'}, timeout=40)
    response.raise_for_status()
    frame = pd.read_csv(io.BytesIO(response.content), dtype={'Stock': str, 'Theme': str})
    required = {'Review_Date', 'Data_Date', 'Theme', 'Stock'}
    if not required.issubset(frame.columns):
        raise ValueError(f'Missing columns in {filename}: {required - set(frame.columns)}')
    frame['Data_Date'] = pd.to_datetime(frame['Data_Date'], errors='coerce').dt.normalize()
    frame['Review_Date'] = pd.to_datetime(frame['Review_Date'], errors='coerce').dt.normalize()
    frame['Theme'] = frame['Theme'].astype(str).str.strip().str.upper()
    frame['Stock'] = frame['Stock'].astype(str).str.strip().str.upper()
    return frame.dropna(subset=['Data_Date', 'Review_Date'])

def effective_default_date():
    now = datetime.now(IST)
    return now.date() if now.time() >= time(17, 0) else (now - timedelta(days=1)).date()

def select_snapshot(frame, selected_date):
    # Data_Date is the EOD date used to build the watchlist; review dates can
    # fall on the following calendar day. The user asked for EOD availability.
    eligible = frame[frame['Data_Date'] <= pd.Timestamp(selected_date)]
    if eligible.empty:
        return eligible, None
    latest = eligible['Data_Date'].max()
    # One snapshot per strategy, never mix earlier and later snapshots.
    candidates = eligible[eligible['Data_Date'] == latest]
    review = candidates['Review_Date'].max()
    return candidates[candidates['Review_Date'] == review], latest

def show_list(title, symbols, prefix):
    st.subheader(f'{title} ({len(symbols)})')
    if symbols:
        st.write(', '.join(symbols))
    else:
        st.info('No active stocks in this category for the selected date.')
    csv_bytes = pd.DataFrame({'Symbol': symbols}).to_csv(index=False).encode('utf-8')
    txt_bytes = ','.join(symbols).encode('utf-8')
    c1, c2 = st.columns(2)
    with c1:
        st.download_button('Download CSV', data=csv_bytes, file_name=f'{prefix}.csv', mime='text/csv', use_container_width=True)
    with c2:
        st.download_button('Download TXT', data=txt_bytes, file_name=f'{prefix}.txt', mime='text/plain', use_container_width=True)

# Streamlit native pages have distinct URL paths and browser history.
# Keep the navigation sidebar hidden; use the existing NC Wealth buttons.

def common_header():
    if st.button('← Back to Home', key='back_home'):
        st.switch_page(PAGES['Home'])
    st.markdown('<div class="brand">NC WEALTH CORPORATION</div>', unsafe_allow_html=True)

def home_page():
    st.markdown('<div class="brand">NC WEALTH CORPORATION</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline">Compounding Relationships.</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">INVESTMENT RESEARCH &nbsp;·&nbsp; TRADING STRATEGIES</div>', unsafe_allow_html=True)
    left, right = st.columns(2, gap='large')
    with left:
        st.markdown('<div class="card"><div class="card-title">Investing</div><div class="card-text">Explore research-driven investment strategies, screening tools and opportunities.</div></div>', unsafe_allow_html=True)
        if st.button('Explore Investing →', key='invest'): st.switch_page(PAGES['Investing'])
    with right:
        st.markdown('<div class="card"><div class="card-title">Trading</div><div class="card-text">A dedicated space for trading strategies, analysis and risk management.</div></div>', unsafe_allow_html=True)
        if st.button('Explore Trading →', key='trade'): st.switch_page(PAGES['Trading'])
def investing_page():
    common_header()
    st.markdown('<div class="tagline">Investing</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Explore our investment research tools</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title">EMA Stock Screener</div><div class="card-text">Screen stocks using EMA-based technical filters, historical market-cap snapshots and momentum rankings.</div></div>', unsafe_allow_html=True)
    st.link_button('Open EMA Stock Screener ↗', SCREENER_URL, use_container_width=True)
    st.caption('Opens the existing EMA Stock Screener application in a new tab.')

def trading_page():
    common_header()
    st.markdown('<div class="tagline">Trading</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Explore our trading research tools</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title">Momentum Trading Watchlist</div><div class="card-text">Explore bullish and bearish stocks using 25- and 50-session price momentum.</div></div>', unsafe_allow_html=True)
    if st.button('Open Momentum Watchlist →', key='open_momentum'): st.switch_page(PAGES['Momentum'])
    st.markdown('<div class="card"><div class="card-title">Triple Bullish &amp; Bearish RSI Divergence</div><div class="card-text">Find confirmed A–B–C bullish and bearish RSI divergences across futures stocks and indices.</div></div>', unsafe_allow_html=True)
    if st.button('Open RSI Divergence Scanner →', key='open_rsi'): st.switch_page(PAGES['RSI'])

def momentum_page():
    common_header()
    st.markdown('<div class="tagline">Momentum Trading Watchlist</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Bullish and bearish momentum stocks</div>', unsafe_allow_html=True)
    cutoff = effective_default_date()
    selected = st.date_input('Select Date', value=cutoff, max_value=datetime.now(IST).date(), min_value=date(2025, 10, 10))
    try:
        frames = [fetch_snapshot(name) for name in FILES]
        snapshots = [select_snapshot(frame, selected) for frame in frames]
        dates = [dt for _, dt in snapshots if dt is not None]
        if not dates:
            st.warning('No watchlist is available for this date. Please select a later date.')
        else:
            most_recent = max(dates)
            st.markdown(f'**Data as of: {most_recent.strftime("%d %B %Y")}**')
            combined = pd.concat([frame for frame, _ in snapshots if not frame.empty], ignore_index=True)
            bullish = sorted(set(combined.loc[combined['Theme'] == 'BULLISH', 'Stock']) - {'', 'NAN'})
            bearish = sorted(set(combined.loc[combined['Theme'] == 'BEARISH', 'Stock']) - {'', 'NAN'})
            c1, c2 = st.columns(2, gap='large')
            with c1:
                show_list('📈 Bullish Momentum', bullish, f'bullish_momentum_{selected:%Y%m%d}')
            with c2:
                show_list('📉 Bearish Momentum', bearish, f'bearish_momentum_{selected:%Y%m%d}')
            st.markdown('### How are stocks selected?')
            st.write('We evaluate stock-price performance over the previous **25 and 50 trading sessions**. Stocks in the **top 30 in both periods** are considered for the bullish watchlist, while stocks in the **bottom 30 in both periods** are considered for the bearish watchlist. Existing selections are reviewed periodically.')
            st.caption('For research and educational purposes only. Not investment advice.')
    except Exception as exc:
        st.error('Unable to load the momentum watchlist. Check the Streamlit Supabase secrets and the published CSV files.')
        import logging
        logging.getLogger("momentum").error("Watchlist loading failed: %s: %s", type(exc).__name__, str(exc).split("?")[0])
        # Avoid showing credential-bearing request details to website visitors.


def rsi_page():
    common_header()
    from rsi_page import show_rsi_page
    show_rsi_page(lambda destination: st.switch_page(PAGES[destination]), IST)

PAGES = {
    'Home': st.Page(home_page, title='Home', icon='🏠', default=True, url_path=''),
    'Investing': st.Page(investing_page, title='Investing', icon='📊', url_path='investing'),
    'Trading': st.Page(trading_page, title='Trading', icon='📈', url_path='trading'),
    'Momentum': st.Page(momentum_page, title='Momentum Watchlist', icon='📈', url_path='momentum'),
    'RSI': st.Page(rsi_page, title='RSI Divergence', icon='📉', url_path='rsi-divergence'),
}

navigation = st.navigation(list(PAGES.values()), position='hidden')
navigation.run()
