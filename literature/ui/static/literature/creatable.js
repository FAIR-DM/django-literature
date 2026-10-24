// Lets a Tom Select control marked data-create take a value typed in, beside
// the choices it offers: a keyword not used before, an identifier type outside
// the known six. django-mvp-forms starts the control and sends
// mvp-forms:tomselect with it, and this turns its create setting on.
(function () {
  "use strict";
  if (window.literatureCreatable) return;
  window.literatureCreatable = true;
  document.addEventListener("mvp-forms:tomselect", function (event) {
    if (!event.target.hasAttribute("data-create")) return;
    const control = event.detail.tomselect;
    control.settings.create = true;
    control.settings.createOnBlur = true;
    control.settings.persist = false;
    if (event.target.multiple) control.settings.delimiter = ",";
  });
})();
