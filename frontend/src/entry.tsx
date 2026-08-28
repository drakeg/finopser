import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'
import './setup.css'

type Session={authenticated:boolean;username:string|null}
type CloudAccount={id:number;name:string;provider:string;provider_account_id:string;status:string;last_error:string}
type Subscription={plan:string;status:string;billing_configured:boolean;max_cloud_accounts:number;features:Record<string,boolean>}
type Bootstrap={onboarding:{required:boolean;current_step:string;completed_at:string|null};organization:{id:number;name:string}|null;subscription:Subscription|null;cloud_accounts:CloudAccount[]}

type ApiError={detail?:string;error?:string;upgrade_required?:boolean}

const originalFetch=window.fetch.bind(window)
async function api<T>(url:string,options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers)
 headers.set('Content-Type','application/json')
 const response=await originalFetch(url,{credentials:'include',...options,headers})
 const data=await response.json().catch(()=>({})) as T&ApiError
 if(!response.ok)throw new Error(data.detail??data.error??`${response.status}`)
 return data
}
function csrfToken(){return document.cookie.split('; ').find(v=>v.startsWith('csrftoken='))?.split('=')[1]??''}
function post<T>(url:string,body:Record<string,unknown>={}):Promise<T>{return api<T>(url,{method:'POST',headers:{'X-CSRFToken':csrfToken()},body:JSON.stringify(body)})}

function Progress({step}:{step:string}){
 const steps=[['organization','Organization'],['cloud_account','AWS account'],['validate','Validate'],['sync','Initial sync']]
 const current=Math.max(steps.findIndex(([key])=>key===step),0)
 return <div className="setup-progress">{steps.map(([key,label],index)=><div className={`setup-progress-step ${index<current?'done':''} ${key===step?'current':''}`} key={key}><span>{index<current?'✓':index+1}</span><b>{label}</b></div>)}</div>
}

function PlanSummary({subscription}:{subscription:Subscription|null}){
 const plans=[
  {code:'free',name:'Free',features:['1 AWS account','Inventory','Cost visibility']},
  {code:'pro',name:'Pro',features:['Up to 5 AWS accounts','Budgets & forecasts','Compliance & policies','Recommendations','Remediation simulation']},
  {code:'business',name:'Business',features:['Up to 50 AWS accounts','Everything in Pro','Multi-user access','Live allowlisted remediation']},
 ]
 return <section className="setup-plans"><div className="setup-section-head"><div><p className="eyebrow">SUBSCRIPTION</p><h2>Choose the capability level you need</h2></div><small>Billing provider integration is not active yet; paid tiers are defined and enforced as entitlements.</small></div><div className="plan-grid">{plans.map(plan=><article className={subscription?.plan===plan.code?'current-plan':''} key={plan.code}><div className="plan-name"><h3>{plan.name}</h3>{subscription?.plan===plan.code&&<span>Current</span>}</div><ul>{plan.features.map(feature=><li key={feature}>✓ {feature}</li>)}</ul>{plan.code==='free'?<small>Included</small>:<button disabled>Upgrade billing coming next</button>}</article>)}</div></section>
}

function Onboarding({initial}:{initial:Bootstrap}){
 const[boot,setBoot]=useState(initial);const[error,setError]=useState('');const[busy,setBusy]=useState(false)
 const[organizationName,setOrganizationName]=useState('');const[accountName,setAccountName]=useState('Primary AWS');const[accountId,setAccountId]=useState('');const[roleArn,setRoleArn]=useState('');const[externalId,setExternalId]=useState('')
 const refresh=async()=>{const next=await api<Bootstrap>('/api/account/bootstrap/');setBoot(next);if(!next.onboarding.required)window.location.reload()}
 const run=async(action:()=>Promise<unknown>)=>{setBusy(true);setError('');try{await action();await refresh()}catch(err){setError(err instanceof Error?err.message:'Setup failed.')}finally{setBusy(false)}}
 const account=boot.cloud_accounts[0]
 const step=boot.onboarding.current_step
 return <div className="setup-shell"><header className="setup-topbar"><div><div className="brand dark">finopser</div><span>Guided setup</span></div><button className="ghost-button" onClick={()=>post('/api/auth/logout/').then(()=>window.location.reload())}>Sign out</button></header><main className="setup-main"><div className="setup-intro"><p className="eyebrow">WELCOME TO FINOPSER</p><h1>Finish setting up your cloud command center.</h1><p>We’ll create your organization, connect AWS using AssumeRole, validate access, and run the first inventory and cost sync. Finopser never asks you to store long-lived AWS access keys.</p></div><Progress step={step}/>{error&&<div className="banner danger">{error}</div>}<section className="setup-card"><div className="setup-card-copy">{step==='organization'&&<><p className="eyebrow">STEP 1</p><h2>Create your organization</h2><p>This becomes the ownership boundary for cloud accounts, projects, subscription entitlements, and eventually team members.</p></>}{step==='cloud_account'&&<><p className="eyebrow">STEP 2</p><h2>Connect your first AWS account</h2><p>Enter the AWS account ID and the IAM role Finopser should assume. External ID is optional but recommended where your trust policy uses one.</p></>}{step==='validate'&&<><p className="eyebrow">STEP 3</p><h2>Validate AWS access</h2><p>Finopser will call STS AssumeRole and GetCallerIdentity to confirm the role works before collecting anything.</p></>}{step==='sync'&&<><p className="eyebrow">STEP 4</p><h2>Run the initial sync</h2><p>This collects normalized resource inventory plus current-month Cost Explorer data. Partial provider failures are recorded rather than silently ignored.</p></>}</div><div className="setup-card-action">{step==='organization'&&<form onSubmit={e=>{e.preventDefault();run(()=>post('/api/onboarding/organization/',{name:organizationName}))}}><label>Organization name<input autoFocus value={organizationName} onChange={e=>setOrganizationName(e.target.value)} placeholder="Acme Cloud Operations" required/></label><button className="primary-button" disabled={busy}>{busy?'Creating…':'Create organization'}</button></form>}{step==='cloud_account'&&<form onSubmit={e=>{e.preventDefault();run(()=>post('/api/onboarding/cloud-account/',{name:accountName,provider_account_id:accountId,role_arn:roleArn,external_id:externalId}))}}><label>Account name<input value={accountName} onChange={e=>setAccountName(e.target.value)} required/></label><label>AWS account ID<input inputMode="numeric" pattern="[0-9]{12}" value={accountId} onChange={e=>setAccountId(e.target.value)} placeholder="123456789012" required/></label><label>Role ARN<input value={roleArn} onChange={e=>setRoleArn(e.target.value)} placeholder="arn:aws:iam::123456789012:role/FinopserReadRole" required/></label><label>External ID <small>optional</small><input value={externalId} onChange={e=>setExternalId(e.target.value)}/></label><button className="primary-button" disabled={busy}>{busy?'Connecting…':'Save AWS connection'}</button></form>}{step==='validate'&&account&&<div className="setup-confirm"><dl><div><dt>Account</dt><dd>{account.name}</dd></div><div><dt>AWS account ID</dt><dd>{account.provider_account_id}</dd></div><div><dt>Status</dt><dd>{account.status}</dd></div></dl>{account.last_error&&<div className="banner danger">{account.last_error}</div>}<button className="primary-button" disabled={busy} onClick={()=>run(()=>post(`/api/onboarding/cloud-account/${account.id}/validate/`))}>{busy?'Validating…':'Validate AWS access'}</button></div>}{step==='sync'&&account&&<div className="setup-confirm"><dl><div><dt>Account</dt><dd>{account.name}</dd></div><div><dt>Connection</dt><dd>Validated</dd></div><div><dt>Next</dt><dd>Inventory + current-month costs</dd></div></dl><button className="primary-button" disabled={busy} onClick={()=>run(()=>post(`/api/onboarding/cloud-account/${account.id}/sync/`))}>{busy?'Syncing…':'Run initial sync'}</button></div>}</div></section><PlanSummary subscription={boot.subscription}/></main></div>
}

function applyPlanNavigation(subscription:Subscription|null){
 if(!subscription)return
 const featureByLabel:Record<string,string>={Budgets:'budgets',Compliance:'compliance',Policies:'policies',Recommendations:'recommendations',Automation:'remediation_simulation'}
 document.querySelectorAll<HTMLButtonElement>('aside nav button').forEach(button=>{
  const label=button.childNodes[0]?.textContent?.trim()??''
  const feature=featureByLabel[label]
  if(!feature||subscription.features[feature])return
  button.disabled=true
  button.classList.add('plan-locked')
  button.title=`Upgrade from ${subscription.plan} to unlock ${label}`
  const marker=button.querySelector('span')
  if(marker)marker.textContent='Upgrade'
 })
 const foot=document.querySelector<HTMLElement>('.side-foot')
 if(foot&&!foot.querySelector('.plan-chip')){
  const chip=document.createElement('div')
  chip.className='plan-chip'
  chip.textContent=`${subscription.plan.toUpperCase()} plan`
  foot.prepend(chip)
 }
}

async function start(){
 let session:Session
 let bootstrap:Bootstrap|null=null
 try{session=await api<Session>('/api/auth/session/')}catch{await import('./main');return}
 if(session.authenticated){
  try{
   bootstrap=await api<Bootstrap>('/api/account/bootstrap/')
   if(bootstrap.onboarding.required){ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><Onboarding initial={bootstrap}/></React.StrictMode>);return}
  }catch{/* fall through to the normal console so existing admins remain usable */}
 }
 const wrapped=window.fetch.bind(window)
 window.fetch=async(input:RequestInfo|URL,init?:RequestInit)=>{
  const response=await wrapped(input,init)
  const url=typeof input==='string'?input:input instanceof URL?input.toString():input.url
  if(response.ok&&(url.includes('/api/auth/login/')||url.includes('/api/auth/register/'))){setTimeout(()=>window.location.reload(),0)}
  return response
 }
 await import('./main')
 if(bootstrap)setTimeout(()=>applyPlanNavigation(bootstrap?.subscription??null),0)
}

start()
