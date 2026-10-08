import Link from '@docusaurus/Link';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

const FeatureList = [
  {
    number: '01',
    title: 'Comece a jornada',
    description: 'Conheça o mundo, os personagens e os sistemas que movem a aventura.',
    to: '/docs/intro',
  },
  {
    number: '02',
    title: 'Prepare-se para lutar',
    description: 'Revise as regras de combate, progressão, checkpoints e confronto final.',
    to: '/regras',
  },
  {
    number: '03',
    title: 'Veja por dentro',
    description: 'Explore os diagramas de classes e os fluxos entre os sistemas do jogo.',
    to: '/diagramas-uml',
  },
];

function Feature({number, title, description, to}) {
  return (
    <Link className={styles.feature} to={to}>
      <span className={styles.number}>{number}</span>
      <Heading as="h3">{title}</Heading>
      <p>{description}</p>
      <span className={styles.action}>Acessar <span aria-hidden="true">↗</span></span>
    </Link>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className={styles.sectionHeading}>
          <p>VENGEANCE REBORN / ARQUIVOS DA JORNADA</p>
          <Heading as="h2">Entre nas ruínas</Heading>
        </div>
        <div className={styles.grid}>
          {FeatureList.map((feature) => (
            <Feature key={feature.number} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}
