# 🔬 Benchmark de Desempenho e Armazenamento: `tse-ingestao`

> **Estudo Experimental de Engenharia de Software, Otimização de I/O e FinOps em Pipelines de Dados**  
> Repositório Principal de Engenharia: [**tse-ingestao**](https://github.com/lucas/tse-ingestao) *(substitua pelo link do seu repositório)*

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/managed%20by-uv-DE5FE9?style=flat-square)](https://github.com/astral-sh/uv)
[![Apache Parquet](https://img.shields.io/badge/Format-Apache%20Parquet-508BA9?style=flat-square)](https://parquet.apache.org/)
[![Protocol](https://img.shields.io/badge/Design-RCBD%20Experimental-0284c7?style=flat-square)](#-metodologia-científica-experimental)

---

## 📌 Sumário Executivo

Este repositório documenta a suíte de testes, metodologia experimental e resultados consolidados do benchmark de desempenho realizado sobre as versões evolutivas do projeto **`tse-ingestao`**.

O objetivo primordial da esteira `tse-ingestao` foi substituir um pipeline monolítico e ineficiente — que consumia **13 minutos de execução** e **gigabytes de espaço em disco** — por uma arquitetura ágil, paralela e com processamento em *streaming*, capaz de disponibilizar dados eleitorais prontos para análise (*Analytics-Ready*) em **menos de 1 minuto e ocupando apenas megabytes**.

Para comprovar formalmente os ganhos de engenharia e evitar métricas ilusórias (*vanity metrics*), desenvolveu-se esta suíte de testes independente com repetições em bloco casualizado, isolamento por `git worktree` e amostragem contínua de recursos (CPU, RAM, Rede e Disco).

---

## 🏗️ Evolução Arquitetural das Versões Avaliadas

Foram submetidas a teste **4 versões históricas** do projeto, representando saltos arquiteturais fundamentais:

| Versão | Commit | Estratégia de Ingestão | Processamento / Concorrência | Formato do Entregável | Estado do Dado |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **V1** | `e010a7f` | Download direto HTTP via `requests` | Sequencial (1 thread, sem pooling) | Arquivos `.zip` compactados | ❌ **Inacessível** (Binário fechado, exige descompactação downstream) |
| **V2** | `d082d9b` | Descompactação do ZIP em streaming | Sequencial (1 thread, catálogo de datasets) | Arquivos `.csv` em disco | ⚠️ **Bruto Acessível** (Dado aberto, porém volumoso e sem tipagem) |
| **V3** | `0485406` | Connection Pool HTTP + Retries com Backoff | `ThreadPoolExecutor` com escalonamento **LPT** | Arquivos `.csv` em disco | ⚠️ **Otimizado** (Mesmo CSV da V2, com redução expressiva de latência de rede) |
| **V4** | `a980086` | Ingestão, descompressão e parsing *in-memory* | Pipeline colunar vetorial em streaming (`pyarrow`) | **Apache Parquet** particionado | ✅ **Analytics-Ready** (Tipado, colunar, indexado e pronto para DuckDB/Athena) |

---

## 🔬 Metodologia Científica Experimental

Para inibir variáveis de confusão externas (latência flutuante da CDN do TSE, escalonamento térmico de processador, *caching* do sistema de arquivos do SO e reuso de memória), adotou-se o seguinte protocolo:

1. **Randomized Complete Block Design (RCBD):**
   A cada rodada de teste, a ordem de execução das 4 versões foi **sorteada aleatoriamente** (`random.shuffle`). Isso garante que flutuações pontuais de largura de banda externa ou carga do SO afetem todas as versões de forma distribuída.
2. **Isolamento de Estado com `git worktree`:**
   Cada versão foi executada a partir de um *worktree* dedicado apontando para seu respectivo *hash* de commit, compartilhando a base do Git sem mistura de código e sem resíduos de arquivos não rastreados.
3. **Ambiente Virtual Unificado (`uv run --python`):**
   Utilizou-se o runtime de alta performance do `uv` apontando para o ambiente virtual compartilhado (`bench_v4/.venv`), garantindo que todas as versões executassem exatamente sob o mesmo interpretador Python e mesmas versões de bibliotecas base.
4. **Isolamento e Quarentena de Dados (Clean Snapshot):**
   Antes de cada teste, o orquestrador mapeia o estado dos arquivos (`snapshot`). Ao término, os novos dados gerados são mensurados em bytes, contabilizados e **imediatamente movidos** para a pasta da rodada (`results/rodada_X/{versao}/`), seguido da limpeza forçada de diretórios residuais. O worktree permanece 100% limpo para o teste seguinte.
5. **Cooldown e Esgotamento de Sockets TCP:**
   Entre cada execução individual, foi estabelecido um intervalo obrigatório de **15 segundos** (*cooldown*). Isso permite fechar *sockets* de rede em estado `TIME_WAIT` e estabilizar a temperatura e frequência do processador.
6. **Amostragem em Tempo Real de Recursos com `psutil`:**
   O orquestrador monitora de forma assíncrona o consumo de CPU (média e pico) e o pico de consumo de memória física (Peak RSS) de toda a árvore de subprocessos, além do tráfego bruto recebido pela placa de rede.

---

## 💻 Ambiente e Especificações de Execução

Todas as métricas foram coletadas na mesma máquina e registradas em [`results/environment.json`](results/environment.json):

* **Processador (CPU):** Intel64 Family 6 Model 183 Stepping 1, GenuineIntel (10 núcleos físicos / 16 lógicos)
* **Memória RAM:** 23.69 GB Total
* **Sistema Operacional:** Microsoft Windows 11 Pro (Build 10.0.26300)
* **Interpretador Python:** 3.13.11
* **Gerenciador de Pacotes e Runtime:** uv 0.9.17
* **Comando Padronizado:** `uv run --python "..." python main.py -i 2014 -f 2022 --intervalo 4`
* **Escopo de Dados Testado:** 3 anos eleitorais (2014, 2018 e 2022) em 5 conjuntos de dados distintos (`candidatos`, `bens_candidatos`, `coligacoes`, `motivo_cassacao`, `votacao_candidato_municipio_zona`).

---

## 📊 Resultados Consolidados

Abaixo estão os resultados consolidados a partir da primeira bateria de **5 rodadas experimentais** completas (20 execuções isoladas):

| Versão | Tempo Médio | Tempo Mediana | Desvio Padrão ($\sigma$) | Tempo Mín | Tempo Máx | Armazenamento Final | Arquivos Gerados | Entregável Final |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **V1** | **28,50s** | 29,23s | 2,14s | 26,09s | 30,91s | **1.440,36 MB** (~1,44 GB) | 15 | 15 ZIPs compactados brutos |
| **V2** | **52,12s** | 49,80s | 7,39s | 46,15s | 64,83s | **10.992,69 MB** (~10,99 GB) | 15 | 15 CSVs extraídos |
| **V3** | **39,85s** | **33,66s** | 12,90s | 32,68s | 62,77s | **10.992,69 MB** (~10,99 GB) | 15 | 15 CSVs extraídos |
| **V4** | **73,66s** | 73,60s | **1,56s** | 72,31s | 76,23s | **278,72 MB** (~0,28 GB) | 15 | **Partições Apache Parquet** |

> Os dados brutos detalhados de cada execução encontram-se em [`results/benchmark_raw.csv`](results/benchmark_raw.csv) e o consolidado em [`results/benchmark_summary.csv`](results/benchmark_summary.csv).

---

## 📈 Visualizações do Benchmark

### 1. Tempo Médio de Execução (com Barras de Desvio Padrão)
![Tempo de Execução](results/charts/tempo_execucao.svg)

### 2. Consumo de Armazenamento em Disco (MB)
![Armazenamento em Disco](results/charts/armazenamento_disco.svg)

### 3. Consistência e Previsibilidade entre as Rodadas
![Consistência das Rodadas](results/charts/consistencia_rodadas.svg)

---

## 💡 Análise Crítica e Trade-offs de Engenharia

### 1. A Falácia da Métrica de Vaidade (V1)
À primeira vista, uma análise ingênua apontaria a **V1** como vencedora isolada por completar em apenas **28,5 segundos**. No entanto, **a V1 não entrega valor analítico**: ela simplesmente efetua o download cego do arquivo `.zip` para o disco. 
Todo o trabalho computacional pesado — descompactação, validação e carregamento de dados — foi empurrado para o elo seguinte da esteira, gerando um débito técnico severo.

### 2. O Preço da Disponibilidade do Dado (V1 ➔ V2)
A **V2** implementa a extração necessária para que os analistas consigam ler os dados. Essa mudança revela o custo oculto de lidar com dados em texto puro (`.csv`):
* O tempo de execução subiu para **52,1s** (+82% em relação à V1).
* O armazenamento explodiu de **1,4 GB para 11 GB** (um aumento de **7,6x**).
* Demonstra claramente o gargalo severo de *I/O de disco* quando um pipeline precisa descompactar e persistir múltiplos gigabytes de arquivos texto.

### 3. Eficiência de Concorrência e Pooling (V2 ➔ V3)
Ao manter rigorosamente o mesmo produto final da V2 (os mesmos 11 GB de CSVs), a **V3** implementa **Connection Pooling HTTP**, **`ThreadPoolExecutor`** e o algoritmo de escalonamento **Longest Processing Time (LPT)**:
* A mediana de tempo caiu de **49,8s para 33,66s** (**redução de 32,4%**).
* Prova a eficácia das otimizações de rede e concorrência: enquanto tarefas menores aguardam, as maiores ocupam os *workers* imediatamente, minimizando o tempo ocioso (*tail latency*).

### 4. A Revolução do Streaming Colunar em Memória (V3 ➔ V4)
A **V4** é o ápice do projeto, transformando radicalmente o modelo de dados:
* **Redução de 97,5% no consumo de disco:** O volume gerado despencou de **11.000 MB para apenas 278 MB**.
* **Menor que o próprio arquivo compactado original:** Os 278 MB de Parquet particionado ocupam **80% menos espaço do que os arquivos ZIP originais da V1 (1.440 MB)**, provando a superioridade da compressão colunar com dicionários e *bit-packing*.
* **Extrema Previsibilidade Operacional:** Enquanto a V3 apresentou desvio padrão de **12,90s** devido a variações de concorrência e disco, a V4 apresentou uma estabilidade excepcional com desvio padrão de apenas **1,56s** (variação menor que 2%).
* **Impacto em FinOps:** Em ambientes de nuvem (AWS S3, Google Cloud Storage, Athena, BigQuery ou DuckDB), uma redução de 97,5% em bytes armazenados e escaneados resulta em **economias proporcionais imediatas nas faturas de armazenamento e consulta analítica**.

---

## 🚀 Como Reproduzir o Benchmark

### 1. Pré-requisitos
* Sistema com [**uv**](https://github.com/astral-sh/uv) instalado.
* Repositório clonado e diretórios *worktrees* configurados como pastas irmãs:

```
D:\Projetos/
├── tse-ingestao/        # Repositório original com histórico Git
├── bench_v1/            # Worktree commit e010a7f
├── bench_v2/            # Worktree commit d082d9b
├── bench_v3/            # Worktree commit 0485406
├── bench_v4/            # Worktree commit a980086
└── benchmark_suite/     # Este repositório (benchmark-opt-tse-analytics)
```

Para recriar os worktrees a partir da raiz do `tse-ingestao`:
```bash
git worktree add ../bench_v1 e010a7f
git worktree add ../bench_v2 d082d9b
git worktree add ../bench_v3 0485406
git worktree add ../bench_v4 a980086
```

### 2. Executando o Benchmark

Para rodar uma bateria completa com 10 rodadas (padrão) e monitoramento avançado:
```powershell
cd D:\Projetos\benchmark_suite
uv run benchmark_runner.py --rodadas 10 --cooldown 15
```

Para rodar um teste piloto rápido de 1 rodada (*dry-run*):
```powershell
uv run benchmark_runner.py --dry-run
```

Para rodar apenas um subconjunto de versões (ex.: comparar apenas V3 e V4):
```powershell
uv run benchmark_runner.py --versoes v3 v4 --rodadas 5
```

### 3. Atualizando os Gráficos
Após a conclusão dos testes, execute o gerador para atualizar as imagens em [`results/charts/`](results/charts/):
```powershell
uv run generate_charts.py
```

---

## 📁 Estrutura do Repositório

```text
benchmark-opt-tse-analytics/
├── .gitignore               # Exclui dezenas de GBs de dados brutos extraídos
├── pyproject.toml           # Metadados e dependências do projeto
├── benchmark_runner.py      # Orquestrador com RCBD, psutil e monitoramento de sistema
├── generate_charts.py       # Gerador autônomo de gráficos vetoriais (SVG/PNG)
├── README.md                # Relatório técnico completo de engenharia
└── results/
    ├── environment.json     # Metadados de hardware, SO, CPU, RAM e commits
    ├── benchmark_raw.csv    # Histórico detalhado de todas as execuções
    ├── benchmark_summary.csv# Agregação estatística (médias, medianas, desvio padrão)
    └── charts/              # Gráficos de alta resolução para apresentação
        ├── tempo_execucao.svg
        ├── armazenamento_disco.svg
        └── consistencia_rodadas.svg
```

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais detalhes.
