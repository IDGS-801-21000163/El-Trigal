(() => {
  const MIN_OPTIONS = 0;
  const DEFAULT_PLACEHOLDER = "Seleccione una opción";

  function normalizeText(value) {
    return (value || "").toString().trim().toLowerCase();
  }

  function getSelectedOption(selectEl) {
    const opt = selectEl.selectedOptions && selectEl.selectedOptions[0];
    if (opt) return opt;
    return selectEl.options[selectEl.selectedIndex] || null;
  }

  function ensurePlaceholderOption(selectEl) {
    if (!(selectEl instanceof HTMLSelectElement)) return;
    if (selectEl.dataset.ssPlaceholder === "false") return;

    // If there is already an empty option, assume it's acting as placeholder.
    const existingEmpty = selectEl.querySelector("option[value='']");
    if (existingEmpty) return;

    // Many existing forms use value="0" as a placeholder. Avoid duplicating it.
    const existingZero = selectEl.querySelector("option[value='0']");
    if (existingZero) {
      const text = normalizeText(existingZero.textContent);
      const looksLikePlaceholder =
        existingZero.disabled ||
        text === normalizeText(DEFAULT_PLACEHOLDER) ||
        text.startsWith(normalizeText(DEFAULT_PLACEHOLDER));
      if (looksLikePlaceholder) return;
    }

    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = selectEl.dataset.ssPlaceholderText || DEFAULT_PLACEHOLDER;
    opt.disabled = true;
    opt.dataset.ssPlaceholder = "true";

    // If nothing meaningful is selected, keep the placeholder selected so the first real option
    // doesn't get auto-selected.
    const selected = getSelectedOption(selectEl);
    const hasRealSelection = Boolean(selected && selected.value !== "");
    if (!hasRealSelection) opt.selected = true;

    selectEl.insertBefore(opt, selectEl.firstChild);
  }

  function shouldEnhance(selectEl) {
    if (!(selectEl instanceof HTMLSelectElement)) return false;
    if (selectEl.dataset.nativeSelect === "true") return false;
    if (selectEl.multiple) return false;
    if (selectEl.size && Number(selectEl.size) > 1) return false;
    if (selectEl.closest("[data-native-select='true']")) return false;
    if (selectEl.dataset.searchable === "false") return false;

    const optionCount = selectEl.querySelectorAll("option").length;
    if (selectEl.dataset.searchable === "true") return true;
    return optionCount >= MIN_OPTIONS;
  }

  function buildDropdownItems(selectEl, listEl, query) {
    const q = normalizeText(query);
    listEl.innerHTML = "";
    const options = Array.from(selectEl.options);

    const visible = options.filter((opt) => {
      if (!opt) return false;
      const text = normalizeText(opt.textContent);
      return q.length === 0 || text.includes(q);
    });

    if (visible.length === 0) {
      const empty = document.createElement("div");
      empty.className = "ss-item ss-item--empty";
      empty.textContent = "Sin resultados";
      listEl.appendChild(empty);
      return;
    }

    visible.forEach((opt) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "ss-item";
      item.textContent = opt.textContent;
      item.dataset.value = opt.value;
      item.disabled = Boolean(opt.disabled);
      if (opt.selected) item.setAttribute("aria-selected", "true");
      listEl.appendChild(item);
    });
  }

  function enhanceSelect(selectEl) {
    if (selectEl.dataset.ssEnhanced === "true") return;
    if (!shouldEnhance(selectEl)) return;

    ensurePlaceholderOption(selectEl);

    selectEl.dataset.ssEnhanced = "true";
    selectEl.classList.add("ss-native");

    const wrapper = document.createElement("div");
    wrapper.className = "ss";

    const input = document.createElement("input");
    input.type = "text";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.className = `form-input ss-input${selectEl.classList.contains("form-input--compact") ? " form-input--compact" : ""}`;
    input.placeholder = selectEl.dataset.ssPlaceholderText || selectEl.dataset.placeholder || DEFAULT_PLACEHOLDER;

    const list = document.createElement("div");
    list.className = "ss-list";
    list.hidden = true;

    // Mount.
    selectEl.parentNode.insertBefore(wrapper, selectEl);
    wrapper.appendChild(input);
    wrapper.appendChild(list);
    wrapper.appendChild(selectEl);

    const syncFromSelect = () => {
      const selected = getSelectedOption(selectEl);
      if (!selected || selected.value === "" || selected.dataset.ssPlaceholder === "true") {
        input.value = "";
      } else {
        input.value = selected.textContent.trim();
      }
      input.disabled = selectEl.disabled;
    };

    const open = () => {
      if (input.disabled) return;
      buildDropdownItems(selectEl, list, input.value);
      list.hidden = false;
      wrapper.classList.add("ss--open");
    };

    const close = () => {
      list.hidden = true;
      wrapper.classList.remove("ss--open");
    };

    const toggle = () => {
      if (list.hidden) open();
      else close();
    };

    // Initial state.
    syncFromSelect();

    // Keep in sync.
    selectEl.addEventListener("change", () => {
      syncFromSelect();
    });

    // If options are changed dynamically (e.g. municipio list), rebuild.
    const observer = new MutationObserver(() => {
      ensurePlaceholderOption(selectEl);
      // If the select has no selection yet, keep input empty to prompt user.
      syncFromSelect();
      if (!list.hidden) buildDropdownItems(selectEl, list, input.value);
    });
    observer.observe(selectEl, { childList: true, subtree: true });

    // Events.
    input.addEventListener("focus", () => open());
    input.addEventListener("click", (e) => {
      e.stopPropagation();
      open();
    });

    input.addEventListener("input", () => {
      if (list.hidden) open();
      else buildDropdownItems(selectEl, list, input.value);
    });

    list.addEventListener("click", (e) => {
      const target = e.target;
      if (!(target instanceof HTMLElement)) return;
      const item = target.closest(".ss-item");
      if (!item || item.classList.contains("ss-item--empty")) return;
      if (item instanceof HTMLButtonElement && item.disabled) return;

      const value = item.dataset.value ?? "";
      selectEl.value = value;
      selectEl.dispatchEvent(new Event("change", { bubbles: true }));
      close();
    });

    document.addEventListener("click", (e) => {
      if (!wrapper.contains(e.target)) close();
    });
  }

  function enhanceAll(root = document) {
    const selects = root.querySelectorAll("select");
    selects.forEach(enhanceSelect);
  }

  // Expose a small API so pages that dynamically add selects (repeatable forms)
  // can re-run enhancement only on the new subtree.
  window.SearchableSelect = {
    enhanceAll,
  };

  document.addEventListener("DOMContentLoaded", () => {
    enhanceAll();
  });
})();
