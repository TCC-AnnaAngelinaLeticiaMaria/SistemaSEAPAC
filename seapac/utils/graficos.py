import base64, io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def br_for_float(valor):
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    return float(str(valor).replace("R$", "").strip().replace(".", "").replace(",", "."))

def grafico_barrasVerticais(anos, valores, titulo, ylabel, cor='#6ab04c', prefixo=''):
    fig, ax = plt.subplots(figsize=(7, 3.5))

    if len(anos) == 1:
        largura = 0.25
    elif len(anos) <= 3:
        largura = 0.4
    else:
        largura = 0.4
    barras = ax.bar([str(a) for a in anos], valores, color=cor, width=largura)

    ax.set_title(titulo, fontsize=11, fontweight='bold')
    ax.set_ylabel(ylabel)
    ax.set_xlabel('Ano')
    ax.spines[['top', 'right']].set_visible(False)
    ax.axhline(0, color='#333', linewidth=0.8)

    rotulos = [
        f'{prefixo}{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') for v in valores
    ]
    ax.bar_label(barras, labels=rotulos, padding=2, fontsize=8)

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def grafico_mix(anos, valores_monetarios, valores_nao_monetarios):
    fig, ax1 = plt.subplots(figsize=(7, 3.5))

    x = range(len(anos))
    largura = 0.35

    barras_monetarias = ax1.bar(
        [i - largura / 2 for i in x],
        valores_monetarios,
        width=largura,
        color='#6ab04c',
        label='Monetário'
    )

    ax1.set_ylabel('Valor (R$)')
    ax1.set_xlabel('Ano')

    ax2 = ax1.twinx()

    barras_nao_monetarias = ax2.bar(
        [i + largura / 2 for i in x],
        valores_nao_monetarios,
        width=largura,
        color='#4a7c59',
        label='Não monetário'
    )

    ax2.set_ylabel('Quantidade')

    ax1.set_xticks(list(x))
    ax1.set_xticklabels([str(ano) for ano in anos])
    ax1.set_title(
        'Valores monetários e não monetários por ano',
        fontsize=11,
        fontweight='bold'
    )

    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)

    for barra, valor in zip(barras_monetarias, valores_monetarios):
        ax1.annotate(
            f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
            xy=(
                barra.get_x() + barra.get_width() / 2,
                barra.get_height()
            ),
            xytext=(-8, 3),
            textcoords='offset points',
            ha='center',
            va='bottom',
            fontsize=8
        )

    rotulos_nao_monetarios = [
        f'{v:,.2f}'
        .replace(',', 'X')
        .replace('.', ',')
        .replace('X', '.')
        for v in valores_nao_monetarios
    ]
    ax2.bar_label(
        barras_nao_monetarias,
        labels=rotulos_nao_monetarios,
        padding=3,
        fontsize=8
    )

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')