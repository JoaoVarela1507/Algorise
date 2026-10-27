import { useRef, useState } from 'react'
import { Camera, Loader2, Trash2 } from 'lucide-react'
import { AvatarIniciais } from '@/components/home/AvatarIniciais'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { toast } from '@/components/ui/toaster'
import { useAuth } from '@/contexts/AuthContext'
import type { Usuario } from '@/types/usuario'

/** O mesmo teto do backend (`tamanho_maximo_avatar`), para avisar antes de enviar. */
const TAMANHO_MAXIMO = 2 * 1024 * 1024
const TIPOS_ACEITOS = 'image/png,image/jpeg,image/webp'

/**
 * Foto do perfil com os botões de trocar e remover.
 *
 * A conferência daqui é só para o aluno não esperar o envio para descobrir que
 * o arquivo é grande demais. Quem decide é o servidor, que abre a imagem e
 * recusa o que não for PNG, JPEG ou WebP de verdade.
 */
export function FotoPerfil({ usuario }: { usuario: Usuario }) {
  const { enviarAvatar, removerAvatar } = useAuth()
  const entrada = useRef<HTMLInputElement>(null)
  const [enviando, setEnviando] = useState(false)

  async function executar(acao: () => Promise<void>, mensagem: string) {
    setEnviando(true)
    try {
      await acao()
      toast.success(mensagem)
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : 'Não foi possível salvar a foto.')
    } finally {
      setEnviando(false)
    }
  }

  function aoEscolher(evento: React.ChangeEvent<HTMLInputElement>) {
    const arquivo = evento.target.files?.[0]
    // Limpa para escolher o mesmo arquivo de novo disparar o evento.
    evento.target.value = ''
    if (!arquivo) return
    if (arquivo.size > TAMANHO_MAXIMO) {
      toast.error('A foto pode ter até 2 MB.')
      return
    }
    void executar(() => enviarAvatar(arquivo), 'Foto atualizada')
  }

  return (
    <div className="group relative">
      {usuario.avatarUrl ? (
        <Avatar className="size-24 ring-4 ring-primary/30">
          <AvatarImage src={usuario.avatarUrl} alt="" />
          <AvatarFallback>{usuario.nome[0]}</AvatarFallback>
        </Avatar>
      ) : (
        <AvatarIniciais nome={usuario.nome} className="size-24 text-3xl ring-4 ring-primary/30" />
      )}

      <input
        ref={entrada}
        type="file"
        accept={TIPOS_ACEITOS}
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        data-testid="entrada-avatar"
        onChange={aoEscolher}
      />

      <button
        type="button"
        onClick={() => entrada.current?.click()}
        disabled={enviando}
        aria-label="Trocar foto do perfil"
        className="absolute inset-0 flex items-center justify-center rounded-full bg-foreground/50 text-background opacity-0 transition-opacity focus-visible:opacity-100 group-hover:opacity-100 disabled:cursor-wait disabled:opacity-100"
      >
        {enviando ? (
          <Loader2 className="size-7 animate-spin" aria-hidden />
        ) : (
          <Camera className="size-7" aria-hidden />
        )}
      </button>

      {usuario.avatarUrl && (
        <button
          type="button"
          onClick={() => void executar(removerAvatar, 'Foto removida')}
          disabled={enviando}
          aria-label="Remover foto do perfil"
          className="absolute -left-1 -top-1 flex size-8 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow transition-colors hover:text-destructive disabled:cursor-wait"
        >
          <Trash2 className="size-4" aria-hidden />
        </button>
      )}
    </div>
  )
}
