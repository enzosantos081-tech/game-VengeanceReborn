import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './imagens-do-jogo.module.css';

const screenshots = [
  {
    title: 'Exploração e combate',
    description: 'Kael atravessa cavernas, enfrenta inimigos e coleta moedas.',
    image: '/img/gameImage/Captura%20de%20tela%202026-10-21%20210616.png',
    alt: 'Kael em uma caverna, entre inimigos, moedas e obstáculos.',
  },
  {
    title: 'Arsenal do Núcleo',
    description: 'A loja permite comprar espadas e melhorias usando moedas.',
    image: '/img/gameImage/Captura%20de%20tela%202026-10-21%20210625.png',
    alt: 'Tela da loja Arsenal do Núcleo com espadas disponíveis para compra.',
  },
  {
    title: 'Confronto com Vharok',
    description: 'A batalha contra o Rei do Abismo acontece em sua arena.',
    image: '/img/gameImage/Captura%20de%20tela%202026-10-21%20210712.png',
    alt: 'Kael enfrenta Vharok na arena, com a barra de vida do chefe no topo.',
  },
];

export default function ImagensDoJogo() {
  return (
    <Layout
      title="Imagens do jogo"
      description="Confira algumas telas de Vengeance Reborn.">
      <main className={styles.page}>
        <div className="container">
          <header className={styles.header}>
            <p className={styles.eyebrow}>VENGEANCE REBORN / GALERIA</p>
            <Heading as="h1">Imagens do jogo</Heading>
            <p className={styles.lede}>
              Uma prévia da exploração, da loja e do confronto final.
            </p>
          </header>

          <section className={styles.gallery} aria-label="Telas do jogo">
            {screenshots.map((screenshot, index) => (
              <article className={styles.card} key={screenshot.image}>
                <a
                  className={styles.imageLink}
                  href={screenshot.image}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Abrir imagem: ${screenshot.title}`}>
                  <img src={screenshot.image} alt={screenshot.alt} loading="lazy" />
                </a>
                <div className={styles.caption}>
                  <span className={styles.number}>{String(index + 1).padStart(2, '0')}</span>
                  <div>
                    <Heading as="h2">{screenshot.title}</Heading>
                    <p>{screenshot.description}</p>
                  </div>
                </div>
              </article>
            ))}
          </section>
        </div>
      </main>
    </Layout>
  );
}