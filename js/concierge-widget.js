/* FairClaims Concierge Widget — vanilla JS, no deps.
 *
 * Mounts a fixed bottom-right chat bubble on every page. State is
 * in-memory only — no localStorage, no per-visitor history. Reload
 * clears the transcript by design.
 *
 * Disable mount by setting `data-fc-concierge-disabled` on <body>.
 *
 * Talks to /concierge/ask same-origin. Server runs the FAQ retrieval,
 * guardrails, PII scrub, and (when configured) Groq synthesis.
 */
(function () {
  "use strict";

  // ── Don't double-mount, don't mount when disabled ──────────────
  if (window.__fcConciergeMounted) return;
  if (document.body && document.body.hasAttribute("data-fc-concierge-disabled")) return;
  window.__fcConciergeMounted = true;

  // Lucide MessageCircle icon (https://lucide.dev/icons/message-circle).
  // Inlined so we don't ship a CDN dep.
  var ICON_SVG =
    '<svg class="fc-concierge__icon" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>' +
    '</svg>';

  var OPENING_MSG =
    "Hi — I'm the FairClaims assistant. Ask me anything about charity care, " +
    "medical debt, prior authorization, workplace injury, or toxic exposure.";

  var ENDPOINT = "/concierge/ask";

  // ── Build DOM ──────────────────────────────────────────────────
  function buildDom() {
    var root = document.createElement("div");
    root.className = "fc-concierge";
    root.setAttribute("data-fc-concierge", "");
    root.innerHTML = [
      '<button type="button" class="fc-concierge__bubble" ',
      'aria-label="Open FairClaims chat" aria-expanded="false">',
      ICON_SVG,
      "</button>",
      '<section class="fc-concierge__panel" role="dialog" ',
      'aria-label="FairClaims chat" aria-hidden="true">',
      '  <header class="fc-concierge__header">',
      "    <strong>Ask FairClaims</strong>",
      '    <button type="button" class="fc-concierge__close" ',
      'aria-label="Close chat">×</button>',
      "  </header>",
      '  <div class="fc-concierge__transcript" role="log" ',
      'aria-live="polite"></div>',
      '  <form class="fc-concierge__input">',
      "    <textarea required maxlength=\"500\" rows=\"2\" ",
      "      placeholder=\"Ask about charity care, debt, denials…\"></textarea>",
      '    <button type="submit" aria-label="Send">Send</button>',
      "  </form>",
      '  <footer class="fc-concierge__footer">',
      "    Not legal, medical, or financial advice. ",
      '    <a href="/pages/get-started.html">Get personal help →</a>',
      "  </footer>",
      "</section>",
    ].join("");
    return root;
  }

  // ── State + helpers ────────────────────────────────────────────
  var root, bubble, panel, transcript, form, textarea, sendBtn;
  var isOpen = false;
  var isSending = false;
  var openerShown = false;

  function escapeHTML(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function appendMessage(role, text, citations) {
    var msg = document.createElement("div");
    msg.className =
      "fc-concierge__msg fc-concierge__msg--" +
      (role === "user" ? "user" : "assistant");
    var html =
      '<div class="fc-concierge__bubble-text">' +
      escapeHTML(text) +
      "</div>";
    if (citations && citations.length) {
      var chips = citations
        .filter(function (c) {
          return c && c.question;
        })
        .slice(0, 3)
        .map(function (c) {
          return (
            '<span class="fc-concierge__citation" title="' +
            escapeHTML(c.question) +
            '">' +
            escapeHTML(c.question) +
            "</span>"
          );
        })
        .join("");
      if (chips) {
        html += '<div class="fc-concierge__citations">' + chips + "</div>";
      }
    }
    msg.innerHTML = html;
    transcript.appendChild(msg);
    transcript.scrollTop = transcript.scrollHeight;
  }

  function showTyping() {
    hideTyping();
    var msg = document.createElement("div");
    msg.className = "fc-concierge__msg fc-concierge__msg--assistant";
    msg.id = "fc-concierge-typing";
    msg.innerHTML =
      '<div class="fc-concierge__typing"><span></span><span></span><span></span></div>';
    transcript.appendChild(msg);
    transcript.scrollTop = transcript.scrollHeight;
  }

  function hideTyping() {
    var t = document.getElementById("fc-concierge-typing");
    if (t && t.parentNode) t.parentNode.removeChild(t);
  }

  function setSending(sending) {
    isSending = sending;
    sendBtn.disabled = sending;
    textarea.disabled = sending;
  }

  // ── API call with graceful fallback ────────────────────────────
  function ask(question) {
    setSending(true);
    showTyping();
    var pageUrl = window.location.pathname + (window.location.search || "");
    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, page_url: pageUrl }),
    })
      .then(function (r) {
        hideTyping();
        if (r.status === 503) {
          appendMessage(
            "assistant",
            "The concierge is offline right now. Visit Get Started for a real person."
          );
          return null;
        }
        if (!r.ok) {
          appendMessage(
            "assistant",
            "Something went wrong on our side. Try again, or visit Get Started."
          );
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        appendMessage("assistant", data.answer, data.citations);
      })
      .catch(function () {
        hideTyping();
        appendMessage(
          "assistant",
          "Network error. Please try again."
        );
      })
      .then(function () {
        setSending(false);
        textarea.focus();
      });
  }

  // ── Open / close ───────────────────────────────────────────────
  function openPanel() {
    if (isOpen) return;
    isOpen = true;
    root.classList.add("fc-concierge--open");
    bubble.setAttribute("aria-expanded", "true");
    panel.setAttribute("aria-hidden", "false");
    if (!openerShown) {
      appendMessage("assistant", OPENING_MSG);
      openerShown = true;
    }
    // Defer focus until after the transition starts so it doesn't
    // jank the open animation.
    setTimeout(function () {
      textarea.focus();
    }, 50);
  }

  function closePanel() {
    if (!isOpen) return;
    isOpen = false;
    root.classList.remove("fc-concierge--open");
    bubble.setAttribute("aria-expanded", "false");
    panel.setAttribute("aria-hidden", "true");
    bubble.focus();
  }

  // ── Event wiring ───────────────────────────────────────────────
  function handleSubmit(e) {
    e.preventDefault();
    if (isSending) return;
    var q = textarea.value.trim();
    if (!q) return;
    appendMessage("user", q);
    textarea.value = "";
    ask(q);
  }

  function init() {
    if (document.body && document.body.hasAttribute("data-fc-concierge-disabled")) {
      return;
    }
    root = buildDom();
    document.body.appendChild(root);

    bubble = root.querySelector(".fc-concierge__bubble");
    panel = root.querySelector(".fc-concierge__panel");
    transcript = root.querySelector(".fc-concierge__transcript");
    form = root.querySelector(".fc-concierge__input");
    textarea = form.querySelector("textarea");
    sendBtn = form.querySelector("button[type='submit']");

    bubble.addEventListener("click", function () {
      isOpen ? closePanel() : openPanel();
    });
    root.querySelector(".fc-concierge__close").addEventListener(
      "click",
      closePanel
    );
    form.addEventListener("submit", handleSubmit);

    // Submit on Enter (without shift) — common chat UX.
    textarea.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
      }
    });

    // Esc closes when the panel is open.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isOpen) closePanel();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
