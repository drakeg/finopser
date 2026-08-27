import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

const nav = ['Dashboard','Organization','Accounts','Resources','Costs','Compliance','Policies','Automation','Reports','Administration']

type ResourceSummary = {
  total: number
  active: number
  inactive: number
  by_type: { resource_type: string; count: number }[]
}

function App() {
  const [active, setActive] = useState('Dashboard')
  const [resourceSummary, setResourceSummary] = useState<ResourceSummary | null>(null)

  useEffect(() => {
    fetch('/api/resources/summary/', { credentials: 'include' })
      .then((response) => response.ok ? response.json() : null)
      .then((data) => { if (data) setResourceSummary(data) })
      .catch(() => undefined)
  }, [])

  return <div className="app-shell">
    <aside>
      <div className="brand">finopser</div>
      <div className="tagline">Cloud governance & FinOps</div>
      <nav>{nav.map((item) => <button onClick={() => setActive(item)} className={active === item ? 'active' : ''} key={item}>{item}<span>{['Dashboard','Organization','Accounts','Resources','Administration'].includes(item) ? '●' : 'Soon'}</span></button>)}</nav>
    </aside>
    <main>
      {active === 'Dashboard' && <>
        <header><div><p className="eyebrow">SPRINT 4</p><h1>Cloud operations at a glance</h1></div><div className="status"><i/>Local platform online</div></header>
        <section className="cards">
          <article><span>Cloud spend</span><strong>—</strong><small>FinOps arrives later</small></article>
          <article><span>Cloud accounts</span><strong>AWS</strong><small>STS onboarding enabled</small></article>
          <article><span>Active resources</span><strong>{resourceSummary?.active ?? '—'}</strong><small>Read-only inventory</small></article>
          <article><span>Safety</span><strong>Observe</strong><small>No cloud mutations</small></article>
        </section>
        <section className="panel"><div><p className="eyebrow">IMMEDIATE ATTENTION</p><h2>Resource inventory is available</h2><p>Validated AWS accounts can now run an explicit read-only inventory sync. Discovered resources are normalized, retained historically, and visible without enabling remediation or cost ingestion.</p></div><div className="pill">OBSERVE</div></section>
      </>}
      {active === 'Organization' && <>
        <header><div><p className="eyebrow">ORGANIZATION</p><h1>Hierarchy & projects</h1></div></header>
        <section className="panel"><h2>Organization management</h2><p>Platform and Cloud Administrators can create and modify organizations, recursive nodes, and projects.</p><ul><li><b>Organizations</b><span>/api/organizations/</span></li><li><b>Nodes</b><span>/api/organization-nodes/</span></li><li><b>Projects</b><span>/api/projects/</span></li></ul></section>
      </>}
      {active === 'Accounts' && <>
        <header><div><p className="eyebrow">AWS ACCOUNTS</p><h1>Account onboarding</h1></div><div className="pill">OBSERVE</div></header>
        <section className="grid"><div className="panel"><h3>Register & validate</h3><p>Cloud accounts are scoped to an organization and optional project. Configure the AWS account ID, role ARN, and optional ExternalId, then validate the role before inventory.</p><ul><li><b>Accounts API</b><span>/api/cloud-accounts/</span></li><li><b>Validate role</b><span>POST /api/cloud-accounts/&lt;id&gt;/validate/</span></li><li><b>Sync inventory</b><span>POST /api/cloud-accounts/&lt;id&gt;/sync-inventory/</span></li></ul></div><div className="panel"><h3>Credential boundary</h3><p>finopser does not accept IAM access keys. Temporary STS credentials remain in memory and are never persisted.</p></div></section>
      </>}
      {active === 'Resources' && <>
        <header><div><p className="eyebrow">RESOURCE INVENTORY</p><h1>AWS resources</h1></div><div className="pill">READ ONLY</div></header>
        <section className="cards"><article><span>Total inventory</span><strong>{resourceSummary?.total ?? '—'}</strong><small>Historical records</small></article><article><span>Active</span><strong>{resourceSummary?.active ?? '—'}</strong><small>Seen in latest complete sync</small></article><article><span>Inactive</span><strong>{resourceSummary?.inactive ?? '—'}</strong><small>Not hard-deleted</small></article><article><span>Resource types</span><strong>{resourceSummary?.by_type.length ?? '—'}</strong><small>Normalized AWS types</small></article></section>
        <section className="panel"><h2>Inventory by type</h2>{resourceSummary ? <ul>{resourceSummary.by_type.map((item) => <li key={item.resource_type}><b>{item.resource_type}</b><span>{item.count}</span></li>)}</ul> : <p>Sign in and run an inventory sync to populate resource data.</p>}<p>Filter the full inventory through <b>/api/resources/</b> using cloud_account, resource_type, region, state, and active query parameters.</p></section>
      </>}
      {active === 'Administration' && <>
        <header><div><p className="eyebrow">ADMINISTRATION</p><h1>Roles & audit</h1></div></header>
        <section className="grid"><div className="panel"><h3>Managed roles</h3><p>Platform Administrator, Cloud Administrator, FinOps Analyst, Security / Compliance Engineer, Project Owner, and Auditor.</p><p>Platform Administrators can assign managed roles through <b>/api/users/&lt;id&gt;/roles/</b>.</p></div><div className="panel"><h3>Inventory history</h3><p>Inventory resources and sync history are read-only in Django administration. All sync requests and outcomes are audited.</p></div></section>
      </>}
      {!['Dashboard','Organization','Accounts','Resources','Administration'].includes(active) && <section className="panel"><p className="eyebrow">PLANNED</p><h2>{active}</h2><p>This capability is intentionally outside Sprint 4.</p></section>}
    </main>
  </div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
