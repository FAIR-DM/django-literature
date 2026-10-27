// Turns Tom Select's create setting on for controls marked data-create (CreatableSelect
// in literature/ui/forms.py), when django-mvp-forms sends mvp-forms:tomselect.
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
