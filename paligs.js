// US-10: progresīvs uzlabojums čata palīgam. Bez JS forma strādā ar parastu POST un pārlādi.
(function () {
  // Escape aizver atvērto palīgu un atgriež fokusu uz «Palīgs» (lai tas neaizsedz lapas saturu)
  var details = document.querySelector(".paligs details");
  if (details) {
    details.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && details.open) {
        details.open = false;
        details.querySelector("summary").focus();
      }
    });
  }

  var forma = document.querySelector(".paligs-forma");
  var zinas = document.getElementById("paligs-zinas");
  if (!forma || !zinas || !window.fetch) return;
  var lauks = document.getElementById("paligs-jautajums");
  var poga = forma.querySelector("button");

  function pievienot(klase, kas, teksts) {
    var li = document.createElement("li");
    var strong = document.createElement("strong");
    li.className = klase;
    strong.textContent = kas + ":";
    li.appendChild(strong);
    li.appendChild(document.createTextNode(" " + teksts));
    zinas.appendChild(li);
    li.scrollIntoView({ block: "nearest" });
  }

  forma.addEventListener("submit", function (e) {
    if (!lauks.value.trim()) return; // tukšu formu apstrādā serveris
    e.preventDefault();
    poga.disabled = true;
    poga.textContent = "Gaida atbildi…";
    fetch(forma.action, {
      method: "POST",
      headers: { "Accept": "application/json" },
      body: new FormData(forma)
    })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (dati) {
        pievienot("paligs-jus", "Jūs", dati.jautajums);
        pievienot("paligs-mi", "MI palīgs", dati.atbilde);
        lauks.value = "";
        poga.disabled = false;
        poga.textContent = "Jautāt";
        lauks.focus();
      })
      .catch(function () { forma.submit(); }); // kļūdas gadījumā — parasta iesniegšana
  });
})();
