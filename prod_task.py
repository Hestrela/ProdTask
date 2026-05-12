import streamlit as st
import json
import os
from datetime import datetime
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
            if not isinstance(dados, list):
                return []
            
            for t in dados:
                try:
                    t['Código'] = int(t['Código'])
                except (ValueError, TypeError):
                    t['Código'] = random.randint(10000, 99999) 
            return dados
    except (json.JSONDecodeError, IOError):
        return []

def salvar_dados(arquivo, dados):
    try:
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except IOError as e:
        st.error(f"Erro ao salvar: {e}")

# ==========================================
# ESTRUTURAS DE DADOS
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
# ALGORITMOS DE ORDENAÇÃO 
# ==========================================
def calcular_peso_tarefa(tarefa):
    ordem_status = {"FAZENDO": 1, "PENDENTE": 2, "CONCLUÍDA": 3}
    ordem_prioridade = {"URGENTE": 1, "ALTA": 2, "MÉDIA": 3, "BAIXA": 4}
    
    s = ordem_status.get(tarefa.get("Status", "PENDENTE"), 99)
    p = ordem_prioridade.get(tarefa.get("Prioridade", "BAIXA"), 5)
    return (s, p)

def selection_sort_por_data(arr):
    n = len(arr)
    arr_ordenado = arr.copy()
    for i in range(n):
        min_idx = i
        for j in range(i+1, n):
            try:
                data_j = datetime.strptime(arr_ordenado[j].get("Data", ""), "%d/%m/%Y %H:%M:%S")
            except:
                data_j = datetime.min
            try:
                data_min = datetime.strptime(arr_ordenado[min_idx].get("Data", ""), "%d/%m/%Y %H:%M:%S")
            except:
                data_min = datetime.min
                
            if data_j < data_min:
                min_idx = j
        arr_ordenado[i], arr_ordenado[min_idx] = arr_ordenado[min_idx], arr_ordenado[i]
    return arr_ordenado

def quick_sort(arr):
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

qtd_arquivadas = executar_arquivamento()
if qtd_arquivadas > 0:
    st.toast(f"🧹 {qtd_arquivadas} tarefa(s) arquivada(s) automaticamente pelo sistema!")

def gerar_codigo():
    todas = st.session_state.tarefas + st.session_state.arquivadas
    if not todas: return 1
    maior = max([t.get('Código', 0) for t in todas if isinstance(t.get('Código'), int)], default=0)
    return maior + 1

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
            
    st.markdown("---")
    st.header("⚡ Ações Rápidas")
    tarefa_alvo_str = st.text_input("Cód. da Tarefa (Numérico):")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Executar"):
            if tarefa_alvo_str.isdigit():
                alvo = int(tarefa_alvo_str)
                for t in st.session_state.tarefas:
                    if t['Código'] == alvo and t['Status'] == 'PENDENTE':
                        t['Status'] = 'FAZENDO'
                        salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
                        st.success("Em execução!")
                        time.sleep(1)
                        st.rerun()
    with col_b:
        if st.button("Concluir"):
            if tarefa_alvo_str.isdigit():
                alvo = int(tarefa_alvo_str)
                # 1. Busca a tarefa que queremos concluir
                tarefa_alvo = next((t for t in st.session_state.tarefas if t['Código'] == alvo), None)
                
                if tarefa_alvo:
                    if tarefa_alvo['Status'] != 'CONCLUÍDA':
                        # 2. Pega o "peso" da prioridade (1 = Urgente, 4 = Baixa)
                        peso_alvo = calcular_peso_tarefa(tarefa_alvo)[1]
                        
                        # 3. Verifica se tem alguma tarefa mais importante em andamento
                        bloqueio_prioridade = False
                        for t in st.session_state.tarefas:
                            if t['Status'] == 'FAZENDO':
                                peso_t = calcular_peso_tarefa(t)[1]
                                # Se o peso for menor, a prioridade é maior
                                if peso_t < peso_alvo:
                                    bloqueio_prioridade = True
                                    break
                        
                        # 4. Aplica a trava ou conclui
                        if bloqueio_prioridade:
                            st.error("⚠️ Operação bloqueada: Há uma tarefa de maior prioridade em execução!")
                        else:
                            tarefa_alvo['Status'] = 'CONCLUÍDA'
                            tarefa_alvo['dataConclusao'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)