import './api-token-workspace.css'

type ApiCredential={id:number;name:string;token_prefix:string;is_active:boolean;last_used_at:string|null;created_at:string;revoked_at:string|null;created_by:string}
type IssuedApiCredential=ApiCredential&{token:string;token_notice:string}
type ApiError={detail?:string}

let mountedSection:HTMLElement|null=null
let currentSecret=''

function csrfToken(){return document.cookie.split('; ').find(value=>value.startsWith('csrftoken='))?.split('=')[1]??''}
function escapeHtml(value:string):string{return value.replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]??char))}
function when(value:string|null){return value?new Date(value).toLocaleString():'Never'}
async function request<T>(url:string,options:RequestInit={}):Promise<T>{const headers=new Headers(options.headers);if(options.method==='POST'){headers.set('Content-Type','application/json');headers.set('X-CSRFToken',csrfToken())}const response=await fetch(url,{credentials:'include',...options,headers});const data=await response.json().catch(()=>({})) as T&ApiError;if(!response.ok)throw new Error(data.detail??`${response.status}`);return data}

function administrationButton():HTMLButtonElement|null{return Array.from(document.querySelectorAll<HTMLButtonElement>('aside nav button')).find(button=>button.childNodes[0]?.textContent?.trim()==='Administration')??null}
function isAdministrationActive(){return administrationButton()?.classList.contains('active')??false}
function administrationMain():HTMLElement|null{return document.querySelector('main')}

function tokenRows(tokens:ApiCredential[]):string{return tokens.map(token=>`<tr><td><b>${escapeHtml(token.name)}</b><small>finopser_${escapeHtml(token.token_prefix)}_…</small></td><td><span class="api-token-state ${token.is_active?'active':'revoked'}">${token.is_active?'Active':'Revoked'}</span></td><td>${escapeHtml(token.created_by)}</td><td>${escapeHtml(when(token.created_at))}</td><td>${escapeHtml(when(token.last_used_at))}</td><td>${token.revoked_at?escapeHtml(when(token.revoked_at)):'—'}</td><td>${token.is_active?`<button class="ghost-button compact" data-token-revoke="${token.id}">Revoke</button>`:'—'}</td></tr>`).join('')}

function render(article:HTMLElement,tokens:ApiCredential[]){article.innerHTML=`<div class="api-token-head"><div><p class="eyebrow">INTEGRATIONS</p><h2>API tokens</h2></div><span class="api-token-count">${tokens.filter(token=>token.is_active).length} active</span></div><p class="api-token-intro">Issue read-only Bearer tokens for CLI and automation access. Token secrets are shown once and never stored in plaintext.</p><form class="api-token-form" data-token-form><label>Token name<input name="name" maxlength="120" placeholder="Example: reporting-cli" required/></label><button class="primary-button" type="submit">Issue token</button></form><div data-token-secret></div>${tokens.length?`<div class="table-wrap api-token-table"><table><thead><tr><th>Name</th><th>State</th><th>Created by</th><th>Created</th><th>Last used</th><th>Revoked</th><th></th></tr></thead><tbody>${tokenRows(tokens)}</tbody></table></div>`:'<div class="empty">No API tokens have been issued for this workspace.</div>'}<p class="api-token-note">Bearer tokens are currently limited to approved read-only API endpoints. Revocation takes effect immediately.</p>`
 const form=article.querySelector<HTMLFormElement>('[data-token-form]');form?.addEventListener('submit',event=>{event.preventDefault();void issue(article,form)})
 article.querySelectorAll<HTMLButtonElement>('[data-token-revoke]').forEach(button=>button.addEventListener('click',()=>void revoke(article,Number(button.dataset.tokenRevoke))))
 if(currentSecret)showSecret(article,currentSecret)
}

function showSecret(article:HTMLElement,token:string){const target=article.querySelector<HTMLElement>('[data-token-secret]');if(!target)return;target.innerHTML=`<div class="api-token-secret"><div><strong>Copy this token now</strong><p>Finopser will not display it again after this page state is cleared.</p></div><code>${escapeHtml(token)}</code><button class="ghost-button compact" data-copy-token>Copy</button><button class="link-button" data-dismiss-token>Dismiss</button></div>`;target.querySelector<HTMLButtonElement>('[data-copy-token]')?.addEventListener('click',async event=>{const button=event.currentTarget as HTMLButtonElement;try{await navigator.clipboard.writeText(token);button.textContent='Copied'}catch{button.textContent='Copy failed'}});target.querySelector<HTMLButtonElement>('[data-dismiss-token]')?.addEventListener('click',()=>{currentSecret='';target.replaceChildren()})}

async function load(article:HTMLElement){try{const tokens=await request<ApiCredential[]>('/api/integrations/tokens/');if(article.isConnected&&isAdministrationActive())render(article,tokens)}catch(error){const message=error instanceof Error?error.message:'request failed';if(message==='Manager access is required.'){article.innerHTML='<div class="api-token-head"><div><p class="eyebrow">INTEGRATIONS</p><h2>API tokens</h2></div></div><div class="empty">API token administration is available to workspace owners and administrators.</div>';return}article.innerHTML=`<div class="api-token-head"><div><p class="eyebrow">INTEGRATIONS</p><h2>API tokens</h2></div></div><div class="banner danger">Unable to load API tokens (${escapeHtml(message)}).</div>`}}
async function issue(article:HTMLElement,form:HTMLFormElement){const input=form.elements.namedItem('name') as HTMLInputElement|null;const name=input?.value.trim()??'';if(!name)return;const button=form.querySelector<HTMLButtonElement>('button[type="submit"]');if(button){button.disabled=true;button.textContent='Issuing…'}try{const issued=await request<IssuedApiCredential>('/api/integrations/tokens/',{method:'POST',body:JSON.stringify({name})});currentSecret=issued.token;await load(article)}catch(error){const banner=document.createElement('div');banner.className='banner danger';banner.textContent=`Unable to issue token (${error instanceof Error?error.message:'request failed'}).`;form.after(banner);if(button){button.disabled=false;button.textContent='Issue token'}}}
async function revoke(article:HTMLElement,id:number){if(!window.confirm('Revoke this API token? Any automation using it will immediately lose access.'))return;try{await request(`/api/integrations/tokens/${id}/revoke/`,{method:'POST',body:'{}'});await load(article)}catch(error){const banner=document.createElement('div');banner.className='banner danger';banner.textContent=`Unable to revoke token (${error instanceof Error?error.message:'request failed'}).`;article.prepend(banner)}}

function mount(){if(!isAdministrationActive())return;const main=administrationMain();if(!main)return;let article=main.querySelector<HTMLElement>('[data-api-token-workspace]');if(!article){article=document.createElement('section');article.className='panel api-token-panel';article.dataset.apiTokenWorkspace='true';main.appendChild(article)}if(article===mountedSection&&article.dataset.apiTokenMounted==='true')return;mountedSection=article;article.dataset.apiTokenMounted='true';article.innerHTML='<h2>API tokens</h2><div class="empty">Loading integration credentials…</div>';void load(article)}
function schedule(){window.setTimeout(mount,0)}

document.addEventListener('click',event=>{const target=event.target as HTMLElement|null;if(target?.closest('aside nav button'))schedule()})
new MutationObserver(()=>schedule()).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']})
schedule()
