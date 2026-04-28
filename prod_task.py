import streamlit as st
import json
import os
from datetime import datetime, timedelta
import time
import pandas as pd
import random

# ==========================================
# CONFIGURAÇÕES E DADOS GLOBAIS
# ==========================================
ARQUIVO_TAREFAS = 'tarefas.json'
ARQUIVO_HISTORICO = 'tarefas_arquivadas.json'

def carregar_dados(arquivo):
    if not os.path.exists(arquivo):
        return []
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            return dados if isinstance(dados, list) else []
    except (json.JSONDecodeError, IOError):
        return []

def salvar_dados(arquivo, dados):
    try:
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except IOError as e:
        st.error(f"Erro ao salvar: {e}")

# ==========================================
# ESTRUTURAS DE DADOS (FASE 1 DO PDF)
# ==========================================
class Pilha:
    def __init__(self):
        self.itens = []
    def empilhar(self, item):
        self.itens.append(item)
    def desempilhar(self):
        return self.itens.pop() if not self.vazia() else None
    def vazia(self):
        return len(self.itens) == 0

class Fila:
    def __init__(self):
        self.itens = []
    def enfileirar(self, item):
        self.itens.append(item)
    def desenfileirar(self):
        return self.itens.pop(0) if not self.vazia() else None
    def vazia(self):
        return len(self.itens) == 0

# ==========================================
# ORDENAÇÃO MANUAL (SELECTION SORT E QUICK SORT)
# ==========================================
def calcular_peso_tarefa(tarefa):
    """Calcula um valor numérico para ordenar por Status e Prioridade."""
    ordem_status = {"FAZENDO": 1, "PENDENTE": 2, "CONCLUÍDA": 3}
    ordem_prioridade = {"URGENTE": 1, "ALTA": 2, "MÉDIA": 3, "BAIXA": 4}
    
    s = ordem_status.get(tarefa.get("Status", "PENDENTE"), 99)
    p = ordem_prioridade.get(tarefa.get("Prioridade", "BAIXA"), 5)
    return (s, p)

def selection_sort(arr):
    """Ordenação manual O(n^2) com Selection Sort."""
    n = len(arr)
    arr_ordenado = arr.copy()
    for i in range(n):
        min_idx = i
        for j in range(i+1, n):
            if calcular_peso_tarefa(arr_ordenado[j]) < calcular_peso_tarefa(arr_ordenado[min_idx]):
                min_idx = j
        arr_ordenado[i], arr_ordenado[min_idx] = arr_ordenado[min_idx], arr_ordenado[i]
    return arr_ordenado

def quick_sort(arr):
    """Ordenação manual O(n log n) com Quick Sort."""
    if len(arr) <= 1:
        return arr
    pivo = arr[len(arr) // 2]
    peso_pivo = calcular_peso_tarefa(pivo)
    
    esquerda = [x for x in arr if calcular_peso_tarefa(x) < peso_pivo]
    meio = [x for x in arr if calcular_peso_tarefa(x) == peso_pivo]
    direita = [x for x in arr if calcular_peso_tarefa(x) > peso_pivo]
    
    return quick_sort(esquerda) + meio + quick_sort(direita)

# ==========================================
# LÓGICA DE ARQUIVAMENTO AUTOMÁTICO
# ==========================================
def executar_arquivamento():
    """Move tarefas concluídas há >7 dias ou excluídas para o histórico."""
    data_atual = datetime.now()
    tarefas_ativas = []
    tarefas_mover = []
    
    for tarefa in st.session_state.tarefas:
        mover = False
        if tarefa.get("Status") == "EXCLUÍDA":
            mover = True
        elif tarefa.get("Status") == "CONCLUÍDA" and tarefa.get("dataConclusao"):
            try:
                data_conclusao = datetime.strptime(tarefa["dataConclusao"], "%d/%m/%Y %H:%M:%S")
                # Se passou de 7 dias, marca para mover
                if (data_atual - data_conclusao).days >= 7:
                    tarefa["Status"] = "ARQUIVADO"
                    mover = True
            except (ValueError, TypeError):
                pass
                
        if mover:
            tarefas_mover.append(tarefa)
        else:
            tarefas_ativas.append(tarefa)
            
    if tarefas_mover:
        st.session_state.tarefas = tarefas_ativas
        st.session_state.arquivadas.extend(tarefas_mover)
        salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
        salvar_dados(ARQUIVO_HISTORICO, st.session_state.arquivadas)
        return len(tarefas_mover)
    return 0

# ==========================================
# INICIALIZAÇÃO DE ESTADOS DO STREAMLIT
# ==========================================
st.set_page_config(page_title="Gerenciador de Tarefas", layout="wide")

if 'tarefas' not in st.session_state:
    st.session_state.tarefas = carregar_dados(ARQUIVO_TAREFAS)
if 'arquivadas' not in st.session_state:
    st.session_state.arquivadas = carregar_dados(ARQUIVO_HISTORICO)
if 'pilha_desfazer' not in st.session_state:
    st.session_state.pilha_desfazer = Pilha()
if 'telemetria' not in st.session_state:
    st.session_state.telemetria = []

# Automação: Roda a verificação de arquivamento a cada interação do sistema
qtd_arquivadas = executar_arquivamento()
if qtd_arquivadas > 0:
    st.toast(f"🧹 {qtd_arquivadas} tarefa(s) arquivada(s) automaticamente pelo sistema!")

def gerar_codigo():
    todas = st.session_state.tarefas + st.session_state.arquivadas
    if not todas: return "001"
    maior = max([int(t.get('Código', 0)) for t in todas if str(t.get('Código')).isdigit()], default=0)
    return str(maior + 1).zfill(3)

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.title("🚀 Gerenciador de Tarefas PRO")

with st.sidebar:
    st.header("📝 Nova Tarefa")
    novo_titulo = st.text_input("Título da Tarefa")
    nova_desc = st.text_area("Descrição")
    nova_priori = st.selectbox("Prioridade", ["URGENTE", "ALTA", "MÉDIA", "BAIXA"])
    nova_origem = st.selectbox("Origem", ["E-MAIL", "TELEFONE", "CHAMADO DO SISTEMA"])
    
    if st.button("Cadastrar Tarefa", use_container_width=True):
        if novo_titulo.strip():
            nova_tarefa = {
                "Código": gerar_codigo(),
                "Titulo": novo_titulo,
                "Descrição": nova_desc,
                "Prioridade": nova_priori,
                "Status": "PENDENTE",
                "Origem": nova_origem,
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "dataConclusao": None
            }
            st.session_state.tarefas.append(nova_tarefa)
            salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
            st.success("Tarefa cadastrada!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("O título não pode ser vazio.")
            
    st.write("---")
    st.write("🛠️ **Testes e Depuração**")
    if st.button("Gerar Tarefa de Teste (-1 Mês)", use_container_width=True):
        # Cria uma tarefa fictícia concluída há 30 dias atrás
        data_passada = datetime.now() - timedelta(days=30)
        tarefa_teste = {
            "Código": gerar_codigo(),
            "Titulo": "Tarefa Teste de Arquivamento Automático",
            "Descrição": "Esta tarefa disparará o arquivamento.",
            "Prioridade": "ALTA",
            "Status": "CONCLUÍDA",
            "Origem": "CHAMADO DO SISTEMA",
            "Data": data_passada.strftime("%d/%m/%Y %H:%M:%S"),
            "dataConclusao": data_passada.strftime("%d/%m/%Y %H:%M:%S")
        }
        st.session_state.tarefas.append(tarefa_teste)
        salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
        st.rerun()

tab_ativas, tab_arquivadas, tab_telemetria = st.tabs(["📋 Tarefas Ativas", "🗄️ Arquivadas & Histórico", "📈 Dashboard (Fase 3)"])

with tab_ativas:
    st.subheader("Painel de Tarefas")
    
    col_acoes, col_tabela = st.columns([1, 4])
    
    with col_acoes:
        st.write("**Ações Rápidas**")
        tarefa_alvo = st.text_input("Cód. da Tarefa:")
        
        if st.button("Concluir"):
            for t in st.session_state.tarefas:
                if t['Código'] == tarefa_alvo and t['Status'] != 'CONCLUÍDA':
                    t['Status'] = 'CONCLUÍDA'
                    t['dataConclusao'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
                    st.success("Concluída!")
                    time.sleep(1)
                    st.rerun()
                    
        if st.button("🗑️ Excluir (Pilha)"):
            for i, t in enumerate(st.session_state.tarefas):
                if t['Código'] == tarefa_alvo:
                    removida = st.session_state.tarefas.pop(i)
                    st.session_state.pilha_desfazer.empilhar(removida)
                    salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
                    st.warning(f"Tarefa {tarefa_alvo} excluída.")
                    time.sleep(1)
                    st.rerun()
                    
        if not st.session_state.pilha_desfazer.vazia():
            if st.button("⏪ Desfazer Exclusão"):
                tarefa_recuperada = st.session_state.pilha_desfazer.desempilhar()
                st.session_state.tarefas.append(tarefa_recuperada)
                salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
                st.success("Tarefa restaurada!")
                time.sleep(1)
                st.rerun()

    with col_tabela:
        if st.session_state.tarefas:
            # Usando a nova implementação do QUICK SORT para exibição principal
            tarefas_exibicao = quick_sort(st.session_state.tarefas)
            df = pd.DataFrame(tarefas_exibicao)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhuma tarefa ativa no momento.")

with tab_arquivadas:
    st.subheader("Relatório de Tarefas Arquivadas")
    if st.session_state.arquivadas:
        df_arq = pd.DataFrame(st.session_state.arquivadas)
        st.dataframe(df_arq, use_container_width=True)
    else:
        st.write("O histórico está vazio.")

with tab_telemetria:
    st.header("Dashboard de Performance")
    st.write("Gere dados fictícios para observar a diferença entre **O(n²)** e **O(n log n)** na prática.")
    
    qtd = st.number_input("Adicionar tarefas para Teste de Stress:", min_value=10, max_value=5000, step=100)
    
    if st.button("Gerar e Medir Tempo de Ordenação"):
        dados_teste = []
        for i in range(qtd):
            dados_teste.append({
                "Status": random.choice(["FAZENDO", "PENDENTE", "CONCLUÍDA"]),
                "Prioridade": random.choice(["URGENTE", "ALTA", "MÉDIA", "BAIXA"]),
                "Código": f"TEST-{i}"
            })
            
        # Medir Selection Sort
        inicio_selection = time.perf_counter()
        selection_sort(dados_teste)
        fim_selection = time.perf_counter()
        tempo_selection = (fim_selection - inicio_selection) * 1000
        
        # Medir Quick Sort
        inicio_quick = time.perf_counter()
        quick_sort(dados_teste)
        fim_quick = time.perf_counter()
        tempo_quick = (fim_quick - inicio_quick) * 1000
        
        st.session_state.telemetria.append({
            "Volume (n)": qtd,
            "O(n²) - Selection Sort (ms)": tempo_selection,
            "O(n log n) - Quick Sort (ms)": tempo_quick
        })
        
    if st.session_state.telemetria:
        df_tel = pd.DataFrame(st.session_state.telemetria)
        st.write("### Histórico de Latência")
        st.dataframe(df_tel)
        st.line_chart(df_tel.set_index("Volume (n)"))