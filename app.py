import streamlit as st

st.set_page_config(page_title='NC Wealth Corporation', page_icon='📈', layout='wide', initial_sidebar_state='collapsed')
SCREENER_URL = 'https://ema-stock-screener.streamlit.app/'

st.markdown('''<style>
#MainMenu, footer, header {visibility:hidden;}
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
.stLinkButton>a {background:#d8bb80!important;color:#0d1826!important;border:0!important;border-radius:10px!important;font-weight:700!important;}
.back .stButton>button {background:transparent;color:#d8bb80;border:1px solid #5d6774;}
</style>''', unsafe_allow_html=True)

if 'page' not in st.session_state:
    st.session_state.page = 'Home'

def navigate(page):
    st.session_state.page = page
    st.rerun()

if st.session_state.page == 'Home':
    st.markdown('<div class="brand">NC WEALTH CORPORATION</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline">Compounding Relationships.</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">INVESTMENT RESEARCH &nbsp;·&nbsp; TRADING STRATEGIES</div>', unsafe_allow_html=True)
    left, right = st.columns(2, gap='large')
    with left:
        st.markdown('<div class="card"><div class="card-title">Investing</div><div class="card-text">Explore research-driven investment strategies, screening tools and opportunities.</div></div>', unsafe_allow_html=True)
        if st.button('Explore Investing →', key='invest'): navigate('Investing')
    with right:
        st.markdown('<div class="card"><div class="card-title">Trading</div><div class="card-text">A dedicated space for trading strategies, analysis and risk management.</div></div>', unsafe_allow_html=True)
        if st.button('Explore Trading →', key='trade'): navigate('Trading')
else:
    st.markdown('<div class="back">', unsafe_allow_html=True)
    if st.button('← Back to Home'): navigate('Home')
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand">NC WEALTH CORPORATION</div>', unsafe_allow_html=True)
    if st.session_state.page == 'Investing':
        st.markdown('<div class="tagline">Investing</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Explore our investment research tools</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title">EMA Stock Screener</div><div class="card-text">Screen stocks using EMA-based technical filters, historical market-cap snapshots and momentum rankings.</div></div>', unsafe_allow_html=True)
        st.link_button('Open EMA Stock Screener ↗', SCREENER_URL, use_container_width=True)
        st.caption('Opens the existing EMA Stock Screener application in a new tab.')
    else:
        st.markdown('<div class="tagline">Trading</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Trading strategies and tools are coming soon.</div>', unsafe_allow_html=True)
