import { Lock, Play } from 'lucide-react'
import { useAccessibility } from '@/contexts/AccessibilityContext'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
 * Vitrine do design system: serve para conferir, num lugar só, se os
 * componentes respondem aos tokens — inclusive no alto contraste e na fonte
 * ampliada.
 */
export function DesignSystemPage() {
  const { tamanhoFonte, altoContraste, setTamanhoFonte, setAltoContraste } = useAccessibility()

  return (
    <div className="flex flex-col gap-8 pb-12">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-primary">Design System</h1>
          <p className="text-muted-foreground">
            Componentes e tokens do Algorise, conforme o protótipo do Figma.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={altoContraste ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAltoContraste(!altoContraste)}
          >
            Alto contraste
          </Button>
          <Button
            variant={tamanhoFonte === 'alta' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setTamanhoFonte(tamanhoFonte === 'alta' ? 'normal' : 'alta')}
          >
            Fonte grande
          </Button>
        </div>
      </header>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Botões</h2>
        <div className="flex flex-wrap items-center gap-3">
          <Button>Continuar</Button>
          <Button variant="secondary">Médio</Button>
          <Button variant="outline">Pular para login</Button>
          <Button variant="ghost">Voltar</Button>
          <Button variant="destructive">Excluir conta</Button>
          <Button variant="locked">
            <Lock /> Bloqueado
          </Button>
          <Button size="icon" aria-label="Começar">
            <Play />
          </Button>
        </div>
        <Button full size="lg">
          Começar trilha
        </Button>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Formulário</h2>
        <div className="grid max-w-md gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="Insira seu email" />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="nivel">Nível</Label>
            <Select>
              <SelectTrigger id="nivel">
                <SelectValue placeholder="Selecione seu nível" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="alto">Alto</SelectItem>
                <SelectItem value="medio">Médio</SelectItem>
                <SelectItem value="baixo">Baixo</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="termos" />
            <Label htmlFor="termos" className="text-foreground">
              Concordo com os termos de uso
            </Label>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Trilha</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Badge variant="categoria">Linguagens</Badge>
                <Badge variant="success">3/10</Badge>
                <Badge periodo={1}>1º Período</Badge>
              </div>
              <CardTitle>Introdução Python</CardTitle>
              <CardDescription>Recomendação pelo Algorise</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Progress value={30} aria-label="Progresso da trilha" />
              <Button size="sm">
                <Play /> Continuar
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Badge variant="categoria">Gerais</Badge>
                <Badge periodo={2}>2º Período</Badge>
              </div>
              <CardTitle className="text-muted-foreground">Matemática</CardTitle>
              <CardDescription>Conhecimentos gerais</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Progress value={0} aria-label="Progresso da trilha" />
              <Button size="sm" variant="locked">
                <Lock /> Bloqueada
              </Button>
            </CardContent>
          </Card>
        </div>
        <div className="flex flex-wrap gap-2">
          {periodos.map((p) => (
            <Badge key={p} periodo={p}>
              {p}º Período
            </Badge>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Ranking e navegação</h2>
        <div className="flex items-center gap-3">
          <Avatar>
            <AvatarFallback>JC</AvatarFallback>
          </Avatar>
          <span className="font-bold">João Carlos</span>
          <Badge variant="outline">4º lugar</Badge>
        </div>
        <Tabs defaultValue="conversas" className="max-w-md">
          <TabsList>
            <TabsTrigger value="novo">Novo bate papo</TabsTrigger>
            <TabsTrigger value="conversas">Conversas</TabsTrigger>
            <TabsTrigger value="agrupar">Agrupar</TabsTrigger>
          </TabsList>
          <TabsContent value="novo">Comece uma conversa com o Algorise.</TabsContent>
          <TabsContent value="conversas">Seu histórico de conversas aparece aqui.</TabsContent>
          <TabsContent value="agrupar">Selecione conversas para agrupar por tema.</TabsContent>
        </Tabs>
      </section>

      <section className="flex flex-wrap gap-3">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">Abrir diálogo</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Trocar modo de trilha?</DialogTitle>
              <DialogDescription>
                Mudar de Guiada para Livre mantém seu progresso, mas reordena os próximos passos.
              </DialogDescription>
            </DialogHeader>
          </DialogContent>
        </Dialog>
        <Button variant="outline" onClick={() => toast.success('+40 XP ganhos!')}>
          Disparar toast
        </Button>
      </section>
    </div>
  )
}
