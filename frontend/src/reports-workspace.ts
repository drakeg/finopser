import './reports-workspace.css'

type ReportDefinition={code:string;name:string;description:string;format:string;target:string}
type CatalogResponse={reports:ReportDefinition[]}
type Account={id:number;name:string}
type Project={id:number;name:string}
type ListResponse<T>=T[]|{results:T[]}

type FilterConfig={name:string;label:string;type:'text'|'date'|'select';options?:{value:string;label:string}[]}

const endpointByCode:Record<string,string>={
  'resource-inventory':'/api/reports/resource-inventory.csv',
  'cost-detail':'/api/reports/cost-detail.csv',
  'compliance-findings':'/api/reports/compliance-findings.csv',
  'policy-violations':'/api/reports/policy-violations.csv',
  'recommendations':'/api/reports/recommendations.csv',
  'remediation-history':'/api/reports/remediation-history.csv',
  'audit-events':'/api/reports/audit-events.csv',
}

const filtersByCode:Record<string,FilterConfig[]>={
  'resource-inventory':[
    {name:'account',label:'Account',type:'select'},
    {name:'resource_type',label:'Resource type',type:'text'},
    {name:'active',label:'Active state',type:'select',options:[{value:'',label:'All states'},{value:'true',label:'Active only'},{value:'false',label:'Inactive only'}]},
  ],
  'cost-detail':[
    {name:'account',label:'Account',type:'select'},
    {name:'project',label:'Project',type:'select'},
    {name:'service',label:'Service',type:'text'},
    {name:'start_date',label:'Start date',type:'date'},
    {name:'end_date',label:'End date',type:'date'},
  ],
  'compliance-findings':[
    {name:'account',label:'Account',type:'select'},
    {name:'status',label:'Status',type:'select',options:[{value:'',label:'All statuses'},{value:'open',label:'Open'},{value:'excepted',label:'Excepted'},{value:'resolved',label:'Resolved'}]},
    {name:'severity',label:'Severity',type:'select',options:[{value:'',label:'All severities'},{value:'critical',label:'Critical'},{value:'high',label:'High'},{value:'medium',label:'Medium'},{value:'low',label:'Low'}]},
  ],
  'policy-violations':[
    {name:'account',label:'Account',type:'select'},
    {name:'status',label:'Status',type:'select',options:[{value:'',label:'All statuses'},{value:'open',label:'Open'},{value:'resolved',label:'Resolved'}]},
    {name:'severity',label:'Severity',type:'select',options:[{value:'',label:'All severities'},{value:'critical',label:'Critical'},{value:'high',label:'High'},{value:'medium',label:'Medium'},{value:'low',label:'Low'}]},
  ],
  'recommendations':[
    {name:'account',label:'Account',type:'select'},
    {name:'status',label:'Status',type:'select',options:[{value:'',label:'All statuses'},{value:'open',label:'Open'},{value:'dismissed',label:'Dismissed'},{value:'resolved',label:'Resolved'}]},
    {name:'priority',label:'Priority',type:'select',options:[{value:'',label:'All priorities'},{value:'critical',label:'Critical'},{value:'high',label:'High'},{value:'medium',label:'Medium'},{value:'low',label:'Low'}]},
    {name:'category',label:'Category',type:'select',options:[{value:'',label:'All categories'},{value:'cost',label:'Cost'},{value:'governance',label:'Governance'},{value:'operations',label:'Operations'}]},
  ],
  'remediation-history':[
    {name:'account',label:'Account',type:'select'},
    {name:'status',label:'Status',type:'select',options:[{value:'',label:'All statuses'},{value:'requested',label:'Requested'},{value:'previewed',label:'Previewed'},{value:'approved',label:'Approved'},{value:'succeeded',label:'Succeeded'},{value:'failed',label:'Failed'},{value:'stale',label:'Stale'},{value:'rejected',label:'Rejected'}]},
    {name:'simulation',label:'Execution mode',type:'select',options:[{value:'',label:'All modes'},{value:'true',label:'Simulation'},{value:'false',label:'Live'}]},
  ],
  'audit-events':[
    {name:'action',label:'Action',type:'text'},
    {name:'object_type',label:'Object type',type:'text'},
  ],
}

let catalog:ReportDefinition[]=[]
let accounts:Account[]=[]
let projects:Project[]=[]
let selectedCode=''
let mountedSection:HTMLElement|null=null

function listFrom<T>(value:ListResponse<T>):T[]{return Array.isArray(value)?value:value.results??[]}
async function json<T>(url:string):Promise<T>{const response=await fetch(url,{credentials:'include'});if(!response.ok)throw new Error(`${response.status}`);return response.json()}
function escapeHtml(value:string):string{return value.replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]??char))}
function option(value:string,label:string):string{return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`}

function reportsButton():HTMLButtonElement|null{return Array.from(document.querySelectorAll<HTMLButtonElement>('aside nav button')).find(button=>button.childNodes[0]?.textContent?.trim()==='Reports')??null}
function reportPlaceholder():HTMLElement|null{return Array.from(document.querySelectorAll<HTMLElement>('main section.panel')).find(section=>section.querySelector('h2')?.textContent?.trim()==='Reporting workspace')??null}

function setSidebarReady(){const button=reportsButton();const status=button?.querySelector('span');if(status)status.textContent='●'}
function isReportsActive(){return reportsButton()?.classList.contains('active')??false}

async function ensureData(){if(catalog.length)return;const [catalogResult,accountResult,projectResult]=await Promise.all([
  json<CatalogResponse>('/api/reports/'),
  json<ListResponse<Account>>('/api/cloud-accounts/').catch(()=>[] as Account[]),
  json<ListResponse<Project>>('/api/projects/').catch(()=>[] as Project[]),
]);catalog=catalogResult.reports;accounts=listFrom(accountResult);projects=listFrom(projectResult);selectedCode=catalog[0]?.code??''}

function renderFilter(config:FilterConfig):string{
  const base=`class="report-filter" data-report-filter="${escapeHtml(config.name)}"`
  if(config.type==='date')return `<label>${escapeHtml(config.label)}<input ${base} type="date"/></label>`
  if(config.type==='text')return `<label>${escapeHtml(config.label)}<input ${base} type="text" placeholder="Any"/></label>`
  let options=config.options
  if(!options&&config.name==='account')options=[{value:'',label:'All accounts'},...accounts.map(item=>({value:String(item.id),label:item.name}))]
  if(!options&&config.name==='project')options=[{value:'',label:'All projects'},...projects.map(item=>({value:String(item.id),label:item.name}))]
  return `<label>${escapeHtml(config.label)}<select ${base}>${(options??[{value:'',label:'All'}]).map(item=>option(item.value,item.label)).join('')}</select></label>`
}

function renderWorkspace(section:HTMLElement){
  const selected=catalog.find(item=>item.code===selectedCode)??catalog[0]
  if(!selected){section.innerHTML='<h2>Reporting workspace</h2><div class="empty">No reports are available for your current plan.</div>';return}
  const cards=catalog.map(report=>`<button class="report-card ${report.code===selected.code?'selected':''}" data-report-code="${escapeHtml(report.code)}"><span class="report-target">${escapeHtml(report.target)}</span><strong>${escapeHtml(report.name)}</strong><small>${escapeHtml(report.description)}</small><b>CSV export →</b></button>`).join('')
  const filters=(filtersByCode[selected.code]??[]).map(renderFilter).join('')
  section.innerHTML=`<div class="report-heading"><div><p class="eyebrow">PERSISTED EVIDENCE</p><h2>Reporting workspace</h2><p>Export tenant-scoped reports from evidence already stored in Finopser. Available reports reflect your current feature entitlements.</p></div><span class="report-count">${catalog.length} available</span></div><div class="report-layout"><div class="report-catalog">${cards}</div><div class="report-builder"><div class="report-builder-head"><div><span class="report-target">${escapeHtml(selected.target)}</span><h3>${escapeHtml(selected.name)}</h3><p>${escapeHtml(selected.description)}</p></div><span class="report-format">CSV</span></div><div class="report-filters">${filters||'<p class="report-no-filters">No filters are required for this report.</p>'}</div><div class="report-actions"><button class="primary-button" data-report-download>Download CSV</button><button class="ghost-button" data-report-clear>Clear filters</button></div><p class="report-note">Exports are generated synchronously from persisted tenant evidence and capped at 5,000 rows. Generated timestamp, row count, and truncation state are returned with each export. Larger/background report jobs remain a future extension.</p></div></div>`
  section.querySelectorAll<HTMLButtonElement>('[data-report-code]').forEach(button=>button.addEventListener('click',()=>{selectedCode=button.dataset.reportCode??selectedCode;renderWorkspace(section)}))
  section.querySelector<HTMLButtonElement>('[data-report-clear]')?.addEventListener('click',()=>section.querySelectorAll<HTMLInputElement|HTMLSelectElement>('[data-report-filter]').forEach(control=>{control.value=''}))
  section.querySelector<HTMLButtonElement>('[data-report-download]')?.addEventListener('click',()=>downloadSelected(section,selected.code))
}

function downloadSelected(section:HTMLElement,code:string){
  const endpoint=endpointByCode[code]
  if(!endpoint)return
  const params=new URLSearchParams()
  section.querySelectorAll<HTMLInputElement|HTMLSelectElement>('[data-report-filter]').forEach(control=>{const name=control.dataset.reportFilter;if(name&&control.value)params.set(name,control.value)})
  const query=params.toString()
  window.location.assign(query?`${endpoint}?${query}`:endpoint)
}

async function mountReports(){
  setSidebarReady()
  if(!isReportsActive())return
  const section=reportPlaceholder()
  if(!section)return
  if(section===mountedSection&&section.dataset.reportsMounted==='true')return
  mountedSection=section
  section.dataset.reportsMounted='true'
  section.innerHTML='<h2>Reporting workspace</h2><div class="empty">Loading available reports…</div>'
  try{await ensureData();if(isReportsActive()&&section.isConnected)renderWorkspace(section)}catch(error){section.innerHTML=`<h2>Reporting workspace</h2><div class="banner danger">Unable to load report catalog (${escapeHtml(error instanceof Error?error.message:'request failed')}).</div>`}
}

function scheduleMount(){window.setTimeout(()=>{void mountReports()},0)}

document.addEventListener('click',event=>{const target=event.target as HTMLElement|null;if(target?.closest('aside nav button'))scheduleMount()})
new MutationObserver(()=>scheduleMount()).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']})
scheduleMount()
