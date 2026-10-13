import io
from datetime import datetime, timedelta, date
from urllib.parse import quote
import pandas as pd
import requests
import streamlit as st

@st.cache_data(ttl=300, show_spinner=False)
def get_signals():
    url=st.secrets['SUPABASE_URL'].rstrip('/')
    key=st.secrets['SUPABASE_SERVICE_ROLE_KEY']
    endpoint=f"{url}/storage/v1/object/authenticated/rsi-divergence/{quote('signals.csv')}"
    r=requests.get(endpoint,headers={'apikey':key,'Authorization':f'Bearer {key}'},timeout=40)
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content),dtype={'Stock':str})

def show_rsi_page(navigate, ist):
    if st.button('← Back to Trading',key='back_rsi'): navigate('Trading')
    st.markdown('<div class="tagline">Triple Bullish RSI Divergence</div>',unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Confirmed daily futures-stock divergence</div>',unsafe_allow_html=True)
    today=datetime.now(ist).date()
    if 'rsi_start' not in st.session_state:st.session_state.rsi_start=date(2025,1,1)
    if 'rsi_end' not in st.session_state:st.session_state.rsi_end=today
    c1,c2,c3=st.columns(3)
    if c1.button('Last 15 days',key='rsi15'):
        st.session_state.rsi_start=today-timedelta(days=14);st.session_state.rsi_end=today
    if c2.button('Last 30 days',key='rsi30'):
        st.session_state.rsi_start=today-timedelta(days=29);st.session_state.rsi_end=today
    if c3.button('From 01/01/2025',key='rsi_all'):
        st.session_state.rsi_start=date(2025,1,1);st.session_state.rsi_end=today
    d1,d2=st.columns(2)
    start=d1.date_input('From',key='rsi_start',min_value=date(2025,1,1),max_value=today)
    end=d2.date_input('To',key='rsi_end',min_value=date(2025,1,1),max_value=today)
    if start>end:st.warning('Start must be on or before end.');return
    st.caption('Dates refer to the confirmation candle, one trading session after Point C.')
    if not st.button('Scan Divergence',key='scan_rsi'):return
    try:
        df=get_signals()
        expected={'Confirmation Date','Stock','A Date','B Date','C Date'}
        if not expected.issubset(df.columns):
            raise ValueError('Missing signal columns: '+', '.join(sorted(expected-set(df.columns))))
        dates=pd.to_datetime(df['Confirmation Date'],errors='coerce')
        df=df.loc[(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end))].copy()
        df=df.sort_values(['Confirmation Date','Stock'],ascending=[False,True])
        st.metric('Confirmed signals',len(df))
        if not df.empty:
            st.caption('Latest confirmation in selected range: '+str(df['Confirmation Date'].max()))
        if df.empty:st.info('No confirmed signals in this date range.');return
        st.dataframe(df[['Confirmation Date','Stock','A Date','B Date','C Date']],hide_index=True,use_container_width=True)
        st.download_button('Download complete CSV',df.to_csv(index=False).encode(),file_name=f'rsi_divergence_{start}_{end}.csv',mime='text/csv')
        st.caption('Research use only. Not investment advice.')
    except Exception:
        st.error('Signals unavailable. Run the GitHub Actions daily updater first and verify Supabase secrets.')
