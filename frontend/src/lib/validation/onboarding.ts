import { z } from 'zod'

/** Espelha `tamanho_maximo_ementa` do backend, que confere de novo no envio. */
// O aluno costuma mandar o PPC do curso, bem maior que uma ementa.
export const TAMANHO_MAXIMO_EMENTA = 30 * 1024 * 1024

const escolhaSchema = z.object({ texto: z.string(), id: z.number().nullable() })

// Aqui só o tipo e o tamanho. Se o conteúdo é mesmo um PDF, só o servidor sabe:
// um .txt renomeado passa daqui e volta com o erro da API.
const ementaSchema = z
  .instanceof(File)
  .nullable()
  .refine(
    (arquivo) =>
      !arquivo || arquivo.type === 'application/pdf' || arquivo.name.toLowerCase().endsWith('.pdf'),
    'Envie a ementa em PDF.',
  )
  .refine(
    (arquivo) => !arquivo || arquivo.size <= TAMANHO_MAXIMO_EMENTA,
    'A ementa precisa ter até 30 MB.',
  )

/**
 * Passo 3 do onboarding (telas 14 e 15).
 *
 * Só a instituição é obrigatória; curso e período o aluno pode deixar para
 * depois. A ementa é opcional nas trilhas livre e mista, e obrigatória na
 * guiada, porque o plano de estudos dela parte da ementa.
 */
export function configuracaoTrilhaSchema(ementaObrigatoria: boolean) {
  return z
    .object({
      instituicao: escolhaSchema.refine(
        (escolha) => escolha.texto.trim().length > 0,
        'Informe sua instituição de ensino.',
      ),
      curso: escolhaSchema,
      periodo: z.string(),
      ementa: ementaSchema,
    })
    .refine((dados) => !ementaObrigatoria || dados.ementa !== null, {
      message: 'Na trilha guiada, envie a ementa para montarmos o seu plano de estudos.',
      path: ['ementa'],
    })
}

export type ConfiguracaoTrilhaValues = z.infer<ReturnType<typeof configuracaoTrilhaSchema>>
