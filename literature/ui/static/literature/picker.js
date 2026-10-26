// Lets a Tom Select control marked data-search-url find references on the
// server as the reader types, in place of listing the whole catalogue.
// django-mvp-forms starts the control and sends mvp-forms:tomselect with it,
// and this gives it a load function that asks the search route. The select
// holds only the chosen references, so there is nothing local to match: the
// options the last search returned are offered, in the order it returned them,
// and a chosen reference the search did not return is not.
(function () {
  "use strict";
  if (window.literaturePicker) return;
  window.literaturePicker = true;

  document.addEventListener("mvp-forms:tomselect", function (event) {
    const url = event.target.dataset.searchUrl;
    if (!url) return;
    const key = event.target.dataset.searchKey;
    const control = event.detail.tomselect;
    const settings = control.settings;
    settings.valueField = "value";
    settings.labelField = "text";
    settings.searchField = [];
    // The values the last search returned. A chosen reference stays an option
    // of the control after a later search that does not match it, so it is
    // offered only when that search returned it.
    let found = new Set();
    settings.score = function () {
      return function (option) {
        return found.has(String(option.value)) ? 1 : 0;
      };
    };
    settings.shouldLoad = function (text) {
      return text.length > 0;
    };
    let latest = 0;
    settings.load = function (text, callback) {
      // Drop the matches of the last search but keep what is chosen, and let
      // an earlier search be typed again and loaded again.
      control.clearOptions();
      const request = ++latest;
      const query = new URLSearchParams({ q: text });
      if (key) query.set("key", key);
      fetch(url + "?" + query.toString(), {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Search answered " + response.status);
          return response.json();
        })
        .then(function (data) {
          // A slower answer to text the reader has since typed past is dropped.
          if (request !== latest) return callback();
          found = new Set(data.results.map(function (result) {
            return String(result.value);
          }));
          callback(data.results);
        })
        .catch(function () {
          if (request !== latest) return callback();
          found = new Set();
          callback();
        });
    };
  });
})();
