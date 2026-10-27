"""O aluno logado sobre a própria conta, e o perfil público dos outros.

- perfil (tela 18) e o que o onboarding grava (telas 7 a 15): `GET/PATCH /usuarios/me`;
- preferências de acessibilidade, modo de trilha e foto: `/usuarios/me/...`;
- direitos do titular (LGPD, #40): exportar os dados e excluir a conta;
- perfil reduzido de outro aluno, para o ranking: `GET /usuarios/{username}`.

Toda rota de escrita é sobre `/me`: o aluno é sempre o dono do token, e não
existe caminho que receba o id ou o username de outra pessoa para alterar.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.config import settings
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.schemas.auth import ExclusaoConta
from app.schemas.perfil import (
    AtualizacaoPerfil,
    AtualizacaoPreferencias,
    Perfil,
    PerfilPublico,
    Preferencias,
    TrocaDeTrilha,
)
from app.services import avatar, conta
from app.services import perfil as servico_perfil

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class ExclusaoAgendada(BaseModel):
    detail: str
    exclusao_agendada_para: datetime


@router.get("/me", response_model=Perfil)
def obter_perfil(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Perfil:
    return servico_perfil.montar_perfil(db, usuario)


@router.patch("/me", response_model=Perfil)
def atualizar_perfil(
    dados: AtualizacaoPerfil, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Perfil:
    try:
        return servico_perfil.atualizar_perfil(db, usuario, dados)
    except servico_perfil.CursoSemInstituicao as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Informe a instituição antes do curso",
        ) from erro


@router.patch("/me/preferencias", response_model=Preferencias)
def atualizar_preferencias(
    dados: AtualizacaoPreferencias, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Preferencias:
    """Tamanho da fonte, alto contraste e animações. Só o que for enviado muda."""
    return servico_perfil.atualizar_preferencias(db, usuario, dados)


@router.patch("/me/trilha", response_model=Perfil)
def trocar_modo_trilha(
    dados: TrocaDeTrilha, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Perfil:
    """Alterna entre Guiada, Livre e Mista sem perder progresso.

    Muda o que está liberado nas trilhas a partir de agora; o que já foi
    concluído continua concluído.
    """
    return servico_perfil.trocar_modo_trilha(db, usuario, dados.tipo_trilha)


@router.put("/me/avatar", response_model=Perfil)
def enviar_avatar(
    usuario: UsuarioAtual,
    arquivo: UploadFile = File(description="PNG, JPEG ou WebP de até 2 MB"),
    db: Session = Depends(get_db),
) -> Perfil:
    """Troca a foto do perfil. A imagem é recortada em quadrado e salva sem metadados."""
    # Um byte além do limite basta para saber que passou, sem ler o resto.
    conteudo = arquivo.file.read(settings.tamanho_maximo_avatar + 1)
    try:
        avatar.salvar(db, usuario, conteudo)
    except avatar.AvatarGrandeDemais as erro:
        megabytes = settings.tamanho_maximo_avatar // (1024 * 1024)
        raise ErroDeNegocio(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code="avatar_grande_demais",
            message=f"A foto pode ter até {megabytes} MB.",
            details={"limite_bytes": settings.tamanho_maximo_avatar},
        ) from erro
    except avatar.AvatarInvalido as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="avatar_invalido",
            message=str(erro),
        ) from erro

    return servico_perfil.montar_perfil(db, usuario)


@router.delete("/me/avatar", response_model=Perfil)
def remover_avatar(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Perfil:
    """Volta para as iniciais do nome no lugar da foto."""
    avatar.remover(db, usuario)
    return servico_perfil.montar_perfil(db, usuario)


@router.get("/me/dados")
def exportar_meus_dados(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> JSONResponse:
    """Tudo o que o Algorise guarda sobre o aluno, para baixar como arquivo."""
    return JSONResponse(
        conta.exportar_dados(db, usuario),
        headers={
            "Content-Disposition": 'attachment; filename="algorise-meus-dados.json"',
            # Dado pessoal: nem o navegador nem proxy no caminho guardam cópia.
            "Cache-Control": "no-store",
        },
    )


@router.delete("/me", response_model=ExclusaoAgendada, status_code=status.HTTP_202_ACCEPTED)
def excluir_minha_conta(
    dados: ExclusaoConta, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> ExclusaoAgendada:
    """Pede a exclusão da conta: desativa agora e apaga tudo no fim do prazo.

    202 e não 204: o pedido foi aceito, mas a exclusão só se completa no expurgo.
    """
    try:
        data = conta.agendar_exclusao(db, usuario, confirmacao=dados.confirmacao, senha=dados.senha)
    except conta.ConfirmacaoInvalida as erro:
        detalhe = (
            "Senha incorreta."
            if str(erro) == "senha"
            else f'Digite "{conta.CONFIRMACAO_DE_EXCLUSAO}" para confirmar.'
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalhe) from erro

    return ExclusaoAgendada(
        detail="Conta desativada. Os dados serão apagados na data indicada; "
        "entrar de novo antes disso cancela a exclusão.",
        exclusao_agendada_para=data,
    )


# Por último: declarada antes, engoliria "me" como se fosse um username.
@router.get("/{username}", response_model=PerfilPublico)
def obter_perfil_publico(
    username: str, _usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> PerfilPublico:
    """Perfil reduzido de outro aluno: o que o ranking já mostra, mais nível e streak.

    Pede login, como o resto da área do aluno: o perfil existe para quem está
    no ranking, e não para varrer a base de usernames de fora.
    """
    publico = servico_perfil.perfil_publico(db, username)
    if publico is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="usuario_nao_encontrado",
            message="Aluno não encontrado",
            details={"username": username},
        )
    return publico
