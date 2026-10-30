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
- Fase 1 expandida para **30 telas / 30.720 px**: Floresta (15 telas) + Caverna (15 telas) em um mapa contínuo, com apenas **3 checkpoints** (meio da floresta, transição floresta → caverna e meio da caverna)
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
- **Salvamento e continuação de partida** (`core/save.py`, `core/run_state.py`):
  o jogo salva sozinho e o menu inicial oferece **Continuar** (volta à mesma
  fase, posição, vida, moedas, melhorias, checkpoints, inimigos derrotados e
  itens coletados). Detalhes na seção "Salvamento" abaixo.
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
├── core/                    # game loop, input, estados, save (save.py) + estado da partida (run_state.py), debug overlay (F3)
├── player/                  # Kael: física, ataque, stats/progressão, sprite
├── enemies/                 # inimigo base, comum, à distância, voador, boss
├── world/                   # plataformas, obstáculos, moedas, checkpoints, level (fases), background (cenário)
├── systems/                 # colisão, combate, progressão, loja, respawn, áudio, partículas
├── screens/                 # menu, HUD, game over, vitória, pausa, história
└── tests/                   # testes automatizados do sistema de salvamento
```

### Salvamento

- **Quando salva:** a cada 30 s de jogo (`AUTOSAVE_INTERVAL_SECONDS` em
  `config/settings.py`, esperando Kael estar no chão), ao ativar um checkpoint,
  ao comprar/aprimorar na loja, ao entrar na arena do Boss, ao pausar, ao sair
  pelo menu de pausa, ao renascer depois de morrer e ao fechar a janela. Nunca
  grava a cada quadro (um save leva ~1 ms).
- **O que salva:** progressão permanente (`"stats"`: moedas, melhorias, espadas)
  e estado da partida (`"run"`: fase/bioma, posição e vida, Núcleo/checkpoint
  atual, checkpoints ativos, moedas coletadas, inimigos — posição, vida, vivo
  ou morto e tempo para reaparecer —, plataformas móveis/quebradiças,
  estalactites (inclui a ponte do puzzle da fenda), Boss e gatilhos de
  história). O mapa em si não é salvo: as fases são geradas por código de forma
  determinística e o save guarda só o que mudou, por índice.
- **Onde fica:** `savegame.json` na pasta de dados do usuário —
  Windows `%APPDATA%\VengeanceReborn`, macOS
  `~/Library/Application Support/VengeanceReborn`, Linux
  `~/.local/share/VengeanceReborn` (ao lado ficam `savegame.json.bak`, o último
  save válido anterior). Um `savegame.json` antigo na pasta do projeto ainda é
  lido (só a progressão).
- **Segurança:** a gravação é atômica (arquivo temporário + `os.replace`) e o
  backup `.bak` é usado se o principal estiver corrompido. Arquivo ausente,
  truncado ou inválido nunca trava o jogo.
- **Morte x fechar o jogo:** morrer segue as regras de sempre (volta ao último
  Núcleo/checkpoint). Se o jogo for fechado na tela de derrota, o save já
  guarda Kael no Núcleo, nunca no ponto da morte. Fechar em jogo retoma a
  posição exata.
- **Novo jogo:** com uma partida salva, pede confirmação ("Substituir partida
  salva?", padrão Cancelar) antes de apagá-la. Vencer o Boss encerra a campanha
  e limpa o save.
- **Testes:** `python -m unittest tests.test_save_system -v` (headless, usa uma
  pasta temporária, não toca no seu save).

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

## Fase 1: Floresta (15 telas) + Caverna (15 telas)

`build_main_level` (em `world/level.py`) monta a Jornada por **módulos** (classe `_JourneyBuilder`): trechos prontos de terreno, perigos, inimigos e moedas, encadeados da esquerda para a direita. Cada módulo começa e termina em chão na altura `GROUND_Y`, então qualquer ordem continua jogável.

- **Tamanho**: `FOREST_SCREENS = 15` e `CAVE_SCREENS = 15` (1 tela = 1024 px) -> mapa de 30.720 px. O fundo em parallax faz o crossfade floresta -> caverna num intervalo de 1000 px centrado em x = 15.360.
- **Checkpoints (só 3)**: x = 7.680 (meio da floresta), x = 15.360 (transição) e x = 23.040 (meio da caverna). Cada trecho entre checkpoints tem 7,5 telas. Para mudar, edite as chamadas `self.rest(...)` em `_JourneyBuilder.build()`. A loja só abre no início e nesses 3 checkpoints.
- **Dificuldade**: a segunda metade de cada área usa as variantes `hard=True` (mais atiradores, morcegos e espinhos). O puzzle da fenda (estalactite-ponte) fica logo depois do checkpoint do meio da caverna.
- **Desempenho**: inimigos a mais de `ENEMY_ACTIVE_RANGE` px de Kael não são atualizados, e os fora da tela (`ENEMY_DRAW_MARGIN`) não são desenhados; `PlatformGroup.rects()` guarda a lista de sólidos por frame.

## Moedas e plataformas da caverna

- **Valor**: cada moeda comum dá **5** de dinheiro (`COIN_VALUE`); as da área secreta dão 15 (`SECRET_COIN_VALUE`). Os custos da loja não foram alterados.
- **Posicionamento das moedas**: em `world/level.py`, os ajudantes `_coins_centered`, `_coins_on(plataforma)` e `_coin_arc` calculam a posição a partir do topo do chão/plataforma, então a moeda nunca nasce dentro de plataformas nem no fundo de poços. Arcos sobre espinhos (`SPIKE_ARC_BASE`) ficam acima da cabeça: só se pega saltando.
- **Plataformas da caverna** (geometrias herdadas da fase antiga, agora reaproveitadas nos módulos da caverna a partir de x = 15.360): escadas de passos de até 65 px de altura e vão de até 65 px (bem dentro do pulo simples, que cobre ~170 px nesse desnível), sempre cobrindo um espinho ou um vão; pontes centradas nos vãos; elevador centrado no vão de 9250-9380. Espinhos saíram do ponto de pouso dos vãos e inimigos que nasciam sobre espinhos ou sobre o vão foram para o chão firme.

## Visual do Boss (Vharok) - Cavaleiro Sombrio

- Fontes: as spritesheets em `assets/boss/source/` (soco, investida, rajada multidirecional, explosão no chão, smash, projétil de energia, efeitos e `pixel_walk_sheet.png`, a caminhada de 6 quadros em fundo preto, que a ferramenta transforma em transparente). Não são grades regulares e o cavaleiro tem escala levemente diferente em cada folha.
- `tools/process_knight_sheets.py` recorta cada quadro (componentes conectados + cortes explícitos onde quadros se tocam), iguala as escalas e grava um PNG por quadro em `assets/boss/knight/` + `manifest.json` com a âncora dos pés. Precisa de Pillow, numpy e scipy; **não é necessário para jogar**.
- Código: `enemies/boss_sprites.py` (carrega os quadros, tabelas de animação, mapa de quadros no topo do arquivo) e `enemies/boss.py` (a animação apenas acompanha a máquina de estados).
- Ataques: slam = smash + erupção de fogo; golpe curto = soco poderoso; investida = body charge; explosão multidirecional = leque de 360° de estilhaços (um mira em Kael); **orbe de energia** (novo) = esfera arremessada com Kael longe.
- Ajustes: `BOSS_SPRITE_SCALE`, `BOSS_WALK_FRAME_TICKS*`, `BOSS_ORB_*`, `BOSS_BARRAGE_*` etc. em `config/settings.py`. `BOSS_ORB_IN_PHASE1 = False` deixa o orbe só na Fase 2. A hitbox (`BOSS_WIDTH/HEIGHT`) é independente do tamanho do sprite.
- Se os quadros não existirem, o Boss volta ao desenho retangular.

## Visual do Morcego Sombrio (FlyingEnemy) - spritesheet

- Assets: `assets/morcego/morcego_sheet_96px.png` (192x192, células 96x96: linha 0 olhando p/ a direita, linha 1 p/ a esquerda; coluna 0 asas erguidas, coluna 1 asas abaixadas), a mesma arte em tamanho original (`morcego_sheet_24px.png`) e a imagem de origem (`morcego_inimigo_original.webp`). `tools/process_morcego_sheet.py` refaz a sheet a partir da imagem de origem (precisa de Pillow + numpy; não é necessário para jogar).
- Código: `enemies/flying_enemy_sprites.py` (recorte, escala, espelhamento e flash de dano) e `enemies/flying_enemy.py` (apenas escolhe o quadro; movimento e dano não mudaram).
- Ajustes em `config/settings.py`: `FLYING_ENEMY_SPRITE_SCALE` (None = automática, 2 px de tela por pixel da arte) e `FLYING_ENEMY_FLAP_TICKS` (velocidade do bater de asas). A hitbox (`FLYING_ENEMY_WIDTH/HEIGHT`) é independente do tamanho do sprite.
- Se a sheet não existir, o morcego volta ao desenho simples antigo (elipse + asas).
