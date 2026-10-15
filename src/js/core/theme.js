(function(){
  try{
    var mode=localStorage.getItem('einvite-theme-mode')||'system';
    var dark=mode==='dark'||(mode==='system'&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme=dark?'dark':'light';
    document.documentElement.dataset.themeMode=mode;
    document.documentElement.style.colorScheme=dark?'dark':'light';
  }catch(e){}
})();

/* Pre-paint language bootstrap: moved out of every page's inline <head> script on
   2026-10-13 because the server's CSP (`script-src 'self'`, no nonce, no hash list — see
   server.py CSP_HEADER) refuses inline blocks, so the correction never ran. It has to stay
   here and stay small: it loads in the <head> of 15 of 16 routes and the route script
   budgets are measured maxima. Rationale and measurements: docs/reviews/C1-2026-10-13.md.
   Behaviour is byte-for-byte the inline block it replaces. */
(function(){try{
  var el=document.documentElement,lang=localStorage.getItem('einvite-lang');
  if(!lang){var nav=navigator.language||(navigator.languages&&navigator.languages[0])||'';lang=nav.toLowerCase().indexOf('km')===0?'km':'en'}
  el.lang=lang;
}catch(e){}})();


// V13 browser security bridge: attach the per-session double-submit CSRF token
// to same-origin mutation requests. Authentication still relies exclusively on
// the HttpOnly session cookie; this readable token is not an authentication token.
(function(){
  if(!window.fetch||window.__einviteSecureFetch)return;
  window.__einviteSecureFetch=true;
  var nativeFetch=window.fetch.bind(window);
  function cookie(name){
    try{return document.cookie.split(';').map(function(v){return v.trim()}).filter(function(v){return v.indexOf(name+'=')===0})[0]?.slice(name.length+1)||''}catch(e){return''}
  }
  window.fetch=function(input,init){
    init=init?Object.assign({},init):{};
    var url=typeof input==='string'?input:(input&&input.url)||'';
    var method=String(init.method||(input&&input.method)||'GET').toUpperCase();
    var same=true;
    try{same=new URL(url||location.href,location.href).origin===location.origin}catch(e){}
    if(same&&!['GET','HEAD','OPTIONS','TRACE'].includes(method)){
      var token=decodeURIComponent(cookie('einvite_csrf')||'');
      if(token){var headers=new Headers(init.headers||(input&&input.headers)||{});if(!headers.has('X-CSRF-Token'))headers.set('X-CSRF-Token',token);init.headers=headers}
      if(!init.credentials)init.credentials='same-origin';
    }
    return nativeFetch(input,init);
  };
})();
