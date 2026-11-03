"""Tarefas rodadas fora da API.

- `expurgo`: manutenção, pelo cron ou pelo agendador do deploy;
- `ementa`: a leitura da ementa, pelo worker da fila (`app/core/fila.py`);
- `busca`: a busca de vídeos para as lacunas de uma disciplina, também pelo worker.
"""
