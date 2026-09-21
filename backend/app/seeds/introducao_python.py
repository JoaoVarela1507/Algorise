"""Seed da trilha "Introdução Python" — a trilha do protótipo.

Idempotente: identifica a trilha pelo slug e os módulos pela ordem, então rodar
duas vezes atualiza em vez de duplicar.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Atividade, Modulo, Trilha
from app.models.enums import TipoAtividade

SLUG = "introducao-python"

MODULOS: list[dict] = [
    {
        "ordem": 1,
        "titulo": "Iniciando no Python",
        "descricao": "Instale o Python e confirme que está tudo certo pelo terminal.",
        "video_url": "https://www.youtube.com/watch?v=S9uPNppGsGo",
        "atividades": [
            {
                "ordem": 1,
                "tipo": TipoAtividade.terminal,
                "enunciado": "No terminal do Windows, baixe a versão mais recente do Python",
                "dica": "Apresentado no vídeo, na parte de instalação",
                "comando_esperado": "winget install Python.Python.3.14",
                "saida_esperada": "Instalação concluída com êxito",
                "tempo_sugerido_segundos": 9,
                "xp": 10,
            },
            {
                "ordem": 2,
                "tipo": TipoAtividade.terminal,
                "enunciado": "No terminal do Windows, verifique a versão do Python",
                "dica": "Apresentado no vídeo, depois da instalação",
                "comando_esperado": "python --version",
                "saida_esperada": "Python 3.14.0",
                "tempo_sugerido_segundos": 9,
                "xp": 10,
            },
            {
                "ordem": 3,
                "tipo": TipoAtividade.resposta_aberta,
                "enunciado": "Explique com suas palavras o que significa a FLAG (--version)",
                "resposta_esperada": (
                    "Flags são parâmetros que modificam o comportamento de um comando. "
                    "No exemplo --version, a flag faz o Python exibir a versão instalada."
                ),
                "tempo_sugerido_segundos": 9,
                "xp": 20,
            },
        ],
    },
    {"ordem": 2, "titulo": "Primeiro print()", "atividades": []},
    {"ordem": 3, "titulo": "Variáveis e tipos", "atividades": []},
    {"ordem": 4, "titulo": "Entrada de dados", "atividades": []},
    {"ordem": 5, "titulo": "Operadores", "atividades": []},
    {"ordem": 6, "titulo": "Condicionais", "atividades": []},
    {"ordem": 7, "titulo": "Listas", "atividades": []},
    {"ordem": 8, "titulo": "Repetição", "atividades": []},
    {"ordem": 9, "titulo": "Funções", "atividades": []},
    {
        "ordem": 10,
        "titulo": "Projeto: planejamento financeiro",
        "descricao": "Crie um programa capaz de salvar em lista seu gasto diário.",
        "atividades": [
            {
                "ordem": 1,
                "tipo": TipoAtividade.desafio_codigo,
                "enunciado": (
                    "Crie um programa de planejamento capaz de salvar em lista seu gasto diário"
                ),
                "dica": "Instale python, crie o arquivo .py e use condicionais",
                "xp": 40,
            }
        ],
    },
]


def aplicar(db: Session) -> Trilha:
    trilha = db.execute(select(Trilha).where(Trilha.slug == SLUG)).scalar_one_or_none()
    if trilha is None:
        trilha = Trilha(slug=SLUG)
        db.add(trilha)

    trilha.nome = "Introdução Python"
    trilha.disciplina = "Introdução à Programação"
    trilha.categoria = "Linguagens"
    trilha.periodo = 1
    trilha.descricao = "Do primeiro comando no terminal ao seu primeiro programa."
    trilha.publicada = True
    db.flush()

    existentes = {modulo.ordem: modulo for modulo in trilha.modulos}

    for dados in MODULOS:
        modulo = existentes.get(dados["ordem"])
        if modulo is None:
            modulo = Modulo(trilha_id=trilha.id, ordem=dados["ordem"])
            db.add(modulo)

        modulo.titulo = dados["titulo"]
        modulo.descricao = dados.get("descricao")
        modulo.video_url = dados.get("video_url")
        db.flush()

        atividades_existentes = {atividade.ordem: atividade for atividade in modulo.atividades}
        for dados_atividade in dados["atividades"]:
            atividade = atividades_existentes.get(dados_atividade["ordem"])
            if atividade is None:
                atividade = Atividade(modulo_id=modulo.id, ordem=dados_atividade["ordem"])
                db.add(atividade)

            for campo, valor in dados_atividade.items():
                setattr(atividade, campo, valor)

    db.commit()
    return trilha
