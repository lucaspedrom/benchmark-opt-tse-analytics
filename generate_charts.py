# /// script
# dependencies = [
#   "pandas",
# ]
# ///
"""
Gerador de Gráficos do Benchmark TSE-Ingestão
=============================================
Gera visualizações gráficas de alta qualidade (vetorial SVG e PNG se matplotlib estiver disponível)
com base nos resultados consolidados das baterias de testes.
"""

import sys
import pandas as pd
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SUITE_DIR / "results"
CHARTS_DIR = RESULTS_DIR / "charts"

# Paleta de cores moderna para o tema de engenharia de dados
COLORS = {
    "v1": "#64748b",  # Slate (Baseline/Cru)
    "v2": "#f59e0b",  # Amber (CSV não otimizado)
    "v3": "#3b82f6",  # Blue (Concorrência)
    "v4": "#10b981",  # Emerald (Parquet otimizado)
}

VERSION_LABELS = {
    "v1": "V1 (ZIP Baseline)",
    "v2": "V2 (CSV Iterativo)",
    "v3": "V3 (CSV Concorrente)",
    "v4": "V4 (Parquet Streaming)",
}


def create_svg_bar_chart(title, subtitle, labels, values, unit, filename, colors=None, error_values=None):
    """Gera um gráfico de barras vetorial SVG elegante e responsivo sem dependências externas."""
    width = 800
    height = 450
    margin_top = 80
    margin_bottom = 70
    margin_left = 90
    margin_right = 50

    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    max_val = max(values) if values else 1
    # Escala com 15% de folga no topo
    scale_max = max_val * 1.2 if max_val > 0 else 1

    bar_group_width = plot_width / len(labels)
    bar_width = min(80, bar_group_width * 0.55)

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="background:#0f172a; font-family:-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;">',
        f'<defs>',
        f'  <linearGradient id="grid-grad" x1="0%" y1="0%" x2="0%" y2="100%">',
        f'    <stop offset="0%" stop-color="#334155" stop-opacity="0.2"/>',
        f'    <stop offset="100%" stop-color="#334155" stop-opacity="0.05"/>',
        f'  </linearGradient>',
        f'</defs>',
        # Fundo do gráfico
        f'<rect width="{width}" height="{height}" rx="12" fill="#0f172a"/>',
        # Título e Subtítulo
        f'<text x="{margin_left}" y="36" fill="#f8fafc" font-size="20" font-weight="700">{title}</text>',
        f'<text x="{margin_left}" y="58" fill="#94a3b8" font-size="13">{subtitle}</text>',
    ]

    # Linhas de grade horizontais
    grid_steps = 5
    for i in range(grid_steps + 1):
        step_val = (scale_max / grid_steps) * i
        y_pos = margin_top + plot_height - (step_val / scale_max) * plot_height
        svg_lines.append(f'<line x1="{margin_left}" y1="{y_pos:.1f}" x2="{width - margin_right}" y2="{y_pos:.1f}" stroke="#1e293b" stroke-width="1"/>')
        val_str = f"{step_val:,.1f}" if scale_max < 100 else f"{step_val:,.0f}"
        svg_lines.append(f'<text x="{margin_left - 12}" y="{y_pos + 4:.1f}" fill="#64748b" font-size="11" text-anchor="end">{val_str} {unit}</text>')

    # Linha base do eixo X
    svg_lines.append(f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{width - margin_right}" y2="{margin_top + plot_height}" stroke="#334155" stroke-width="2"/>')

    # Barras
    for i, (label, val) in enumerate(zip(labels, values)):
        bar_h = (val / scale_max) * plot_height
        bar_x = margin_left + i * bar_group_width + (bar_group_width - bar_width) / 2
        bar_y = margin_top + plot_height - bar_h
        color = colors[i] if colors else "#3b82f6"

        # Barra com cantos arredondados no topo
        svg_lines.append(f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width:.1f}" height="{bar_h:.1f}" rx="6" fill="{color}" opacity="0.95"/>')

        # Valor no topo da barra
        val_text = f"{val:,.2f}" if val < 100 else f"{val:,.1f}"
        svg_lines.append(f'<text x="{bar_x + bar_width/2:.1f}" y="{bar_y - 10:.1f}" fill="#f8fafc" font-size="13" font-weight="700" text-anchor="middle">{val_text} {unit}</text>')

        # Barra de erro (desvio padrão) se fornecida
        if error_values and i < len(error_values) and error_values[i] > 0:
            err = error_values[i]
            err_h = (err / scale_max) * plot_height
            y_top = max(margin_top, bar_y - err_h)
            y_bottom = min(margin_top + plot_height, bar_y + err_h)
            svg_lines.append(f'<line x1="{bar_x + bar_width/2:.1f}" y1="{y_top:.1f}" x2="{bar_x + bar_width/2:.1f}" y2="{y_bottom:.1f}" stroke="#cbd5e1" stroke-width="2"/>')
            svg_lines.append(f'<line x1="{bar_x + bar_width/2 - 6:.1f}" y1="{y_top:.1f}" x2="{bar_x + bar_width/2 + 6:.1f}" y2="{y_top:.1f}" stroke="#cbd5e1" stroke-width="2"/>')
            svg_lines.append(f'<line x1="{bar_x + bar_width/2 - 6:.1f}" y1="{y_bottom:.1f}" x2="{bar_x + bar_width/2 + 6:.1f}" y2="{y_bottom:.1f}" stroke="#cbd5e1" stroke-width="2"/>')

        # Rótulo da versão no eixo X
        svg_lines.append(f'<text x="{bar_x + bar_width/2:.1f}" y="{margin_top + plot_height + 25:.1f}" fill="#cbd5e1" font-size="12" font-weight="600" text-anchor="middle">{label}</text>')

    svg_lines.append('</svg>')

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CHARTS_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))
    print(f"📊 Gráfico vetorial salvo: {out_path.name}")


def create_svg_scatter_chart(raw_df: pd.DataFrame, filename: str):
    """Gera gráfico SVG de dispersão (tempo x rodadas) demonstrando estabilidade."""
    width = 800
    height = 450
    margin_top = 80
    margin_bottom = 60
    margin_left = 90
    margin_right = 50

    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    max_time = raw_df["tempo_segundos"].max() * 1.15
    rounds = sorted(raw_df["rodada"].unique())
    versions = ["v1", "v2", "v3", "v4"]

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="background:#0f172a; font-family:-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;">',
        f'<rect width="{width}" height="{height}" rx="12" fill="#0f172a"/>',
        f'<text x="{margin_left}" y="36" fill="#f8fafc" font-size="20" font-weight="700">Consistência e Variação por Rodada</text>',
        f'<text x="{margin_left}" y="58" fill="#94a3b8" font-size="13">Tempo de execução medido em cada rodada independente (em segundos)</text>',
    ]

    # Grid Y
    for i in range(6):
        val = (max_time / 5) * i
        y_pos = margin_top + plot_height - (val / max_time) * plot_height
        svg_lines.append(f'<line x1="{margin_left}" y1="{y_pos:.1f}" x2="{width - margin_right}" y2="{y_pos:.1f}" stroke="#1e293b" stroke-width="1"/>')
        svg_lines.append(f'<text x="{margin_left - 12}" y="{y_pos + 4:.1f}" fill="#64748b" font-size="11" text-anchor="end">{val:.0f}s</text>')

    # Linhas dos pontos por rodada
    step_x = plot_width / (len(rounds) + 1)

    for r_idx, r in enumerate(rounds):
        x_pos = margin_left + (r_idx + 1) * step_x
        svg_lines.append(f'<line x1="{x_pos:.1f}" y1="{margin_top}" x2="{x_pos:.1f}" y2="{margin_top + plot_height}" stroke="#1e293b" stroke-dasharray="3,3"/>')
        svg_lines.append(f'<text x="{x_pos:.1f}" y="{margin_top + plot_height + 25:.1f}" fill="#94a3b8" font-size="12" text-anchor="middle">Rodada {r}</text>')

    # Pontos
    for v in versions:
        sub = raw_df[raw_df["versao"] == v]
        color = COLORS.get(v, "#3b82f6")
        pts = []
        for _, row in sub.iterrows():
            r = row["rodada"]
            t = row["tempo_segundos"]
            r_idx = rounds.index(r)
            x_pos = margin_left + (r_idx + 1) * step_x
            y_pos = margin_top + plot_height - (t / max_time) * plot_height
            pts.append((x_pos, y_pos))
            svg_lines.append(f'<circle cx="{x_pos:.1f}" cy="{y_pos:.1f}" r="6" fill="{color}" stroke="#0f172a" stroke-width="2"/>')

        # Linha conectando as rodadas da mesma versão
        if len(pts) > 1:
            d_str = " ".join([f"{'M' if idx == 0 else 'L'} {px:.1f} {py:.1f}" for idx, (px, py) in enumerate(pts)])
            svg_lines.append(f'<path d="{d_str}" fill="none" stroke="{color}" stroke-width="2" opacity="0.6"/>')

    # Legenda no canto superior direito
    leg_x = width - margin_right - 180
    for idx, v in enumerate(versions):
        ly = margin_top + 10 + idx * 22
        c = COLORS.get(v, "#ffffff")
        svg_lines.append(f'<circle cx="{leg_x}" cy="{ly}" r="5" fill="{c}"/>')
        svg_lines.append(f'<text x="{leg_x + 12}" y="{ly + 4}" fill="#cbd5e1" font-size="11">{VERSION_LABELS.get(v, v)}</text>')

    svg_lines.append('</svg>')

    out_path = CHARTS_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))
    print(f"📊 Gráfico vetorial de dispersão salvo: {out_path.name}")


def main():
    summary_path = RESULTS_DIR / "benchmark_summary.csv"
    raw_path = RESULTS_DIR / "benchmark_raw.csv"

    if not summary_path.exists() or not raw_path.exists():
        print(f"❌ Erro: Arquivos CSV de resultados não encontrados em: {RESULTS_DIR}")
        sys.exit(1)

    df_summary = pd.read_csv(summary_path)
    df_raw = pd.read_csv(raw_path)

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    print("🎨 Gerando gráficos do benchmark...")

    labels = [VERSION_LABELS.get(v, v) for v in df_summary["versao"]]
    colors = [COLORS.get(v, "#3b82f6") for v in df_summary["versao"]]

    # 1. Gráfico de Tempo Médio com Desvio Padrão
    tempo_medio = df_summary["tempo_medio_s"].tolist()
    desvio_padrao = df_summary["tempo_desvio_padrao"].tolist()
    create_svg_bar_chart(
        title="Tempo Médio de Execução por Versão",
        subtitle="Média amostral das rodadas (em segundos) com barras de erro de desvio padrão",
        labels=labels,
        values=tempo_medio,
        unit="s",
        filename="tempo_execucao.svg",
        colors=colors,
        error_values=desvio_padrao
    )

    # 2. Gráfico de Armazenamento em Disco
    armazenamento = df_summary["armazenamento_medio_mb"].tolist()
    create_svg_bar_chart(
        title="Consumo de Armazenamento em Disco",
        subtitle="Volume final persistido em disco por versão (em Megabytes)",
        labels=labels,
        values=armazenamento,
        unit="MB",
        filename="armazenamento_disco.svg",
        colors=colors
    )

    # 3. Gráfico de Dispersão das Rodadas
    create_svg_scatter_chart(
        raw_df=df_raw,
        filename="consistencia_rodadas.svg"
    )

    # Opcional: Se matplotlib estiver instalado, gera também versões PNG
    try:
        import matplotlib.pyplot as plt
        import matplotlib as mpl

        mpl.rcParams["figure.facecolor"] = "#0f172a"
        mpl.rcParams["axes.facecolor"] = "#0f172a"
        mpl.rcParams["text.color"] = "#f8fafc"
        mpl.rcParams["axes.labelcolor"] = "#94a3b8"
        mpl.rcParams["xtick.color"] = "#cbd5e1"
        mpl.rcParams["ytick.color"] = "#cbd5e1"

        # Salva PNG de Tempo
        fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
        ax.bar(labels, tempo_medio, yerr=desvio_padrao, capsize=5, color=colors)
        ax.set_ylabel("Segundos")
        ax.set_title("Tempo de Execução (s)")
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "tempo_execucao.png")
        plt.close()

        # Salva PNG de Armazenamento
        fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
        ax.bar(labels, armazenamento, color=colors)
        ax.set_ylabel("Megabytes (MB)")
        ax.set_title("Armazenamento em Disco (MB)")
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "armazenamento_disco.png")
        plt.close()
        print("🖼️ Versões PNG geradas com matplotlib com sucesso!")
    except ImportError:
        print("ℹ️ Matplotlib não detectado: gráficos vetoriais SVG gerados com suporte total!")

    print(f"✨ Gráficos prontos em: {CHARTS_DIR}")


if __name__ == "__main__":
    main()
