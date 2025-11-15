from flask import Flask, render_template, request, jsonify, redirect, url_for
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Arquivo CSV para armazenar os dados
ARQUIVO_DADOS = 'dados_acesso.csv'

# Inicializar arquivo CSV se não existir
def inicializar_csv():
    if not os.path.exists(ARQUIVO_DADOS):
        df = pd.DataFrame(columns=[
            'id', 'nome', 'cpf', 'empresa', 'destino', 
            'data_entrada', 'hora_entrada', 'data_saida', 'hora_saida'
        ])
        df.to_csv(ARQUIVO_DADOS, index=False)

# Gerar gráficos
def gerar_graficos():
    try:
        df = pd.read_csv(ARQUIVO_DADOS)
        
        if df.empty:
            return None
        
        # Converter datas
        df['data_entrada'] = pd.to_datetime(df['data_entrada'])
        
        # Gráfico 1: Acessos por dia
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 2, 1)
        acessos_por_dia = df.groupby(df['data_entrada'].dt.date).size()
        acessos_por_dia.plot(kind='bar', color='skyblue')
        plt.title('Acessos por Dia')
        plt.xlabel('Data')
        plt.ylabel('Número de Acessos')
        plt.xticks(rotation=45)
        
        # Gráfico 2: Acessos por destino
        plt.subplot(2, 2, 2)
        acessos_por_destino = df['destino'].value_counts()
        acessos_por_destino.plot(kind='pie', autopct='%1.1f%%')
        plt.title('Acessos por Destino')
        
        # Gráfico 3: Acessos por empresa
        plt.subplot(2, 2, 3)
        acessos_por_empresa = df['empresa'].value_counts().head(10)
        acessos_por_empresa.plot(kind='bar', color='lightgreen')
        plt.title('Top 10 Empresas')
        plt.xlabel('Empresa')
        plt.ylabel('Número de Acessos')
        plt.xticks(rotation=45)
        
        # Gráfico 4: Horário de pico
        plt.subplot(2, 2, 4)
        df['hora'] = pd.to_datetime(df['hora_entrada']).dt.hour
        acessos_por_hora = df['hora'].value_counts().sort_index()
        acessos_por_hora.plot(kind='line', marker='o', color='orange')
        plt.title('Acessos por Hora do Dia')
        plt.xlabel('Hora')
        plt.ylabel('Número de Acessos')
        plt.grid(True)
        
        plt.tight_layout()
        
        # Converter gráfico para base64
        img = io.BytesIO()
        plt.savefig(img, format='png', dpi=300, bbox_inches='tight')
        img.seek(0)
        grafico_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
        
        return grafico_url
        
    except Exception as e:
        print(f"Erro ao gerar gráficos: {e}")
        return None

# Rotas da aplicação
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    grafico_url = gerar_graficos()
    
    # Estatísticas
    try:
        df = pd.read_csv(ARQUIVO_DADOS)
        total_acessos = len(df)
        acessos_hoje = len(df[df['data_entrada'] == datetime.now().strftime('%Y-%m-%d')])
        
        # Pessoas atualmente no local (sem data de saída)
        pessoas_presentes = len(df[df['data_saida'].isna()])
        
    except:
        total_acessos = 0
        acessos_hoje = 0
        pessoas_presentes = 0
    
    return render_template('dashboard.html', 
                         grafico_url=grafico_url,
                         total_acessos=total_acessos,
                         acessos_hoje=acessos_hoje,
                         pessoas_presentes=pessoas_presentes)

@app.route('/registrar', methods=['GET', 'POST'])
def registrar_acesso():
    if request.method == 'POST':
        # Coletar dados do formulário
        nome = request.form['nome']
        cpf = request.form['cpf']
        empresa = request.form['empresa']
        destino = request.form['destino']
        tipo_acesso = request.form['tipo_acesso']  # entrada ou saida
        
        data_atual = datetime.now().strftime('%Y-%m-%d')
        hora_atual = datetime.now().strftime('%H:%M:%S')
        
        df = pd.read_csv(ARQUIVO_DADOS)
        
        if tipo_acesso == 'entrada':
            # Registrar entrada
            novo_id = len(df) + 1
            nova_linha = {
                'id': novo_id,
                'nome': nome,
                'cpf': cpf,
                'empresa': empresa,
                'destino': destino,
                'data_entrada': data_atual,
                'hora_entrada': hora_atual,
                'data_saida': '',
                'hora_saida': ''
            }
            
            df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
            mensagem = f"Entrada registrada para {nome}"
            
        else:
            # Registrar saída
            mask = (df['cpf'] == cpf) & (df['data_saida'].isna())
            if mask.any():
                df.loc[mask, 'data_saida'] = data_atual
                df.loc[mask, 'hora_saida'] = hora_atual
                mensagem = f"Saída registrada para {nome}"
            else:
                mensagem = "Nenhuma entrada pendente encontrada para este CPF"
        
        df.to_csv(ARQUIVO_DADOS, index=False)
        return render_template('registrar.html', mensagem=mensagem)
    
    return render_template('registrar.html')

@app.route('/dados')
def obter_dados():
    try:
        df = pd.read_csv(ARQUIVO_DADOS)
        
        # Últimos 10 registros
        ultimos_registros = df.tail(10).to_dict('records')
        
        # Estatísticas para o gráfico
        df['data_entrada'] = pd.to_datetime(df['data_entrada'])
        acessos_por_dia = df.groupby(df['data_entrada'].dt.date).size()
        
        dados_grafico = {
            'labels': [str(data) for data in acessos_por_dia.index],
            'valores': acessos_por_dia.values.tolist()
        }
        
        return jsonify({
            'ultimos_registros': ultimos_registros,
            'grafico': dados_grafico
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    inicializar_csv()
    app.run(debug=True, host='0.0.0.0', port=5000)
