import { isValidElement, memo, type ReactNode } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import remarkGfm from 'remark-gfm'
import bash from 'highlight.js/lib/languages/bash'
import c from 'highlight.js/lib/languages/c'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import { CodigoBloco } from './CodigoBloco'

/*
 * Por que react-markdown e não estender o parser à mão: o antigo (regex)
 * não cobria títulos, listas aninhadas, itálico com `*` nem tabelas, e cada
 * regra nova abre casos de borda (negrito dentro de lista, cerca sem fechar).
 * react-markdown monta elementos React, sem innerHTML, e ignora HTML cru
 * (não usamos rehype-raw), então o texto vindo da IA não injeta nada. Ele
 * também aceita markdown pela metade: uma cerca ``` sem fechar vira um bloco
 * de código até o fim do texto, que é o que queremos durante o streaming.
 *
 * Realce: só as linguagens que o tutor usa são registradas (highlight.js
 * "core"), em vez das ~37 do pacote `common`, para o bundle não inchar.
 */
const linguagens = { bash, c, java, javascript, json, python, sql, typescript, xml }

const remarkPlugins = [remarkGfm]
const rehypePlugins: [typeof rehypeHighlight, Parameters<typeof rehypeHighlight>[0]][] = [
  // Linguagem fora da lista cai em texto simples (sem detecção automática).
  [rehypeHighlight, { languages: linguagens, detect: false }],
]

function linguagemDe(className?: string) {
  return /language-([\w+#-]+)/.exec(className ?? '')?.[1]
}

const componentes: Components = {
  h1: ({ children }) => <h3 className="mt-1 text-lg font-bold">{children}</h3>,
  h2: ({ children }) => <h4 className="mt-1 text-base font-bold">{children}</h4>,
  h3: ({ children }) => <h5 className="mt-1 text-base font-semibold">{children}</h5>,
  h4: ({ children }) => <h6 className="text-sm font-semibold">{children}</h6>,
  p: ({ children }) => <p className="break-words">{children}</p>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-semibold underline underline-offset-2 hover:opacity-80"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-primary/40 pl-3 italic opacity-90">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="border-border" />,
  table: ({ children }) => (
    <div className="max-w-full overflow-x-auto">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-border bg-muted px-2 py-1 text-left font-semibold">{children}</th>
  ),
  td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
  // Código em linha. Fundo translúcido para servir no balão claro e no primário.
  code: ({ className, children }) => (
    <code className={className ?? 'rounded bg-foreground/10 px-1.5 py-0.5 font-mono text-[0.9em]'}>
      {children}
    </code>
  ),
  // Bloco: lemos o <code> filho (já realçado) e entregamos ao CodigoBloco.
  pre: ({ children }) => {
    const filho: ReactNode = Array.isArray(children) ? children[0] : children
    if (!isValidElement<{ className?: string; children?: ReactNode }>(filho)) return <pre />
    return (
      <CodigoBloco linguagem={linguagemDe(filho.props.className)}>
        {filho.props.children}
      </CodigoBloco>
    )
  },
}

/** Markdown do chat. Memoizado: durante o streaming só o texto muda. */
export const Markdown = memo(function Markdown({ texto }: { texto: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={componentes}
      >
        {texto}
      </ReactMarkdown>
    </div>
  )
})
