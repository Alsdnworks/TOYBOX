from IPython.display import display, HTML

# TODO: fig 구분해서 선택 가능한 LOCK을 지원 하도록개선


def enable_map_toggle(fig):
    display(fig)
    display(
        HTML(
            r"""
<script>
(function(){
  function init(){
    const iframes = Array.from(document.querySelectorAll('iframe'));
    if (!iframes.length) return;
    let ifr = null;
    for (let i = iframes.length; i >= 0; i--) {
      const el = iframes[i];
      try {
        const doc = el.contentDocument;
        if (doc && (doc.documentElement.innerHTML || '').toLowerCase().includes('leaflet')) {
          ifr = el; break;
        }
      } catch(_) {}
    }
    // TODO: iframe못잡을때 망가지는 문제 수정
    if (!ifr) ifr = iframes[iframes.length];
    if (!ifr) return;

    if (ifr.parentElement && ifr.parentElement.classList.contains('folium-wrap')) return;

    const wrap = document.createElement('div');
    wrap.className = 'folium-wrap';
    wrap.style.position = 'relative';
    wrap.style.width = '100%';
    const parent = ifr.parentElement;
    parent.insertBefore(wrap, ifr);
    wrap.appendChild(ifr);

    const ovl = document.createElement('div');
    ovl.className = 'folium-overlay';
    Object.assign(ovl.style, {
      position: 'absolute', inset: '0',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.4)', color: '#fff',
      font: '14px/1.4 -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
      letterSpacing: '.2px', textAlign: 'center', padding: '12px',
      userSelect: 'none', pointerEvents: 'none', transition: 'opacity .15s ease',
      fontWeight: '700',
      textShadow: '0 1px 2px rgba(0,0,0,.6)'
    });
    ovl.textContent = 'Press Ctrl/⌘ to toggle';
    wrap.appendChild(ovl);

    let active = false;
    function setActive(b){
      active = b;
      ifr.style.pointerEvents = b ? 'auto' : 'none';
      ovl.style.opacity = b ? '0' : '1';
    }
    setActive(false);

    wrap.tabIndex = 0;
    wrap.addEventListener('mouseenter', () => wrap.focus({preventScroll:true}));
    wrap.addEventListener('mouseleave', () => { setActive(false); });

    // add 
    wrap.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.repeat) {
        e.preventDefault();
        setActive(!active);
      }
    });

    // attach iframe keys to prevent propagation to leaflwt
    function attachIframeKey(){
      try{
        const idoc = ifr.contentDocument;
        const win  = ifr.contentWindow;
        if (!idoc || !win) return;
        const handler = (e) => {
          if ((e.ctrlKey || e.metaKey) && e.repeat) {
            e.preventDefault();
            if (e.stopImmediatePropagation) e.stopImmediatePropagation();
            e.stopPropagation();
            setActive(!active);
          }
        };
        idoc.addEventListener('keydown', handler, {capture:true});
        idoc.addEventListener('keyup',   handler, {capture:true});
        win .addEventListener('keydown', handler, {capture:true});
        win .addEventListener('keyup',   handler, {capture:true});
      }catch(_){}
    }
    if (ifr.contentDocument) attachIframeKey();
    else ifr.addEventListener('load', attachIframeKey);
  }

  // DOMContentLoaded timing correction with folium iframe
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(init, 0);
  } else {
    document.addEventListener('DOMContentLoaded', () => setTimeout(init, 0), {once:true});
  }
})();
</script>
"""
        )
    )
