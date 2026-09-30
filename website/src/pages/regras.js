import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './regras.module.css';

const rules = [
  {
    number: '01',
    title: 'Sobreviva à jornada',
    text: 'Você começa cada região com três vidas. Encostar em armadilhas ou receber um golpe inimigo custa uma vida; ao perder todas, a jornada termina.',
  },
  {
    number: '02',
    title: 'Ataque no momento certo',
    text: 'O ataque alcança inimigos próximos à sua frente. Depois de cada golpe, aguarde um instante antes de atacar novamente. Chefes podem exigir mais de um acerto.',
  },
  {
    number: '03',
    title: 'Colete cristais',
    text: 'Cristais deixados pelos inimigos podem ser trocados por melhorias na loja entre regiões. Cada melhoria vale até o fim da tentativa atual.',
  },
  {
    number: '04',
    title: 'Ative os marcos',
    text: 'Marcos de retorno registram seu progresso. Se cair em combate, você volta ao último marco ativado, mas perde uma vida e parte dos cristais carregados.',
  },
  {
    number: '05',
    title: 'Vença o Guardião',
    text: 'Desvie dos ataques do Guardião e golpeie durante as pausas entre investidas. A vitória acontece quando sua energia chega a zero; fugir não conta como conclusão.',
  },
];

export default function Rules() {
  return (
    <Layout
      title="Regras do jogo"
      description="Regras fictícias de Vengeance Reborn: combate, cristais, marcos e vitória.">
      <main className={styles.page}>
        <div className="container">
          <header className={styles.header}>
            <p className={styles.eyebrow}>GUIA DE JOGO / 01</p>
            <Heading as="h1">Regras da jornada</Heading>
            <p className={styles.intro}>
              Em Vengeance Reborn, sobreviver depende de escolher quando lutar,
              quando avançar e o que levar consigo.
            </p>
          </header>

          <section className={styles.ruleList} aria-label="Regras do jogo">
            {rules.map((rule) => (
              <article className={styles.rule} key={rule.number}>
                <span className={styles.number}>{rule.number}</span>
                <div>
                  <Heading as="h2">{rule.title}</Heading>
                  <p>{rule.text}</p>
                </div>
              </article>
            ))}
          </section>

          <p className={styles.note}>
            Estas regras são fictícias e servem como material de ambientação do jogo.
          </p>
        </div>
      </main>
    </Layout>
  );
}