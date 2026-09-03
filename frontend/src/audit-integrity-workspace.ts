import './audit-integrity-workspace.css'

type IntegrityStatus={status:'unverified'|'valid'|'invalid';valid:boolean|null;algorithm:string;checkpoint_event_id:number|null;through_event_id:number|null;event_count:number;unchecked_event_count:number}

let mountedSection:HTMLElement|null=null

function csrfToken(){return document.cookie.split('; ').find(value=>value.startsWith('csrftoken='))?.split('=')[1]??''}
async function request<T>(method:'GET'|'POST'):Promise<T>{const response=await fetch('/api/audit-integrity/',{method,credentials:'include',headers:method==='POST'?{'Content-Type':'application/json','X-CSRFToken':csrfToken()}:undefined,body:method==='POST'?'{}':undefined});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail??`${response.status}`);return data}
function escapeHtml(value:string):string{return value.replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]??char))}

function administrationButton():HTMLButtonElement|null{return Array.from(document.querySelectorAll<HTMLButtonElement>('aside nav button')).find(button=>button.childNodes[0]?.textContent?.trim()==='Administration')??null}
function isAdministrationActive(){return administrationButton()?.classList.contains('active')??false}
function administrationGrid():HTMLElement|null{return Array.from(document.querySelectorAll<HTMLElement>('main section.grid')).find(section=>Array.from(section.querySelectorAll('article.panel h2')).some(heading=>heading.textContent?.trim()==='Recent audit activity'))??null}

function statusCopy(status:IntegrityStatus):{title:string;detail:string;className:string}{
 if(status.status==='valid')return{title:'Integrity verified',detail:status.unchecked_event_count?`${status.event_count} events are covered by the latest checkpoint; ${status.unchecked_event_count} newer event${status.unchecked_event_count===1?' is':'s are'} not yet checkpointed.`:`${status.event_count} events are covered and no newer audit events remain unchecked.`,className:'valid'}
 if(status.status==='invalid')return{title:'Integrity check failed',detail:'Stored audit evidence covered by the latest checkpoint no longer matches its recorded SHA-256 digest or event count.',className:'invalid'}
 return{title:'No integrity checkpoint yet',detail:`${status.unchecked_event_count} audit event${status.unchecked_event_count===1?' is':'s are'} currently unverified. Create a checkpoint to establish the first integrity baseline.`,className:'unverified'}
}

function renderCard(article:HTMLElement,status:IntegrityStatus){const copy=statusCopy(status);article.innerHTML=`<div class="integrity-head"><div><p class="eyebrow">AUDIT EVIDENCE</p><h2>Integrity status</h2></div><span class="integrity-state ${copy.className}">${escapeHtml(copy.title)}</span></div><p class="integrity-detail">${escapeHtml(copy.detail)}</p><div class="integrity-metrics"><div><small>Algorithm</small><strong>${escapeHtml(status.algorithm.toUpperCase())}</strong></div><div><small>Covered events</small><strong>${status.event_count}</strong></div><div><small>Unchecked newer</small><strong>${status.unchecked_event_count}</strong></div><div><small>Checkpoint event</small><strong>${status.checkpoint_event_id??'—'}</strong></div></div><div class="integrity-actions"><button class="primary-button" data-integrity-checkpoint>Create checkpoint</button><button class="ghost-button" data-integrity-refresh>Verify again</button></div><p class="integrity-note">Checkpoints are application-level tamper evidence over tenant-scoped audit rows. They do not replace independently anchored WORM or external SIEM storage.</p>`
 article.querySelector<HTMLButtonElement>('[data-integrity-refresh]')?.addEventListener('click',()=>void refresh(article))
 article.querySelector<HTMLButtonElement>('[data-integrity-checkpoint]')?.addEventListener('click',()=>void createCheckpoint(article))
}

async function refresh(article:HTMLElement){try{const status=await request<IntegrityStatus>('GET');if(article.isConnected&&isAdministrationActive())renderCard(article,status)}catch(error){article.innerHTML=`<h2>Integrity status</h2><div class="banner danger">Unable to verify audit integrity (${escapeHtml(error instanceof Error?error.message:'request failed')}).</div>`}}
async function createCheckpoint(article:HTMLElement){const button=article.querySelector<HTMLButtonElement>('[data-integrity-checkpoint]');if(button){button.disabled=true;button.textContent='Creating…'}try{await request<unknown>('POST');await refresh(article)}catch(error){const message=document.createElement('div');message.className='banner danger';message.textContent=`Unable to create checkpoint (${error instanceof Error?error.message:'request failed'}).`;article.appendChild(message);if(button){button.disabled=false;button.textContent='Create checkpoint'}}}

function mount(){if(!isAdministrationActive())return;const grid=administrationGrid();if(!grid)return;let article=grid.querySelector<HTMLElement>('[data-audit-integrity]');if(!article){article=document.createElement('article');article.className='panel integrity-panel';article.dataset.auditIntegrity='true';grid.prepend(article)}if(article===mountedSection&&article.dataset.integrityMounted==='true')return;mountedSection=article;article.dataset.integrityMounted='true';article.innerHTML='<h2>Integrity status</h2><div class="empty">Verifying audit evidence…</div>';void refresh(article)}
function schedule(){window.setTimeout(mount,0)}

document.addEventListener('click',event=>{const target=event.target as HTMLElement|null;if(target?.closest('aside nav button'))schedule()})
new MutationObserver(()=>schedule()).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']})
schedule()
