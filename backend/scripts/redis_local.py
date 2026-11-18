"""Redis em memória para rodar o backend sem Docker.

O login precisa de Redis (é onde vivem os refresh tokens, ver
`app/services/sessoes.py`). Sem Docker e sem Redis instalado, isto sobe um
servidor compatível, em Python, com o `fakeredis` das dependências de dev:

    python scripts/redis_local.py          # escuta em localhost:6379

Os dados somem quando ele é fechado: só serve para desenvolvimento. A fila do
RQ não roda sobre ele; deixe `FILA=local` no backend/.env.
"""

import sys

from fakeredis import TcpFakeServer
from fakeredis._clients._tcp_server import HAS_FCNTL, TCPFakeRequestHandler


class _Conexao(TCPFakeRequestHandler):
    """A conexão do `fakeredis`, com o pub/sub funcionando no Windows.

    O laço do `fakeredis` alterna entre ler o socket e entregar o que o servidor
    empurra sozinho (as mensagens do pub/sub). Para isso o socket precisa ser
    não bloqueante, e ele faz isso com o `fcntl`, que só existe no Linux/macOS.
    No Windows a leitura fica parada esperando o cliente, e a mensagem só sai
    quando o assinante manda outro comando: o chat pelo WebSocket, que escuta
    o pub/sub, nunca recebe a resposta da IA.
    """

    def setup(self) -> None:
        super().setup()
        if not HAS_FCNTL:
            self.connection.setblocking(False)


def main() -> None:
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 6379
    servidor = TcpFakeServer(("127.0.0.1", porta), server_type="redis")
    servidor.RequestHandlerClass = _Conexao
    print(f"Redis em memória em redis://localhost:{porta}/0 (Ctrl+C para parar)", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.shutdown()


if __name__ == "__main__":
    main()
