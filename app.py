import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import warnings
import fundamentus

warnings.filterwarnings('ignore')

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA 
# ==============================================================================
st.set_page_config(
    page_title="Braytiner Analytics", 
    layout="wide", 
    page_icon="💎",
    initial_sidebar_state="expanded" 
)

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #f8fafc; }
    
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
    }
    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }
    [data-testid="stSidebar"] input {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        color: #4ade80 !important;
        font-weight: bold;
    }

    .modern-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        height: 220px; 
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
        animation: fadeIn 0.8s ease-out;
    }
    
    .modern-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.7);
        border-color: #475569;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse-green {
        0% { text-shadow: 0 0 0 rgba(74, 222, 128, 0.0); }
        50% { text-shadow: 0 0 20px rgba(74, 222, 128, 0.6); }
        100% { text-shadow: 0 0 0 rgba(74, 222, 128, 0.0); }
    }

    .card-title { font-size: 1rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700; margin-bottom: 10px;}
    .score-big { font-size: 4.5rem; font-weight: 900; line-height: 1; margin: 5px 0; }
    
    .status-green { color: #4ade80; animation: pulse-green 2.5s infinite; }
    .status-yellow { color: #facc15; }
    .status-red { color: #f87171; }
    
    .score-label { font-size: 1.1rem; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-top: 5px;}
    .sub-text { font-size: 0.85rem; color: #64748b; margin-top: 8px; font-weight: 500;}
    .value-big { font-size: 2.8rem; font-weight: 800; color: #f1f5f9; margin: 5px 0;}
    .perc-value { font-size: 1.3rem; font-weight: 700; margin-top: 5px; }
    
    [data-testid="stExpander"] details summary {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px;
        color: #f8fafc !important;
    }
    [data-testid="stExpander"] details summary p {
        font-weight: 700 !important;
        color: #f8fafc !important;
        font-size: 1.1rem;
    }
    [data-testid="stExpander"] details {
        background-color: #0b0f19 !important;
    }

    [data-testid="stDataFrame"] { background-color: #0b0f19 !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# MOTOR DE BUSCA 6.4 (BLINDAGEM NUVEM E FUNDAMENTUS CORRIGIDO)
# ==============================================================================
BRAPI_TOKEN = "6MeAw9XFNRGDZiqvnMcrXR"

@st.cache_data(ttl=3600)
def fetch_financial_data(ticker):
    dados = {'info': {}, 'historico': pd.DataFrame(), 'erro': None}
    ticker_upper = ticker.upper().strip()
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    
    stock = None
    try:
        stock = yf.Ticker(ticker_upper + ".SA", session=session)
        info = stock.info
        
        price = info.get('currentPrice', info.get('previousClose', 0))
        if price > 0:
            dados['info'] = {
                'price': float(price),
                'lpa': float(info.get('trailingEps', info.get('forwardEps', 0))),
                'vpa': float(info.get('bookValue', 0)),
                'dividend_yield': float(info.get('dividendYield', info.get('trailingAnnualDividendYield', 0))),
                'longName': info.get('longName', ticker_upper)
            }
    except Exception:
        pass

    # PLANO B: FUNDAMENTUS COM CONVERSOR BLINDADO
    if not dados.get('info') or dados.get('info', {}).get('price', 0) == 0:
        try:
            df_fund = fundamentus.get_papel(ticker_upper)
            if not df_fund.empty:
                
                def safe_float(val):
                    if isinstance(val, (int, float, np.number)):
                        return float(val)
                    val = str(val).replace('%', '').replace('.', '').replace(',', '.')
                    return float(val) if val else 0.0

                p = safe_float(df_fund.loc[ticker_upper, 'Cotacao'])
                l = safe_float(df_fund.loc[ticker_upper, 'LPA'])
                v = safe_float(df_fund.loc[ticker_upper, 'VPA'])
                dy = safe_float(df_fund.loc[ticker_upper, 'Div_Yield'])
                
                # Previne que o yield seja 7.2 ao invés de 0.072
                if dy > 1.0: 
                    dy = dy / 100.0

                dados['info'] = {
                    'price': p,
                    'lpa': l,
                    'vpa': v,
                    'dividend_yield': dy
                }
        except Exception:
            pass

    # HISTÓRICO VIA BRAPI PRO
    try:
        url = f"https://brapi.dev/api/quote/{ticker_upper}?modules=incomeStatementHistory,balanceSheetHistory&token={BRAPI_TOKEN}"
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            dados['erro'] = f"A API recusou o acesso. Código: {response.status_code}"
            return dados

        data = response.json()
        results = data.get('results', [{}])[0]
        
        # Garante o nome correto
        if 'longName' in results and 'longName' not in dados.get('info', {}):
            if 'info' not in dados: dados['info'] = {}
            dados['info']['longName'] = results['longName']

        inc_raw = results.get('incomeStatementHistory', [])
        bal_raw = results.get('balanceSheetHistory', [])
        
        inc_hist = inc_raw.get('incomeStatementHistory', []) if isinstance(inc_raw, dict) else inc_raw
        bal_hist = bal_raw.get('balanceSheetHistory', []) if isinstance(bal_raw, dict) else bal_raw

        if not inc_hist or not bal_hist:
            dados['erro'] = "A API não retornou os 10 anos de histórico."
            return dados

        df_inc = pd.DataFrame(inc_hist)
        df_bal = pd.DataFrame(bal_hist)
        
        df_inc['Ano'] = pd.to_datetime(df_inc['endDate']).dt.year
        df_bal['Ano'] = pd.to_datetime(df_bal['endDate']).dt.year
        
        df_inc.set_index('Ano', inplace=True)
        df_bal.set_index('Ano', inplace=True)
        
        df_hist = df_inc.join(df_bal, how='outer', lsuffix='_DRE', rsuffix='_BAL')
        
        def get_col(df_target, possible_names):
            for col in possible_names:
                if col in df_target.columns:
                    s = pd.to_numeric(df_target[col], errors='coerce')
                    if not s.dropna().empty and s.sum() != 0: 
                        return s
            return pd.Series(dtype=float, index=df_target.index)

        df_braytiner = pd.DataFrame(index=df_hist.index)
        
        df_braytiner['Lucro Líquido'] = get_col(df_hist, ['cleanNetIncome', 'netIncomeApplicableToCommonShares', 'netIncome', 'netIncomeFromContinuingOps'])
        df_braytiner['Receita Líquida'] = get_col(df_hist, ['financialIncome', 'totalRevenue', 'operatingRevenue'])
        
        patrimonio = get_col(df_hist, ['shareholdersEquity', 'totalStockholderEquity', 'totalEquityGrossMinorityInterest', 'totalEquity'])
        if patrimonio.dropna().empty:
            ativos = get_col(df_hist, ['totalAssets'])
            passivos = get_col(df_hist, ['totalLiab', 'totalLiabilities'])
            if not ativos.dropna().empty and not passivos.dropna().empty:
                patrimonio = ativos - passivos
                
        divida = get_col(df_hist, [
            'loansAndFinancing', 'shortLongTermDebtTotal', 'totalDebt', 'currentDebt', 
            'longTermLoansAndFinancing', 'debentures', 'longTermDebentures'
        ])

        if stock is not None:
            try:
                fin_yf = stock.financials.T
                bal_yf = stock.balance_sheet.T
                
                if not fin_yf.empty:
                    fin_yf.index = pd.to_datetime(fin_yf.index).year
                    if df_braytiner['Lucro Líquido'].dropna().empty:
                        lucro_yf = get_col(fin_yf, ['Net Income', 'Net Income Common Stock', 'Operating Income'])
                        for ano, val in lucro_yf.items(): df_braytiner.loc[ano, 'Lucro Líquido'] = val
                    if df_braytiner['Receita Líquida'].dropna().empty:
                        rec_yf = get_col(fin_yf, ['Total Revenue', 'Operating Revenue'])
                        for ano, val in rec_yf.items(): df_braytiner.loc[ano, 'Receita Líquida'] = val

                if not bal_yf.empty:
                    bal_yf.index = pd.to_datetime(bal_yf.index).year
                    if patrimonio.dropna().empty:
                        pat_yf = get_col(bal_yf, ['Stockholders Equity', 'Total Equity Gross Minority Interest', 'Total Equity'])
                        for ano, val in pat_yf.items(): patrimonio.loc[ano] = val
                    if divida.dropna().empty:
                        div_yf = get_col(bal_yf, ['Total Debt', 'Long Term Debt'])
                        for ano, val in div_yf.items(): divida.loc[ano] = val
            except:
                pass

        ebitda = get_col(df_hist, ['cleanEbitda', 'ebitda', 'normalizedEBITDA', 'cleanEbit'])
        if ebitda.dropna().empty: ebitda = df_braytiner['Lucro Líquido']
        df_braytiner['EBITDA'] = ebitda
        
        if not patrimonio.dropna().empty:
            df_braytiner['ROE'] = df_braytiner['Lucro Líquido'] / patrimonio
            
        if not df_braytiner['Receita Líquida'].dropna().empty:
            df_braytiner['Margem Líquida'] = df_braytiner['Lucro Líquido'] / df_braytiner['Receita Líquida']
            
        if not divida.dropna().empty and not patrimonio.dropna().empty:
            df_braytiner['Dívida/PL'] = divida / patrimonio
        elif not patrimonio.dropna().empty:
            df_braytiner['Dívida/PL'] = patrimonio 
        else:
            df_braytiner['Dívida/PL'] = pd.Series(0, index=df_braytiner.index)
        
        df_braytiner = df_braytiner.sort_index(ascending=True)
        df_braytiner = df_braytiner[~df_braytiner.index.duplicated(keep='last')]
        
        dados['historico'] = df_braytiner.tail(10)

    except Exception as e:
        dados['erro'] = f"Erro ao processar dados: {str(e)}"

    return dados

# ==============================================================================
# MOTOR MATEMÁTICO (MÉTODO BRAYTINER)
# ==============================================================================
def calculate_braytiner_score(series, is_inverted=False):
    if series is None or series.empty or len(series.dropna()) < 2:
        return 0.0, pd.DataFrame()

    df = pd.DataFrame({'Valor': series.dropna()})
    df['Variação'] = df['Valor'].pct_change().fillna(0) # CORRIGE O "NONE" NA MATEMÁTICA
    
    df['Bin_Positivo'] = 0
    df['Bin_Crescimento'] = 0

    if is_inverted:
        df['Bin_Positivo'] = 1 
    else:
        df['Bin_Positivo'] = np.where(df['Valor'] > 0, 1, 0)

    for i in range(1, len(df)):
        var = df['Variação'].iloc[i]
        if is_inverted:
            df.iloc[i, df.columns.get_loc('Bin_Crescimento')] = 1 if var < 0 else 0
        else:
            df.iloc[i, df.columns.get_loc('Bin_Crescimento')] = 1 if var > 0 else 0

    df_10y = df.copy()
    df_5y = df.tail(5)

    max_pts_10y = max((len(df_10y) * 2) - 1, 1)
    max_pts_5y = max(len(df_5y) * 2, 1)
    
    if len(df_10y) <= 5 and len(df_5y) > 0:
        max_pts_5y -= 1
        max_pts_5y = max(max_pts_5y, 1)
    
    pts_10y = df_10y['Bin_Positivo'].sum() + df_10y['Bin_Crescimento'].sum()
    pts_5y = df_5y['Bin_Positivo'].sum() + df_5y['Bin_Crescimento'].sum()

    nota_10y = (pts_10y / max_pts_10y) * 10 if max_pts_10y > 0 else 0
    nota_5y = (pts_5y / max_pts_5y) * 10 if max_pts_5y > 0 else 0

    nota_final = (nota_5y * 0.80) + (nota_10y * 0.20)
    
    return min(round(nota_final, 1), 10.0), df

# ==============================================================================
# FRONTEND 6.4
# ==============================================================================
def style_negative_positive(val):
    if isinstance(val, (int, float)):
        if val < 0:
            return 'color: #f87171; font-weight: bold;'
        elif val > 0:
            return 'color: #4ade80; font-weight: bold;'
    return 'color: #94a3b8;'

def main():
    st.sidebar.markdown("## 💎 Braytiner Analytics")
    st.sidebar.caption("v6.4 - Blindagem de Dados em Nuvem")
    st.sidebar.divider()
    
    ticker_input = st.sidebar.text_input("Código do Ativo (ex: ABEV3)", value="ITUB4").upper().strip()
    
    if st.sidebar.button("🔍 Gerar Valuation", use_container_width=True):
        with st.spinner(f"Sincronizando dados oficiais da CVM para {ticker_input}..."):
            dados = fetch_financial_data(ticker_input)
            
            if dados.get('erro'):
                st.error(f"⚠️ Atenção: {dados['erro']}")
                return
            
            hist = dados.get('historico', pd.DataFrame())
            info = dados.get('info', {})

            if hist.empty:
                st.warning("Não foi possível gerar as notas. O histórico contábil está vazio ou incompleto.")
                return

            cards = {}
            cards['Lucro Líquido'] = calculate_braytiner_score(hist.get('Lucro Líquido'))
            cards['ROE'] = calculate_braytiner_score(hist.get('ROE'))
            cards['EBITDA'] = calculate_braytiner_score(hist.get('EBITDA'))
            cards['Margem Líquida'] = calculate_braytiner_score(hist.get('Margem Líquida'))
            cards['Receita Líquida'] = calculate_braytiner_score(hist.get('Receita Líquida'))
            cards['Dívida Bruta/PL'] = calculate_braytiner_score(hist.get('Dívida/PL'), is_inverted=True)

            pesos = {
                'Lucro Líquido': 0.30, 'ROE': 0.25, 'EBITDA': 0.15,
                'Margem Líquida': 0.15, 'Receita Líquida': 0.10, 'Dívida Bruta/PL': 0.05
            }
            nota_geral = sum(cards[k][0] * v for k, v in pesos.items())

            price = info.get('price', 0)
            lpa = info.get('lpa', 0)
            vpa = info.get('vpa', 0)
            div_yield = info.get('dividend_yield', 0)

            graham = (22.5 * lpa * vpa) ** 0.5 if (lpa > 0 and vpa > 0) else 0
            div_pago = price * div_yield if div_yield else 0
            bazin = div_pago / 0.06 if div_pago > 0 else 0

            upside_g = ((graham - price) / price * 100) if price > 0 else 0
            upside_b = ((bazin - price) / price * 100) if price > 0 else 0

            if nota_geral >= 8.0: 
                status_text, color_class = "COMPRAR SEM MEDO", "status-green"
            elif nota_geral >= 6.0: 
                status_text, color_class = "COMPRAR COM CAUTELA", "status-yellow"
            else: 
                status_text, color_class = "NÃO COMPRAR", "status-red"

            color_up_g = "#4ade80" if upside_g > 0 else "#f87171"
            color_up_b = "#4ade80" if upside_b > 0 else "#f87171"

            st.markdown(f"<h2 style='text-align: center; margin-bottom: 30px; font-weight: 800;'>{ticker_input} <span style='color: #64748b;'>| {info.get('longName', 'Empresa')}</span></h2>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown(f'''
                <div class="modern-card">
                    <div class="card-title">🛡️ Sistema Braytiner</div>
                    <div class="score-big {color_class}">{nota_geral:.1f}</div>
                    <div class="score-label {color_class}">{status_text}</div>
                </div>
                ''', unsafe_allow_html=True)

            with c2:
                st.markdown(f'''
                <div class="modern-card">
                    <div class="card-title">⚖️ Valor Justo (Graham)</div>
                    <div class="value-big">R$ {graham:.2f}</div>
                    <div class="perc-value" style="color: {color_up_g};">{upside_g:+.1f}%</div>
                    <div class="sub-text">Cotação Atual: R$ {price:.2f}</div>
                </div>
                ''', unsafe_allow_html=True)

            with c3:
                st.markdown(f'''
                <div class="modern-card">
                    <div class="card-title">💰 Preço Teto (Bazin)</div>
                    <div class="value-big">R$ {bazin:.2f}</div>
                    <div class="perc-value" style="color: {color_up_b};">{upside_b:+.1f}%</div>
                    <div class="sub-text">Div. Yield Atual: {div_yield*100:.2f}%</div>
                </div>
                ''', unsafe_allow_html=True)

            st.markdown("<br><br>", unsafe_allow_html=True)
            
            st.markdown("<h4 style='color: #94a3b8; font-weight: 700; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 20px;'>📊 Raio-X Contábil (10 Anos)</h4>", unsafe_allow_html=True)
            
            cols = st.columns(3)
            idx = 0
            for indicador, (nota, df_detalhe) in cards.items():
                with cols[idx % 3]:
                    with st.expander(f"{indicador} | Nota: {nota}", expanded=True):
                        st.progress(nota / 10)
                        if not df_detalhe.empty:
                            # CORRIGE O VISUAL DO NONE NAS TABELAS
                            df_view = df_detalhe[['Valor', 'Variação']].copy().sort_index(ascending=False).fillna(0)
                            
                            styled_df = df_view.style.format({
                                'Valor': '{:,.2f}', 
                                'Variação': '{:.1%}'
                            }).applymap(style_negative_positive)
                            
                            st.dataframe(styled_df, use_container_width=True, height=200)
                idx += 1

if __name__ == "__main__":
    main()
