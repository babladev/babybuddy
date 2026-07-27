if (typeof jQuery === "undefined") {
  throw new Error("Baby Buddy requires jQuery.");
}

/**
 * Baby Buddy Namespace
 *
 * Default namespace for the Baby Buddy app.
 *
 * @type {{}}
 */
var BabyBuddy = (function () {
  return {};
})();

/**
 * Pull to refresh.
 *
 * @type {{init: BabyBuddy.PullToRefresh.init, onRefresh: BabyBuddy.PullToRefresh.onRefresh}}
 */
BabyBuddy.PullToRefresh = (function (ptr) {
  return {
    init: function () {
      ptr.init({
        mainElement: "body",
        onRefresh: this.onRefresh,
      });
    },

    onRefresh: function () {
      window.location.reload();
    },
  };
})(PullToRefresh);

/**
 * Show a loading spinner on the submit button when a form is submitted and
 * prevent double-submission.
 */
(function handleFormSubmit() {
  // Forms marked data-bb-async-form handle their own submission and never
  // navigate. Disabling their button would leave it stuck with a spinner,
  // because nothing ever replaces the page to reset it.
  $("form")
    .not("[data-bb-async-form]")
    .on("submit", function (event) {
      var submitter =
        (event.originalEvent && event.originalEvent.submitter) ||
        $(this).find('[type="submit"]')[0];
      if (!submitter || $(submitter).prop("disabled")) return;
      $(submitter)
        .prop("disabled", true)
        .prepend(
          '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>',
        );
    });
})();

BabyBuddy.RememberAdvancedToggle = function (ptr) {
  localStorage.setItem("advancedForm", event.newState);
};

(function toggleAdvancedFields() {
  window.addEventListener("load", function () {
    if (localStorage.getItem("advancedForm") !== "open") {
      return;
    }

    document.querySelectorAll(".advanced-fields").forEach(function (node) {
      node.open = true;
    });
  });
})();

/**
 * Light and dark appearance.
 *
 * The preference is stored server side, on the user's settings, so it follows
 * the account across devices. The initial scheme is applied by an inline script
 * in the page head to avoid a flash of the wrong colours; this module handles
 * switching afterwards.
 *
 * @type {{init: BabyBuddy.Theme.init, apply: BabyBuddy.Theme.apply}}
 */
BabyBuddy.Theme = (function () {
  var root = document.documentElement;
  var lightQuery = window.matchMedia("(prefers-color-scheme: light)");

  function preference() {
    return root.getAttribute("data-bb-theme-preference") || "auto";
  }

  function resolve(value) {
    if (value === "auto") {
      return lightQuery.matches ? "light" : "dark";
    }
    return value;
  }

  return {
    apply: function (value) {
      root.setAttribute("data-bb-theme-preference", value);
      root.setAttribute("data-bs-theme", resolve(value));

      // Reflect the choice in every appearance control on the page.
      document
        .querySelectorAll(".bb-theme-toggle__option")
        .forEach(function (button) {
          var form = button.closest("[data-bb-theme-form]");
          var input = form && form.querySelector('input[name="theme"]');
          var isActive = !!input && input.value === value;
          button.classList.toggle("active", isActive);
          if (isActive) {
            button.setAttribute("aria-current", "true");
          } else {
            button.removeAttribute("aria-current");
          }
        });
    },

    init: function () {
      var self = this;

      // Follow the operating system while the preference is "auto".
      var onSystemChange = function () {
        if (preference() === "auto") {
          root.setAttribute("data-bs-theme", resolve("auto"));
        }
      };
      if (typeof lightQuery.addEventListener === "function") {
        lightQuery.addEventListener("change", onSystemChange);
      } else if (typeof lightQuery.addListener === "function") {
        // Safari below 14.
        lightQuery.addListener(onSystemChange);
      }

      // Apply the new scheme immediately and persist it in the background. The
      // forms submit normally if this handler is never registered.
      document
        .querySelectorAll("[data-bb-theme-form]")
        .forEach(function (form) {
          form.addEventListener("submit", function (event) {
            var input = form.querySelector('input[name="theme"]');
            if (!input) {
              return;
            }
            event.preventDefault();
            self.apply(input.value);

            fetch(form.action, {
              method: "POST",
              body: new FormData(form),
              credentials: "same-origin",
              headers: { "X-Requested-With": "XMLHttpRequest" },
            }).catch(function () {
              // A failed save only means the choice is not remembered for the
              // next visit, so there is nothing useful to tell the user here.
            });
          });
        });
    },
  };
})();

/**
 * Floating action button.
 *
 * On small screens a form's own submit button is fixed to the bottom of the
 * viewport, which would collide with the action button, so the body is flagged
 * and CSS hides the button on those pages.
 */
BabyBuddy.QuickAdd = (function () {
  return {
    init: function () {
      if (document.querySelector(".submit-primary")) {
        document.body.classList.add("bb-has-fixed-submit");
      }
    },
  };
})();

(function initInterface() {
  window.addEventListener("DOMContentLoaded", function () {
    BabyBuddy.Theme.init();
    BabyBuddy.QuickAdd.init();
    BabyBuddy.DurationPresets.init();
  });
})();

/**
 * Quick duration presets on activity forms.
 *
 * Sets the end time to the start time plus a fixed number of minutes, which
 * covers the common case of logging a short activity that has already
 * finished. The controls stay hidden unless this runs, since they do nothing
 * without scripting.
 *
 * @type {{init: BabyBuddy.DurationPresets.init}}
 */
BabyBuddy.DurationPresets = (function () {
  /**
   * Format a Date for a datetime-local input, in local time.
   *
   * toISOString would convert to UTC and shift the value, so the parts are
   * assembled by hand.
   */
  function toInputValue(date) {
    function pad(value) {
      return String(value).padStart(2, "0");
    }
    return (
      date.getFullYear() +
      "-" +
      pad(date.getMonth() + 1) +
      "-" +
      pad(date.getDate()) +
      "T" +
      pad(date.getHours()) +
      ":" +
      pad(date.getMinutes()) +
      ":" +
      pad(date.getSeconds())
    );
  }

  function apply(container, minutes) {
    var startField = document.getElementById(
      container.getAttribute("data-bb-start-field"),
    );
    var endField = document.getElementById(
      container.getAttribute("data-bb-end-field"),
    );
    if (!startField || !endField) {
      return;
    }

    var start = startField.value ? new Date(startField.value) : new Date();
    if (isNaN(start.getTime())) {
      start = new Date();
    }
    startField.value = toInputValue(start);

    var end = new Date(start.getTime() + minutes * 60000);
    endField.value = toInputValue(end);

    // Let any listeners (validation, timers) know the values changed.
    [startField, endField].forEach(function (field) {
      field.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  return {
    init: function () {
      document
        .querySelectorAll("[data-bb-duration-presets]")
        .forEach(function (container) {
          container.removeAttribute("hidden");
          container
            .querySelectorAll("[data-bb-duration-minutes]")
            .forEach(function (button) {
              button.addEventListener("click", function () {
                var minutes = parseInt(
                  button.getAttribute("data-bb-duration-minutes"),
                  10,
                );
                if (!isNaN(minutes)) {
                  apply(container, minutes);
                }
              });
            });
        });
    },
  };
})();
