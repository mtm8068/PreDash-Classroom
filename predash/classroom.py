"""Classroom credentials are held only in the current Streamlit session."""
import streamlit as st
from predash.kis import KIS, BrokerError


def account_settings(mode=None):
    settings = st.session_state.get('classroom_credentials', {})
    selected = mode or settings.get('mode', 'demo')
    if selected != settings.get('mode'):
        return dict(mode=selected, key='', secret='', cano='', product='')
    return dict(mode=selected, **{k: settings.get(k, '') for k in ('key','secret','cano','product')})


def connection_form():
    if st.session_state.pop('classroom_clear_inputs', False):
        for key in ('class_key','class_secret','class_cano','class_product'):
            st.session_state.pop(key, None)
    st.subheader('내 증권사 계좌 연결')
    st.caption('각자 Fork한 앱에서 본인 키를 입력하세요. 현재 접속 세션에서만 사용합니다.')
    if st.session_state.get('classroom_credentials'):
        st.success('계좌 연결됨 · ' + ('모의투자' if account_settings()['mode']=='demo' else '실전 조회'))
        if st.button('계좌 연결 해제'):
            authorized = st.session_state.get('authorized')
            st.session_state.clear()
            if authorized: st.session_state.authorized = True
            st.rerun()
        return
    with st.form('classroom_connection'):
        mode = st.radio('투자 환경', ['모의투자','실전 조회'], horizontal=True, key='class_mode')
        key = st.text_input('App Key', type='password', key='class_key')
        secret = st.text_input('App Secret', type='password', key='class_secret')
        cano = st.text_input('계좌번호 앞 8자리', type='password', max_chars=8, key='class_cano')
        product = st.text_input('계좌번호 뒤 2자리', max_chars=2, key='class_product')
        submitted = st.form_submit_button('연결 확인', type='primary', use_container_width=True)
    if submitted:
        settings = dict(mode='demo' if mode=='모의투자' else 'real',key=key.strip(),secret=secret.strip(),cano=cano.strip(),product=product.strip())
        try:
            client = KIS(settings=settings)
            with st.spinner('잔고 조회 권한을 확인합니다…'):
                client.balance()
            st.session_state.classroom_credentials = settings
            st.session_state['_kis_client_demo' if settings['mode']=='demo' else '_kis_client'] = client
            st.session_state.classroom_clear_inputs = True
            st.rerun()
        except BrokerError as error:
            st.error(str(error))
    st.info('연결 해제와 로그아웃은 키·잔고·접속 중 실습 기록을 지웁니다. 필요한 기록은 먼저 백업하세요.')
    st.divider()
    st.subheader('KIS API 연결 진단')
    st.caption('토큰 발급과 잔고 조회를 순서대로 테스트합니다. App Key·Secret·계좌번호는 결과에 표시하지 않습니다.')
    if st.button('KIS API 연결 진단', key='kis_api_diagnosis', use_container_width=True):
        mode_value = st.session_state.get('class_mode', 'demo')
        settings = dict(mode=mode_value, key=st.session_state.get('class_key', '').strip(),
                        secret=st.session_state.get('class_secret', '').strip(),
                        cano=st.session_state.get('class_cano', '').strip(),
                        product=st.session_state.get('class_product', '').strip())
        try:
            client = KIS(settings=settings)
            diagnosis = client.diagnose()
            st.session_state.kis_diagnosis = diagnosis
        except BrokerError as error:
            st.session_state.kis_diagnosis = {'mode': settings['mode'], 'error': str(error),
                                               'environment_mismatch': True}
    diagnosis = st.session_state.get('kis_diagnosis')
    if diagnosis:
        st.caption('선택 환경: ' + ('모의투자' if diagnosis.get('mode') == 'demo' else '실전 조회') + ' · 엔드포인트: ' + diagnosis.get('endpoint', '확인 불가'))
        token = diagnosis.get('token', {})
        balance = diagnosis.get('balance', {})
        st.write(('✅' if token.get('ok') else '❌') + ' 토큰 발급: ' + ('성공' if token.get('ok') else '실패') +
                 (f" · HTTP {token.get('http')} · KIS 코드 {token.get('msg_cd') or '없음'}" if token else ''))
        if balance:
            st.write(('✅' if balance.get('ok') else '❌') + ' 잔고 조회: ' + ('성공' if balance.get('ok') else '실패') +
                     f" · HTTP {balance.get('http')} · KIS 코드 {balance.get('msg_cd') or '없음'}")
            if balance.get('ok') and balance.get('positions') is not None:
                st.caption(f"잔고 응답 보유종목 행: {balance['positions']}건")
            elif balance.get('reason'):
                st.warning(balance['reason'])
        if diagnosis.get('error'):
            st.error(diagnosis['error'])
        if diagnosis.get('environment_mismatch'):
            st.warning('실전/모의 환경 불일치 가능성이 있습니다. 선택한 환경의 KIS App Key·App Secret과 해당 환경의 계좌번호가 한 세트인지 확인하세요.')
