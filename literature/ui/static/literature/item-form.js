// The write form's own behaviour, beside the Alpine components django-mvp
// ships: contributor rows that switch between a person and an organisation and
// move up and down, and the error summary's links into closed tabs and panels.
// Registered on alpine:init, so this file runs before Alpine does: a plain
// script at the foot of the page runs ahead of every deferred one.
(function () {
  "use strict";
  if (window.literatureItemForm) return;
  window.literatureItemForm = true;

  // Writes each row's ORDER from its place on screen. Each role is a set of
  // its own, so a set's rows are numbered from zero.
  function renumber(set) {
    set.querySelectorAll(":scope > [data-contributor-row] [data-order]").forEach(function (input, index) {
      input.value = index;
    });
  }

  // Renumbers a contributor set as its form is sent.
  window.literatureWatchOrder = function (set) {
    set.closest("form").addEventListener("submit", function () {
      renumber(set);
    });
  };

  // Opens the tab and every collapsed panel holding the field, then moves focus to it.
  window.literatureShowField = function (id) {
    const field = document.getElementById(id);
    if (!field) return;
    const pane = field.closest(".tab-content");
    if (pane && pane.previousElementSibling) pane.previousElementSibling.checked = true;
    for (let set = field.closest("fieldset"); set; set = set.parentElement.closest("fieldset")) {
      const toggle = set.querySelector(":scope > input.peer[type=checkbox]");
      if (toggle) toggle.checked = true;
    }
    const control = field.tomselect ? field.tomselect.control_input : field;
    control.scrollIntoView({ block: "center" });
    control.focus();
  };

  document.addEventListener("alpine:init", function () {
    Alpine.data("literatureContributor", function (organisation) {
      return {
        organisation: organisation,
        switched: false,
        hasDetails: false,
        init() {
          this.readDetails();
          // A row switched between person and organisation sends only the
          // inputs it shows, so a family name typed before the switch is not
          // stored beside the organisation. A row nobody switched sends what
          // it held, so saving it unchanged changes nothing.
          const row = this.$el;
          this.$el.closest("form").addEventListener("submit", () => {
            if (!this.switched) return;
            const hidden = this.organisation ? "[data-person] input" : "[data-organisation] input";
            row.querySelectorAll(hidden).forEach(function (input) {
              input.value = "";
            });
          });
        },
        choose(organisation) {
          if (organisation !== this.organisation) this.switched = true;
          this.organisation = organisation;
        },
        readDetails() {
          this.hasDetails = Array.from(this.$refs.details.querySelectorAll("input[type=text]")).some(function (input) {
            return input.value.trim() !== "";
          });
        },
        move(step, event) {
          const row = this.$root.closest("[data-contributor-row]");
          const target = step < 0 ? row.previousElementSibling : row.nextElementSibling;
          if (!target || !target.matches("[data-contributor-row]")) return;
          if (step < 0) target.before(row);
          else target.after(row);
          renumber(row.parentElement);
          const button = event.currentTarget;
          this.$nextTick(function () {
            button.focus();
          });
        },
      };
    });
  });
})();
