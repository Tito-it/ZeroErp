## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_default_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la tabella su cui è montata
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni del workflow
>
> Approfondimento funzioni:
>
> * [pratiche.fn_risolvi_definizione](/dbzero/pratiche/funzioni/fn_risolvi_definizione) — sceglie l'edizione
> * [pratiche.trgfn_pratiche_guard_pin_immutabile](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_pin_immutabile) — tiene fermo il pin dopo la nascita
> * [pratiche.trgfn_template_flussi_default_definizione](/dbzero/pratiche/funzioni/trgfn_template_flussi_default_definizione) — lo stesso default sui template dei flussi

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_default_definizione` fissa l'edizione del workflow di una
pratica alla sua nascita, quando chi la crea non la indica.

---

### ⭐ Il pin è per sempre

Scatta `BEFORE INSERT` su `pratiche.pratiche`, nella fase dei default, prima dei guard. Se
`definizione_id` è vuoto lo risolve con `pratiche.fn_risolvi_definizione` per il tipo di prestazione e
l'emittente della pratica: l'edizione pubblicata dell'emittente vince sul preset.

Una pratica resta sull'edizione con cui è nata, qualunque cosa accada dopo alle definizioni: il pin non
si cambia, e lo impedisce `pratiche.trgfn_pratiche_guard_pin_immutabile`.

* Un pin esplicito passa intatto: la coerenza col tipo la garantisce la FK composita.
* Chi crea la pratica non deve passare la colonna: il default sta nel database, qualunque sia la
  strada di scrittura.

---

### Codici errore

* `E_DEFINIZIONE_NON_TROVATA` — sollevato da `pratiche.fn_risolvi_definizione` quando il tipo non ha
  nessuna edizione pubblicata: la pratica non nasce.

---

### Test

* `pratiche/test-workflow-definizioni-fase0` — una pratica inserita senza definizione riceve il preset
  del tipo.

---

### Note di migrazione

* 2026-07-02 — nasce insieme alle definizioni versionate, prima del vincolo di obbligatorietà sulla
  colonna, così la creazione delle pratiche dal backend resta invariata
  (brief-db-step-dominio-e-definizioni-versionate).

---

{% include-markdown "signature-core.md" %}
