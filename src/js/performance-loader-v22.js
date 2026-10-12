(()=>{let p,a='performance-observability-v22.js,interaction-scheduler-v22.js,incremental-scene-renderer-v22.js,render-worker-bridge-v22.js,professional-workflow-v23.js,navigation-history-v23.js,style-history-v23.js,asset-workflow-v23.js,photo-workflow-v23.js,photo-style-library-v23.js,review-v23.js,direct-manipulation-v24.js,content-browser-v24.js,smart-layout-v24.js,brand-components-v24.js,collaboration-v24.js,export-quality-v24.js,adaptive-templates-v25.js,studio-governance-v25.js,print-readiness-v25.js,template-bindings-v25.js,studio-operations-v26.js,studio-automation-v27.js'.split(',');
/* Preload the whole chain before the first script is appended.
   Measured, the serial chain used to spend more wall clock waiting than
   transferring: `tools/module-loading-strategy.mjs` measured a 3174 ms chain
   span against 1346 ms of transfer, i.e. 1828 ms spent waiting for the previous
   script to finish before the next fetch even started. Declaring each fetch as
   `<link rel=preload as=script>` starts the transfers as soon as the loader runs
   and costs no extra bytes — these are the same 23 URLs, fetched the same number
   of times, only earlier. Execution is still strictly one script at a time and in
   this order, because the chain below is unchanged: each script is appended only
   after the previous `onload`.
   The declaration is skipped on a connection that asks to save data, where 23
   overlapping fetches would compete with the critical path for no benefit. */
try{if(!navigator.connection||!navigator.connection.saveData){for(const n of a){const l=document.createElement('link');l.rel='preload';l.as='script';l.href=n;document.head.append(l)}}}catch(e){}
EInvitePerformanceReady=()=>p??=a.reduce((p,n)=>p.then(()=>new Promise((r,j)=>{let s=document.createElement('script');s.src=n;s.onload=r;s.onerror=j;document.head.append(s)})),Promise.resolve()).catch(()=>0);EInvitePerformanceReady()})();
/* v54 refactor: `workspace-experience-v24.js` was removed from this deferred
   list because its functionality now ships in the main index bundle as
   `editor/editor-core.js` (a documented, consolidated port). The bundled
   editor-core.js also claims `window.EInviteWorkspaceExperience` so any stray
   late copy no-ops, preventing duplicate canvas chrome. */
