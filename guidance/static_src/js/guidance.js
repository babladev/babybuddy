/**
 * Guidance action toggles.
 *
 * Each toggle is a real form that posts and redirects, so the feature works
 * without JavaScript. When JavaScript is available the state flips immediately
 * and the save happens in the background, which avoids losing your scroll
 * position on a long list.
 *
 * @type {{init: BabyBuddy.Guidance.init}}
 */
BabyBuddy.Guidance = (function () {
  function setState(form, completed) {
    var button = form.querySelector(".bb-guidance-check");
    var entry = form.closest(".bb-guidance-entry");
    if (button) {
      button.setAttribute("aria-pressed", completed ? "true" : "false");
    }
    if (entry) {
      entry.classList.toggle("bb-guidance-entry--done", completed);
    }
    updateProgress(form);
  }

  /**
   * Recount the "n of m done" badge for the group the form belongs to.
   */
  function updateProgress(form) {
    var group = form.closest(".bb-guidance-group");
    if (!group) {
      return;
    }
    var badge = group.querySelector(".bb-guidance-group__progress");
    if (!badge) {
      return;
    }
    var checks = group.querySelectorAll(".bb-guidance-check");
    var done = group.querySelectorAll(
      '.bb-guidance-check[aria-pressed="true"]',
    );
    badge.textContent = badge.textContent.replace(
      /\d+(\D+)\d+/,
      done.length + "$1" + checks.length,
    );
    badge.classList.toggle(
      "bb-guidance-group__progress--complete",
      checks.length > 0 && done.length === checks.length,
    );
  }

  return {
    init: function () {
      document
        .querySelectorAll("[data-bb-guidance-form]")
        .forEach(function (form) {
          form.addEventListener("submit", function (event) {
            var button = form.querySelector(".bb-guidance-check");
            if (!button) {
              return;
            }
            event.preventDefault();

            var next = button.getAttribute("aria-pressed") !== "true";
            setState(form, next);

            fetch(form.action, {
              method: "POST",
              body: new FormData(form),
              credentials: "same-origin",
              headers: { "X-Requested-With": "XMLHttpRequest" },
            })
              .then(function (response) {
                if (!response.ok) {
                  throw new Error("Request failed");
                }
                return response.json();
              })
              .then(function (data) {
                setState(form, data.completed);
              })
              .catch(function () {
                // Put the control back so it never shows a state that was not
                // saved.
                setState(form, !next);
              });
          });
        });
    },
  };
})();

(function initGuidance() {
  window.addEventListener("DOMContentLoaded", function () {
    BabyBuddy.Guidance.init();
  });
})();
