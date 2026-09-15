import React from "react";
import ReactDOM from "react-dom/client";

import "./styles.css";

const services = [
  {
    title: "AI workflow systems",
    body: "Agentic workflows, document intelligence, review queues, and dashboards that keep people in control."
  },
  {
    title: "Automation delivery",
    body: "Focused software that removes repetitive admin, connects existing tools, and makes operational work easier to trust."
  },
  {
    title: "Cloud foundations",
    body: "Secure web apps, APIs, deployment pipelines, and monitoring for systems that need to run beyond the demo."
  }
];

const capabilities = [
  "Claims and operations automation",
  "Secure document processing",
  "Human-in-the-loop decision support",
  "AWS, Vercel, and modern web delivery",
  "Australian business context"
];

const approach = [
  ["01", "Understand the work", "Map the workflow, data, exceptions, and decision points before prescribing technology."],
  ["02", "Ship a useful wedge", "Deliver a focused first system that proves value without turning the project into a transformation saga."],
  ["03", "Harden for production", "Add review controls, observability, deployment hygiene, and documentation so the system can keep earning trust."]
];

function App() {
  return (
    <main>
      <section className="hero" id="top" aria-labelledby="hero-title">
        <img className="hero__image" src="/images/dorrigo-hero.png" alt="" />
        <div className="hero__overlay" />
        <nav className="nav" aria-label="Primary navigation">
          <a className="brand" href="#top" aria-label="Dorrigo Technology home">
            <span className="brand__mark">DT</span>
            <span>Dorrigo Technology</span>
          </a>
          <div className="nav__links">
            <a href="#services">Services</a>
            <a href="#approach">Approach</a>
            <a href="#contact">Contact</a>
          </div>
        </nav>
        <div className="hero__content">
          <p className="eyebrow">AI systems for Australian operations</p>
          <h1 id="hero-title">Dorrigo Technology</h1>
          <p className="hero__lead">
            We build pragmatic AI, automation, and cloud software for teams that want better systems, cleaner decisions, and less manual drag.
          </p>
          <div className="hero__actions">
            <a className="button button--primary" href="mailto:support@dorrigotechnology.com.au?subject=Dorrigo%20Technology%20project%20enquiry">
              Start a project
            </a>
            <a className="button button--ghost" href="#services">
              Explore services
            </a>
          </div>
        </div>
      </section>

      <section className="intro" aria-label="Company focus">
        <div>
          <p className="section-kicker">What we do</p>
          <h2>Software for the complicated middle of business operations.</h2>
        </div>
        <p>
          Dorrigo Technology helps organisations turn document-heavy, judgement-heavy, and approval-heavy processes into clear digital workflows that are reviewable, observable, and ready for production.
        </p>
      </section>

      <section className="section" id="services" aria-labelledby="services-title">
        <div className="section__heading">
          <p className="section-kicker">Services</p>
          <h2 id="services-title">Designed around outcomes that survive first contact with real work.</h2>
        </div>
        <div className="service-grid">
          {services.map((service) => (
            <article className="service-card" key={service.title}>
              <h3>{service.title}</h3>
              <p>{service.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="capability-band" aria-label="Capabilities">
        <div className="capability-band__text">
          <p className="section-kicker">Specialties</p>
          <h2>Claims, documents, decisions, and dependable delivery.</h2>
          <p>
            The focus is practical automation: secure intake, document understanding, risk analysis, recommended actions, and human review where judgement still matters.
          </p>
        </div>
        <ul className="capability-list">
          {capabilities.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="section" id="approach" aria-labelledby="approach-title">
        <div className="section__heading">
          <p className="section-kicker">Approach</p>
          <h2 id="approach-title">Clear discovery, focused delivery, production discipline.</h2>
        </div>
        <div className="timeline">
          {approach.map(([number, title, body]) => (
            <article className="timeline__item" key={number}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="contact" id="contact" aria-labelledby="contact-title">
        <div>
          <p className="section-kicker">Contact</p>
          <h2 id="contact-title">Bring the messy workflow. We will make it legible.</h2>
          <p>
            Send through the process you want improved, the systems involved, and the outcome you want the team to feel.
          </p>
        </div>
        <div className="contact__actions">
          <a className="button button--primary" href="mailto:support@dorrigotechnology.com.au?subject=Dorrigo%20Technology%20project%20enquiry">
            support@dorrigotechnology.com.au
          </a>
          <a className="domain-link" href="https://dorrigotechnology.com.au">
            dorrigotechnology.com.au
          </a>
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
