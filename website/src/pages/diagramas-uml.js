import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './diagramas-uml.module.css';

const classDiagrams = [
  {
    title: 'Visão geral com herança',
    description: 'Mapa dos pacotes do jogo e das relações de herança, composição, agregação e dependência.',
    image: '/img/uml/classes/vengeance_reborn_classes.svg',
    source: '/img/uml/classes/vengeance_reborn_classes.puml',
  },
  ...[
  ['Áudio', 'audio', 'Representa o gerenciador de sons e a reprodução dos efeitos do jogo.'],
  ['Inimigo básico', 'basic_enemy', 'Mostra o inimigo que patrulha uma área e seus limites de movimento.'],
  ['Chefe', 'boss', 'Resume estados, ataques, projéteis e barra de vida do chefe.'],
  ['Pontos de retorno', 'checkpoints', 'Apresenta os marcos de checkpoint e sua ativação pelo jogador.'],
  ['Moedas', 'coins', 'Mostra moedas coletáveis e o grupo responsável por atualizá-las.'],
  ['Inimigo', 'enemy', 'Define atributos e comportamentos compartilhados pelos inimigos.'],
  ['Inimigo voador', 'flying_enemy', 'Descreve o inimigo que patrulha e oscila pelo cenário.'],
  ['Jogo', 'game', 'Centraliza o loop principal, estados e sistemas que compõem a partida.'],
  ['Tela de derrota', 'game_over', 'Apresenta a tela de derrota e o fluxo para continuar ou retornar.'],
  ['HUD', 'hud', 'Exibe as informações de jogo, como vida, moedas e opções disponíveis.'],
  ['Entrada', 'input', 'Mapeia teclado e mouse para ações do jogador e da interface.'],
  ['Fase', 'level', 'Reúne cenário, plataformas, obstáculos, inimigos e pontos de progressão.'],
  ['Menu inicial', 'menu', 'Mostra a tela inicial e os elementos de apresentação do jogo.'],
  ['Obstáculos', 'obstacles', 'Agrupa espinhos e define sua interação com o jogador.'],
  ['Partículas', 'particles', 'Representa partículas individuais e o sistema que as emite e atualiza.'],
  ['Pausa', 'pause', 'Apresenta as opções disponíveis enquanto a partida está pausada.'],
  ['Plataformas', 'platforms', 'Mostra plataformas comuns, móveis e quebráveis, além do grupo gerenciador.'],
  ['Jogador', 'player', 'Reúne movimento, combate, vida, habilidades e estado do personagem.'],
  ['Ataque do jogador', 'player_attack', 'Modela a duração, recarga e área de acerto do ataque.'],
  ['Animações do jogador', 'player_sprites', 'Controla estados, quadros e superfícies das animações.'],
  ['Atributos do jogador', 'player_stats', 'Apresenta atributos, moedas e melhorias persistentes do personagem.'],
  ['Respawn', 'respawn', 'Define o sistema que reposiciona o jogador no ponto de retorno.'],
  ['Loja', 'shop', 'Mostra opções de compra, seleção e validação de melhorias.'],
  ['Estados', 'states', 'Representa a máquina de estados e a navegação entre estados do jogo.'],
  ['História', 'story', 'Apresenta o popup de história e seu controle de exibição.'],
  ['Vitória', 'victory', 'Mostra a tela de vitória e as informações finais da partida.'],
  ['Sentinela de parede', 'wall_sentinel', 'Descreve o inimigo fixo que dispara projéteis a partir da parede.'],
  ].map(([title, name, description]) => ({
    title,
    description,
    image: `/img/uml/classes/${name}.class-diagram.png`,
  })),
];

const sequenceDiagrams = [
  ['Áudio', 'audio', 'Fluxo de criação dos sons e reprodução de um efeito durante o jogo.', 'jpeg'],
  ['Inimigo básico', 'basic_enemy', 'Atualização do inimigo comum, incluindo movimento e interação com o jogador.', 'jpeg'],
  ['Chefe', 'boss', 'Ciclo de estados do chefe, escolha de ataques e aplicação de dano.', 'jpeg'],
  ['Pontos de retorno', 'checkpoints', 'Ativação de um checkpoint e atualização do ponto usado no respawn.', 'jpeg'],
  ['Moedas', 'coins', 'Coleta, atração magnética, renderização e atualização das moedas.', 'jpeg'],
  ['Inimigo', 'enemy', 'Comportamento base de dano, respawn, contato e desenho do inimigo.', 'jpeg'],
  ['Inimigo voador', 'flying_enemy', 'Patrulha, movimento oscilatório, colisão e respawn do inimigo voador.', 'jpeg'],
  ['Loop do jogo', 'game', 'Fluxo principal de eventos, atualização dos sistemas e desenho de cada quadro.', 'png'],
  ['Tela de derrota', 'game_over', 'Exibição da derrota, contagem e retorno do jogador ao fluxo do jogo.', 'png'],
  ['HUD', 'hud', 'Renderização das informações e interações mostradas na interface durante a partida.', 'png'],
  ['Entrada', 'input', 'Percurso dos eventos de teclado e mouse até as ações do jogo.', 'png'],
  ['Fase', 'level', 'Construção do nível e atualização de cenário, colisões e entidades.', 'png'],
  ['Menu inicial', 'menu', 'Atualização e desenho do menu, aguardando a confirmação para iniciar.', 'png'],
  ['Obstáculos', 'obstacles', 'Verificação de colisão entre espinhos e jogador e aplicação de dano.', 'jpeg'],
  ['Partículas', 'particles', 'Criação, atualização e desenho das partículas de efeitos.','jpeg'],
  ['Pausa', 'pause', 'Navegação pelas opções do menu de pausa e execução da ação escolhida.', 'jpeg'],
  ['Plataformas', 'platforms', 'Atualização de plataformas e transição de plataformas quebráveis.', 'jpeg'],
  ['Ataque do jogador', 'player_attack', 'Início do ataque, atualização da recarga e registro de acertos.', 'jpeg'],
  ['Jogador', 'player', 'Movimento, pulo, dash, colisões e atualização da animação do personagem.', 'jpeg'],
  ['Animações do jogador', 'player_sprites', 'Carregamento em cache e seleção de quadros da animação.', 'jpeg'],
  ['Atributos do jogador', 'player_stats', 'Inicialização, melhorias e persistência dos atributos do personagem.', 'jpeg'],
  ['Respawn', 'respawn', 'Ativação de checkpoints e reposicionamento do jogador após a derrota.', 'jpeg'],
  ['Loja', 'shop', 'Seleção de melhorias, verificação de saldo e compra de itens.', 'jpeg'],
  ['Estados', 'states', 'Transições entre estados e retorno ao estado anterior após a pausa.', 'jpeg'],
  ['História', 'story', 'Exibição temporizada de mensagens com efeitos de entrada e saída.', 'png'],
  ['Vitória', 'victory', 'Apresentação do resultado da partida e retorno ao menu principal.', 'png'],
  ['Sentinela de parede', 'wall_sentinel', 'Disparo, movimentação de projéteis e interação com o jogador.', 'png'],
].map(([title, name, description, extension]) => ({
  title,
  description,
  image: name === 'game_over'
    ? '/img/uml/sequences/diagrama_game_over_py.png'
    : `/img/uml/sequences/diagrama_sequencia_${name}_py.${extension}`,
}));

function DiagramSection({id, title, description, diagrams}) {
  return (
    <section className={styles.section} id={id}>
      <header className={styles.sectionHeader}>
        <Heading as="h2">{title}</Heading>
        <p>{description}</p>
      </header>
      <div className={styles.grid}>
        {diagrams.map((diagram, index) => (
          <article className={styles.diagram} key={diagram.image}>
            <a
              className={styles.imageLink}
              href={diagram.image}
              target="_blank"
              rel="noreferrer"
              aria-label={`Abrir diagrama: ${diagram.title}`}>
              <img src={diagram.image} alt={`Diagrama UML: ${diagram.title}`} loading="lazy" />
            </a>
            <div className={styles.caption}>
              <span className={styles.index}>{String(index + 1).padStart(2, '0')}</span>
              <div>
                <Heading as="h3">{diagram.title}</Heading>
                <p>{diagram.description}</p>
                {diagram.source && (
                  <a className={styles.sourceLink} href={diagram.source} download>
                    Baixar fonte PlantUML (.puml)
                  </a>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function DiagramasUml() {
  return (
    <Layout
      title="Diagramas UML"
      description="Diagramas de classes e sequência do projeto Vengeance Reborn.">
      <main className={styles.page}>
        <div className="container">
          <header className={styles.header}>
            <p className={styles.eyebrow}>DOCUMENTAÇÃO / UML</p>
            <Heading as="h1">Diagramas do projeto</Heading>
            <p className={styles.intro}>
              Uma visão visual das estruturas do jogo e das interações entre seus componentes.
            </p>
            <nav className={styles.sectionNav} aria-label="Seções dos diagramas">
              <a href="#classes">Classes <span>28</span></a>
              <a href="#sequencias">Sequência <span>27</span></a>
            </nav>
          </header>

          <DiagramSection
            id="classes"
            title="Diagramas de classes"
            description="Estrutura das principais classes, seus atributos e responsabilidades."
            diagrams={classDiagrams}
          />
          <DiagramSection
            id="sequencias"
            title="Diagramas de sequência"
            description="Fluxos de chamadas e interações entre os componentes em cada comportamento."
            diagrams={sequenceDiagrams}
          />
        </div>
      </main>
    </Layout>
  );
}