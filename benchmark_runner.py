# /// script
# dependencies = [
#   "pandas",
#   "psutil",
# ]
# ///
"""
Suíte de Testes e Benchmark Científico de Ingestão de Dados do TSE
===================================================================
Este script orquestra a execução controlada e comparativa das versões do
projeto opt-tse-analytics utilizando o modelo experimental Randomized Complete Block
Design (RCBD), medição em tempo real de CPU, RAM e Rede com psutil, isolamento
de arquivos e cálculo de métricas estatísticas consolidadas.
"""

import os
import sys
import time
import json
import shutil
import random
import argparse
import platform
import threading
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
import psutil

# --- ESTRUTURA DE DIRETÓRIOS ---
SUITE_DIR = Path(__file__).resolve().parent
BASE_DIR = SUITE_DIR.parent
RESULTS_DIR = SUITE_DIR / "results"

# Caminho do ambiente virtual compartilhado que possui as dependências necessárias
SHARED_VENV = BASE_DIR / "bench_v4" / ".venv"

# Mapeamento padrão dos worktrees das versões
VERSIONS = {
    "v1": BASE_DIR / "bench_v1",
    "v2": BASE_DIR / "bench_v2",
    "v3": BASE_DIR / "bench_v3",
    "v4": BASE_DIR / "bench_v4",
}

# Informações técnicas dos commits testados
VERSION_METADATA = {
    "v1": {
        "commit": "e010a7f",
        "titulo": "V1 - Baseline HTTP Download (ZIP)",
        "descricao": "Download sequencial direto de ZIPs via requests sem extração.",
        "formato_saida": "ZIP (compactado bruto)"
    },
    "v2": {
        "commit": "d082d9b",
        "titulo": "V2 - Extração e Catálogo para CSV",
        "descricao": "Streaming de descompactação e catálogo de datasets para CSVs locais.",
        "formato_saida": "CSV (texto puro descompactado)"
    },
    "v3": {
        "commit": "0485406",
        "titulo": "V3 - Concorrência, Pooling & LPT",
        "descricao": "ThreadPoolExecutor, Connection Pool HTTP persistente, ordenação LPT e retries.",
        "formato_saida": "CSV (texto puro descompactado)"
    },
    "v4": {
        "commit": "a980086",
        "titulo": "V4 - Streaming em Memória para Apache Parquet",
        "descricao": "Streaming em memória e escrita direta em Apache Parquet particionado.",
        "formato_saida": "Apache Parquet (colunar analítico particionado)"
    }
}

# Comando padrão de execução nos worktrees
COMMAND_ARGS = ["-i", "2014", "-f", "2022", "--intervalo", "4"]

# Pastas e extensões técnicas a serem desconsideradas na contagem de dados
IGNORE_NAMES = {".git", "__pycache__", ".venv", ".ruff_cache", ".pytest_cache"}


class ProcessMonitor(threading.Thread):
    """
    Monitor assíncrono que amostra o consumo de CPU e RAM
    de todo o grafo de processos (processo pai + filhos recursivos).
    """
    def __init__(self, pid: int, interval: float = 0.15):
        super().__init__(daemon=True)
        self.pid = pid
        self.interval = interval
        self.stop_event = threading.Event()
        self.cpu_samples = []
        self.max_rss_bytes = 0

    def run(self):
        try:
            parent = psutil.Process(self.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

        while not self.stop_event.is_set():
            try:
                procs = [parent] + parent.children(recursive=True)
                rss_sum = 0
                cpu_sum = 0
                for p in procs:
                    try:
                        rss_sum += p.memory_info().rss
                        cpu_sum += p.cpu_percent(interval=None)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if rss_sum > self.max_rss_bytes:
                    self.max_rss_bytes = rss_sum
                if cpu_sum > 0:
                    self.cpu_samples.append(cpu_sum)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(self.interval)

    def stop(self):
        self.stop_event.set()
        self.join(timeout=1.0)
        pico_ram_mb = round(self.max_rss_bytes / (1024 * 1024), 2)
        cpu_media = round(sum(self.cpu_samples) / len(self.cpu_samples), 2) if self.cpu_samples else 0.0
        cpu_pico = round(max(self.cpu_samples), 2) if self.cpu_samples else 0.0
        return pico_ram_mb, cpu_media, cpu_pico


def get_files_snapshot(folder: Path) -> set:
    """Mapeia os arquivos atuais ignorando arquivos técnicos e de compilação."""
    snapshot = set()
    for p in folder.rglob("*"):
        if p.is_file():
            if any(ign in p.parts for ign in IGNORE_NAMES) or p.suffix == ".pyc":
                continue
            snapshot.add(p.relative_to(folder))
    return snapshot


def collect_environment_metadata():
    """Coleta e persiste os metadados do hardware, sistema operacional e runtime."""
    env_data = {
        "project": {
            "name": "benchmark-opt-tse-analytics",
            "target_repository": "opt-tse-analytics",
            "description": "Suíte de benchmark experimental e análise de desempenho das versões de ingestão de dados do TSE",
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "hardware": {
            "cpu_model": platform.processor(),
            "cpu_physical_cores": psutil.cpu_count(logical=False),
            "cpu_logical_cores": psutil.cpu_count(logical=True),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
            "os_name": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version()
        },
        "runtime": {
            "python_version": platform.python_version(),
            "shared_venv": str(SHARED_VENV.relative_to(BASE_DIR)) if SHARED_VENV.exists() else None
        },
        "benchmark_protocol": {
            "design": "Randomized Complete Block Design (RCBD)",
            "isolation_method": "Git Worktree (commits imutáveis isolados)",
            "cli_arguments": COMMAND_ARGS,
            "tested_years": [2014, 2018, 2022],
            "tested_datasets": [
                "candidatos",
                "bens_candidatos",
                "coligacoes",
                "motivo_cassacao",
                "votacao_candidato_municipio_zona"
            ]
        },
        "versions_under_test": VERSION_METADATA
    }
    
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    env_file = RESULTS_DIR / "environment.json"
    with open(env_file, "w", encoding="utf-8") as f:
        json.dump(env_data, f, indent=2, ensure_ascii=False)
    return env_data


def run_benchmark(n_rounds: int, cooldown_sec: int, selected_versions: list):
    """Executa a bateria completa do benchmark com medições ampliadas."""
    print("=" * 70)
    print("🔬 SUÍTE DE TESTES E BENCHMARK CIENTÍFICO: TSE-INGESTÃO")
    print(f"Diretório da Suíte:     {SUITE_DIR}")
    print(f"Diretório dos Worktrees: {BASE_DIR}")
    print(f"Total de rodadas:        {n_rounds} (Total de {n_rounds * len(selected_versions)} execuções)")
    print(f"Versões selecionadas:    {', '.join(selected_versions)}")
    print(f"Tempo de resfriamento:   {cooldown_sec}s")
    print("=" * 70)

    # Validar presença dos diretórios dos worktrees
    for v in selected_versions:
        path = VERSIONS.get(v)
        if not path or not path.exists():
            print(f"❌ ERRO CRÍTICO: Worktree da versão '{v}' não encontrado em: {path}")
            sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    collect_environment_metadata()
    all_metrics = []

    for round_num in range(1, n_rounds + 1):
        # Randomized Complete Block Design (RCBD) para mitigar flutuações temporais e de rede
        order = list(selected_versions)
        random.shuffle(order)

        print(f"\n📢 ==================== RODADA {round_num}/{n_rounds} ====================")
        print(f"Ordem de execução sorteada: {' ➔ '.join(order.upper() for order in order)}")

        for version in order:
            worktree_dir = VERSIONS[version]
            archive_dir = RESULTS_DIR / f"rodada_{round_num}" / version
            archive_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n▶ [{version.upper()}] Executando em: {worktree_dir.name}...")
            horario_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 1. Snapshot do estado antes da execução
            initial_files = get_files_snapshot(worktree_dir)

            # 2. Medição da rede antes da execução
            net_before = psutil.net_io_counters()

            # 3. Montar comando usando o venv compartilhado
            cmd = ["uv", "run", "--python", str(SHARED_VENV), "python", "main.py"] + COMMAND_ARGS

            start_time = time.perf_counter()
            process = subprocess.Popen(
                cmd,
                cwd=str(worktree_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 4. Monitoramento assíncrono de CPU e RAM
            monitor = ProcessMonitor(process.pid)
            monitor.start()

            stdout, stderr = process.communicate()
            elapsed_time = time.perf_counter() - start_time
            horario_fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Finalizar monitor e capturar métricas de sistema
            pico_ram_mb, cpu_media_pct, cpu_pico_pct = monitor.stop()

            # 5. Medição de tráfego de rede
            net_after = psutil.net_io_counters()
            bytes_recv = max(0, net_after.bytes_recv - net_before.bytes_recv)
            net_recv_mb = round(bytes_recv / (1024 * 1024), 2)
            download_speed_mbs = round(net_recv_mb / elapsed_time, 2) if elapsed_time > 0 else 0.0

            # 6. Snapshot depois do teste
            current_files = get_files_snapshot(worktree_dir)
            created_files = current_files - initial_files

            # Cálculo do tamanho total dos dados gerados em disco
            total_bytes = sum((worktree_dir / rel_path).stat().st_size for rel_path in created_files)
            total_mb = round(total_bytes / (1024 * 1024), 2)
            success = (process.returncode == 0)

            # 7. Mover arquivos gerados para a pasta da rodada (isola dados e limpa worktree)
            for rel_path in created_files:
                src = worktree_dir / rel_path
                dst = archive_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))

            # Limpeza rigorosa de pastas residuais no worktree
            data_dir = worktree_dir / "data"
            if data_dir.exists():
                shutil.rmtree(data_dir, ignore_errors=True)

            for item in list(worktree_dir.glob("*")):
                if item.is_dir() and item.name not in IGNORE_NAMES and not any(item.iterdir()):
                    try:
                        item.rmdir()
                    except OSError:
                        pass

            # Feedback no console e salvamento de logs em caso de erro
            if not success:
                print(f"⚠️ FALHA em {version} (Código de saída: {process.returncode})!")
                with open(archive_dir / "error.log", "w", encoding="utf-8") as f:
                    f.write(stderr)
            else:
                print(
                    f"✅ SUCESSO! Tempo: {elapsed_time:.2f}s | "
                    f"Disco: {total_mb} MB | "
                    f"Pico RAM: {pico_ram_mb} MB | "
                    f"CPU Média: {cpu_media_pct}% | "
                    f"Down: {download_speed_mbs} MB/s"
                )

            # 8. Registrar métricas ampliadas
            all_metrics.append({
                "rodada": round_num,
                "versao": version,
                "horario_inicio": horario_inicio,
                "horario_fim": horario_fim,
                "tempo_segundos": round(elapsed_time, 2),
                "armazenamento_mb": total_mb,
                "qtd_arquivos": len(created_files),
                "pico_ram_mb": pico_ram_mb,
                "cpu_media_pct": cpu_media_pct,
                "cpu_pico_pct": cpu_pico_pct,
                "dados_rede_mb": net_recv_mb,
                "velocidade_download_mbs": download_speed_mbs,
                "sucesso": success
            })

            # Atualiza CSV bruto incrementalmente
            df_raw = pd.DataFrame(all_metrics)
            df_raw.to_csv(RESULTS_DIR / "benchmark_raw.csv", index=False)

            # Cooldown entre execuções para estabilizar CPU e portas TCP
            print(f"⏳ Pausa de resfriamento ({cooldown_sec}s)...")
            time.sleep(cooldown_sec)

    # --- RELATÓRIO ESTATÍSTICO CONSOLIDADO ---
    print("\n" + "=" * 70)
    print("📊 RESULTADOS CONSOLIDADOS DO BENCHMARK")
    print("=" * 70)
    df = pd.DataFrame(all_metrics)

    summary = df[df["sucesso"]].groupby("versao").agg(
        tempo_medio_s=("tempo_segundos", "mean"),
        tempo_mediana_s=("tempo_segundos", "median"),
        tempo_desvio_padrao=("tempo_segundos", "std"),
        tempo_min_s=("tempo_segundos", "min"),
        tempo_max_s=("tempo_segundos", "max"),
        armazenamento_medio_mb=("armazenamento_mb", "mean"),
        pico_ram_medio_mb=("pico_ram_mb", "mean"),
        cpu_media_pct=("cpu_media_pct", "mean"),
        velocidade_download_media_mbs=("velocidade_download_mbs", "mean")
    ).reset_index()

    summary.to_csv(RESULTS_DIR / "benchmark_summary.csv", index=False)
    print(summary.to_string(index=False))
    print(f"\n📁 Todos os artefatos e CSVs foram salvos em: {RESULTS_DIR}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Suíte de Benchmark Científico para Ingestão de Dados do TSE"
    )
    parser.add_argument(
        "--rodadas", "-r",
        type=int,
        default=10,
        help="Quantidade de rodadas de teste a serem executadas (padrão: 10)"
    )
    parser.add_argument(
        "--cooldown", "-c",
        type=int,
        default=15,
        help="Intervalo de resfriamento em segundos entre testes (padrão: 15s)"
    )
    parser.add_argument(
        "--versoes", "-v",
        nargs="+",
        default=["v1", "v2", "v3", "v4"],
        choices=["v1", "v2", "v3", "v4"],
        help="Versões a incluir no teste (padrão: todas as quatro)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa um teste piloto rápido de 1 rodada para validar a integridade dos worktrees"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    rounds = 1 if args.dry_run else args.rodadas
    run_benchmark(
        n_rounds=rounds,
        cooldown_sec=args.cooldown,
        selected_versions=args.versoes
    )
