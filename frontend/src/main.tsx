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
      <nav>{nav.map((item) => <button onClick={() => setActive(item)} className={active === item ? 'active' : ''} key={item}>{item}<span>{['Dashboard','Organization','Accounts','Administration'].includes(item) ? '●' : 'Soon'}</span></button>)}</nav>
    </aside>
    <main>
      {active === 'Dashboard' && <>
        <header><div><p className="eyebrow">SPRINT 3</p><h1>Cloud operations at a glance</h1></div><div className="status"><i/>Local platform online</div></header>
        <section className="cards">
          <article><span>Cloud spend</span><strong>—</strong><small>FinOps arrives later</small></article>
          <article><span>Cloud accounts</span><strong>AWS</strong><small>STS onboarding enabled</small></article>
          <article><span>Access model</span><strong>Role</strong><small>No stored IAM access keys</small></article>
          <article><span>Safety</span><strong>Observe</strong><small>Identity validation only</small></article>
        </section>
        <section className="panel"><div><p className="eyebrow">IMMEDIATE ATTENTION</p><h2>AWS onboarding is available</h2><p>Register accounts against an organization/project, then explicitly validate the configured IAM role with STS. No inventory, cost ingestion, or AWS resource changes are enabled.</p></div><div className="pill">OBSERVE</div></section>
      </>}
      {active === 'Organization' && <>
        <header><div><p className="eyebrow">ORGANIZATION</p><h1>Hierarchy & projects</h1></div></header>
        <section className="panel"><h2>Organization management</h2><p>Platform and Cloud Administrators can create and modify organizations, recursive nodes, and projects.</p><ul><li><b>Organizations</b><span>/api/organizations/</span></li><li><b>Nodes</b><span>/api/organization-nodes/</span></li><li><b>Projects</b><span>/api/projects/</span></li></ul></section>
      </>}
      {active === 'Accounts' && <>
        <header><div><p className="eyebrow">AWS ACCOUNTS</p><h1>Account onboarding</h1></div><div className="pill">OBSERVE</div></header>
        <section className="grid"><div className="panel"><h3>Register an account</h3><p>Cloud accounts are scoped to an organization and optional project. Configure the AWS account ID, role ARN, and optional ExternalId through the authenticated API or Django administration.</p><ul><li><b>Accounts API</b><span>/api/cloud-accounts/</span></li><li><b>Validate role</b><span>POST /api/cloud-accounts/&lt;id&gt;/validate/</span></li></ul></div><div className="panel"><h3>Credential boundary</h3><p>finopser does not accept IAM access keys. STS credentials exist only in memory during explicit validation and are never persisted.</p><p><a href="/admin/core/cloudaccount/">Open account administration</a></p></div></section>
      </>}
      {active === 'Administration' && <>
        <header><div><p className="eyebrow">ADMINISTRATION</p><h1>Roles & audit</h1></div></header>
        <section className="grid"><div className="panel"><h3>Managed roles</h3><p>Platform Administrator, Cloud Administrator, FinOps Analyst, Security / Compliance Engineer, Project Owner, and Auditor.</p><p>Platform Administrators can assign managed roles through <b>/api/users/&lt;id&gt;/roles/</b>.</p></div><div className="panel"><h3>Django administration</h3><p>Use the built-in administration interface for local bootstrap and detailed model management.</p><p><a href="/admin/">Open administration</a></p></div></section>
      </>}
      {!['Dashboard','Organization','Accounts','Administration'].includes(active) && <section className="panel"><p className="eyebrow">PLANNED</p><h2>{active}</h2><p>This capability is intentionally outside Sprint 3.</p></section>}
    </main>
  </div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
