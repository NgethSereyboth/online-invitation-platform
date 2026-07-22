(function(){
  try{
    var mode=localStorage.getItem('einvite-theme-mode')||'system';
    var dark=mode==='dark'||(mode==='system'&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme=dark?'dark':'light';
    document.documentElement.dataset.themeMode=mode;
    document.documentElement.style.colorScheme=dark?'dark':'light';
  }catch(e){}
})();
