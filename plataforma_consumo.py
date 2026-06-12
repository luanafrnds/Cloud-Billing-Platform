import streamlit as st
import pandas as pd
import plotly.express as px
import io

# Configuração global da página do Streamlit
st.set_page_config(
    page_title="Dashboard de Consumo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MENU PRINCIPAL DE NAVEGAÇÃO NA SIDEBAR ---
st.sidebar.title(" Painel de Controle")
modulo_principal = st.sidebar.selectbox(
    "Selecione o Módulo:",
    ["📊 Dashboard de Consumo", "💳 Subscrições & Créditos"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tipo de Arquivo / Conta")
modo_analise = st.sidebar.radio(
    "Selecione o seu Modelo (Apenas para o Dashboard):",
    ["Padrão - Instance / Billing", "Enterprise"]
)

# ==============================================================================
# 🛠️ FUNÇÕES DE PARSER (BLINDADAS)
# ==============================================================================

def carregar_padrão_consumo(conteudo, filename):
    try:
        linhas = conteudo.splitlines()
        mes_faturamento, nome_conta = "Mês Indefinido", "Conta Indefinida"
        
        for idx, linha in enumerate(linhas[:10]):
            if 'Billing Month' in linha:
                meta_valores = linhas[idx+1].split(',')
                if len(meta_valores) > 2:
                    mes_faturamento = meta_valores[2].replace('"', '').strip()
                    nome_conta = meta_valores[1].replace('"', '').strip()
                break
        
        linhas_dados = []
        capturando = False
        for linha in linhas:
            if 'Service Name' in linha:
                capturando = True
            if capturando:
                if '--this is the end of report--' in linha:
                    break
                linhas_dados.append(linha)
                
        if not linhas_dados:
            return None
            
        df = pd.read_csv(io.StringIO("\n".join(linhas_dados)), skipinitialspace=True, on_bad_lines='skip')
        df.columns = [col.replace('"', '').strip() for col in df.columns]
        df = df[df['Service Name'].notna() & (df['Service Name'] != '--this is the end of report--')]
        
        colunas_numericas = ['Cost', 'Original Cost', 'Usage Quantity', 'Volume Cost', 'Volume Discount']
        for col in colunas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['Mês de Faturamento'] = mes_faturamento
        df['Nome da Conta'] = nome_conta
        df['Currency'] = df['Currency Code'] if 'Currency Code' in df.columns else "BRL"
        return df
    except Exception as e:
        return None

def carregar_enterprise_consumo(conteudo, filename):
    try:
        linhas = conteudo.splitlines()
        mes_faturamento, nome_enterprise = "N/A", "Enterprise"
        
        for idx, linha in enumerate(linhas[:15]):
            if '"Billing Month"' in linha:
                meta_valores = linhas[idx+1].split(',')
                mes_faturamento = meta_valores[2].replace('"', '').strip() if len(meta_valores) > 2 else "N/A"
            if '"Entity Type","Entity Name"' in linha or '"Entity ID","Entity Type","Entity Name"' in linha:
                meta_valores = linhas[idx+1].split(',')
                nome_enterprise = meta_valores[2].replace('"', '').strip() if len(meta_valores) > 2 else "Enterprise"
                
        linhas_mapping = []
        capturando_map = False
        for linha in linhas:
            if '"Parent Entity ID","Parent Entity Name"' in linha or '"Entity ID","Entity Type","Entity Name"' in linha:
                capturando_map = True
                linhas_mapping.append(linha)
                continue
            if capturando_map:
                if linha.strip() == "":
                    break
                linhas_mapping.append(linha)
        df_map = pd.read_csv(io.StringIO("\n".join(linhas_mapping)), on_bad_lines='skip')
        
        linhas_consumo = []
        capturando_cons = False
        for linha in linhas:
            if '"Parent Entity ID"' in linha and '"Service Name"' in linha:
                capturando_cons = True
                linhas_consumo.append(linha)
                continue
            if capturando_cons:
                if linha.strip() == "" or '"Overage"' in linha:
                    break
                linhas_consumo.append(linha)
                
        if not linhas_consumo:
            return None
            
        df_ent = pd.read_csv(io.StringIO("\n".join(linhas_consumo)), on_bad_lines='skip')
        
        if 'Entity ID' in df_ent.columns and 'Entity ID' in df_map.columns:
            df_merged = df_ent.merge(df_map[['Entity ID', 'Entity Name']], on='Entity ID', how='left')
        else:
            df_merged = df_ent
            df_merged['Entity Name'] = "Conta Indefinida"
            
        df_merged['Mês de Faturamento'] = mes_faturamento
        df_merged['Nome da Conta'] = nome_enterprise
        df_merged['Cost'] = pd.to_numeric(df_merged['Cost'], errors='coerce').fillna(0)
        df_merged['Quantity'] = pd.to_numeric(df_merged['Quantity'], errors='coerce').fillna(0)
        df_merged['Currency'] = df_merged['Currency Code'] if 'Currency Code' in df_merged.columns else "BRL"
        return df_merged
    except Exception as e:
        return None

def extrair_dados_subscricao_padrão(conteudo):
    try:
        linhas = conteudo.splitlines()
        mes_faturamento, nome_conta, moeda = "N/A", "Conta Indefinida", "BRL"
        
        for idx, inline in enumerate(linhas[:15]):
            if '"Billing Month"' in inline:
                meta_valores = linhas[idx+1].split(',')
                mes_faturamento = meta_valores[2].replace('"', '').strip() if len(meta_valores) > 2 else "N/A"
                nome_conta = meta_valores[1].replace('"', '').strip() if len(meta_valores) > 1 else "N/A"
            if '"Currency Code"' in inline:
                meta_valores = linhas[idx+1].split(',')
                moeda = meta_valores[3].replace('"', '').strip() if len(meta_valores) > 3 else "BRL"

        linhas_bloco = []
        capturando = False
        for linha in linhas:
            if '"Subscription ID"' in linha and '"Subscription Amount"' in linha:
                capturando = True
                linhas_bloco.append(linha)
                continue
            if capturando:
                if '"Plan Name"' in linha or '"Service Name"' in linha or '"Account ID"' in linha:
                    break
                if linha.strip() == "" and len(linhas_bloco) > 1:
                    break
                linhas_bloco.append(linha)
                
        if len(linhas_bloco) <= 1:
            return None
        df_sub = pd.read_csv(io.StringIO("\n".join(linhas_bloco)), on_bad_lines='skip')
        df_sub['Mês'] = mes_faturamento
        df_sub['Conta'] = nome_conta
        df_sub['Currency'] = moeda
        df_sub['Overage_Value'] = 0.0
        return df_sub
    except Exception as e:
        return None

def extrair_dados_subscricao_enterprise(conteudo):
    try:
        linhas = conteudo.splitlines()
        mes_faturamento, nome_conta, moeda = "N/A", "Enterprise", "BRL"
        
        for idx, linha_meta in enumerate(linhas[:15]):
            if '"Billing Month"' in linha_meta:
                meta_valores = linhas[idx+1].split(',')
                mes_faturamento = meta_valores[2].replace('"', '').strip() if len(meta_valores) > 2 else "N/A"
            if '"Entity Type","Entity Name"' in linha_meta or '"Entity ID","Entity Type","Entity Name"' in linha_meta:
                meta_valores = linhas[idx+1].split(',')
                nome_conta = meta_valores[2].replace('"', '').strip() if len(meta_valores) > 2 else "Enterprise"

        # --- CAPTURA DOS POOLS ---
        linhas_bloco = []
        capturando = False

        for linha in linhas:
            if (
                '"Subscription ID"' in linha
                and '"Subscription Amount"' in linha
                and '"Credits Total"' in linha
            ):
                capturando = True
                linhas_bloco.append(linha)
                continue

            if capturando:
                if (
                    linha.strip() == ""
                    and len(linhas_bloco) > 1
                ):
                    break
                linhas_bloco.append(linha)

        if len(linhas_bloco) > 1:
            df_sub = pd.read_csv(io.StringIO("\n".join(linhas_bloco)))
        else:
            df_sub = pd.DataFrame()

        if not df_sub.empty:
            df_sub.columns = [col.replace('"', '').strip() for col in df_sub.columns]
            df_sub["Credits Total"] = pd.to_numeric(df_sub["Credits Total"], errors="coerce").fillna(0)
            df_sub["Credits Used"] = pd.to_numeric(df_sub["Credits Used"], errors="coerce").fillna(0)
            df_sub["Credits Balance"] = pd.to_numeric(df_sub["Credits Balance"], errors="coerce").fillna(0)
            df_sub["Subscription Amount"] = pd.to_numeric(df_sub["Subscription Amount"], errors="coerce").fillna(0)

            if 'Currency Code' in df_sub.columns:
                moeda = df_sub['Currency Code'].iloc[0]

        total_overage_arquivo = 0.0
        indice_overage = None
        for i, linha in enumerate(linhas):
            linha_limpa = linha.replace('"', '').strip()
            if "Subscription ID" in linha_limpa and "Category" in linha_limpa and "Overage" in linha_limpa:
                indice_overage = i
                break

        if indice_overage is not None:
            bloco_overage = []
            for linha in linhas[indice_overage:]:
                if "Offer ID" in linha or "Support Cost" in linha:
                    break
                bloco_overage.append(linha)

            try:
                df_ov_temp = pd.read_csv(io.StringIO("\n".join(bloco_overage)), on_bad_lines="skip")
                df_ov_temp.columns = [c.replace('"', '').strip() for c in df_ov_temp.columns]
                if "Overage" in df_ov_temp.columns:
                    df_ov_temp["Overage"] = pd.to_numeric(df_ov_temp["Overage"], errors="coerce").fillna(0)
                    total_overage_arquivo = float(df_ov_temp["Overage"].sum())
            except:
                pass

        if df_sub.empty:
            df_sub = pd.DataFrame([{
                'Subscription ID': 'PUBLIC_PLATFORM_OVERAGE', 'Type': 'SUBSCRIPTION',
                'Subscription Amount': 0.0, 'Credits Starting': 0.0, 'Credits Used': 0.0, 'Credits Balance': 0.0
            }])

        df_sub['Mês'] = mes_faturamento
        df_sub['Conta'] = nome_conta
        df_sub['Currency'] = moeda
        df_sub['Overage_Value'] = total_overage_arquivo
        return df_sub
    except Exception as e:
        return None

# ==============================================================================
# 🚀 INTERFACE E RENDERIZAÇÃO
# ==============================================================================

st.title(f"{modulo_principal}")

if modulo_principal == "Plataforma Análise de Créditos - Cloud":
    st.write(f"Modo de Filtros Ativo: **Modelo {modo_analise}**")
    label_dinamico_upload = f"Upload de arquivos CSV para o Dashboard ({modo_analise})"
else:
    st.write("Modo Unificado: Leitura automática de Subscrições & Créditos")
    label_dinamico_upload = "Upload de arquivos CSV (Billing Summary / Pools)"

arquivos_uploadeados = st.file_uploader(label_dinamico_upload, type=["csv"], accept_multiple_files=True)

if arquivos_uploadeados:
    lista_dados_processados = []
    
    for arquivo in arquivos_uploadeados:
        conteudo_bruto = arquivo.read().decode('utf-8')
        arquivo.seek(0)
        
        if '"Service Name,""Service ID""' in conteudo_bruto or '"Account Owner ID,""Account Name""' in conteudo_bruto:
            conteudo_bruto = conteudo_bruto.replace('""', '"')
            
        is_enterprise_file = "Parent Entity ID" in conteudo_bruto or "EnterpriseUsage" in conteudo_bruto
        is_subscription_summary = "Credits Total" in conteudo_bruto or "Overage" in conteudo_bruto or "True Up" in conteudo_bruto
        
        # --- SEPARAÇÃO DE ARQUIVOS ADAPTADA ---
        if modulo_principal == "📊 Dashboard de Consumo":
            if modo_analise == "Padrão - Instance / Billing":
                if is_enterprise_file:
                    st.error(f"❌ O arquivo `{arquivo.name}` pertence ao modelo **Enterprise**. Altere o seletor na barra lateral para 'Enterprise' ou remova este arquivo.")
                    continue
                df_res = carregar_padrão_consumo(conteudo_bruto, arquivo.name)
            else:
                if not is_enterprise_file and "Instance Name" in conteudo_bruto:
                    st.error(f"❌ O arquivo `{arquivo.name}` pertence ao modelo **Padrão (Instance/Billing)**. Altere o seletor na barra lateral para 'Padrão' ou remova este arquivo.")
                    continue
                df_res = carregar_enterprise_consumo(conteudo_bruto, arquivo.name)
        else:
            if is_subscription_summary or is_enterprise_file or "Subscription ID" in conteudo_bruto:
                df_res = extrair_dados_subscricao_enterprise(conteudo_bruto)
            else:
                df_res = extrair_dados_subscricao_padrão(conteudo_bruto)
            
        if df_res is not None:
            lista_dados_processados.append(df_res)
            
    if lista_dados_processados:
        df_completo = pd.concat(lista_dados_processados, ignore_index=True)
        df_completo = df_completo.loc[:, ~df_completo.columns.duplicated()]
        
        col_mes_ref = 'Mês de Faturamento' if modulo_principal == "📊 Dashboard de Consumo" else 'Mês'
        col_conta_ref = 'Nome da Conta' if modulo_principal == "📊 Dashboard de Consumo" else 'Conta'
        
        meses_disponiveis = sorted(df_completo[col_mes_ref].unique())
        contas_disponiveis = df_completo[col_conta_ref].unique()
        moeda_identificada = df_completo['Currency'].iloc[0] if 'Currency' in df_completo.columns else "BRL"
        simbolo_moeda = "R$" if moeda_identificada == "BRL" else "$"
        
        # --- FUNÇÃO INTERNA DE FORMATAÇÃO (APLICADA SÓ NA EXIBIÇÃO TEXTUAL) ---
        def fmt_br(val, com_moeda=True):
            try:
                val = float(val)
                prefixo = f"{simbolo_moeda} " if com_moeda else ""
                return f"{prefixo}{val:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            except:
                return str(val)

        st.sidebar.subheader("🎯 Filtros Aplicados")
        st.sidebar.info(f"**Escopo:** {', '.join(contas_disponiveis)}")
        meses_selecionados = st.sidebar.multiselect("Filtrar Meses:", meses_disponiveis, default=meses_disponiveis)
        
        df_filtrado = df_completo[df_completo[col_mes_ref].isin(meses_selecionados)]
        
        # ======================================================================
        # MÓDULO 1: DASHBOARD DE CONSUMO
        # ======================================================================
        if modulo_principal == "📊 Dashboard de Consumo":
            st.subheader("📅 Resumo Financeiro Mensal")
            resumo_por_mes = df_filtrado.groupby('Mês de Faturamento')['Cost'].sum().reset_index().sort_values('Mês de Faturamento')
            resumo_por_mes['Variação Absoluta'] = resumo_por_mes['Cost'].diff().fillna(0.0)
            resumo_por_mes['Variação Percentual (%)'] = (resumo_por_mes['Cost'].pct_change() * 100).fillna(0.0)
            
            formatos_topo = {
                'Cost': lambda x: fmt_br(x),
                'Variação Absoluta': lambda x: fmt_br(x) if x != 0 else f"{simbolo_moeda} 0,00",
                'Variação Percentual (%)': lambda x: f"{x:+.2f}%".replace(".", ",") if x != 0 else "0,00%"
            }
            st.dataframe(resumo_por_mes.style.format(formatos_topo), use_container_width=True, hide_index=True)
            
            custo_total = float(df_filtrado['Cost'].sum())
            num_servicos = df_filtrado['Service Name'].nunique() if 'Service Name' in df_filtrado.columns else 0
            
            if len(resumo_por_mes) >= 2:
                taxa_crescimento_media = 1 + (resumo_por_mes['Variação Percentual (%)'].mean() / 100)
                custo_projetado = float(resumo_por_mes['Cost'].iloc[-1] * taxa_crescimento_media)
            else:
                custo_projetado = float(custo_total * 1.02)
            
            if modo_analise == "Padrão - Instance / Billing":
                st.subheader("📌 Indicadores Operacionais")
                kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
                custo_original = float(df_filtrado['Original Cost'].sum() if 'Original Cost' in df_filtrado.columns else custo_total)
                desconto_total = custo_original - custo_total
                
                kpi1.metric("Custo Total Real", fmt_br(custo_total))
                kpi2.metric("Custo Original", fmt_br(custo_original))
                kpi3.metric("Economia Estimada", fmt_br(desconto_total))
                kpi4.metric("Produtos Únicos", f"{num_servicos}")
                kpi5.metric("Previsão (Próximo Mês)", fmt_br(custo_projetado))
                
                label_aba_dinamica = "📁 Divisão por Resource Group"
            else:
                st.subheader("📌 Indicadores Corporativos")
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                num_contas_vinculadas = df_filtrado['Entity Name'].nunique() if 'Entity Name' in df_filtrado.columns else 0
                kpi1.metric("Custo Consolidado Enterprise", fmt_br(custo_total))
                kpi2.metric("Contas Vinculadas Ativas", f"{num_contas_vinculadas}")
                kpi3.metric("Serviços em Uso", f"{num_servicos}")
                kpi4.metric("Previsão (Próximo Mês)", fmt_br(custo_projetado))
                
                label_aba_dinamica = "🏢 Distribuição por Conta (Entity Name)"
                
            st.markdown("---")
            aba_top10, aba_tendencias, aba_dinamica, aba_detalhes = st.tabs(["🔝 Top 10 Produtos", "📈 Regiões Geográficas", label_aba_dinamica, "💰 Tabela Analítica"])
            
            with aba_top10:
                coluna_grupo = 'Service Name'
                if modo_analise == "Padrão - Instance / Billing" and 'Instance Name' in df_filtrado.columns:
                    coluna_grupo = st.radio("Agrupar gráficos por:", ["Service Name", "Instance Name"], horizontal=True)
                
                top10_df = df_filtrado.groupby(coluna_grupo)['Cost'].sum().reset_index().sort_values(by='Cost', ascending=False).head(10)
                
                # --- ALTERAÇÃO REALIZADA: FORMATADO O COUT E HOVER PARA PADRÃO BRASILEIRO NO PLOTLY ---
                fig_top10 = px.bar(top10_df, x='Cost', y=coluna_grupo, orientation='h', color='Cost', color_continuous_scale='Reds')
                
                # Seta o prefixo de moeda e substitui ponto e vírgula para simular localização pt-BR direto nas barras
                fig_top10.update_layout(
                    xaxis_tickprefix=f"{simbolo_moeda} ", 
                    xaxis_tickformat=',.2f', 
                    yaxis={'categoryorder':'total ascending'}, 
                    title=f"Top 10 Maiores Custos por {coluna_grupo}"
                )
                fig_top10.update_traces(
                    texttemplate=f'{simbolo_moeda} %{{x:,.2f}}', 
                    textposition='outside', 
                    hovertemplate='<b>%{y}</b><br>Custo: ' + simbolo_moeda + ' %{x:,.2f}<extra></extra>'
                )
                st.plotly_chart(fig_top10, use_container_width=True)
                
            with aba_tendencias:
                col_reg = 'Region' if modo_analise == "Padrão - Instance / Billing" else 'Pricing Region'
                if col_reg in df_filtrado.columns:
                    custo_regiao = df_filtrado.groupby(col_reg)['Cost'].sum().reset_index().sort_values('Cost', ascending=False)
                    fig_regiao = px.bar(custo_regiao, x=col_reg, y='Cost', title="Custos Alocados por Data Center / Região", color='Cost', color_continuous_scale='Blues')
                    fig_regiao.update_layout(xaxis_tickprefix="", yaxis_tickprefix=f"{simbolo_moeda} ", yaxis_tickformat=',.2f')
                    st.plotly_chart(fig_regiao, use_container_width=True)
                else:
                    st.info("ℹ️ Informação regional não disponível neste arquivo.")
                
            with aba_dinamica:
                col_agrup = 'Resource Group Name' if modo_analise == "Padrão - Instance / Billing" else 'Entity Name'
                if col_agrup in df_filtrado.columns:
                    df_agrup_aba = df_filtrado.groupby(col_agrup)['Cost'].sum().reset_index().sort_values(by='Cost', ascending=False)
                    c_g, c_t = st.columns([1.1, 0.9])
                    with c_g:
                        fig_p = px.pie(df_agrup_aba, values='Cost', names=col_agrup, title=f"Participação de Gastos por {col_agrup}", color_discrete_sequence=px.colors.qualitative.Pastel)
                        st.plotly_chart(fig_p, use_container_width=True)
                    with c_t:
                        st.dataframe(df_agrup_aba.style.format({'Cost': lambda x: fmt_br(x)}), use_container_width=True, hide_index=True)
                else:
                    st.info(f"ℹ️ Coluna de agrupamento `{col_agrup}` não encontrada neste lote.")
                    
            with aba_detalhes:
                if 'Service Name' in df_filtrado.columns:
                    servico_escolhido = st.selectbox("Selecione um produto para auditoria:", sorted(df_filtrado['Service Name'].unique()))
                    df_servico = df_filtrado[df_filtrado['Service Name'] == servico_escolhido].copy()
                    
                    colunas_exibir = ['Mês de Faturamento', 'Instance Name', 'Region', 'Resource Group Name', 'Usage Metric', 'Usage Quantity', 'Cost'] if modo_analise == "Padrão - Instance / Billing" else ['Mês de Faturamento', 'Entity Name', 'Plan Name', 'Pricing Region', 'Metric', 'Quantity', 'Cost']
                    colunas_existentes = [c for c in colunas_exibir if c in df_servico.columns]
                    
                    formatos_dinamicos = {}
                    if 'Cost' in colunas_existentes:
                        formatos_dinamicos['Cost'] = lambda x: fmt_br(x)
                    if 'Usage Quantity' in colunas_existentes:
                        formatos_dinamicos['Usage Quantity'] = lambda x: fmt_br(x, com_moeda=False)
                    if 'Quantity' in colunas_existentes:
                        formatos_dinamicos['Quantity'] = lambda x: fmt_br(x, com_moeda=False)
                        
                    st.dataframe(df_servico[colunas_existentes].style.format(formatos_dinamicos), use_container_width=True, hide_index=True)

        # ----------------------------------------------------------------------
        # 💳 MÓDULO 2: SUBSCRIÇÕES E CRÉDITOS
        # ----------------------------------------------------------------------
        else:
            colunas_financeiras = ['Subscription Amount', 'Credits Total', 'Credits Starting', 'Credits Used', 'Credits Balance']
            for col in colunas_financeiras:
                if col in df_filtrado.columns:
                    df_filtrado[col] = pd.to_numeric(df_filtrado[col], errors='coerce').fillna(0.0)
            
            if 'Overage_Value' in df_filtrado.columns and 'Mês' in df_filtrado.columns:
                overage_total = float(df_filtrado.groupby('Mês')['Overage_Value'].max().sum())
            else:
                overage_total = float(df_filtrado['Overage_Value'].max()) if 'Overage_Value' in df_filtrado.columns else 0.0
            
            st.subheader("📊 Balanço Geral dos Contratos")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            total_contratado = float(df_filtrado['Subscription Amount'].sum() if 'Subscription Amount' in df_filtrado.columns else 0.0)
            total_consumido_mes = float(df_filtrado['Credits Used'].sum() if 'Credits Used' in df_filtrado.columns else 0.0)
            total_saldo_restante = float(df_filtrado['Credits Balance'].sum() if 'Credits Balance' in df_filtrado.columns else 0.0)
            
            kpi1.metric("Total Contratado", fmt_br(total_contratado))
            kpi2.metric("Créditos Utilizados", fmt_br(total_consumido_mes))
            kpi3.metric("Saldo Restante Disponível", fmt_br(total_saldo_restante))
            kpi4.metric("Excedente (Overage) Realizado", fmt_br(overage_total), delta="Atenção" if overage_total > 0 else None, delta_color="inverse")
            
            st.markdown("---")
            st.subheader("📋 Detalhes Individuais das Assinaturas")
            
            colunas_ordem = ['Subscription ID', 'Mês', 'Type', 'Subscription Amount', 'Credits Total', 'Credits Used', 'Credits Balance', 'Start', 'End'] if 'Credits Total' in df_filtrado.columns else ['Subscription ID', 'Mês', 'Subscription Amount', 'Currency', 'Start', 'End']
            colunas_finais = [c for c in colunas_ordem if c in df_filtrado.columns]
            
            df_tabela_sub = df_filtrado[df_filtrado['Subscription ID'] != 'PUBLIC_PLATFORM_OVERAGE'] if 'Subscription ID' in df_filtrado.columns else df_filtrado
            
            if not df_tabela_sub.empty and len(colunas_finais) > 0:
                formatos_tabela = {}
                for col_tab in colunas_finais:
                    if col_tab in ['Subscription Amount', 'Credits Total', 'Credits Starting', 'Credits Used', 'Credits Balance', 'Overage_Value']:
                        formatos_tabela[col_tab] = lambda x: fmt_br(x)
                
                st.dataframe(df_tabela_sub[colunas_finais].style.format(formatos_tabela, na_rep="-"), use_container_width=True, hide_index=True)
            
            if overage_total > 0:
                st.markdown("---")
                st.error(f"🚨 **Alerta FinOps:** Foi identificado um estouro de consumo (Overage) no valor de **{fmt_br(overage_total)}** faturado diretamente neste ciclo.")
            
else:
    st.info("💡 Selecione o módulo desejado, configure o tipo na barra lateral esquerda se necessário, e envie os arquivos CSV para auditoria.")