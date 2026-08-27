import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

const nav = ['Dashboard','Organization','Accounts','Resources','Costs','Compliance','Policies','Automation','Reports','Administration']

type Dashboard = {
  spend: { mtd: number | string; previous_comparable: number | string; change_percent: number | string | null; currency: string }
  resources: {
    total: number
    active: number
    inactive: number
    by_type: { resource_type: string; count: number }[]
    by_account: { cloud_account: number; cloud_account__name: string; count: number }[]
    by_region: { region: string; count: number }[]
  }
  top_costs: {
    service: { service: string; total: number | string }[]
    account: { cloud_account: number; cloud_account__name: string; total: number | string }[]
    project: { project: number | null; project__name: string | null; total: number | string }[]
    region: { region: string; total: number | string }[]
  }
  accounts: { total: number; by_status: { status: string; count: number }[] }
  attention: { severity: string; kind: string; title: string; detail: string; target: string }[]
}

const money = (value: number | string | undefined) => value === undefined ? '—' : `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

function App() {
  const [active, setActive] = useState('Dashboard')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [dashboardError, setDashboardError] = useState(false)

  useEffect(() => {
    fetch('/api/dashboard/', { credentials: 'include' })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((data) => setDashboard(data))
      .catch(() => setDashboardError(true))
  }, [])

  const spendChange = dashboard?.spend.change_percent
  const spendChangeText = spendChange === null || spendChange === undefined
    ? 'No comparable prior-period data'
    : `${Number(spendChange) >= 0 ? '+' : ''}${spendChange}% vs comparable prior period`

  return <div className="app-shell">
    <aside>
      <div className="brand">finopser</div>
      <div className="tagline">Cloud governance & FinOps</div>
      <nav>{nav.map((item) => <button onClick={() => setActive(item)} className={active === item ? 'active' : ''} key={item}>{item}<span>{['Dashboard','Organization','Accounts','Resources','Costs','Administration'].includes(item) ? '●' : 'Soon'}</span></button>)}</nav>
    </aside>
    <main>
      {active === 'Dashboard' && <>
        <header><div><p className="eyebrow">SPRINT 6</p><h1>What needs attention right now?</h1></div><div className="status"><i/>Persisted data only</div></header>
        {dashboardError && <section className="panel"><h2>Dashboard data unavailable</h2><p>Sign in and verify the API is healthy. The dashboard does not make live AWS calls.</p></section>}
        <section className="cards">
          <article><span>MTD cloud spend</span><strong>{money(dashboard?.spend.mtd)}</strong><small>{spendChangeText}</small></article>
          <article><span>Cloud accounts</span><strong>{dashboard?.accounts.total ?? '—'}</strong><small>Validation state tracked</small></article>
          <article><span>Active resources</span><strong>{dashboard?.resources.active ?? '—'}</strong><small>{dashboard?.resources.inactive ?? '—'} inactive historically</small></article>
          <article><span>Attention items</span><strong>{dashboard?.attention.length ?? '—'}</strong><small>Evidence-backed operational signals</small></article>
        </section>
        <section className="grid">
          <div className="panel"><p className="eyebrow">IMMEDIATE ATTENTION</p><h2>Prioritized signals</h2>{dashboard ? (dashboard.attention.length ? <ul>{dashboard.attention.map((item, index) => <li key={`${item.kind}-${index}`}><b>{item.severity.toUpperCase()} · {item.title}</b><span>{item.target}</span><small>{item.detail}</small></li>)}</ul> : <p>No current operational attention signals.</p>) : <p>Loading operational signals…</p>}</div>
          <div className="panel"><p className="eyebrow">COST DRIVERS</p><h2>Top services this month</h2>{dashboard?.top_costs.service.length ? <ul>{dashboard.top_costs.service.map((item) => <li key={item.service}><b>{item.service}</b><span>{money(item.total)}</span></li>)}</ul> : <p>No current-month cost data loaded.</p>}</div>
        </section>
        <section className="grid"><div className="panel"><h2>Resources by type</h2>{dashboard?.resources.by_type.length ? <ul>{dashboard.resources.by_type.map((item) => <li key={item.resource_type}><b>{item.resource_type}</b><span>{item.count}</span></li>)}</ul> : <p>No inventory data loaded.</p>}</div><div className="panel"><h2>Spend by account</h2>{dashboard?.top_costs.account.length ? <ul>{dashboard.top_costs.account.map((item) => <li key={item.cloud_account}><b>{item.cloud_account__name}</b><span>{money(item.total)}</span></li>)}</ul> : <p>No current-month cost data loaded.</p>}</div></section>
      </>}
      {active === 'Organization' && <><header><div><p className="eyebrow">ORGANIZATION</p><h1>Hierarchy & projects</h1></div></header><section className="panel"><h2>Organization management</h2><p>Platform and Cloud Administrators can manage organizations, recursive nodes, and projects through the existing authenticated APIs.</p></section></>}
      {active === 'Accounts' && <><header><div><p className="eyebrow">AWS ACCOUNTS</p><h1>Account onboarding</h1></div><div className="pill">OBSERVE</div></header><section className="panel"><h2>Register, validate, then sync</h2><ul><li><b>Validate role</b><span>POST /api/cloud-accounts/&lt;id&gt;/validate/</span></li><li><b>Sync inventory</b><span>POST /api/cloud-accounts/&lt;id&gt;/sync-inventory/</span></li><li><b>Sync costs</b><span>POST /api/cloud-accounts/&lt;id&gt;/sync-costs/</span></li></ul></section></>}
      {active === 'Resources' && <><header><div><p className="eyebrow">RESOURCE INVENTORY</p><h1>AWS resources</h1></div><div className="pill">READ ONLY</div></header><section className="cards"><article><span>Total inventory</span><strong>{dashboard?.resources.total ?? '—'}</strong><small>Historical records</small></article><article><span>Active</span><strong>{dashboard?.resources.active ?? '—'}</strong><small>Current inventory</small></article><article><span>Inactive</span><strong>{dashboard?.resources.inactive ?? '—'}</strong><small>Retained historically</small></article><article><span>Types</span><strong>{dashboard?.resources.by_type.length ?? '—'}</strong><small>Normalized types</small></article></section></>}
      {active === 'Costs' && <><header><div><p className="eyebrow">FINOPS</p><h1>AWS cost visibility</h1></div><div className="pill">READ ONLY</div></header><section className="cards"><article><span>MTD spend</span><strong>{money(dashboard?.spend.mtd)}</strong><small>Current month</small></article><article><span>Prior comparable</span><strong>{money(dashboard?.spend.previous_comparable)}</strong><small>Same number of days last month</small></article><article><span>Services</span><strong>{dashboard?.top_costs.service.length ?? '—'}</strong><small>Current-month drivers</small></article><article><span>Regions</span><strong>{dashboard?.top_costs.region.length ?? '—'}</strong><small>Current-month regions</small></article></section><section className="grid"><div className="panel"><h2>Top services</h2>{dashboard?.top_costs.service.length ? <ul>{dashboard.top_costs.service.map((item) => <li key={item.service}><b>{item.service}</b><span>{money(item.total)}</span></li>)}</ul> : <p>No cost data loaded.</p>}</div><div className="panel"><h2>Top regions</h2>{dashboard?.top_costs.region.length ? <ul>{dashboard.top_costs.region.map((item) => <li key={item.region || 'global'}><b>{item.region || 'Unspecified'}</b><span>{money(item.total)}</span></li>)}</ul> : <p>No cost data loaded.</p>}<p><a href="/api/costs/export/">Export normalized CSV</a></p></div></section></>}
      {active === 'Administration' && <><header><div><p className="eyebrow">ADMINISTRATION</p><h1>Roles & audit</h1></div></header><section className="panel"><h2>Governed operations</h2><p>Roles, audit events, inventory syncs, and cost syncs remain available through the existing administration and authenticated APIs.</p></section></>}
      {!['Dashboard','Organization','Accounts','Resources','Costs','Administration'].includes(active) && <section className="panel"><p className="eyebrow">PLANNED</p><h2>{active}</h2><p>This capability is intentionally outside Sprint 6.</p></section>}
    </main>
  </div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
