import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';

import Heading from '@theme/Heading';
import styles from './index.module.css';

function HomepageHeader() {
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className={clsx('container', styles.heroContent)}>
        <p className={styles.heroKicker}>AÇÃO · FANTASIA SOMBRIA · VENGEANCE REBORN</p>
        <Heading as="h1" className="hero__title">Vengeance Reborn</Heading>
        <p className={clsx('hero__subtitle', styles.heroSubtitle)}>
          Atravesse as ruínas, enfrente Vharok e conquiste sua vingança.
        </p>
        <div className={styles.buttons}>
          <Link className="button button--primary button--lg" to="/docs/intro">
            Explorar o tutorial
          </Link>
          <Link className="button button--outline button--secondary button--lg" to="/diagramas-uml">
            Ver diagramas UML
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home() {
  return (
    <Layout
      title="Vengeance Reborn"
      description="Explore o universo, as regras e a arquitetura de Vengeance Reborn.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
