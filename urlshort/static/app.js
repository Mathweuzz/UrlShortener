(function () {
  function onCopyClick(e) {
    const btn = e.target.closest(".copy-btn");
    if (!btn) return;
    const text = btn.getAttribute("data-copy");
    if (!text) return;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        flashOK(btn);
      }).catch(() => {
        fallbackCopy(text, btn);
      });
    } else {
      fallbackCopy(text, btn);
    }
  }

  function fallbackCopy(text, btn) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.top = "-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
    flashOK(btn);
  }

  function flashOK(btn) {
    const original = btn.textContent;
    btn.textContent = "Copiado!";
    btn.disabled = true;
    setTimeout(() => { btn.textContent = original; btn.disabled = false; }, 1200);
  }

  document.addEventListener("click", onCopyClick);
})();
