import './api-token-workspace.css'

type ApiCredential={id:number;name:string;token_prefix:string;scopes:string[];expires_at:string|null;is_active:boolean;last_used_at:string|null;created_at:string;revoked_at:string|null;created_by:string}
type IssuedApiCredential=ApiCredential&{token:string;token_notice:string}
type ApiError={detail?:string}

const scopeOptions=[
 ['accounts:read','Accounts'],
 ['dashboard:read','Dashboard'],
 ['resources:read','Resources'],
 ['costs:read','Costs'],
 ['compliance:read','Compliance'],
 ['policies:read','Policies'],
 ['recommendations:read','Recommendations'],
 ['reports:read','Reports'],
] as const

let mountedSection:HTMLElement|null=null
let currentSecret=''
let currentSecretNotice=''

function csrfToken(){return document.cookie.split('; ').find(value=>value.startsWith('csrftoken='))?.split('=')[1]??''}
function escapeHtml(value:string):string{return value.replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]??char))}
function when(value:string|null){return value?new Date(value).toLocaleString():'Never'}
function isExpired(token:ApiCredential){return Boolean(token.expires_at&&new Date(token.expires_at).getTime()<=Date.now())}
function tokenState(token:ApiCredential){if(!token.is_active)return 'Revoked';if(isExpired(token))return 'Expired';return 'Active'}
function tokenStateClass(token:ApiCredential){return tokenState(token).toLowerCase()}
async function request<T>(url:string,options:RequestInit={}):Promise<T>{const headers=new Headers(options.headers);if(options.method==='POST'){headers.set('Content-Type','application/json');headers.set('X-CSRFToken',csrfToken())}const response=await fetch(url,{credentials:'include',...options,headers});const data=await response.json().catch(()=>({})) as T&ApiError;if(!response.ok)throw new Error(data.detail??`${response.status}`);return data}

function administrationButton():HTMLButtonElement|null{return Array.from(document.querySelectorAll<HTMLButtonElement>('aside nav button')).find(button=>button.childNodes[0]?.textContent?.trim()==='Administration')??null}
function isAdministrationActive(){return administrationButton()?.classList.contains('active')??false}
function administrationMain():HTMLElement|null{return document.querySelector('main')}
function clearTransientSecret(){currentSecret='';currentSecretNotice=''}

function scopeBadges(scopes:string[]):string{return scopes.map(scope=>`<span class="api-token-scope">${escapeHtml(scope)}</span>`).join('')}
function tokenRows(tokens:ApiCredential[]):string{return tokens.map(token=>`<tr><td><b>${escapeHtml(token.name)}</b><small>finopser_${escapeHtml(token.token_prefix)}_…</small></td><td><span class="api-token-state ${tokenStateClass(token)}">${tokenState(token)}</span></td><td><div class="api-token-scopes">${scopeBadges(token.scopes)}</div></td><td>${token.expires_at?escapeHtml(when(token.expires_at)):'Never'}</td><td>${escapeHtml(token.created_by)}</td><td>${escapeHtml(when(token.last_used_at))}</td><td><div class="api-token-actions">${token.is_active?`<button class="ghost-button compact" data-token-rotate="${token.id}">Rotate</button><button class="ghost-button compact" data-token-revoke="${token.id}">Revoke</button>`:'—'}</div></td></tr>`).join('')}
function scopeCheckboxes():string{return scopeOptions.map(([value,label],index)=>`<label class="api-token-scope-option"><input type="checkbox" name="scopes" value="${value}" ${index===0?'checked':''}/><span>${label}</span><small>${value}</small></label>`).join('')}

function render(article:HTMLElement,tokens:ApiCredential[]){article.innerHTML=`<div class="api-token-head"><div><p class="eyebrow">INTEGRATIONS</p><h2>API tokens</h2></div><span class="api-token-count">${tokens.filter(token=>token.is_active&&!isExpired(token)).length} active</span></div><p class="api-token-intro">Issue least-privilege read-only Bearer tokens for CLI and automation access. Token secrets are shown once and never stored in plaintext.</p><form class="api-token-form" data-token-form><label class="api-token-name">Token name<input name="name" type="text" maxlength="120" placeholder="Example: reporting-cli" required/></label><label class="api-token-expiration">Expires (optional)<input name="expires_at" type="datetime-local"/></label><fieldset class="api-token-scope-fieldset"><legend>Read scopes</legend><div class="api-token-scope-grid">${scopeCheckboxes()}</div></fieldset><button class="primary-button" type="submit">Issue token</button></form><div data-token-secret></div>${tokens.length?`<div class="table-wrap api-token-table"><table><thead><tr><th>Name</th><th>State</th><th>Scopes</th><th>Expires</th><th>Created by</th><th>Last used</th><th></th></tr></thead><tbody>${tokenRows(tokens)}</tbody></table></div>`:'<div class="empty">No API tokens have been issued for this workspace.</div>'}<p class="api-token-note">Bearer tokens remain limited to approved read-only API endpoints. Rotation invalidates the previous secret immediately; revocation takes effect immediately.</p>`
 const form=article.querySelector<HTMLFormElement>('[data-token-form]');form?.addEventListener('submit',event=>{event.preventDefault();void issue(article,form)})
 article.querySelectorAll<HTMLButtonElement>('[data-token-rotate]').forEach(button=>button.addEventListener('click',()=>void rotate(article,Number(button.dataset.tokenRotate))))
 article.querySelectorAll<HTMLButtonElement>('[data-token-revoke]').forEach(button=>button.addEventListener('click',()=>void revoke(article,Number(button.dataset.tokenRevoke))))
 if(currentSecret)showSecret(article,currentSecret,currentSecretNotice)
}

function showSecret(article:HTMLElement,token:string,notice:string){const target=article.querySelector<HTMLElement>('[data-token-secret]');if(!target)return;target.innerHTML=`<div class="api-token-secret"><div><strong>Copy this token now</strong><p>${escapeHtml(notice||'Finopser will not display it again after this page state is cleared.')}</p></div><code>${escapeHtml(token)}</code><button class="ghost-button compact" data-copy-token>Copy</button><button class="link-button" data-dismiss-token>Dismiss</button></div>`;target.querySelector<HTMLButtonElement>('[data-copy-token]')?.addEventListener('click',async event=>{const button=event.currentTarget as HTMLButtonElement;try{await navigator.clipboard.writeText(token);button.textContent='Copied'}catch{button.textContent='Copy failed'}});target.querySelector<HTMLButtonElement>('[data-dismiss-token]')?.addEventListener('click',()=>{clearTransientSecret();target.replaceChildren()})}

async function load(article:HTMLElement){try{const tokens=await request<ApiCredential[]>('/api/integrations/tokens/');if(article.isConnected&&isAdministrationActive())render(article,tokens)}catch(error){const message=error instanceof Error?error.message:'request failed';if(message==='Manager access is required.'){article.innerHTML='<div class="api-token-head"><div><p class="eyebrow">INTEGRATIONS</p><h2>API tokens</h2></div></div><div class="empty">API token administration is available to workspace owners and administrators.</div>';return}article.innerHTML=`<div class="api-token-head"><div><p class="eyebrow">INTEGRATIONS</p><h2>API tokens</h2></div></div><div class="banner danger">Unable to load API tokens (${escapeHtml(message)}).</div>`}}
async function issue(article:HTMLElement,form:HTMLFormElement){const input=form.elements.namedItem('name') as HTMLInputElement|null;const name=input?.value.trim()??'';if(!name)return;const scopes=Array.from(form.querySelectorAll<HTMLInputElement>('input[name="scopes"]:checked')).map(input=>input.value);if(!scopes.length){window.alert('Select at least one read scope.');return}const expirationInput=form.elements.namedItem('expires_at') as HTMLInputElement|null;const expiresAt=expirationInput?.value?new Date(expirationInput.value).toISOString():null;const button=form.querySelector<HTMLButtonElement>('button[type="submit"]');if(button){button.disabled=true;button.textContent='Issuing…'}try{const issued=await request<IssuedApiCredential>('/api/integrations/tokens/',{method:'POST',body:JSON.stringify({name,scopes,expires_at:expiresAt})});currentSecret=issued.token;currentSecretNotice=issued.token_notice;await load(article)}catch(error){const banner=document.createElement('div');banner.className='banner danger';banner.textContent=`Unable to issue token (${error instanceof Error?error.message:'request failed'}).`;form.after(banner);if(button){button.disabled=false;button.textContent='Issue token'}}}
async function rotate(article:HTMLElement,id:number){if(!window.confirm('Rotate this API token? The current secret will stop working immediately.'))return;try{const issued=await request<IssuedApiCredential>(`/api/integrations/tokens/${id}/rotate/`,{method:'POST',body:'{}'});currentSecret=issued.token;currentSecretNotice=issued.token_notice;await load(article)}catch(error){const banner=document.createElement('div');banner.className='banner danger';banner.textContent=`Unable to rotate token (${error instanceof Error?error.message:'request failed'}).`;article.prepend(banner)}}
async function revoke(article:HTMLElement,id:number){if(!window.confirm('Revoke this API token? Any automation using it will immediately lose access.'))return;try{await request(`/api/integrations/tokens/${id}/revoke/`,{method:'POST',body:'{}'});await load(article)}catch(error){const banner=document.createElement('div');banner.className='banner danger';banner.textContent=`Unable to revoke token (${error instanceof Error?error.message:'request failed'}).`;article.prepend(banner)}}

function mount(){if(!isAdministrationActive()){clearTransientSecret();mountedSection=null;return}const main=administrationMain();if(!main)return;let article=main.querySelector<HTMLElement>('[data-api-token-workspace]');if(!article){article=document.createElement('section');article.className='panel api-token-panel';article.dataset.apiTokenWorkspace='true';main.appendChild(article)}if(article===mountedSection&&article.dataset.apiTokenMounted==='true')return;mountedSection=article;article.dataset.apiTokenMounted='true';article.innerHTML='<h2>API tokens</h2><div class="empty">Loading integration credentials…</div>';void load(article)}
function schedule(){window.setTimeout(mount,0)}

document.addEventListener('click',event=>{const target=event.target as HTMLElement|null;if(target?.closest('aside nav button'))schedule()})
new MutationObserver(()=>schedule()).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']})
schedule()
