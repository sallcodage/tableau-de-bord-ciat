/* Graphiques du tableau de bord (Chart.js 4, hébergé localement).
   - couleurs de la charte ISEP
   - clic sur une barre de domaine / cohorte → filtre le tableau de bord
   - bouton « PNG » sur chaque graphique (export image) */
(function () {
  const C = {
    brun: "#4B2E1F", brun2: "#8C5A3C", caramel: "#C8956D", sable: "#E3CDB8",
    vert: "#2F7D5B", ambre: "#D19A3A", rouge: "#B3412E", gris: "#CFC6BE", grille: "#EFE7DF",
  };
  Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = "#6F6158";
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.tooltip.backgroundColor = "#2A1D16";

  const nf = new Intl.NumberFormat("fr-FR");
  const fcfa = v => v >= 1e6 ? nf.format(Math.round(v / 1e5) / 10) + " M FCFA" : nf.format(v) + " FCFA";

  function axes(horizontal, opts) {
    const val = Object.assign({ beginAtZero: true, grid: { color: C.grille }, ticks: { precision: 0 } }, opts || {});
    const cat = { grid: { display: false } };
    return horizontal ? { x: val, y: cat } : { x: cat, y: val };
  }

  function filtrerPar(param, valeur) {
    const url = new URL(window.location.href);
    url.searchParams.set(param, valeur);
    window.location.href = url.toString();
  }

  // Fond blanc pour les exports PNG
  const fondBlanc = { id: "fondBlanc", beforeDraw(c) {
    const ctx = c.canvas.getContext("2d"); ctx.save(); ctx.globalCompositeOperation = "destination-over";
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, c.width, c.height); ctx.restore(); } };
  Chart.register(fondBlanc);

  window.CIAT = {
    C, fcfa, nf,
    graphique(id, config) {
      const el = document.getElementById(id);
      if (!el) return null;
      config.options = Object.assign({ responsive: true, maintainAspectRatio: false }, config.options || {});
      const g = new Chart(el, config);
      const bouton = document.querySelector(`[data-png="${id}"]`);
      if (bouton) bouton.addEventListener("click", () => {
        const a = document.createElement("a");
        a.href = g.toBase64Image("image/png", 1);
        a.download = `ciat_${id}.png`;
        a.click();
      });
      return g;
    },
    entonnoir(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.etape), datasets: [{ data: data.map(d => d.n),
          backgroundColor: data.map((_, i) => i === data.length - 1 ? C.brun : C.caramel), borderRadius: 6 }] },
        options: { indexAxis: "y", scales: axes(true), plugins: { legend: { display: false },
          tooltip: { callbacks: { afterLabel: ctx => ctx.dataIndex ? `${Math.round(100 * ctx.raw / (data[0].n || 1))} % des idées reçues` : "" } } } } });
    },
    cohortes(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.cohorte), datasets: [
          { label: "Idées", data: data.map(d => d.idees), backgroundColor: C.sable, borderRadius: 4 },
          { label: "Incubés", data: data.map(d => d.selectionnes), backgroundColor: C.caramel, borderRadius: 4 },
          { label: "Prototypes", data: data.map(d => d.prototypes), backgroundColor: C.brun2, borderRadius: 4 },
          { label: "Sortis", data: data.map(d => d.sortis), backgroundColor: C.brun, borderRadius: 4 }] },
        options: { scales: axes(false), onClick: (e, el) => el.length && filtrerPar("cohorte", data[el[0].index].cohorte),
          plugins: { legend: { position: "bottom" } } } });
    },
    taux(id, data) {
      return this.graphique(id, { type: "line",
        data: { labels: data.map(d => d.cohorte), datasets: [
          { label: "Taux de sélection", data: data.map(d => d.taux_selection), borderColor: C.caramel, backgroundColor: C.caramel, tension: .25 },
          { label: "Prototypes / incubés", data: data.map(d => d.taux_prototype), borderColor: C.brun2, backgroundColor: C.brun2, tension: .25 },
          { label: "Taux de réussite", data: data.map(d => d.taux_reussite), borderColor: C.vert, backgroundColor: C.vert, tension: .25 },
          { label: "Part des femmes", data: data.map(d => d.part_femmes), borderColor: C.ambre, backgroundColor: C.ambre, borderDash: [5, 4], tension: .25 }] },
        options: { scales: axes(false, { max: 100, ticks: { callback: v => v + " %" } }),
          plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: c => `${c.dataset.label} : ${nf.format(c.raw)} %` } } } } });
    },
    domaines(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.domaine), datasets: [
          { label: "Idées", data: data.map(d => d.idees), backgroundColor: C.sable, borderRadius: 4 },
          { label: "Incubés", data: data.map(d => d.selectionnes), backgroundColor: C.brun, borderRadius: 4 }] },
        options: { indexAxis: "y", scales: axes(true), onClick: (e, el) => el.length && filtrerPar("domaine", data[el[0].index].code),
          plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { afterBody: it => `Taux de sélection : ${nf.format(data[it[0].dataIndex].taux_selection)} %` } } } } });
    },
    genre(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.genre), datasets: [
          { label: "Idées", data: data.map(d => d.idees), backgroundColor: C.sable, borderRadius: 4 },
          { label: "Incubés", data: data.map(d => d.selectionnes), backgroundColor: C.caramel, borderRadius: 4 },
          { label: "Sortis", data: data.map(d => d.sortis), backgroundColor: C.brun, borderRadius: 4 }] },
        options: { scales: axes(false), plugins: { legend: { position: "bottom" },
          tooltip: { callbacks: { afterBody: it => `Taux de sélection : ${nf.format(data[it[0].dataIndex].taux_selection)} %` } } } } });
    },
    retards(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.domaine), datasets: [
          { label: "À temps", data: data.map(d => d.a_temps), backgroundColor: C.vert },
          { label: "Réalisés en retard", data: data.map(d => d.realise_retard), backgroundColor: C.ambre },
          { label: "En retard (non réalisés)", data: data.map(d => d.en_retard), backgroundColor: C.rouge },
          { label: "À venir", data: data.map(d => d.a_venir), backgroundColor: C.gris }] },
        options: { indexAxis: "y", scales: { x: { stacked: true, grid: { color: C.grille } }, y: { stacked: true, grid: { display: false } } },
          plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { afterBody: it => `Taux de retard : ${nf.format(data[it[0].dataIndex].taux_retard)} %` } } } } });
    },
    financements(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.type), datasets: [{ label: "Montant obtenu", data: data.map(d => d.montant), backgroundColor: C.caramel, borderRadius: 6 }] },
        options: { scales: axes(false, { ticks: { callback: v => fcfa(v) } }), plugins: { legend: { display: false },
          tooltip: { callbacks: { label: c => `${fcfa(c.raw)} (${data[c.dataIndex].n} financements)` } } } } });
    },
    depots(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.mois), datasets: [{ label: "Idées déposées", data: data.map(d => d.n), backgroundColor: C.brun, borderRadius: 4 }] },
        options: { scales: axes(false), plugins: { legend: { display: false } } } });
    },
    filieres(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.filiere), datasets: [
          { label: "Idées", data: data.map(d => d.idees), backgroundColor: data.map(d => d.departement === "TIC" ? C.caramel : (d.departement === "Automobile" ? C.brun2 : C.ambre)), borderRadius: 4 },
          { label: "Incubés", data: data.map(d => d.selectionnes), backgroundColor: C.brun, borderRadius: 4 }] },
        options: { indexAxis: "y", scales: axes(true), onClick: (e, el) => el.length && filtrerPar("filiere", data[el[0].index].code),
          plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { afterBody: it => `Département : ${data[it[0].dataIndex].departement}` } } } } });
    },
    regions(id, data) {
      return this.graphique(id, { type: "bar",
        data: { labels: data.map(d => d.region), datasets: [{ label: "Idées", data: data.map(d => d.n), backgroundColor: C.caramel, borderRadius: 4 }] },
        options: { indexAxis: "y", scales: axes(true), onClick: (e, el) => el.length && filtrerPar("region", data[el[0].index].region),
          plugins: { legend: { display: false } } } });
    },
  };
})();
