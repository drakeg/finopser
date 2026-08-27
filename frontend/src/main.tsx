import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

const nav = ['Dashboard','Organization','Accounts','Resources','Costs','Compliance','Policies','Automation','Reports','Administration']

function App() {
  const [active, setActive] = useState('Dashboard')
  return <div className="app-shell">
    <aside>
      <div className="brand">finopser</div>
      <div className="tagline">Cloud governance & FinOps</div>
      <nav>{nav.map((item) => <button onClick={() => setActive(item)} className={active === item ? 'active' : ''} key={item}>{item}<span>{item === 'Dashboard' || item === 'Organization' || item === 'Administration' ? '●' : 'Soon'}</span></button>)}</nav>
    </aside>
    <main>
      {active === 'Dashboard' && <>
        <header><div><p className="eyebrow">SPRINT 2</p><h1>Cloud operations at a glance</h1></div><div className="status"><i/>Local platform online</div></header>
        <section className="cards">
          <article><span>Cloud spend</span><strong>—</strong><small>FinOps arrives later</small></article>
          <article><span>Organizations</span><strong>Ready</strong><small>Hierarchy APIs enabled</small></article>
          <article><span>Access control</span><strong>RBAC</strong><small>Server-side role enforcement</small></article>
          <article><span>Audit</span><strong>On</strong><small>Privileged mutations recorded</small></article>
        </section>
        <section className="panel"><div><p className="eyebrow">IMMEDIATE ATTENTION</p><h2>Governance foundation is active</h2><p>Sprint 2 adds organizations, recursive nodes, projects, managed roles, and immutable audit records while cloud-provider access remains disabled.</p></div><div className="pill">OBSERVE</div></section>
      </>}
      {active === 'Organization' && <>
        <header><div><p className="eyebrow">ORGANIZATION</p><h1>Hierarchy & projects</h1></div></header>
        <section className="panel"><h2>Organization management is available</h2><p>Authenticated users can read organization data through the API. Platform and Cloud Administrators can create and modify organizations, recursive organization nodes, and projects.</p><ul><li><b>Organizations</b><span>/api/organizations/</span></li><li><b>Nodes</b><span>/api/organization-nodes/</span></li><li><b>Projects</b><span>/api/projects/</span></li></ul></section>
      </>}
      {active === 'Administration' && <>
        <header><div><p className="eyebrow">ADMINISTRATION</p><h1>Roles & audit</h1></div></header>
        <section className="grid"><div className="panel"><h3>Managed roles</h3><p>Platform Administrator, Cloud Administrator, FinOps Analyst, Security / Compliance Engineer, Project Owner, and Auditor.</p><p>Platform Administrators can assign managed roles through <b>/api/users/&lt;id&gt;/roles/</b>.</p></div><div className="panel"><h3>Django administration</h3><p>Use the built-in administration interface for local bootstrap and detailed model management.</p><p><a href="/admin/">Open administration</a></p></div></section>
      </>}
      {!['Dashboard','Organization','Administration'].includes(active) && <section className="panel"><p className="eyebrow">PLANNED</p><h2>{active}</h2><p>This capability is intentionally outside Sprint 2.</p></section>}
    </main>
  </div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
