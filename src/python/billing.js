const $=selector=>document.querySelector(selector);
localStorage.removeItem('sovan-auth-token');
const _isKm=()=>(window.EInviteI18n&&window.EInviteI18n.get?window.EInviteI18n.get():(document.documentElement.lang||'').toLowerCase()).startsWith('km');
const _txt=(en,km)=>_isKm()?(km!=null?km:en):en;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const b=(en,km)=>`<span class="i18n i18n-en">${esc(en)}</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">${esc(km!=null?km:en)}</span>`;

const plans={
  free:{name:'Free',invitations:3,templates:5,storageBytes:250_000_000,features:['Create and publish invitations','Basic templates and editor','RSVP and guest tools','250 MB material storage']},
  creator:{name:'Creator',invitations:50,templates:100,storageBytes:5_000_000_000,features:['Higher invitation capacity','Large reusable template library','5 GB material storage','Designed for frequent creators']},
  studio:{name:'Studio',invitations:500,templates:1000,storageBytes:50_000_000_000,features:['High-volume invitation production','Designer and studio workflows','50 GB material storage','Best fit for professional teams']}
};

async function api(path,options={}){
  const response=await fetch(path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})}});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(data.error||'Request failed');
  return data;
}
const fmtBytes=value=>{const n=Number(value||0);if(n<1e6)return `${(n/1e3).toFixed(n<1e5?1:0)} KB`;if(n<1e9)return `${(n/1e6).toFixed(n<1e8?1:0)} MB`;return `${(n/1e9).toFixed(1)} GB`};
const fmtPrice=(minor,currency)=>new Intl.NumberFormat(undefined,{style:'currency',currency,minimumFractionDigits:currency==='KHR'?0:2}).format(Number(minor||0)/(currency==='KHR'?1:100));
const meter=(value,limit)=>{const percent=limit?Math.min(100,Math.round(value/limit*100)):0;return `<div class="meter"><i style="width:${percent}%"></i></div><small>${percent}% ${_txt('used','បានប្រើ')}</small>`};

function checkoutBanner(){
  const state=new URLSearchParams(location.search).get('checkout');
  if(!state)return;
  const banner=$('#checkoutResult');banner.hidden=false;
  if(state==='success'){
    banner.className='checkout-result verifying';
    banner.innerHTML=`<strong>${b('Payment submitted','ការទូទាត់ត្រូវបានបញ្ជូនរួចរាល់')}</strong><span>${b('We are securely confirming your card payment. Your plan will update as soon as the payment is confirmed.','We are securely confirming your card payment. Your plan will update as soon as the payment is confirmed.')}</span>`;
  }else{
    banner.className='checkout-result cancelled';
    banner.innerHTML=`<strong>${b('Checkout cancelled','Checkout ត្រូវបានបោះបង់')}</strong><span>${b('Your card was not charged by this website and your current plan has not changed.','ប័ណ្ណរបស់អ្នកមិនត្រូវគេទូទាត់ដោយគេហទំព័រនេះទេ ហើយកញ្ចប់បច្ចុប្បន្នរបស់អ្នកមិនបានផ្លាស់ប្តូរទេ។')}</span>`;
  }
}

async function init(){
  if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;
  if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){
    window.EInviteBackend.message(document.querySelector('main')||document.body,'<span class="i18n i18n-en">Billing, plan usage and card checkout require the full application server.</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">Billing, plan usage and card checkout require the full application server.</span>');
    return;
  }
  try{
    checkoutBanner();
    const [me,usage,billing]=await Promise.all([api('/api/auth/me'),api('/api/account/usage'),api('/api/billing/status')]);
    if(!me.user)throw Error('Sign in required');
    const current=usage.plan||me.user.plan||'free';
    $('#currentPlan').textContent=plans[current]?.name||current;
    $('#planRole').textContent=`${me.user.role||'customer'} ${_txt('account','គណនី')}`;
    const u=usage.usage,l=usage.limits;
    $('#usageGrid').innerHTML=`<article class="usage-card"><small>${b('Invitations','ការអញ្ជើញ')}</small><strong>${u.invitations} / ${l.invitations}</strong>${meter(u.invitations,l.invitations)}</article><article class="usage-card"><small>${b('Reusable templates','ពុម្ពអត្ថបទប្រើឡើងវិញបាន')}</small><strong>${u.templates} / ${l.templates}</strong>${meter(u.templates,l.templates)}</article><article class="usage-card"><small>${b('Material storage','កន្លែងរក្សាទុកសម្ភារៈ')}</small><strong>${fmtBytes(u.storageBytes)} / ${fmtBytes(l.storageBytes)}</strong>${meter(u.storageBytes,l.storageBytes)}</article>`;
    $('#gatewayName').textContent=billing.provider||_txt('Secure card checkout','Checkout ដោយប័ណ្ណដោយសុវត្ថិភាព');
    $('#gatewayState').textContent=billing.configured?_txt('Card checkout is connected','Checkout តាមប័ណ្ណត្រូវបានភ្ជាប់រួចរាល់'):_txt('Gateway credentials still need to be configured','គ្រឿងបញ្ជាក់គ្រឹះស្ថានទូទាត់នៅត្រូវការកំណត់រចនាសម្ព័ន្ធថែមទៀត');
    $('#gatewayState').className=billing.configured?'gateway-ready':'gateway-pending';
    $('#planCards').innerHTML=Object.entries(plans).map(([key,plan])=>{
      const isCurrent=key===current;
      const price=key==='free'?_txt('No card required','មិនត្រូវការប័ណ្ណទេ'):fmtPrice(billing.prices?.[key],billing.currency||'USD');
      const action=isCurrent?`<button disabled>${b('Current plan','កញ្ចប់បច្ចុប្បន្ន')}</button>`:key==='free'?'<button disabled>'+b('Included','រួមបញ្ចូលគ្នា')+'</button>':`<button class="card-checkout" type="button" data-plan="${key}" ${billing.configured?'':'disabled'}><span>${b('Pay securely by card','ទូទាត់តាមប័ណ្ណដោយសុវត្ថិភាព')}</span><small>${b('Visa · Mastercard','Visa · Mastercard')}</small></button>`;
      return `<article class="plan ${isCurrent?'current':''}"><span class="badge">${isCurrent?b('Current plan','កញ្ចប់បច្ចុប្បន្ន'):b('Available tier','កម្រិតដែលអាចរើសបាន')}</span><h2>${plan.name}</h2><div class="plan-price">${price}${key==='free'?'':` <small>${b('per billing period','ក្នុងមួយរយៈពេលទូទាត់')}</small>`}</div><p>${plan.invitations} ${_txt('active invitations','ការអញ្ជើញសកម្ម')} · ${plan.templates} ${_txt('templates','ពុម្ពអត្ថបទ')} · ${fmtBytes(plan.storageBytes)} ${_txt('storage','កន្លែងរក្សាទុក')}</p><ul>${plan.features.map(feature=>`<li>${b(feature,feature)}</li>`).join('')}</ul>${action}</article>`;
    }).join('');
    document.querySelectorAll('[data-plan]').forEach(button=>button.onclick=async()=>{
      button.disabled=true;const previous=button.innerHTML;button.textContent=_txt('Opening secure checkout…','កំពុងបើក checkout ដោយសុវត្ថិភាព…');
      try{const result=await api('/api/billing/checkout',{method:'POST',body:JSON.stringify({plan:button.dataset.plan})});location.assign(result.url)}
      catch(error){window.uiAlert?(uiAlert(error.message,{title:_txt('Checkout unavailable','Checkout មិនអាចប្រើបាន')})):alert(error.message)}
      finally{button.disabled=false;button.innerHTML=previous}
    });
    $('#billingNotice').textContent=billing.configured
      ?_txt('Payments are completed on the gateway’s hosted checkout. This website does not receive or store your full card number or security code.','ការទូទាត់ត្រូវបានបញ្ចប់នៅលើ hosted checkout របស់គ្រឹះស្ថានទូទាត់។ គេហទំព័រនេះមិនទទួលឬរក្សាទុកលេខប័ណ្ណរបស់អ្នកឬកូដសុវត្ថិភាពទេ។')
      :_txt('Online card payment is not available yet.','Online card payment is not available yet.');
  }catch(error){
    document.querySelector('.billing-page').innerHTML=`<h1>${b('Plans unavailable','កញ្ចប់មិនអាចប្រើបាន')}</h1><p>${esc(error.message)}</p><a href="dashboard.html" class="button-link">${b('Back to dashboard','ត្រឡប់ទៅផ្ទាំងគ្រប់គ្រង')}</a>`;
  }
}
function render(){checkoutBanner()}
if(window.EInviteI18n&&typeof window.EInviteI18n.subscribe==='function'){window.EInviteI18n.subscribe(render)}
init();
