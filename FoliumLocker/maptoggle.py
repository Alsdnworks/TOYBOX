from IPython.display import display, HTML
import uuid
import html
import math


def enable_map_toggle(
    fig,
    lock=True,
    fig_id=None,
):
    w = "100%"
    if fig_id is None:
        fig_id = f"{fig.get_name()}"
    if getattr(fig, "width", None) is not None:
        w = fig.width
        if isinstance(w, int):
            w = f"{w}px"
        if w.endswith("%"):
            wval = float(float(w[:-1])) - 1.5
            w = f"{wval}%"
    else:
        fig.width = "100%"

    wrap_id = f"folium-wrap-{uuid.uuid4().hex}"
    iframe_html = fig._repr_html_()

    display(
        HTML(
            f"""
<div id="{wrap_id}" class="folium-wrap" data-fig-id="{html.escape(fig_id)}" style="position:relative;width:100%;height:100%;aspect-ratio:inherit;">
  {iframe_html}
/*
<style>
    .folium-overlay {{
        opacity: 0; 
    }}
    .folium-overlay:focus {{
        opacity: 1;
    }}

</style>
*/
  <div class="folium-overlay"
       style="position:absolute;top:0;left:0;right:0;bottom:0;display:flex;align-items:center;justify-content:center;width:{w};height:100%;
              background:rgba(0,0,0,0.4);color:#fff;font:14px/1.4 -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
              letter-spacing:.2px;text-align:center;padding:12px;user-select:none;pointer-events:none;transition:opacity .15s ease;
              font-weight:700;text-shadow:0 1px 2px rgba(0,0,0,.6);z-index:1000;">
        "Click or Press Ctrl(⌘) to toggle"
  </div>
</div>
<script>
(function(){{
  const wrap = document.getElementById({wrap_id!r});
  if (!wrap) return;
  const ifr = wrap.querySelector('iframe');
  const ovl = wrap.querySelector('.folium-overlay');
  if (!ifr || !ovl) return;

  let active = {'false' if lock else 'true'};
  function setActive(b){{
    active = b;
    ifr.style.pointerEvents = b ? 'auto' : 'none';
    ovl.style.opacity = b ? '0' : '1';
    
  }}
  setActive(false);

  wrap.tabIndex = 0;
  wrap.addEventListener('mouseenter', () => wrap.focus({{preventScroll:true}}));
  wrap.addEventListener('mouseleave', () => setActive(false)); blur();
  wrap.addEventListener('click', (e) => {{

      e.preventDefault();
      setActive(!active);

  }});
  wrap.addEventListener('keydown', (e) => {{
    if (e.ctrlKey || e.metaKey) {{
      e.preventDefault();
      setActive(!active);
    }}
  }});

  function attachIframeKey(){{
    try {{
      const idoc = ifr.contentDocument;
      const win  = ifr.contentWindow;
      if (!idoc || !win) return;
      const handler = (e) => {{
        if (e.ctrlKey || e.metaKey || e.type === 'keyup') {{
          e.preventDefault();
          if (e.stopImmediatePropagation) e.stopImmediatePropagation();
          e.stopPropagation();
          setActive(!active);
        }}
      }};
      idoc.addEventListener('keydown', handler, {{capture:true}});
      idoc.addEventListener('keyup',   handler, {{capture:true}});
      win .addEventListener('keydown', handler, {{capture:true}});
      win .addEventListener('keyup',   handler, {{capture:true}});
     
      
    }} catch (e){{
      console.log('Could not attach key handlers to iframe:', e);
    }}
  }}
  if (ifr.contentDocument) attachIframeKey();
  else ifr.addEventListener('load', attachIframeKey);
}})();
</script>
    """
        )
    )
