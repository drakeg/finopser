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

type CostSummary = {
  total: number | string
  mtd: number | string
  by_service: { service: string; total: number | string }[]
  by_account: { cloud_account: number; cloud_account__name: string; total: number | string }[]
  by_region: { region: string; total: number | string }[]
  monthly: { month: string; total: number | string }[]
}

const money = (value: number | string | undefined) => value === undefined ? '—' : `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

function App() {
  const [active, setActive] = useState('Dashboard')
  const [resourceSummary, setResourceSummary] = useState<ResourceSummary | null>(null)
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null)

  useEffect(() => {
    fetch('/api/resources/summary/', { credentials: 'include' })
      .then((response) => response.ok ? response.json() : null)
      .then((data) => { if (data) setResourceSummary(data) })
      .catch(() => undefined)
    fetch('/api/costs/summary/', { credentials: 'include' })
      .then((response) => response.ok ? response.json() : null)
      .then((data) => { if (data) setCostSummary(data) })
      .catch(() => undefined)
  }, [])

  return <div className="app-shell">
    <aside>
      <div className="brand">finopser</div>
      <div className="tagline">Cloud governance & FinOps</div>
      <nav>{nav.map((item) => <button onClick={() => setActive(item)} className={active === item ? 'active' : ''} key={item}>{item}<span>{['Dashboard','Organization','Accounts','Resources','Costs','Administration'].includes(item) ? '●' : 'Soon'}</span></button>)}</nav>
    </aside>
    <main>
      {active === 'Dashboard' && <>
        <header><div><p className="eyebrow">SPRINT 5</p><h1>Cloud operations at a glance</h1></div><div className="status"><i/>Local platform online</div></header>
        <section className="cards">
          <article><span>MTD cloud spend</span><strong>{money(costSummary?.mtd)}</strong><small>Normalized Cost Explorer data</small></article>
          <article><span>Cloud accounts</span><strong>AWS</strong><small>STS onboarding enabled</small></article>
          <article><span>Active resources</span><strong>{resourceSummary?.active ?? '—'}</strong><small>Read-only inventory</small></article>
          <article><span>Safety</span><strong>Observe</strong><small>No cloud mutations</small></article>
        </section>
        <section className="panel"><div><p className="eyebrow">IMMEDIATE ATTENTION</p><h2>FinOps visibility is available</h2><p>Validated AWS accounts can explicitly sync Cost Explorer data into normalized daily records. Inventory and cost ingestion remain read-only and nothing runs automatically during Docker startup.</p></div><div className="pill">OBSERVE</div></section>
      </>}
      {active === 'Organization' && <>
        <header><div><p className="eyebrow">ORGANIZATION</p><h1>Hierarchy & projects</h1></div></header>
        <section className="panel"><h2>Organization management</h2><p>Platform and Cloud Administrators can create and modify organizations, recursive nodes, and projects.</p><ul><li><b>Organizations</b><span>/api/organizations/</span></li><li><b>Nodes</b><span>/api/organization-nodes/</span></li><li><b>Projects</b><span>/api/projects/</span></li></ul></section>
      </>}
      {active === 'Accounts' && <>
        <header><div><p className="eyebrow">AWS ACCOUNTS</p><h1>Account onboarding</h1></div><div className="pill">OBSERVE</div></header>
        <section className="grid"><div className="panel"><h3>Register & validate</h3><p>Cloud accounts are scoped to an organization and optional project. Validate the role before inventory or cost ingestion.</p><ul><li><b>Validate role</b><span>POST /api/cloud-accounts/&lt;id&gt;/validate/</span></li><li><b>Sync inventory</b><span>POST /api/cloud-accounts/&lt;id&gt;/sync-inventory/</span></li><li><b>Sync costs</b><span>POST /api/cloud-accounts/&lt;id&gt;/sync-costs/</span></li></ul></div><div className="panel"><h3>Credential boundary</h3><p>finopser does not accept IAM access keys. Temporary STS credentials remain in memory and are never persisted.</p></div></section>
      </>}
      {active === 'Resources' && <>
        <header><div><p className="eyebrow">RESOURCE INVENTORY</p><h1>AWS resources</h1></div><div className="pill">READ ONLY</div></header>
        <section className="cards"><article><span>Total inventory</span><strong>{resourceSummary?.total ?? '—'}</strong><small>Historical records</small></article><article><span>Active</span><strong>{resourceSummary?.active ?? '—'}</strong><small>Seen in latest complete sync</small></article><article><span>Inactive</span><strong>{resourceSummary?.inactive ?? '—'}</strong><small>Not hard-deleted</small></article><article><span>Resource types</span><strong>{resourceSummary?.by_type.length ?? '—'}</strong><small>Normalized AWS types</small></article></section>
        <section className="panel"><h2>Inventory by type</h2>{resourceSummary ? <ul>{resourceSummary.by_type.map((item) => <li key={item.resource_type}><b>{item.resource_type}</b><span>{item.count}</span></li>)}</ul> : <p>Sign in and run an inventory sync to populate resource data.</p>}</section>
      </>}
      {active === 'Costs' && <>
        <header><div><p className="eyebrow">FINOPS</p><h1>AWS cost visibility</h1></div><div className="pill">READ ONLY</div></header>
        <section className="cards"><article><span>MTD spend</span><strong>{money(costSummary?.mtd)}</strong><small>Current month</small></article><article><span>Loaded spend</span><strong>{money(costSummary?.total)}</strong><small>Current filtered dataset</small></article><article><span>Services</span><strong>{costSummary?.by_service.length ?? '—'}</strong><small>Cost-producing services</small></article><article><span>Months</span><strong>{costSummary?.monthly.length ?? '—'}</strong><small>Historical periods loaded</small></article></section>
        <section className="grid"><div className="panel"><h2>Top services</h2>{costSummary ? <ul>{costSummary.by_service.slice(0, 8).map((item) => <li key={item.service}><b>{item.service}</b><span>{money(item.total)}</span></li>)}</ul> : <p>Run a cost sync to populate FinOps data.</p>}</div><div className="panel"><h2>Spend by account</h2>{costSummary ? <ul>{costSummary.by_account.map((item) => <li key={item.cloud_account}><b>{item.cloud_account__name}</b><span>{money(item.total)}</span></li>)}</ul> : <p>No cost data loaded.</p>}<p><a href="/api/costs/export/">Export normalized CSV</a></p></div></section>
      </>}
      {active === 'Administration' && <>
        <header><div><p className="eyebrow">ADMINISTRATION</p><h1>Roles & audit</h1></div></header>
        <section className="grid"><div className="panel"><h3>Managed roles</h3><p>Platform Administrator, Cloud Administrator, FinOps Analyst, Security / Compliance Engineer, Project Owner, and Auditor.</p></div><div className="panel"><h3>Audit trail</h3><p>Inventory and cost sync requests and outcomes are audited. Cost and inventory records remain read-only through their public APIs.</p></div></section>
      </>}
      {!['Dashboard','Organization','Accounts','Resources','Costs','Administration'].includes(active) && <section className="panel"><p className="eyebrow">PLANNED</p><h2>{active}</h2><p>This capability is intentionally outside Sprint 5.</p></section>}
    </main>
  </div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
