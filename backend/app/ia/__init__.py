"""IA do Algorise: provedor, contrato e skills.

- `base`: o contrato (`ProvedorIA`, `MensagemIA`, `IAIndisponivel`);
- `ollama` e `eco`: os provedores, o de verdade e o de teste;
- `provedor`: qual deles atende, conforme `IA_PROVEDOR`;
- `skills/`: cada uso da IA, com o prompt e os limites dele. O tutor do chat é
  a primeira; a leitura da ementa (#38) entra como outra;
- `vault/`: a base de conhecimento que as skills consultam (#200).

Uma skill não sabe de banco nem de rota: recebe o que precisa já em texto e
devolve as mensagens para o modelo. Juntar os dados do aluno é do serviço que a
usa, e é isso que deixa a skill testável sem fixture nenhuma.
"""

from app.ia.base import IAIndisponivel, MensagemIA, Papel, ProvedorIA
from app.ia.provedor import get_provedor_ia, get_provedor_ia_tarefas

__all__ = [
    "IAIndisponivel",
    "MensagemIA",
    "Papel",
    "ProvedorIA",
    "get_provedor_ia",
    "get_provedor_ia_tarefas",
]
