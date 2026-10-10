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
| `ESPAÇO` no ar (2ª vez)  | Pulo duplo (se comprado na loja) |
| `E` / `ENTER`           | Interagir (loja / confirmar menu) |
| `ESC` / `P`             | Pausar (abre menu com opções)  |
| `W`/`S` ou `↑`/`↓`      | Navegar itens da loja / pausa |
| `A`/`D` ou `←`/`→`      | Trocar categoria na loja       |
| `F`                     | Aprimorar a espada selecionada |
| `Mouse`                 | Selecionar, comprar e equipar itens da loja |
| `F3`                    | Modo DEBUG (grade, hitboxes, coordenadas) |

## Modo DEBUG (F3)

Ferramenta de desenvolvimento pra ajudar a posicionar objetos na fase
(chão, plataformas, inimigos, moedas etc.) sem precisar adivinhar
coordenadas. Aperte `F3` a qualquer momento durante o jogo pra ligar
ou desligar. Com DEBUG **desligado**, o jogo funciona exatamente como
sempre — o modo é puramente aditivo (`core/debug_overlay.py`).

Com DEBUG **ligado**, aparecem:
- Um painel no canto superior esquerdo com FPS, a posição (X, Y) do
  jogador e a posição do mouse tanto em coordenadas de tela quanto de
  **mundo** (já considerando a câmera — mova a câmera e passe o mouse
  em cima de qualquer ponto do mapa pra descobrir a coordenada real
  daquele ponto).
- Uma grade de referência a cada 100px sobre o cenário, com as
  coordenadas nas linhas principais, que acompanha a câmera (não fica
  fixa na tela).
- As hitboxes de colisão já existentes no jogo, desenhadas por cima:
  jogador (ciano), inimigos (vermelho), chão/plataformas
  (amarelo), espinhos (rosa) e moedas/checkpoints/zona da
  loja/gatilho do Boss (verde). Não é um sistema de colisão novo — são
  os mesmos `Rect` que o jogo já usa pra física e gameplay.

## Status de implementação

### Concluído (Prioridade 1 — obrigatório / MVP)
- Tela inicial, HUD, tela de "morte" (retorno pelo Núcleo) e tela de vitória
- **Sprite animado do Kael** (`assets/player/kael_spritesheet.png`,
  `player/player_sprites.py`): spritesheet única (células de 128x128,
  6 colunas x 10 linhas) com animações de idle, corrida, pulo, queda,
  dash, ataque e morte. O
  mapeamento linha/coluna -> estado está documentado no topo de
  `player_sprites.py`. A hitbox continua independente do tamanho do sprite
- Movimentação, pulo, gravidade e colisões (eixo separado)
- Ataque corpo a corpo com hitbox e cooldown
- Inimigo comum com patrulha e dano por contato
- Sistema de vida e dano (jogador e inimigos) — **barra de 0-100** (não
  mais corações), com cor mudando de verde a vermelho conforme desce
- Moedas coletáveis, vida máxima, pulo duplo, ímã de moedas e poção de cura
- Morte → retorno ao Núcleo → mantém progresso → nova tentativa
- Fase 1 expandida para 12.800px (8 regiões contínuas, com buracos, espinhos, plataformas, inimigos e checkpoints)
- **Cenário de fundo elaborado** (`world/background.py`): a Fase 1
  inteira (Regiões 1 a 8) tem UMA identidade visual contínua — noite,
  lua grande com brilho suave, nuvens, duas camadas de montanhas em
  paralaxe, uma vila destruída ao fundo (casas com telhados quebrados
  e vigas partidas), entulho, janelas com luz quente e fogueiras com
  brasas/fumaça animadas. A arena do Boss tem uma identidade
  completamente diferente — `CastleBackdrop`: céu vermelho/negro,
  silhueta de um castelo em ruínas (torres com ameias, paredes
  quebradas, colunas partidas), fogueiras maiores e uma vinheta escura
  nas bordas pra um clima mais fechado e ameaçador
- Fase 2 (arena do Boss) com Vharok: perseguição, ataque telegrafado
  (slam), fase 2 ao cair para menos de 50% de vida, barra de vida fixa
- Condição de vitória (Vharok derrotado) e tela de encerramento
- Reinício automático de tentativa (sistema básico de "Game Over" temporário)

### Extras já incluídos (Prioridade 2)
- Segundo tipo de inimigo (`RangedEnemy`, ataca à distância com projéteis)
- **Morcego Sombrio** (`FlyingEnemy`): inimigo voador, patrulha no ar em
  zigue-zague sem sofrer gravidade, ignorando plataformas e buracos
- Loja temática com abas de **Espadas**, **Melhorias** e **Consumíveis**:
  quatro espadas equipáveis com dano real no combate e aprimoramento pago;
  vida máxima, pulo duplo, ímã de moedas com alcance aumentado e poção de cura.
  Compras e equipamentos são salvos imediatamente. As antigas melhorias
  genéricas de dano, força de pulo, velocidade de ataque e carga extra de dash
  não estão mais disponíveis na loja.
- Save/load simples em JSON (`core/save.py`) entre execuções
- Boss com **2 padrões de ataque**: "slam"/terremoto corpo a corpo
  (sempre, com uma zona de perigo pulsando no chão avisando onde vai
  bater) e uma **rajada de 5 projéteis rápidos em leque** exclusiva da
  Fase 2 (abaixo de 50% de vida), escolhida aleatoriamente entre as
  investidas
- **Investida do Vharok** (`enemies/boss.py`, parâmetros `BOSS_CHARGE_*` em
  `config/settings.py`): ocasionalmente, com Kael longe, ele avisa (faixa
  azul no chão), vira para o lado de Kael e avança rápido em linha reta;
  para ao acertar (um dano por investida), bater num colisor sólido, chegar ao
  limite da arena ou esgotar distância/tempo, e então fica exposto numa
  recuperação. Há intervalo mínimo entre investidas
- **Golpe curto do Vharok** (`enemies/boss.py`, parâmetros `BOSS_MELEE_*` em
  `config/settings.py`): se Kael ficar a até 90 px (horizontal) e na altura do
  corpo, ele vira para o lado de Kael, avisa (braços erguidos + zona de perigo
  pulsando), golpeia com uma hitbox curta à frente (dano uma vez por golpe,
  respeitando os i-frames de Kael) e se recupera. Intervalo mínimo de 100
  frames entre golpes (85 na Fase 2). Pode **cancelar o aviso do soco no chão
  (slam)**, que ainda não executou nada; se o slam já está para sair ou já
  disparou, termina primeiro e o golpe curto entra assim que a hitbox e a
  animação do slam acabam. Um slam cancelado garante que o próximo vá até o fim
- **Inimigo comum**: ao atacar, dá um passo curto na direção de Kael durante a
  preparação do golpe (`BASIC_ENEMY_ATTACK_ADVANCE_*` em `config/settings.py`),
  com limite de distância, sem ultrapassar Kael nem sair de plataformas; o
  dano continua sendo resolvido uma vez, no quadro de impacto
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
├── core/                    # game loop, input, estados, save, debug overlay (F3)
├── player/                  # Kael: física, ataque, stats/progressão, sprite
├── enemies/                 # inimigo base, comum, à distância, voador, boss
├── world/                   # plataformas, obstáculos, moedas, checkpoints, level (fases), background (cenário)
├── systems/                 # colisão, combate, progressão, loja, respawn, áudio, partículas
└── screens/                 # menu, HUD, game over, vitória, pausa, história
```

### Estrutura do mapa

O jogo tem **dois grandes momentos**, cada um com sua própria
identidade visual (`world/background.py`):

1. **Área inicial → Região 4** (`build_main_level`): um único mapa
   contínuo (sem telas de carregamento nem teleporte entre trechos),
   dividido internamente em Região 1 a 4 só pra organizar ONDE cada
   plataforma/inimigo/moeda é colocado — visualmente é tudo a MESMA
   vila destruída à noite, do início ao fim (`VillageBackdrop`).
2. **Arena do Boss** (`build_boss_level`): o confronto contra Vharok,
   com uma identidade visual própria e propositalmente mais
   ameaçadora (`CastleBackdrop`).

Essa estrutura é proposital e não deve crescer em "biomas" novos
(floresta, ruínas, caverna etc. como regiões visualmente separadas) -
qualquer conteúdo novo de fase deve continuar dentro de uma dessas
duas identidades visuais já existentes.

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

## Visual do Boss (Vharok) - spritesheet

- Assets: `assets/boss/vharok_spritesheet.png` (RGBA, fundo removido) e o original em JPG (`vharok_spritesheet_original.jpg`). `tools/process_vharok_sheet.py` refaz a conversão (precisa de Pillow + numpy; não é necessário para jogar).
- Código: `enemies/boss_sprites.py` (recortes e animações explícitos, por linha/coluna da sheet) e `enemies/boss.py` (apenas métodos visuais; a lógica de combate não mudou).
- Ajustes: `BOSS_SPRITE_SCALE` e demais `BOSS_*_TICKS` em `config/settings.py`. A hitbox (`BOSS_WIDTH/HEIGHT`) é independente do tamanho do sprite.
- Se a sheet não existir, o Boss volta ao desenho retangular antigo.

## Visual do Morcego Sombrio (FlyingEnemy) - spritesheet

- Assets: `assets/morcego/morcego_sheet_96px.png` (192x192, células 96x96: linha 0 olhando p/ a direita, linha 1 p/ a esquerda; coluna 0 asas erguidas, coluna 1 asas abaixadas), a mesma arte em tamanho original (`morcego_sheet_24px.png`) e a imagem de origem (`morcego_inimigo_original.webp`). `tools/process_morcego_sheet.py` refaz a sheet a partir da imagem de origem (precisa de Pillow + numpy; não é necessário para jogar).
- Código: `enemies/flying_enemy_sprites.py` (recorte, escala, espelhamento e flash de dano) e `enemies/flying_enemy.py` (apenas escolhe o quadro; movimento e dano não mudaram).
- Ajustes em `config/settings.py`: `FLYING_ENEMY_SPRITE_SCALE` (None = automática, 2 px de tela por pixel da arte) e `FLYING_ENEMY_FLAP_TICKS` (velocidade do bater de asas). A hitbox (`FLYING_ENEMY_WIDTH/HEIGHT`) é independente do tamanho do sprite.
- Se a sheet não existir, o morcego volta ao desenho simples antigo (elipse + asas).
