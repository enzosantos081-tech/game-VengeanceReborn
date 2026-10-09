import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './historia.module.css';

const historyImage = '/img/Vengeance%20Reborn%20history.jpeg';

const chapters = [
  {
    number: '01',
    title: 'Uma vida em paz',
    text: 'Longe dos grandes reinos, Kael vivia com sua família em uma pequena região. Por muitos anos, aquele lugar permaneceu em paz.',
  },
  {
    number: '02',
    title: 'A expansão de Vharok',
    text: 'A tranquilidade terminou quando Vharok, o Rei do Abismo, avançou sobre a região, destruindo tudo o que encontrava pelo caminho.',
  },
  {
    number: '03',
    title: 'Tudo o que restou',
    text: 'O irmão de Kael morreu tentando proteger a família. Kael sobreviveu à invasão, mas perdeu tudo o que conhecia.',
  },
  {
    number: '04',
    title: 'O Núcleo do Retorno',
    text: 'Consumido pela dor, Kael passou anos estudando as antigas ruínas. Lá descobriu um artefato capaz de guardar sua essência e restaurá-lo após a morte.',
  },
  {
    number: '05',
    title: 'A jornada começa',
    text: 'Agora, munido do Núcleo e determinado a vingar o irmão, Kael parte rumo ao castelo de Vharok. Seu objetivo: derrotar o Rei do Abismo.',
  },
];

export default function Historia() {
  return (
    <Layout
      title="História"
      description="A origem de Kael e a jornada de vingança em Vengeance Reborn.">
      <main className={styles.page}>
        <div className="container">
          <header className={styles.header}>
            <p className={styles.eyebrow}>VENGEANCE REBORN / A ORIGEM</p>
            <Heading as="h1">Uma jornada de vingança</Heading>
            <p className={styles.lede}>
              Da vida tranquila nas fronteiras ao caminho até o castelo do Rei do Abismo.
              Esta é a história de Kael e do Núcleo que o mantém de pé.
            </p>
          </header>

          <figure className={styles.illustration}>
            <a href={historyImage} target="_blank" rel="noreferrer">
              <img
                src={historyImage}
                alt="Seis cenas da história de Kael: sua família, a invasão de Vharok, a descoberta do Núcleo do Retorno e a jornada até o castelo."
              />
            </a>
            <figcaption>Do lar perdido à fortaleza de Vharok.</figcaption>
          </figure>

          <section className={styles.chronicle} aria-labelledby="chronicle-title">
            <div className={styles.sectionIntro}>
              <p className={styles.eyebrow}>A CRÔNICA</p>
              <Heading as="h2" id="chronicle-title">Antes da vingança</Heading>
            </div>
            <ol className={styles.chapters}>
              {chapters.map((chapter) => (
                <li className={styles.chapter} key={chapter.number}>
                  <span className={styles.number}>{chapter.number}</span>
                  <div>
                    <Heading as="h3">{chapter.title}</Heading>
                    <p>{chapter.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className={styles.next}>
            <div>
              <p className={styles.eyebrow}>O CAMINHO ADIANTE</p>
              <Heading as="h2">Agora começa a jornada.</Heading>
              <p>Conheça os desafios e prepare-se para atravessar as ruínas.</p>
            </div>
            <div className={styles.actions}>
              <Link className="button button--primary" to="/docs/intro">
                Explorar o tutorial
              </Link>
              <Link className="button button--outline button--secondary" to="/regras">
                Ler as regras
              </Link>
            </div>
          </section>
        </div>
      </main>
    </Layout>
  );
}