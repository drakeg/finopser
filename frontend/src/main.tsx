import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

const nav = ['Dashboard','Organization','Accounts','Resources','Costs','Compliance','Policies','Automation','Reports','Administration']

function App() {
  return <div className="app-shell">
    <aside>
      <div className="brand">finopser</div>
      <div className="tagline">Cloud governance & FinOps</div>
      <nav>{nav.map((item, i) => <button className={i === 0 ? 'active' : ''} key={item}>{item}<span>{i === 0 ? '●' : 'Soon'}</span></button>)}</nav>
    </aside>
    <main>
      <header><div><p className="eyebrow">SPRINT 1 FOUNDATION</p><h1>Cloud operations at a glance</h1></div><div className="status"><i/>Local platform online</div></header>
      <section className="cards">
        <article><span>Cloud spend</span><strong>—</strong><small>FinOps arrives in a later sprint</small></article>
        <article><span>Cloud accounts</span><strong>0</strong><small>AWS onboarding not enabled yet</small></article>
        <article><span>Compliance</span><strong>—</strong><small>Observe first, enforce later</small></article>
        <article><span>Platform health</span><strong>Ready</strong><small>Docker-first foundation</small></article>
      </section>
      <section className="panel">
        <div><p className="eyebrow">IMMEDIATE ATTENTION</p><h2>Sprint 1 is intentionally quiet</h2><p>This dashboard shell is the first production-shaped vertical slice. No cloud credentials are required, and no cloud resources can be modified.</p></div>
        <div className="pill">OBSERVE</div>
      </section>
      <section className="grid">
        <div className="panel"><h3>Platform services</h3><ul><li><b>API</b><span>/api/health/</span></li><li><b>Database</b><span>PostgreSQL</span></li><li><b>Queue</b><span>Redis + Celery</span></li><li><b>Scheduler</b><span>Celery Beat</span></li></ul></div>
        <div className="panel"><h3>Safety boundary</h3><p>finopser currently operates without AWS access. Account onboarding, inventory, cost ingestion, compliance evaluation, and remediation remain outside Sprint 1.</p></div>
      </section>
    </main>
  </div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
