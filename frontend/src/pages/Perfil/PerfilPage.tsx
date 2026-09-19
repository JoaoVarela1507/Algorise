import { useAccessibility } from '@/contexts/AccessibilityContext'

export function PerfilPage() {
  const { tamanhoFonte, altoContraste, setTamanhoFonte, setAltoContraste } =
    useAccessibility()

  return (
    <div>
      <h1 className="text-2xl font-bold text-neutral-800">Perfil</h1>

      <section className="mt-6 rounded-2xl bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold">Acessibilidade</h2>

        <div className="mb-4">
          <p className="mb-2 font-medium">Tamanho da fonte</p>
          <div className="flex gap-2">
            <button
              className={`rounded-xl px-4 py-2 ${
                tamanhoFonte === 'normal' ? 'bg-salmon text-white' : 'bg-salmon-light/40'
              }`}
              onClick={() => setTamanhoFonte('normal')}
            >
              Normal
            </button>
            <button
              className={`rounded-xl px-4 py-2 ${
                tamanhoFonte === 'alta' ? 'bg-salmon text-white' : 'bg-salmon-light/40'
              }`}
              onClick={() => setTamanhoFonte('alta')}
            >
              Alta
            </button>
          </div>
        </div>

        <div>
          <p className="mb-2 font-medium">Fundo de alto contraste</p>
          <div className="flex gap-2">
            <button
              className={`rounded-xl px-4 py-2 ${
                altoContraste ? 'bg-salmon text-white' : 'bg-salmon-light/40'
              }`}
              onClick={() => setAltoContraste(true)}
            >
              Sim
            </button>
            <button
              className={`rounded-xl px-4 py-2 ${
                !altoContraste ? 'bg-salmon text-white' : 'bg-salmon-light/40'
              }`}
              onClick={() => setAltoContraste(false)}
            >
              Não
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
