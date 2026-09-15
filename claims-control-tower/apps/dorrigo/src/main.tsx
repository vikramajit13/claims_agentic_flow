import React from "react";
import ReactDOM from "react-dom/client";

import "./styles.css";

const services = [
  {
    title: "AI workflow systems",
    body: "Agentic workflows, human review loops, and operational dashboards that fit the way your team already works."
  },
  {
    title: "Automation advisory",
    body: "Clear discovery, practical roadmaps, and delivery plans for cutting repetitive admin without adding fragile tooling."
  },
  {
    title: "Cloud delivery",
    body: "Production-ready web apps, APIs, observability, and deployment pipelines for teams that need dependable systems."
  }
];

const proofPoints = [
  "Insurance and claims automation",
  "Secure document intelligence",
  "Human-in-the-loop decision support",
  "AWS and Vercel delivery",
  "Australian business context"
];

const phases = [
  ["01", "Map the work", "Clarify the process, handoffs, risks, and data sources before a line of code is written."],
  ["02", "Build the wedge", "Ship a focused workflow that proves value quickly and avoids sprawling transformation theatre."],
  ["03", "Harden for use", "Add monitoring, review controls, deployment hygiene, and documentation so the system can live in production."]
];

function App() {
  return (
    <main>
      <section className="hero" aria-labelledby="hero-title">
        <img className="hero__image" src="/images/dorrigo-hero.png" alt="" />
        <div className="hero__shade" />
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
        <div id="top" className="hero__content">
          <p className="eyebrow">AI systems for Australian operations</p>
          <h1 id="hero-title">Dorrigo Technology</h1>
          <p className="hero__lead">
            We design and build pragmatic automation, AI workflows, and cloud software for teams that need dependable systems, not theatre.
          </p>
          <div className="hero__actions">
            <a className="button button--primary" href="mailto:support@dorrigotechnology.com.au?subject=Project%20enquiry%20for%20Dorrigo%20Technology">
              Start a project
            </a>
            <a className="button button--secondary" href="#services">
              View services
            </a>
          </div>
        </div>
      </section>

      <section className="intro" aria-label="Company focus">
        <div>
          <p className="section-kicker">What we do</p>
          <h2>Turn complex manual work into clear, reviewable software.</h2>
        </div>
        <p>
          Dorrigo Technology helps organisations modernise the messy middle: documents, approvals, operational judgement, and teams that still need control while automation does more of the heavy lifting.
        </p>
      </section>

      <section id="services" className="services" aria-labelledby="services-title">
        <div className="section-heading">
          <p className="section-kicker">Services</p>
          <h2 id="services-title">Built for useful production outcomes.</h2>
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

      <section className="capabilities" aria-label="Capabilities">
        <div className="capabilities__panel">
          <p className="section-kicker">Specialties</p>
          <h2>Claims, documents, decisions, and delivery.</h2>
          <p>
            The current engineering focus is agentic claims control tower software: secure intake, document understanding, risk analysis, review queues, and action recommendations.
          </p>
        </div>
        <ul className="proof-list">
          {proofPoints.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </section>

      <section id="approach" className="approach" aria-labelledby="approach-title">
        <div className="section-heading">
          <p className="section-kicker">Approach</p>
          <h2 id="approach-title">Small enough to ship. Strong enough to trust.</h2>
        </div>
        <div className="timeline">
          {phases.map(([number, title, body]) => (
            <article className="timeline__item" key={number}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="contact" className="contact" aria-labelledby="contact-title">
        <div>
          <p className="section-kicker">Contact</p>
          <h2 id="contact-title">Ready to make the workflow real?</h2>
          <p>
            Share the process you want to improve, the systems involved, and what a better outcome would look like.
          </p>
        </div>
        <div className="contact__actions">
          <a className="button button--primary" href="mailto:support@dorrigotechnology.com.au?subject=Project%20enquiry%20for%20Dorrigo%20Technology">
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

export default App;
