# Vengeance Reborn

Jogo de plataforma 2D com elementos de roguelite, desenvolvido em Python
com **Pygame-ce**, baseado no documento de escopo do projeto (equipe
GeniusVerse).

Kael busca vingança contra Vharok, o Rei do Abismo. Ao morrer, o Núcleo
do Retorno o traz de volta ao último ponto conhecido — mas as moedas
coletadas continuam disponíveis para comprar melhorias e tentar de novo.

## Como executar

```bash
pip install pygame-ce numpy
python main.py
```

Requer Python 3.10+.

## Controles

| Tecla                  | Ação                          |
|-------------------------|--------------------------------|
| `A` / `D` ou `←` / `→`  | Mover                          |
| `ESPAÇO` / `W` / `↑`    | Pular (com coyote time + buffer) |
| `Clique esquerdo` (mouse) | Atacar (mira na direção do cursor, sem virar o personagem) |
| `Q`                     | Dash                            |
| Segurar direção da parede no ar | Wall slide (queda freada) + Wall jump se apertar pular |
| `ESPAÇO` no ar (2ª vez)  | Pulo duplo (se comprado na loja) |
| `E` / `ENTER`           | Interagir (loja / confirmar menu) |
| `ESC` / `P`             | Pausar (abre menu com opções)  |
| `W`/`S`                 | Navegar opções (loja / pausa)  |

## Status de implementação

### Concluído (Prioridade 1 — obrigatório / MVP)
- Tela inicial, HUD, tela de "morte" (retorno pelo Núcleo) e tela de vitória
- **Sprite animado do Kael** (`assets/player/`, `player/player_sprites.py`):
  extraído de uma sprite sheet fornecida, com animações reais de
  idle, corrida, pulo, queda, wall slide, dash, ataque (combo de 4
  golpes) e morte — antes o jogador era só um retângulo
- Movimentação, pulo, gravidade e colisões (eixo separado)
- Ataque corpo a corpo com hitbox e cooldown
- Inimigo comum com patrulha e dano por contato
- Sistema de vida e dano (jogador e inimigos) — **barra de 0-100** (não
  mais corações), com cor mudando de verde a vermelho conforme desce
- Moedas coletáveis e sistema de melhorias (vida, dano, pulo)
- Morte → retorno ao Núcleo → mantém progresso → nova tentativa
- Fase 1 completa (Regiões 1 a 4, ~6400px, com buracos, espinhos, plataformas)
- Fase 2 (arena do Boss) com Vharok: perseguição, ataque telegrafado
  (slam), fase 2 ao cair para menos de 50% de vida, barra de vida fixa
- Condição de vitória (Vharok derrotado) e tela de encerramento
- Reinício automático de tentativa (sistema básico de "Game Over" temporário)

### Extras já incluídos (Prioridade 2)
- Segundo tipo de inimigo (`RangedEnemy`, ataca à distância com projéteis)
- **Corvo Sombrio** (`FlyingEnemy`): inimigo voador, patrulha no ar em
  zigue-zague sem sofrer gravidade, ignorando plataformas e buracos
- Loja com interface própria (seleção, custo, nível de melhoria) — agora
  com **8 opções** em duas colunas: vida, dano, pulo, velocidade de
  ataque, pulo duplo, **ímã de moedas** (atrai moedas próximas
  automaticamente), **carga extra de dash** (permite usar o dash 2x
  antes de recarregar) e **cura** (item consumível, restaura vida)
- Save/load simples em JSON (`core/save.py`) entre execuções
- Boss com **2 padrões de ataque**: "slam"/terremoto corpo a corpo
  (sempre, com uma zona de perigo pulsando no chão avisando onde vai
  bater) e uma **rajada de 5 projéteis rápidos em leque** exclusiva da
  Fase 2 (abaixo de 50% de vida), escolhida aleatoriamente entre as
  investidas
- **Fenda Vertical**: área bônus opcional (perto do fim da Região 3) que
  usa de verdade a mecânica de wall jump — o chão normal continua por
  baixo sem bloqueio nenhum, mas quem escalar a escadinha de plataformas
  encontra um corredor estreito flanqueado por duas paredes. Descer por
  ele encadeando wall jumps (e desviando de espinhos grudados na parede
  e de duas **Sentinelas de Parede**, um mob novo que só atira quando o
  jogador cruza a mesma altura) leva a uma saliência com moedas de maior
  valor. Errar não pune: cair simplesmente devolve o jogador ao chão
  normal, sem dano
- **Checkpoints**: bandeiras que, ao serem tocadas, tornam-se o novo
  ponto do Núcleo do Retorno — não é mais preciso voltar à Região 1
  inteira a cada morte. Todo checkpoint já ativado também dá acesso à
  loja, não só a zona fixa da Região 1
- **Inimigos comuns e à distância dão moedas ao serem derrotados** (o
  Boss também, embora a partida termine logo em seguida) e **reaparecem
  automaticamente 1 minuto depois de mortos**, no ponto de spawn original
- **Plataformas móveis** (vaivém vertical/horizontal, carregam o jogador
  junto ao se mover) e **plataformas quebradiças** (tremem ao serem
  pisadas e despencam, reaparecendo depois de um tempo)
- **Sistema de partículas**: poeira ao pousar, faíscas ao acertar
  inimigos, brilho ao coletar moedas, explosão de poeira dourada na
  morte de Kael, e um efeito ao ativar um checkpoint
- **Área secreta**: trecho escondido no alto da Região 2, acessível só
  por uma sequência de pulos precisos, com moedas de valor maior
- **História apresentada durante o jogo**: pequenos textos de lore
  aparecem brevemente ao entrar em cada região e ao se aproximar do
  castelo, sem pausar a partida
- **Efeitos sonoros** (`systems/audio.py`): gerados 100% proceduralmente
  com numpy (ondas seno/quadrada/triângulo + ruído), sem depender de
  nenhum arquivo de áudio externo — pulo, ataque, acerto, dano, moeda,
  checkpoint, morte, ataques do Boss, vitória e sons de menu
- **Screen shake**: tremor de câmera em impactos (dano recebido, morte,
  ataques do Boss — mais forte no "slam", mais sutil na rajada)
- **Menu de pausa completo**: além de continuar, permite **reiniciar a
  tentativa** (volta ao último Núcleo/checkpoint sem esperar morrer) ou
  **sair para o menu principal** salvando o progresso

### Ainda não implementado (Prioridade 2/3 — opcional)
- Sprites/arte de verdade (por enquanto tudo é desenhado com formas
  geométricas e cores sólidas)
- Animações de sprite (idle/correr/pular/atacar) — atualmente só há
  feedback via partículas, screen shake e o "piscar" de invencibilidade
- Música de fundo (os efeitos sonoros já existem; música contínua com
  numpy é possível, mas não foi priorizada)
- Cutscenes e diálogos
- Segunda fase completa antes do castelo (a Região 4 já cumpre esse
  papel de forma simplificada)

## Arquitetura

Estrutura de pastas conforme o documento de escopo original (seção 23),
com pequenos acréscimos (`world/checkpoints.py`, `screens/story.py`,
`screens/pause.py`, `systems/audio.py`, `systems/particles.py`) para
as mecânicas extras:

```
VengeanceReborn/
├── main.py
├── config/settings.py       # todas as constantes de balanceamento
├── core/                    # game loop, input, estados, save
├── player/                  # Kael: física, ataque, stats/progressão
├── enemies/                 # inimigo base, comum, à distância, boss
├── world/                   # plataformas, obstáculos, moedas, checkpoints, level (fases)
├── systems/                 # colisão, combate, progressão, loja, respawn, áudio, partículas
└── screens/                 # menu, HUD, game over, vitória, pausa, história
```

Foram testados (headless, sem tela) os seguintes fluxos, sem exceções:
movimentação/pulo/colisão por ~1500 frames, compra na loja (4 melhorias),
ciclo morte→respawn (incluindo respawn em checkpoint), travessia
completa da Fase 1 até o gatilho do Boss, a luta contra o Boss até a
vitória (incluindo a rajada de projéteis da Fase 2), carregamento do
jogador por plataformas móveis, ciclo completo de uma plataforma
quebradiça, popups de história, coleta das moedas da área secreta,
navegação e ações do menu de pausa (reiniciar tentativa / sair), o
sistema de áudio procedural e o screen shake — além de um teste de
estresse com 6000 frames de input aleatório cobrindo todos os estados
do jogo.

## Ajustando o balanceamento

Praticamente todo número de gameplay (velocidade, dano, custo de
melhorias, vida do Boss, etc.) está centralizado em
`config/settings.py` — ajuste ali sem precisar mexer na lógica.
