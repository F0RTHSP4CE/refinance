document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("fortune-form");
  if (form) {
    const stakeInput = form.querySelector("#stake");
    const currencyInput = form.querySelector("#currency");
    const boostInput = form.querySelector("#boosted");
    const tileInputs = Array.from(form.querySelectorAll(".fortune-tile-input"));
    const presetButtons = Array.from(form.querySelectorAll(".fortune-preset"));
    const submit = form.querySelector(".fortune-submit");
    const submitLabel = submit.querySelector(".fortune-submit-label");
    const selectedCount = document.getElementById("fortune-selected-count");
    const requiredCount = document.getElementById("fortune-required-count");
    const requiredLabels = Array.from(
      document.querySelectorAll("[data-fortune-required]"),
    );
    const selectionProgress = form.querySelector(".fortune-selection-progress");
    const winChance = document.getElementById("fortune-win-chance");
    const totalCost = document.getElementById("fortune-total-cost");
    const grossPrizeDisplay = document.getElementById("fortune-gross-prize");
    const lossCopy = document.getElementById("fortune-loss-copy");
    const boostCost = document.getElementById("fortune-boost-cost");
    const winUpTo = document.getElementById("fortune-win-up-to");
    const maxStakeWarning = document.getElementById("fortune-max-stake-warning");
    let selectionOrder = tileInputs.filter((input) => input.checked);

    const money = (value) => Math.round((value + Number.EPSILON) * 100) / 100;
    const amount = (value) =>
      `${value.toFixed(2)} ${currencyInput.value.toUpperCase()}`;
    const compactPercent = (value) => {
      const percentage = value * 100;
      return `${Number.isInteger(percentage) ? percentage : percentage.toFixed(2)}%`;
    };

    function requiredTiles() {
      return Number(
        boostInput.checked ? form.dataset.boostCount : form.dataset.baseCount,
      );
    }

    function update() {
      const boosted = boostInput.checked;
      const needed = requiredTiles();
      while (selectionOrder.length > needed) {
        const removed = selectionOrder.pop();
        removed.checked = false;
      }
      selectionOrder = selectionOrder.filter((input) => input.checked);

      const maxStakeByCurrency = JSON.parse(
        form.dataset.maxStakeByCurrency || "{}",
      );
      const rawMaxStake = Number(form.dataset.maxStake);
      const selectedCurrency = currencyInput.value || "usd";
      const effectiveMaxStake = Math.min(
        rawMaxStake,
        Number(maxStakeByCurrency[selectedCurrency] ?? rawMaxStake),
      );
      stakeInput.max = String(effectiveMaxStake.toFixed(2));

      const originalStake = Number(stakeInput.value);
      const stakeExceededLimit =
        Number.isFinite(originalStake) && originalStake > effectiveMaxStake;
      if (stakeExceededLimit) {
        stakeInput.value = effectiveMaxStake.toFixed(2);
        if (maxStakeWarning) {
          maxStakeWarning.hidden = false;
          maxStakeWarning.textContent =
            "Fortune is out of money to cover such a big prize. Max allowed stake is " +
            `${effectiveMaxStake.toFixed(2)} ${selectedCurrency.toUpperCase()}.`;
        }
      } else if (maxStakeWarning) {
        maxStakeWarning.hidden = true;
        maxStakeWarning.textContent = "";
      }

      const stake = Number(stakeInput.value);
      const costMultiplier = boosted
        ? Number(form.dataset.boostCostMultiplier)
        : 1;
      const probability = Number(
        boosted
          ? form.dataset.boostProbability
          : form.dataset.baseProbability,
      );
      const validStake =
        Number.isFinite(stake) &&
        stake >= Number(form.dataset.minStake) &&
        stake <= effectiveMaxStake &&
        stakeInput.validity.valid;
      const selectionReady = selectionOrder.length === needed;
      const selectionPercentage = Math.min(
        100,
        (selectionOrder.length / needed) * 100,
      );

      selectedCount.textContent = String(selectionOrder.length);
      requiredCount.textContent = String(needed);
      requiredLabels.forEach((label) => {
        label.textContent = String(needed);
      });
      selectionProgress.classList.toggle("is-ready", selectionReady);
      submit.style.setProperty(
        "--fortune-progress",
        `${selectionPercentage}%`,
      );
      winChance.textContent = compactPercent(probability);

      presetButtons.forEach((button) => {
        const buttonStake = Number(button.dataset.stake);
        const allowed = buttonStake <= effectiveMaxStake;
        button.disabled = !allowed;
        const active = validStake && buttonStake === stake;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
      });

      if (validStake) {
        const cost = money(stake * costMultiplier);
        const boostedCost = money(
          stake * Number(form.dataset.boostCostMultiplier),
        );
        const grossPrize = money(stake * Number(form.dataset.prizeMultiplier));
        totalCost.textContent = amount(cost);
        grossPrizeDisplay.textContent = amount(grossPrize);
        winUpTo.textContent = `Win up to ${amount(grossPrize)}`;
        boostCost.textContent = `${amount(boostedCost)} total`;
        lossCopy.textContent = `If none of your picks match, you lose ${amount(cost)}.`;
        submitLabel.textContent = selectionReady
          ? `Play for ${amount(cost)}`
          : `Pick ${needed - selectionOrder.length} more`;
      } else {
        totalCost.textContent = "—";
        grossPrizeDisplay.textContent = "—";
        winUpTo.textContent = "Win up to —";
        boostCost.textContent = `${form.dataset.boostCostMultiplier}× stake`;
        lossCopy.textContent = "Enter a valid stake to see the possible loss.";
        submitLabel.textContent = "Enter a valid stake";
      }
      const canPlay = selectionReady && validStake;
      submit.classList.toggle("is-ready", canPlay);
      submit.disabled = !canPlay;
    }

    tileInputs.forEach((input) => {
      input.addEventListener("change", () => {
        if (input.checked) {
          if (selectionOrder.length >= requiredTiles()) {
            input.checked = false;
          } else if (!selectionOrder.includes(input)) {
            selectionOrder.push(input);
          }
        } else {
          selectionOrder = selectionOrder.filter((item) => item !== input);
        }
        update();
      });
    });
    boostInput.addEventListener("change", update);
    currencyInput.addEventListener("change", update);
    stakeInput.addEventListener("input", update);
    presetButtons.forEach((button) => {
      button.addEventListener("click", () => {
        stakeInput.value = Number(button.dataset.stake).toFixed(2);
        update();
        stakeInput.focus();
      });
    });
    form.addEventListener("submit", () => {
      submit.disabled = true;
      submitLabel.textContent = "Playing…";
    });
    update();
  }

  const winPopup = document.querySelector("[data-fortune-win-popup]");
  if (winPopup) {
    const closeButton = winPopup.querySelector("[data-fortune-close-win]");
    const closePopup = () => {
      winPopup.hidden = true;
    };
    closeButton.addEventListener("click", closePopup);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !winPopup.hidden) closePopup();
    });
    closeButton.focus();
  }

  const source = document.getElementById("fortune-commitment-source");
  const expectedHash = document.getElementById("fortune-commitment-hash");
  const status = document.getElementById("fortune-verification-status");
  const summary = document.getElementById("fortune-verification-summary");
  if (source && expectedHash && status) {
    if (!window.crypto || !window.crypto.subtle) {
      status.textContent =
        "Automatic verification is unavailable; verify the source manually.";
      status.classList.add("is-unavailable");
      if (summary) summary.textContent = "Manual check";
      return;
    }
    window.crypto.subtle
      .digest("SHA-256", new TextEncoder().encode(source.textContent))
      .then((digest) => {
        const actual = Array.from(new Uint8Array(digest))
          .map((byte) => byte.toString(16).padStart(2, "0"))
          .join("");
        const verified = actual === expectedHash.textContent.trim();
        status.textContent = verified
          ? "✓ The revealed source matches the pre-game hash."
          : `✕ Mismatch: computed ${actual}`;
        status.classList.add(verified ? "is-verified" : "is-mismatch");
        if (summary) summary.textContent = verified ? "Verified" : "Mismatch";
      })
      .catch(() => {
        status.textContent =
          "Automatic verification failed; verify the source manually.";
        status.classList.add("is-unavailable");
        if (summary) summary.textContent = "Manual check";
      });
  }
});
