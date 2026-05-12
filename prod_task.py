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
            
            # Validação: Garante que os códigos sejam int mesmo se o JSON for adulterado
            for t in dados:
                try:
                    t['Código'] = int(t['Código'])
                except (ValueError, TypeError):
                    # Se colocaram letras no JSON, gera um ID aleatório seguro
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
    """Calcula um valor numérico para ordenar por Status e Prioridade."""
    ordem_status = {"FAZENDO": 1, "PENDENTE": 2, "CONCLUÍDA": 3}
    ordem_prioridade = {"URGENTE": 1, "ALTA": 2, "MÉDIA": 3, "BAIXA": 4}
    
    s = ordem_status.get(tarefa.get("Status", "PENDENTE"), 99)
    p = ordem_prioridade.get(tarefa.get("Prioridade", "BAIXA"), 5)
    return (s, p)

def selection_sort_por_data(arr):
    """Ordenação O(n^2) focada na Data de Cadastro."""
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
    """Ordenação O(n log n) focada no peso (Prioridade/Status)."""
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
    # Garante que vai buscar o maior código numérico apenas
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
                # 1. Busca a tarefa que queremos concluir a partir do input convertido ('alvo')
                tarefa_encontrada = next((t for t in st.session_state.tarefas if t['Código'] == alvo), None)
                
                if tarefa_encontrada:
                    if tarefa_encontrada['Status'] != 'CONCLUÍDA':
                        # 2. Pega o "peso" da prioridade usando sua função (1 = Urgente, 4 = Baixa)
                        peso_alvo = calcular_peso_tarefa(tarefa_encontrada)[1]
                        
                        # 3. Verifica se tem alguma tarefa mais importante em andamento
                        bloqueio_prioridade = False
                        for t in st.session_state.tarefas:
                            if t['Status'] == 'FAZENDO':
                                peso_t = calcular_peso_tarefa(t)[1]
                                # Se o peso da tarefa FAZENDO for menor, a prioridade dela é mais alta
                                if peso_t < peso_alvo:
                                    bloqueio_prioridade = True
                                    break
                        
                        # 4. Aplica a trava ou conclui
                        if bloqueio_prioridade:
                            st.toast("⚠️ Operação bloqueada: Há uma tarefa de maior prioridade em execução!")
                        else:
                            tarefa_encontrada['Status'] = 'CONCLUÍDA'
                            tarefa_encontrada['dataConclusao'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
                            st.success("Concluída!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("Esta tarefa já está concluída.")
                else:
                    st.error("Tarefa não encontrada.")
            else:
                if tarefa_alvo_str:
                    st.error("Por favor, digite um código numérico válido.")
    with col_c:
        if st.button("🗑️ Excluir"):
            if tarefa_alvo_str.isdigit():
                alvo = int(tarefa_alvo_str)
                for i, t in enumerate(st.session_state.tarefas):
                    if t['Código'] == alvo:
                        # Validação para não excluir tarefa em execução
                        if t['Status'] == 'FAZENDO':
                            st.error("Erro: Tarefa em execução não pode ser excluída!")
                        else:
                            removida = st.session_state.tarefas.pop(i)
                            st.session_state.pilha_desfazer.empilhar(removida)
                            salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
                            st.warning(f"Tarefa {alvo} excluída.")
                            time.sleep(1)
                            st.rerun()
                            
    st.markdown("---")
    # Botão de desfazer sempre visível, mas desabilitado se a pilha estiver vazia
    if st.button("⏪ Desfazer Exclusão", disabled=st.session_state.pilha_desfazer.vazia(), use_container_width=True):
        tarefa_recuperada = st.session_state.pilha_desfazer.desempilhar()
        st.session_state.tarefas.append(tarefa_recuperada)
        salvar_dados(ARQUIVO_TAREFAS, st.session_state.tarefas)
        st.success("Tarefa restaurada com sucesso!")
        time.sleep(1)
        st.rerun()

# Criação das guias separadas
tab_cadastradas, tab_execucao, tab_arquivadas, tab_telemetria = st.tabs([
    "📌 Tarefas Cadastradas", "⚙️ Em Execução", "🗄️ Histórico", "📈 Dashboard"
])

with tab_cadastradas:
    st.subheader("Fila de Tarefas Pendentes")
    
    # 1. Filtra as pendentes
    pendentes = [t for t in st.session_state.tarefas if t['Status'] == 'PENDENTE' or t['Status'] == 'CONCLUÍDA']
    
    # 2. Ordena por Data de Cadastro usando Selection Sort (Requisito do professor)
    pendentes_ordenadas = selection_sort_por_data(pendentes)
    
    # 3. Cria as instâncias de Fila para cada prioridade
    filas = {
        "URGENTE": Fila(),
        "ALTA": Fila(),
        "MÉDIA": Fila(),
        "BAIXA": Fila()
    }
    
    # 4. Enfileira as tarefas
    for t in pendentes_ordenadas:
        if t['Prioridade'] in filas:
            filas[t['Prioridade']].enfileirar(t)
            
    # 5. Desenfileira respeitando a prioridade para exibição
    tarefas_para_exibicao = []
    for prioridade in ["URGENTE", "ALTA", "MÉDIA", "BAIXA"]:
        while not filas[prioridade].vazia():
            tarefas_para_exibicao.append(filas[prioridade].desenfileirar())
            
    if tarefas_para_exibicao:
        df_cadastradas = pd.DataFrame(tarefas_para_exibicao)
        st.dataframe(df_cadastradas, use_container_width=True)
    else:
        st.info("Nenhuma tarefa pendente na fila.")

with tab_execucao:
    st.subheader("Tarefas Sendo Executadas")
    
    em_execucao = [t for t in st.session_state.tarefas if t['Status'] == 'FAZENDO']
    
    if em_execucao:
        # Aplicação do Quick Sort diretamente na aplicação principal para ordenar o que está em execução
        em_execucao_ordenada = quick_sort(em_execucao)
        df_execucao = pd.DataFrame(em_execucao_ordenada)
        st.dataframe(df_execucao, use_container_width=True)
    else:
        st.info("Nenhuma tarefa em execução no momento.")

with tab_arquivadas:
    st.subheader("Relatório de Tarefas Arquivadas")
    if st.session_state.arquivadas:
        df_arq = pd.DataFrame(st.session_state.arquivadas)
        st.dataframe(df_arq, use_container_width=True)
    else:
        st.write("O histórico está vazio.")

with tab_telemetria:
    st.header("Dashboard de Performance")
    st.write("Teste de estresse comparando **Selection Sort** e **Quick Sort**.")
    
    qtd = st.number_input("Adicionar tarefas fictícias:", min_value=10, max_value=5000, step=100)
    
    if st.button("Gerar e Medir"):
        dados_teste = []
        for i in range(qtd):
            dados_teste.append({
                "Status": random.choice(["FAZENDO", "PENDENTE", "CONCLUÍDA"]),
                "Prioridade": random.choice(["URGENTE", "ALTA", "MÉDIA", "BAIXA"]),
                "Código": i,
                "Data": f"01/01/2026 12:00:00"
            })
            
        inicio_selection = time.perf_counter()
        selection_sort_por_data(dados_teste)
        fim_selection = time.perf_counter()
        tempo_selection = (fim_selection - inicio_selection) * 1000
        
        inicio_quick = time.perf_counter()
        quick_sort(dados_teste)
        fim_quick = time.perf_counter()
        tempo_quick = (fim_quick - inicio_quick) * 1000
        
        st.session_state.telemetria.append({
            "Volume (n)": qtd,
            "Selection Sort (ms)": tempo_selection,
            "Quick Sort (ms)": tempo_quick
        })
        
    if st.session_state.telemetria:
        df_tel = pd.DataFrame(st.session_state.telemetria)
        st.dataframe(df_tel)
        st.line_chart(df_tel.set_index("Volume (n)"))