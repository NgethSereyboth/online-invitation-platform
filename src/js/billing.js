const $=selector=>document.querySelector(selector);
localStorage.removeItem('sovan-auth-token');

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
const meter=(value,limit)=>{const percent=limit?Math.min(100,Math.round(value/limit*100)):0;return `<div class="meter"><i style="width:${percent}%"></i></div><small>${percent}% used</small>`};

function checkoutBanner(){
  const state=new URLSearchParams(location.search).get('checkout');
  if(!state)return;
  const banner=$('#checkoutResult');banner.hidden=false;
  if(state==='success'){
    banner.className='checkout-result verifying';
    banner.innerHTML='<strong>Payment submitted</strong><span>We are securely confirming the card payment. Your plan activates only after the gateway webhook is verified.</span>';
  }else{
    banner.className='checkout-result cancelled';
    banner.innerHTML='<strong>Checkout cancelled</strong><span>Your card was not charged by this website and your current plan has not changed.</span>';
  }
}

async function init(){
  try{
    checkoutBanner();
    const [me,usage,billing]=await Promise.all([api('/api/auth/me'),api('/api/account/usage'),api('/api/billing/status')]);
    if(!me.user)throw Error('Sign in required');
    const current=usage.plan||me.user.plan||'free';
    $('#currentPlan').textContent=plans[current]?.name||current;
    $('#planRole').textContent=`${me.user.role||'customer'} account`;
    const u=usage.usage,l=usage.limits;
    $('#usageGrid').innerHTML=`<article class="usage-card"><small>Invitations</small><strong>${u.invitations} / ${l.invitations}</strong>${meter(u.invitations,l.invitations)}</article><article class="usage-card"><small>Reusable templates</small><strong>${u.templates} / ${l.templates}</strong>${meter(u.templates,l.templates)}</article><article class="usage-card"><small>Material storage</small><strong>${fmtBytes(u.storageBytes)} / ${fmtBytes(l.storageBytes)}</strong>${meter(u.storageBytes,l.storageBytes)}</article>`;
    $('#gatewayName').textContent=billing.provider||'Secure card checkout';
    $('#gatewayState').textContent=billing.configured?'Card checkout is connected':'Gateway credentials still need to be configured';
    $('#gatewayState').className=billing.configured?'gateway-ready':'gateway-pending';
    $('#planCards').innerHTML=Object.entries(plans).map(([key,plan])=>{
      const isCurrent=key===current;
      const price=key==='free'?'No card required':fmtPrice(billing.prices?.[key],billing.currency||'USD');
      const action=isCurrent?'<button disabled>Current plan</button>':key==='free'?'<button disabled>Included</button>':`<button class="card-checkout" type="button" data-plan="${key}" ${billing.configured?'':'disabled'}><span>Pay securely by card</span><small>Visa · Mastercard</small></button>`;
      return `<article class="plan ${isCurrent?'current':''}"><span class="badge">${isCurrent?'Current plan':'Available tier'}</span><h2>${plan.name}</h2><div class="plan-price">${price}${key==='free'?'':' <small>per billing period</small>'}</div><p>${plan.invitations} active invitations · ${plan.templates} templates · ${fmtBytes(plan.storageBytes)} storage</p><ul>${plan.features.map(feature=>`<li>${feature}</li>`).join('')}</ul>${action}</article>`;
    }).join('');
    document.querySelectorAll('[data-plan]').forEach(button=>button.onclick=async()=>{
      button.disabled=true;const previous=button.innerHTML;button.textContent='Opening secure checkout…';
      try{const result=await api('/api/billing/checkout',{method:'POST',body:JSON.stringify({plan:button.dataset.plan})});location.assign(result.url)}
      catch(error){uiAlert(error.message,{title:'Checkout unavailable'})}
      finally{button.disabled=false;button.innerHTML=previous}
    });
    $('#billingNotice').textContent=billing.configured
      ?'Payments are completed on the gateway’s hosted checkout. This website does not receive or store your full card number or security code.'
      :'Card checkout is designed and ready, but it stays disabled until the owner adds production gateway credentials and a webhook secret.';
  }catch(error){
    document.querySelector('.billing-page').innerHTML=`<h1>Plans unavailable</h1><p>${String(error.message)}</p><a href="dashboard.html" class="button-link">Back to dashboard</a>`;
  }
}
init();
