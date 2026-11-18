"""Cliente da API do Gemini, a segunda opção de provedor de IA do Algorise.

O Ollama roda o modelo na própria máquina: não depende de ninguém, mas na CPU é
lento e ocupa memória. O Gemini roda no Google: responde rápido em qualquer
máquina, e a camada gratuita da API (chave criada no Google AI Studio) dá conta
de desenvolver e testar. A troca é só `IA_PROVEDOR=gemini`; quem usa a IA (o
chat, a ementa, as skills) não muda nada, porque fala com o `ProvedorIA`.

Fala direto com a API REST (`generativelanguage.googleapis.com`) pelo `httpx2`,
o mesmo cliente do Ollama: o SDK do Google seria mais uma dependência grande
para usar duas rotas.
"""

import asyncio
import contextlib
import json
import logging
import math
import re
import weakref
from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from typing import Any

import httpx2

from app.core.metricas import medir_ia
from app.ia.base import DIMENSOES_EMBEDDING, IAIndisponivel, MensagemIA

logger = logging.getLogger(__name__)

URL_PADRAO = "https://generativelanguage.googleapis.com/v1beta"

# O `batchEmbedContents` aceita até 100 textos por pedido.
_TEXTOS_POR_LOTE = 100

_FALHAS_DE_CONEXAO = (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.PoolTimeout)

# Status em que vale tentar de novo antes do primeiro pedaço: limite da camada
# gratuita estourado (429) ou o Google sobrecarregado (500/503).
_STATUS_TEMPORARIOS = (429, 500, 503)
# Espera mais longa que o Google pode pedir num 429 para ainda valer a pena
# esperar: a cota por minuto volta em menos que isso; a do dia, não.
_ESPERA_MAXIMA_PELA_COTA = 90

# O mesmo, como o Google escreve no `status` de um erro que vem dentro do stream.
_SITUACOES_TEMPORARIAS = ("RESOURCE_EXHAUSTED", "INTERNAL", "UNAVAILABLE")


class _Sobrecarga(IAIndisponivel):
    """Erro passageiro do lado do Google: modelo sobrecarregado ou limite de pedidos.

    Vale tentar de novo, ou mudar para o modelo reserva. Quem está de fora vê só
    um `IAIndisponivel`, como qualquer outra falha.
    """


# Um cliente HTTP por event loop e por chave, mantido aberto entre os pedidos:
# abrir a conexão HTTPS com o Google (DNS, TCP e TLS) custa uns 500 ms, mais que
# o próprio modelo leva para começar a responder. O cliente fica preso ao loop
# em que nasceu; a API tem um só, mas um script que roda vários `asyncio.run`
# ganha um cliente por loop, e o do loop encerrado vai embora com ele.
_CLIENTES: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, dict[tuple[str, str], httpx2.AsyncClient]
] = weakref.WeakKeyDictionary()


def _compartilhado(url: str, chave: str) -> httpx2.AsyncClient:
    do_loop = _CLIENTES.setdefault(asyncio.get_running_loop(), {})
    cliente = do_loop.get((url, chave))
    if cliente is None or cliente.is_closed:
        # A chave vai no cabeçalho, e não na URL, para não aparecer em log de acesso.
        # O timeout vai em cada pedido: o chat e as tarefas esperam prazos diferentes.
        cliente = httpx2.AsyncClient(base_url=url, headers={"x-goog-api-key": chave})
        do_loop[(url, chave)] = cliente
    return cliente


class Gemini:
    """Cliente do `streamGenerateContent` (SSE) e do `batchEmbedContents`.

    Diferenças para o Ollama que este cliente esconde:

    - o papel `assistant` se chama `model`, e o `system` não entra na lista: vai
      em `systemInstruction`;
    - o JSON Schema da resposta vai em `generationConfig.responseJsonSchema`;
    - o "raciocínio" (thinking) conta no `maxOutputTokens`: com o teto curto das
      skills, ele consumiria a resposta inteira. Por isso vai baixo por padrão
      (`raciocinio`): um nível (`minimal`, `low`...) nos modelos 3.x, ou um
      número de tokens (`0` desliga) nos 2.5. Cada família recusa o jeito da
      outra com 400; aí o pedido é refeito sem o campo, no padrão do modelo.
    """

    def __init__(
        self,
        chave: str,
        modelo: str,
        *,
        timeout_conexao: float,
        timeout_leitura: float,
        tentativas: int,
        modelo_embedding: str = "gemini-embedding-001",
        raciocinio: str | None = "minimal",
        modelo_reserva: str = "",
        esperas_pela_cota: int = 10,
        url: str = URL_PADRAO,
        espera_entre_tentativas: float = 1.0,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self.chave = chave
        self.modelo = modelo
        self.modelo_embedding = modelo_embedding
        self.raciocinio = raciocinio or None
        self.modelo_reserva = modelo_reserva
        # Quantas vezes um lote de embeddings espera a cota por minuto virar
        # (ver `_lote`). Dez minutos cobrem os assuntos de uma ementa grande.
        self.esperas_pela_cota = esperas_pela_cota
        self.url = url.rstrip("/")
        self.timeout = httpx2.Timeout(timeout_leitura, connect=timeout_conexao)
        self.tentativas = max(tentativas, 1)
        self.espera_entre_tentativas = espera_entre_tentativas
        # Injetado pelos testes (`httpx2.MockTransport`); em produção, a rede.
        self.transport = transport

    @property
    def marca_embedding(self) -> str:
        """O que identifica os vetores deste provedor no vault (ver `vault/ingestao.py`)."""
        return f"gemini:{self.modelo_embedding}:{DIMENSOES_EMBEDDING}"

    @contextlib.asynccontextmanager
    async def _cliente(self) -> AsyncIterator[httpx2.AsyncClient]:
        """O cliente HTTP, reaproveitado entre pedidos (ver `_compartilhado`).

        Com o `transport` dos testes, um cliente novo a cada pedido, fechado no fim.
        """
        if self.transport is not None:
            async with httpx2.AsyncClient(
                base_url=self.url,
                timeout=self.timeout,
                transport=self.transport,
                headers={"x-goog-api-key": self.chave},
            ) as cliente:
                yield cliente
        else:
            yield _compartilhado(self.url, self.chave)

    async def gerar(
        self,
        mensagens: Sequence[MensagemIA],
        *,
        max_tokens: int,
        formato: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str]:
        if not self.chave:
            raise IAIndisponivel("GEMINI_API_KEY vazia: crie uma chave no Google AI Studio")

        corpo = _corpo_da_geracao(mensagens, max_tokens, formato, raciocinio=self.raciocinio)
        if formato is not None:
            # Uma extração em JSON: quem pede junta tudo antes de ler, então a
            # resposta é entregue inteira, de uma vez (ver `_inteira`).
            with medir_ia("gerar"):
                yield await self._inteira(corpo)
            return

        with medir_ia("gerar"):
            emitiu = False
            try:
                async for pedaco in self._gerar(corpo, self.modelo):
                    emitiu = True
                    yield pedaco
            except _Sobrecarga as erro:
                # O modelo seguiu sobrecarregado depois das tentativas. Outro
                # modelo tem outra fila de capacidade no Google: vale tentar,
                # desde que nada tenha sido entregue (senão o texto se repetiria).
                reserva = self.modelo_reserva
                if emitiu or not reserva or reserva == self.modelo:
                    raise
                logger.warning("%s sobrecarregado (%s); usando %s", self.modelo, erro, reserva)
                async for pedaco in self._gerar(corpo, reserva):
                    yield pedaco

    async def _inteira(self, corpo: dict[str, Any]) -> str:
        """A resposta completa, recomeçada do zero se o Google a cortar no meio.

        Na camada gratuita o Google às vezes interrompe uma resposta já em curso
        por sobrecarga ("high demand"). No chat não há o que fazer, porque o aluno
        já viu o começo; numa extração, ninguém viu nada, e recomeçar não duplica
        texto. A cada sobrecarga, alterna entre o modelo principal e o reserva.
        """
        modelos = [self.modelo]
        if self.modelo_reserva and self.modelo_reserva != self.modelo:
            modelos.append(self.modelo_reserva)
        for tentativa in range(1, self.tentativas * len(modelos) + 1):
            modelo = modelos[(tentativa - 1) % len(modelos)]
            try:
                return "".join([pedaco async for pedaco in self._gerar(corpo, modelo)])
            except _Sobrecarga as erro:
                if tentativa == self.tentativas * len(modelos):
                    raise
                logger.warning("%s cortou a resposta (%s); recomeçando", modelo, erro)
                await asyncio.sleep(self.espera_entre_tentativas * tentativa)
        raise AssertionError("inalcançável")

    async def _gerar(self, corpo: dict[str, Any], modelo: str) -> AsyncGenerator[str]:
        rota = f"/models/{modelo}:streamGenerateContent"

        for tentativa in range(1, self.tentativas + 1):
            emitiu = False
            try:
                async with (
                    self._cliente() as cliente,
                    cliente.stream(
                        "POST", rota, params={"alt": "sse"}, json=corpo, timeout=self.timeout
                    ) as resposta,
                ):
                    if resposta.status_code != httpx2.codes.OK:
                        await resposta.aread()
                        # O modelo não aceita a configuração de raciocínio
                        # (ver o docstring): de novo, sem ela, sem gastar tentativa.
                        configuracao = corpo["generationConfig"]
                        if (
                            resposta.status_code == httpx2.codes.BAD_REQUEST
                            and "thinkingConfig" in configuracao
                            and _recusou_o_raciocinio(resposta)
                        ):
                            sem_raciocinio = {
                                k: v for k, v in configuracao.items() if k != "thinkingConfig"
                            }
                            corpo = {**corpo, "generationConfig": sem_raciocinio}
                            async for pedaco in self._gerar(corpo, modelo):
                                yield pedaco
                            return
                        if resposta.status_code in _STATUS_TEMPORARIOS:
                            raise _Sobrecarga(_mensagem_de_erro(resposta))
                        raise IAIndisponivel(_mensagem_de_erro(resposta))

                    async for linha in resposta.aiter_lines():
                        # SSE: cada evento vem numa linha `data: {...}`.
                        if not linha.startswith("data:"):
                            continue
                        texto = _ler_evento(linha[len("data:") :].strip())
                        if texto:
                            emitiu = True
                            yield texto
                    return
            except _Sobrecarga:
                # Sobrecarga ou limite da camada gratuita, no status HTTP ou como
                # evento de erro no começo do stream (o Google às vezes responde
                # 200 e manda o erro em seguida). Antes do primeiro pedaço, tenta
                # de novo; depois, repetir duplicaria o texto já entregue.
                if emitiu or tentativa == self.tentativas:
                    raise
                await asyncio.sleep(self.espera_entre_tentativas * tentativa)
            except _FALHAS_DE_CONEXAO as erro:
                if emitiu or tentativa == self.tentativas:
                    raise IAIndisponivel("Sem conexão com a API do Gemini") from erro
                await asyncio.sleep(self.espera_entre_tentativas * tentativa)
            except httpx2.TimeoutException as erro:
                raise IAIndisponivel("O Gemini demorou demais para responder") from erro
            except httpx2.HTTPError as erro:
                raise IAIndisponivel(f"Falha ao falar com o Gemini: {erro}") from erro

    async def embeddings(self, textos: Sequence[str]) -> list[list[float]]:
        if not textos:
            return []
        if not self.chave:
            raise IAIndisponivel("GEMINI_API_KEY vazia: crie uma chave no Google AI Studio")
        with medir_ia("embeddings"):
            vetores: list[list[float]] = []
            for inicio in range(0, len(textos), _TEXTOS_POR_LOTE):
                vetores.extend(await self._lote(textos[inicio : inicio + _TEXTOS_POR_LOTE]))
            return vetores

    async def _lote(self, textos: Sequence[str]) -> list[list[float]]:
        modelo = f"models/{self.modelo_embedding}"
        corpo = {
            "requests": [
                {
                    "model": modelo,
                    "content": {"parts": [{"text": texto}]},
                    # O gemini-embedding-001 gera 3072 posições, mas aceita
                    # devolver menos (Matryoshka): pedimos a dimensão do vault,
                    # para não precisar de migração.
                    "outputDimensionality": DIMENSOES_EMBEDDING,
                }
                for texto in textos
            ]
        }
        rota = f"/{modelo}:batchEmbedContents"

        tentativa = esperas_pela_cota = 0
        while True:
            tentativa += 1
            try:
                async with self._cliente() as cliente:
                    resposta = await cliente.post(rota, json=corpo, timeout=self.timeout)
            except _FALHAS_DE_CONEXAO as erro:
                if tentativa >= self.tentativas:
                    raise IAIndisponivel("Sem conexão com a API do Gemini") from erro
                await asyncio.sleep(self.espera_entre_tentativas * tentativa)
                continue
            except httpx2.TimeoutException as erro:
                raise IAIndisponivel("O Gemini demorou demais para responder") from erro
            except httpx2.HTTPError as erro:
                raise IAIndisponivel(f"Falha ao falar com o Gemini: {erro}") from erro

            # A camada gratuita conta cada texto como um pedido: são 100 por
            # minuto, e mapear os assuntos de uma ementa passa disso. O Google diz
            # quanto esperar; o embedding roda em segundo plano (a ementa, a
            # busca, o vault), então vale esperar a janela virar, sem gastar
            # tentativa. Espera de horas é a cota do dia: aí não adianta.
            espera = _espera_pela_cota(resposta)
            if espera is not None and esperas_pela_cota < self.esperas_pela_cota:
                esperas_pela_cota += 1
                tentativa -= 1
                logger.warning(
                    "Limite de embeddings por minuto do Gemini; esperando %.0f s", espera
                )
                await asyncio.sleep(espera)
                continue

            if resposta.status_code in _STATUS_TEMPORARIOS and tentativa < self.tentativas:
                await asyncio.sleep(self.espera_entre_tentativas * tentativa)
                continue
            break

        if resposta.status_code != httpx2.codes.OK:
            raise IAIndisponivel(_mensagem_de_erro(resposta))
        try:
            vetores = [item["values"] for item in resposta.json()["embeddings"]]
        except (json.JSONDecodeError, KeyError, TypeError) as erro:
            raise IAIndisponivel("Resposta do Gemini fora do formato esperado") from erro

        if len(vetores) != len(textos):
            raise IAIndisponivel("O Gemini devolveu um número de vetores diferente do pedido")
        if any(len(v) != DIMENSOES_EMBEDDING for v in vetores):
            raise IAIndisponivel(
                f"O modelo {self.modelo_embedding} não gerou vetores de "
                f"{DIMENSOES_EMBEDDING} dimensões, a do vault"
            )
        # Com dimensão reduzida o Google não normaliza o vetor; normalizado, a
        # distância de cosseno fica comparável à de um vetor completo.
        return [_normalizar(v) for v in vetores]


def _corpo_da_geracao(
    mensagens: Sequence[MensagemIA],
    max_tokens: int,
    formato: dict[str, Any] | None,
    *,
    raciocinio: str | None,
) -> dict[str, Any]:
    sistema = "\n\n".join(m.conteudo for m in mensagens if m.papel == "system")
    conteudos: list[dict[str, Any]] = []
    for m in mensagens:
        if m.papel == "system":
            continue
        papel = "model" if m.papel == "assistant" else "user"
        # O Gemini aceita turnos seguidos do mesmo papel, mas junta-los evita
        # resposta estranha quando o histórico tem duas mensagens do aluno.
        if conteudos and conteudos[-1]["role"] == papel:
            conteudos[-1]["parts"].append({"text": m.conteudo})
        else:
            conteudos.append({"role": papel, "parts": [{"text": m.conteudo}]})
    # Sem nenhum turno do usuário a API recusa o pedido.
    if not conteudos:
        conteudos.append({"role": "user", "parts": [{"text": ""}]})

    configuracao: dict[str, Any] = {"maxOutputTokens": max_tokens}
    if formato is not None:
        configuracao["responseMimeType"] = "application/json"
        configuracao["responseJsonSchema"] = formato
    if raciocinio:
        configuracao["thinkingConfig"] = (
            {"thinkingBudget": int(raciocinio)}
            if raciocinio.lstrip("-").isdigit()
            else {"thinkingLevel": raciocinio}
        )

    corpo: dict[str, Any] = {"contents": conteudos, "generationConfig": configuracao}
    if sistema:
        corpo["systemInstruction"] = {"parts": [{"text": sistema}]}
    return corpo


def _ler_evento(dado: str) -> str:
    try:
        evento = json.loads(dado)
    except json.JSONDecodeError as erro:
        raise IAIndisponivel("Resposta do Gemini fora do formato esperado") from erro
    if "error" in evento:
        erro = evento["error"] if isinstance(evento["error"], dict) else {}
        mensagem = f"Gemini: {erro.get('message', evento['error'])}"
        if erro.get("code") in _STATUS_TEMPORARIOS or erro.get("status") in _SITUACOES_TEMPORARIAS:
            raise _Sobrecarga(mensagem)
        raise IAIndisponivel(mensagem)

    bloqueio = (evento.get("promptFeedback") or {}).get("blockReason")
    if bloqueio:
        raise IAIndisponivel(f"O Gemini recusou o pedido ({bloqueio})")

    candidatos = evento.get("candidates") or []
    if not candidatos:
        return ""
    partes = (candidatos[0].get("content") or {}).get("parts") or []
    # `thought: true` marca o raciocínio do modelo, que não é resposta.
    return "".join(p.get("text", "") for p in partes if not p.get("thought"))


def _mensagem_de_erro(resposta: httpx2.Response) -> str:
    try:
        erro = resposta.json().get("error") or {}
        motivo = erro.get("message") or resposta.text[:200]
    except (json.JSONDecodeError, AttributeError):
        motivo = resposta.text[:200]
    if resposta.status_code == 429:
        return f"Limite da API do Gemini atingido (429): {motivo}"
    return f"Gemini respondeu {resposta.status_code}: {motivo}"


def _espera_pela_cota(resposta: httpx2.Response) -> float | None:
    """Os segundos que o Google pede para esperar num 429 de cota por minuto.

    `None` quando não é 429, quando o Google não diz, ou quando a espera passa
    de `_ESPERA_MAXIMA_PELA_COTA` (a cota do dia, que só volta amanhã).
    """
    if resposta.status_code != httpx2.codes.TOO_MANY_REQUESTS:
        return None
    segundos = None
    try:
        for detalhe in resposta.json().get("error", {}).get("details", []):
            if "retryDelay" in detalhe:
                segundos = float(str(detalhe["retryDelay"]).rstrip("s"))
                break
    except (json.JSONDecodeError, AttributeError, ValueError):
        pass
    if segundos is None:
        achado = re.search(r"retry in ([\d.]+)s", resposta.text)
        segundos = float(achado.group(1)) if achado else None
    if segundos is None or segundos > _ESPERA_MAXIMA_PELA_COTA:
        return None
    return segundos + 1


def _recusou_o_raciocinio(resposta: httpx2.Response) -> bool:
    """O 400 é do `thinkingConfig`, e não da chave ou do pedido.

    O Gemini 3 responde "Thinking level ... is not supported" a um nível que o
    modelo não tem, e um "invalid argument" seco ao `thinkingBudget` dos 2.5.
    """
    texto = resposta.text.lower()
    return "thinking" in texto or "invalid argument" in texto


def _normalizar(vetor: list[float]) -> list[float]:
    norma = math.sqrt(sum(v * v for v in vetor)) or 1.0
    return [v / norma for v in vetor]
