import { Lock, Play } from 'lucide-react'
import { useAccessibility } from '@/contexts/AccessibilityContext'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from '@/components/ui/toaster'

const periodos = [1, 2, 3, 4, 5, 6, 7, 8] as const

/**
 * Vitrine do design system: serve para conferir, num lugar só, que todos os
 * componentes respondem aos tokens — inclusive no alto contraste e na fonte
 * grande. É a tela que valida o critério de aceite da issue #4.
 */
export function DesignSystemPage() {
  const { tamanhoFonte, altoContraste, setTamanhoFonte, setAltoContraste } = useAccessibility()

  return (
    <div className="flex flex-col gap-8 pb-12">
      <header>
        <h1 className="font-display text-3xl font-extrabold text-primary">Design System</h1>
        <p className="text-muted-foreground">
          Componentes do Algorise sobre os tokens do protótipo.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Acessibilidade</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant={tamanhoFonte === 'alta' ? 'default' : 'secondary'}
            onClick={() => setTamanhoFonte(tamanhoFonte === 'alta' ? 'normal' : 'alta')}
          >
            Fonte: {tamanhoFonte}
          </Button>
          <Button
            variant={altoContraste ? 'default' : 'secondary'}
            onClick={() => setAltoContraste(!altoContraste)}
          >
            Alto contraste: {altoContraste ? 'ligado' : 'desligado'}
          </Button>
        </CardContent>
      </Card>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Botões</h2>
        <div className="flex flex-wrap items-center gap-3">
          <Button>Continuar</Button>
          <Button variant="secondary">Médio</Button>
          <Button variant="outline">Pular</Button>
          <Button variant="ghost">Voltar</Button>
          <Button variant="destructive">Excluir</Button>
          <Button variant="locked">
            <Lock /> Bloqueado
          </Button>
          <Button size="icon" aria-label="Começar">
            <Play />
          </Button>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button size="sm">Pequeno</Button>
          <Button size="lg">Grande</Button>
        </div>
        <Button full>Avançar</Button>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Períodos letivos</h2>
        <div className="flex flex-wrap gap-2">
          {periodos.map((p) => (
            <Badge key={p} periodo={p}>
              {p}º Período
            </Badge>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="categoria">Linguagens</Badge>
          <Badge variant="success">Concluída</Badge>
          <Badge variant="outline">3/10</Badge>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Introdução Python</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Progress value={30} aria-label="Progresso da trilha" />
            <p className="text-sm text-muted-foreground">3 de 10 passos</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Formulário</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="Insira seu email" />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox id="termos" />
              <Label htmlFor="termos">Concordo com os termos de uso</Label>
            </div>
            <Select>
              <SelectTrigger aria-label="Modo de trilha">
                <SelectValue placeholder="Modo de trilha" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="guiada">Trilha guiada</SelectItem>
                <SelectItem value="livre">Trilha livre</SelectItem>
                <SelectItem value="mista">Trilha mista</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Navegação e sobreposição</h2>
        <Tabs defaultValue="chat">
          <TabsList>
            <TabsTrigger value="chat">Novo bate papo</TabsTrigger>
            <TabsTrigger value="conversas">Conversas</TabsTrigger>
            <TabsTrigger value="agrupar">Agrupar</TabsTrigger>
          </TabsList>
          <TabsContent value="chat">Conteúdo do bate papo.</TabsContent>
          <TabsContent value="conversas">Histórico de conversas.</TabsContent>
          <TabsContent value="agrupar">Seleção de conversas.</TabsContent>
        </Tabs>

        <div className="flex flex-wrap items-center gap-3">
          <Avatar>
            <AvatarFallback>JC</AvatarFallback>
          </Avatar>

          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">Abrir diálogo</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Trocar modo de trilha?</DialogTitle>
                <DialogDescription>
                  Seu progresso atual é mantido, mas a ordem dos módulos muda.
                </DialogDescription>
              </DialogHeader>
            </DialogContent>
          </Dialog>

          <Button variant="secondary" onClick={() => toast('Exatamente!', { description: '+40 XP' })}>
            Disparar toast
          </Button>
        </div>
      </section>
    </div>
  )
}
