"""Tarefas rodadas fora da API.

- `expurgo`: manutenção, pelo cron ou pelo agendador do deploy;
- `streak_risco`: o aviso de streak em risco, também pelo cron, no fim da tarde;
- `ementa`: a leitura da ementa, pelo worker da fila (`app/core/fila.py`);
- `busca`: a busca de vídeos para as lacunas de uma disciplina, também pelo worker;
- `transcricao`: a transcrição de cada vídeo escolhido pela busca;
- `segmentacao`: as partes de cada vídeo transcrito;
- `categorizacao`: a matéria de cada parte e as lacunas que ela cobre;
- `exercicios`: os exercícios de prática de um módulo, pedidos pelo aluno.
"""
