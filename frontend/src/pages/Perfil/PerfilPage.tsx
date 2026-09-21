import { useAccessibility } from '@/contexts/AccessibilityContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function PerfilPage() {
  const { tamanhoFonte, altoContraste, setTamanhoFonte, setAltoContraste } = useAccessibility()

  return (
    <div>
      <h1 className="font-display text-2xl font-bold">Perfil</h1>

      <Card className="mt-6 max-w-md">
        <CardHeader>
          <CardTitle>Acessibilidade</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div>
            <p className="mb-2 font-bold">Tamanho da fonte</p>
            <div className="flex gap-2" role="group" aria-label="Tamanho da fonte">
              <Button
                variant={tamanhoFonte === 'normal' ? 'default' : 'secondary'}
                aria-pressed={tamanhoFonte === 'normal'}
                onClick={() => setTamanhoFonte('normal')}
              >
                Normal
              </Button>
              <Button
                variant={tamanhoFonte === 'alta' ? 'default' : 'secondary'}
                aria-pressed={tamanhoFonte === 'alta'}
                onClick={() => setTamanhoFonte('alta')}
              >
                Alta
              </Button>
            </div>
          </div>

          <div>
            <p className="mb-2 font-bold">Fundo de alto contraste</p>
            <div className="flex gap-2" role="group" aria-label="Fundo de alto contraste">
              <Button
                variant={altoContraste ? 'default' : 'secondary'}
                aria-pressed={altoContraste}
                onClick={() => setAltoContraste(true)}
              >
                Sim
              </Button>
              <Button
                variant={!altoContraste ? 'default' : 'secondary'}
                aria-pressed={!altoContraste}
                onClick={() => setAltoContraste(false)}
              >
                Não
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
