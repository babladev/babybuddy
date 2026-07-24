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
  // Appearance forms never navigate, so they must not get a spinner.
  $("form")
    .not("[data-bb-theme-form]")
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
  });
})();
