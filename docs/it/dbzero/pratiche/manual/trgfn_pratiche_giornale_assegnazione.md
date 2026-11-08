## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_giornale_assegnazione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica riassegnata
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si scrive l'evento

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_giornale_assegnazione` scrive nel giornale l'azione
`ASSEGNAZIONE_CAMBIATA` quando cambia l'assegnatario di una pratica: la risorsa umana o l'unità
organizzativa.

---

### La regola

* Scatta dopo l'aggiornamento della pratica, e solo se almeno una delle due colonne di assegnazione
  cambia davvero valore.
* La riga del giornale è della pratica (senza flusso), con origine `SISTEMA`; il dettaglio porta la
  risorsa umana e l'unità organizzativa, prima e dopo, anche quella delle due che non è cambiata.
* La transazione della riga è quella della pratica; se manca, quella della sessione.

---

{% include-markdown "signature-core.md" %}
