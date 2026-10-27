"""Cliente do Ollama, o provedor de IA do Algorise (#11).

O cliente HTTP é o `httpx2`, o mesmo que o Authlib já traz para o projeto: um
cliente a mais só para a IA seria outra dependência para auditar.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass

import httpx2

from app.ia.base import DIMENSOES_EMBEDDING, IAIndisponivel, MensagemIA

# Erros de rede em que vale tentar de novo: o pedido nem chegou ao modelo.
_FALHAS_DE_CONEXAO = (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.PoolTimeout)


class Ollama:
    """Cliente do `/api/chat` do Ollama, com `stream: true`, e do `/api/embed`.

    O Ollama responde uma linha JSON por pedaço (`{"message": {"content": ...},
    "done": false}`) e fecha com `"done": true`. Erro vem como `{"error": ...}`,
    tanto no status HTTP quanto no meio do stream.
    """

    def __init__(
        self,
        url: str,
        modelo: str,
        *,
        timeout_conexao: float,
        timeout_leitura: float,
        tentativas: int,
        modelo_embedding: str = "bge-m3",
        espera_entre_tentativas: float = 0.5,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self.url = url
        self.modelo = modelo
        self.modelo_embedding = modelo_embedding
        self.timeout = httpx2.Timeout(timeout_leitura, connect=timeout_conexao)
        self.tentativas = max(tentativas, 1)
        self.espera_entre_tentativas = espera_entre_tentativas
        # Injetado pelos testes (`httpx2.MockTransport`); em produção, a rede.
        self.transport = transport

    async def gerar(
        self, mensagens: Sequence[MensagemIA], *, max_tokens: int
    ) -> AsyncGenerator[str]:
        corpo = {
            "model": self.modelo,
            "stream": True,
            "messages": [{"role": m.papel, "content": m.conteudo} for m in mensagens],
            # `num_predict` é o teto de tokens da resposta: corta a geração no
            # Ollama, em vez de deixar ele gerar e descartar aqui.
            "options": {"num_predict": max_tokens},
        }

        for tentativa in range(1, self.tentativas + 1):
            emitiu = False
            try:
                async with (
                    httpx2.AsyncClient(
                        base_url=self.url, timeout=self.timeout, transport=self.transport
                    ) as cliente,
                    cliente.stream("POST", "/api/chat", json=corpo) as resposta,
                ):
                    if resposta.status_code != httpx2.codes.OK:
                        await resposta.aread()
                        motivo = _erro_do_corpo(resposta.text)
                        raise IAIndisponivel(f"Ollama respondeu {resposta.status_code}: {motivo}")

                    async for linha in resposta.aiter_lines():
                        if not linha.strip():
                            continue
                        pedaco = _ler_linha(linha)
                        if pedaco.texto:
                            emitiu = True
                            yield pedaco.texto
                        if pedaco.fim:
                            return
                # O Ollama fechou a conexão sem mandar o `done`: a resposta pode
                # ter sido cortada, e quem consome precisa saber.
                raise IAIndisponivel("Ollama encerrou a resposta sem concluir")
            except _FALHAS_DE_CONEXAO as erro:
                if emitiu or tentativa == self.tentativas:
                    raise IAIndisponivel(f"Sem conexão com o Ollama em {self.url}") from erro
                await asyncio.sleep(self.espera_entre_tentativas * tentativa)
            except httpx2.TimeoutException as erro:
                # Timeout de leitura: o modelo travou no meio. Tentar de novo
                # custaria mais uma espera inteira, com o aluno olhando.
                raise IAIndisponivel("O Ollama demorou demais para responder") from erro
            except httpx2.HTTPError as erro:
                raise IAIndisponivel(f"Falha ao falar com o Ollama: {erro}") from erro

    async def embeddings(self, textos: Sequence[str]) -> list[list[float]]:
        """Todos os textos num pedido só: o `/api/embed` aceita uma lista em `input`."""
        if not textos:
            return []
        corpo = {"model": self.modelo_embedding, "input": list(textos)}

        for tentativa in range(1, self.tentativas + 1):
            try:
                async with httpx2.AsyncClient(
                    base_url=self.url, timeout=self.timeout, transport=self.transport
                ) as cliente:
                    resposta = await cliente.post("/api/embed", json=corpo)
                break
            except _FALHAS_DE_CONEXAO as erro:
                if tentativa == self.tentativas:
                    raise IAIndisponivel(f"Sem conexão com o Ollama em {self.url}") from erro
                await asyncio.sleep(self.espera_entre_tentativas * tentativa)
            except httpx2.TimeoutException as erro:
                raise IAIndisponivel("O Ollama demorou demais para responder") from erro
            except httpx2.HTTPError as erro:
                raise IAIndisponivel(f"Falha ao falar com o Ollama: {erro}") from erro

        if resposta.status_code != httpx2.codes.OK:
            motivo = _erro_do_corpo(resposta.text)
            raise IAIndisponivel(f"Ollama respondeu {resposta.status_code}: {motivo}")
        try:
            vetores = resposta.json()["embeddings"]
        except (json.JSONDecodeError, KeyError, TypeError) as erro:
            raise IAIndisponivel("Resposta do Ollama fora do formato esperado") from erro

        if len(vetores) != len(textos):
            raise IAIndisponivel("O Ollama devolveu um número de vetores diferente do pedido")
        # Um modelo trocado no ambiente sem migração gravaria vetores que o banco
        # recusa; melhor dizer qual é o problema aqui.
        if any(len(v) != DIMENSOES_EMBEDDING for v in vetores):
            raise IAIndisponivel(
                f"O modelo {self.modelo_embedding} não gera vetores de "
                f"{DIMENSOES_EMBEDDING} dimensões, a do vault"
            )
        return vetores


@dataclass(frozen=True)
class _Pedaco:
    texto: str
    fim: bool


def _ler_linha(linha: str) -> _Pedaco:
    try:
        dado = json.loads(linha)
    except json.JSONDecodeError as erro:
        raise IAIndisponivel("Resposta do Ollama fora do formato esperado") from erro
    if "error" in dado:
        raise IAIndisponivel(f"Ollama: {dado['error']}")
    texto = (dado.get("message") or {}).get("content") or ""
    return _Pedaco(texto=texto, fim=bool(dado.get("done")))


def _erro_do_corpo(texto: str) -> str:
    try:
        return str(json.loads(texto).get("error") or texto)
    except (json.JSONDecodeError, AttributeError):
        return texto[:200]
