"""Classroom credentials are held only in the current Streamlit session."""
import streamlit as st
from predash.kis import KIS, BrokerError


def account_settings(mode=None):
    settings = st.session_state.get('classroom_credentials', {})
    selected = mode or settings.get('mode', 'demo')
    if selected != settings.get('mode'):
        return dict(mode=selected, key='', secret='', cano='', product='')
    return dict(mode=selected, **{k: settings.get(k, '') for k in ('key','secret','cano','product')})


def _secret_value(name):
    try:
        value = st.secrets.get(name, '')
    except Exception:
        return ''
    return str(value).strip()


def _secret_settings(mode):
    if mode == 'demo':
        names = ('KIS_DEMO_APP_KEY', 'KIS_DEMO_APP_SECRET', 'KIS_DEMO_CANO', 'KIS_DEMO_ACNT_PRDT_CD')
    else:
        names = ('KIS_APP_KEY', 'KIS_APP_SECRET', 'KIS_CANO', 'KIS_ACNT_PRDT_CD')
    key, secret, cano, product = (_secret_value(name) for name in names)
    return {'mode': mode, 'key': key, 'secret': secret, 'cano': cano, 'product': product}


def _secret_status(settings):
    return {
        'App Key': bool(settings['key']),
        'App Secret': bool(settings['secret']),
        '계좌번호': bool(settings['cano']),
        '상품코드': bool(settings['product']),
    }


def _run_secret_diagnosis(mode):
    settings = _secret_settings(mode)
    status = _secret_status(settings)
    if not all(status.values()):
        return {
            'mode': mode,
            'configured': False,
            'missing': [label for label, present in status.items() if not present],
        }
    client = KIS(settings=settings)
    diagnosis = client.diagnose()
    diagnosis['configured'] = True
    return diagnosis


def _render_diagnosis(title, diagnosis):
    st.markdown(f'**{title}**')
    if not diagnosis.get('configured', True):
        st.error('Streamlit Secrets 설정이 완전하지 않습니다.')
        st.caption('누락: ' + ', '.join(diagnosis.get('missing', [])))
        return
    st.caption('엔드포인트: ' + diagnosis.get('endpoint', '확인 불가'))
    token = diagnosis.get('token', {})
    balance = diagnosis.get('balance', {})
    error = diagnosis.get('error')
    token_ok = token.get('ok')
    token_http = token.get('http') or diagnosis.get('http')
    token_code = token.get('msg_cd') or diagnosis.get('msg_cd')
    st.write(('✅' if token_ok else '❌') + ' 토큰 발급: ' + ('성공' if token_ok else '실패') +
             f' · HTTP {token_http or "없음"} · KIS 코드 {token_code or "없음"}')
    if balance:
        st.write(('✅' if balance.get('ok') else '❌') + ' 잔고 조회: ' + ('성공' if balance.get('ok') else '실패') +
                 f' · HTTP {balance.get("http") or "없음"} · KIS 코드 {balance.get("msg_cd") or "없음"}')
        if balance.get('ok') and balance.get('positions') is not None:
            st.caption(f'잔고 응답 보유종목 행: {balance["positions"]}건')
        elif balance.get('reason'):
            st.warning(balance['reason'])
    if error:
        st.error(error)
    if diagnosis.get('environment_mismatch'):
        st.warning('실전/모의 환경 불일치 가능성이 있습니다. 선택 환경의 App Key·App Secret·계좌번호가 같은 환경에서 발급된 한 세트인지 확인하세요.')


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
    st.caption('Streamlit Secrets에 저장된 실전/모의 키를 각각 사용해 토큰 발급과 잔고 조회를 테스트합니다. Secret 값과 계좌번호는 결과에 표시하지 않습니다.')
    col_demo, col_real = st.columns(2)
    if col_demo.button('모의투자 Secrets 진단', key='kis_demo_secret_diagnosis', use_container_width=True):
        with st.spinner('모의투자 KIS API를 진단합니다…'):
            st.session_state.kis_demo_diagnosis = _run_secret_diagnosis('demo')
    if col_real.button('실전 Secrets 진단', key='kis_real_secret_diagnosis', use_container_width=True):
        with st.spinner('실전 KIS API를 진단합니다…'):
            st.session_state.kis_real_diagnosis = _run_secret_diagnosis('real')

    if st.session_state.get('kis_demo_diagnosis'):
        _render_diagnosis('모의투자 결과', st.session_state.kis_demo_diagnosis)
    if st.session_state.get('kis_real_diagnosis'):
        _render_diagnosis('실전 조회 결과', st.session_state.kis_real_diagnosis)
