import { describe, expect, it } from 'vitest'
import { ATIVIDADES, executar, normalizar } from '@/lib/terminal/roteiro'

const instalar = ATIVIDADES['winget install Python.Python.3.14']
const versao = ATIVIDADES['python --version']

describe('normalizar', () => {
  it('ignora espaço sobrando e maiúsculas', () => {
    expect(normalizar('  Python   --VERSION  ')).toBe('python --version')
  })
})

describe('atividade 1: instalar o Python', () => {
  it('aceita o comando certo', () => {
    const { acertou, linhas } = executar('winget install Python.Python.3.14', instalar)

    expect(acertou).toBe(true)
    expect(linhas[linhas.length - 1]).toMatchObject({
      tipo: 'sucesso',
      texto: 'Instalação concluída com êxito',
    })
  })

  it('mostra o download em etapas, como no protótipo', () => {
    const { linhas } = executar('winget install Python.Python.3.14', instalar)

    const porcentagens = linhas.map((linha) => linha.texto.match(/(\d+)%/)?.[1]).filter(Boolean)
    expect(porcentagens).toEqual(['18', '47', '81', '100'])
  })

  it('aceita o comando digitado torto', () => {
    expect(executar('  WINGET install python.python.3.14 ', instalar).acertou).toBe(true)
  })
})

describe('atividade 2: versão do Python', () => {
  it('aceita o comando certo', () => {
    const { acertou, linhas } = executar('python --version', versao)

    expect(acertou).toBe(true)
    expect(linhas[0].texto).toBe('Python 3.14.0')
  })

  it('responde ao erro do protótipo com a dica', () => {
    const { acertou, linhas } = executar('python ---version', versao)

    expect(acertou).toBe(false)
    expect(linhas[0]).toMatchObject({ tipo: 'erro', texto: 'unknown option ---version' })
    expect(linhas[linhas.length - 1].texto).toContain('python -h')
  })

  it('o erro não encerra a atividade: dá para tentar de novo', () => {
    executar('python ---version', versao)

    expect(executar('python --version', versao).acertou).toBe(true)
  })
})

describe('comandos fora do roteiro', () => {
  it('responde como o cmd a um comando desconhecido', () => {
    const { acertou, linhas } = executar('ls', versao)

    expect(acertou).toBe(false)
    expect(linhas[0].tipo).toBe('erro')
    expect(linhas[0].texto).toContain("'ls' não é reconhecido")
  })

  it('`python -h` funciona em qualquer atividade, porque o aluno vai tentar', () => {
    const { linhas } = executar('python -h', instalar)

    expect(linhas.some((linha) => linha.texto.includes('--version'))).toBe(true)
  })

  it('linha vazia não faz nada', () => {
    expect(executar('   ', versao)).toEqual({ linhas: [], acertou: false })
  })

  it('o comando da outra atividade não conta como acerto', () => {
    expect(executar('python --version', instalar).acertou).toBe(false)
  })
})
