import { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, Loader2 } from 'lucide-react'
import { niveis, trilhas } from '@/components/onboarding/opcoes'
import { Segmentado } from '@/components/perfil/Segmentado'
import { toast } from '@/components/ui/toaster'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import type { AtualizacaoPerfil, Usuario } from '@/types/usuario'

/** Modo de trilha (o dropdown "MODO TRILHA GUIADA" do protótipo) e nível. */
export function CaminhoCard({ usuario }: { usuario: Usuario }) {
  const { atualizarPerfil } = useAuth()
  const [salvando, setSalvando] = useState<keyof AtualizacaoPerfil | null>(null)

  async function salvar(dados: AtualizacaoPerfil, mensagem: string) {
    const campo = Object.keys(dados)[0] as keyof AtualizacaoPerfil
    setSalvando(campo)
    try {
      await atualizarPerfil(dados)
      toast.success(mensagem)
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : 'Não foi possível salvar.')
    } finally {
      setSalvando(null)
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-card p-6 shadow-sm">
      <h2 className="font-display text-lg font-bold text-foreground">Modo de trilha</h2>
      <p className="mb-4 text-sm text-muted-foreground">Como você quer estudar no Algorise.</p>

      <div className="flex flex-col gap-2" role="radiogroup" aria-label="Modo de trilha">
        {trilhas.map((opcao) => {
          const ativa = usuario.tipoTrilha === opcao.valor
          return (
            <motion.button
              key={opcao.valor}
              type="button"
              role="radio"
              aria-checked={ativa}
              whileTap={{ scale: 0.98 }}
              disabled={salvando !== null}
              onClick={() =>
                !ativa &&
                salvar(
                  { tipoTrilha: opcao.valor },
                  `Modo trilha ${opcao.titulo.toLowerCase()} ativado`,
                )
              }
              className={cn(
                'flex items-center gap-3 rounded-lg border-2 p-3 text-left transition-colors disabled:cursor-wait',
                ativa ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/50',
              )}
            >
              <span
                className={cn(
                  'flex size-10 shrink-0 items-center justify-center rounded-full transition-colors',
                  ativa ? 'bg-primary text-primary-foreground' : 'bg-accent text-primary',
                )}
              >
                <opcao.icone className="size-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-display font-bold text-foreground">
                  Modo trilha {opcao.titulo.toLowerCase()}
                </span>
                <span className="line-clamp-2 text-xs text-muted-foreground">
                  {opcao.descricao}
                </span>
              </span>
              {ativa && <Check className="size-5 shrink-0 text-primary" strokeWidth={3} />}
            </motion.button>
          )
        })}
      </div>

      <div className="mt-auto pt-5">
        <p className="mb-2 flex items-center gap-2 text-sm font-bold text-foreground">
          Nível em programação
          {salvando === 'nivelExperiencia' && (
            <Loader2 className="size-4 animate-spin text-muted-foreground" aria-label="Salvando" />
          )}
        </p>
        <Segmentado
          rotulo="Nível em programação"
          opcoes={niveis.map((n) => ({ valor: n.valor, rotulo: n.titulo }))}
          valor={usuario.nivelExperiencia}
          desabilitado={salvando !== null}
          onChange={(valor) =>
            salvar({ nivelExperiencia: valor }, 'Nível em programação atualizado')
          }
        />
      </div>
    </div>
  )
}
