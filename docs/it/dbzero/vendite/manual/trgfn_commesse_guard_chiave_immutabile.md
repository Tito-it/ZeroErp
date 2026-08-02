## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_commesse_guard_chiave_immutabile`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse) · [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
>
> **Funzioni:**
>
> • [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — costruisce la chiave a 10 dimensioni
> • [vendite.fn_resolve_termini_pagamento](/dbzero/vendite/funzioni/fn_resolve_termini_pagamento) — legge le condizioni dalla commessa

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

Impedisce di modificare le **condizioni di pagamento** di una commessa
(`termine_pagamento_id`, `modalita_pagamento_id`) quando la commessa **ha già
attività collegate**.

Codice: **`E_COMMESSA_CHIAVE_IMMUTABILE` (576)**.

---

### 🔑 Perché quelle due colonne sono «chiave»

Dalla decisione D-R, termine e modalità sono **elementi della chiave di
raggruppamento** di `fn_get_or_create_commessa` — che da allora ha **10
dimensioni**. Due documenti con condizioni diverse aprono commesse diverse.

Cambiarle a posteriori su una commessa che ha già raccolto lavoro significa
**spostare sotto una chiave nuova ciò che era stato raggruppato sotto quella
vecchia**: la commessa non corrisponde più al criterio che l'ha generata, e la
prossima aggregazione non la ritrova.

---

### 🚦 La soglia è «ha attività collegate», NON lo stato

Scelta deliberata. Il danno non è che la commessa sia avanzata di stato: è che
**qualcosa sia già stato raggruppato** sotto la chiave vecchia.

Conseguenze pratiche:

- commessa ancora **vuota** → modifica **ammessa**, anche se lo stato è avanzato;
- commessa con attività → **respinta**, anche se è appena nata.

Riscrivere lo **stesso** valore è sempre ammesso (`IS DISTINCT FROM`): un `UPDATE`
che non cambia nulla non deve fallire.

---

### Perimetro stretto: `UPDATE OF` le due colonne

Il trigger si sveglia **solo** quando quelle due colonne sono nell'elenco
dell'`UPDATE`. Tutto il resto della commessa resta liberamente modificabile.

⚠️ È anche ciò che ha reso sicuro introdurlo: verificato che **nessuno scrittore
esistente e nessun pgTAP** tocchi quelle due colonne — erano nate il giorno prima
— quindi sugli `UPDATE` già in circolazione (`fn_cambia_stato_commessa`, i test su
`commesse`) il guard **non si sveglia**. Un guard restrittivo si introduce dopo
aver misurato chi passa di lì, non prima.

---

### Bypass GUC

Riconosce la GUC di manutenzione del reset lotto, come gli altri guard di dominio.

---

### 💡 La decisione che questo guard protegge

Il termine «personalizzato» di un documento **non si insegue a valle** risalendo
dalla fattura alla sorgente: **spacca la commessa alla fonte**.

Misurato prima di decidere: una commessa arriva a **32 sorgenti di 4 tipi**
(preventivi, ordini, contratti, DDT), e **contratti e DDT non hanno colonne di
pagamento**. Risalire avrebbe spaccato le fatture per *assenza del campo*, non per
una scelta di qualcuno.

Decidendo alla fonte, la divergenza si vede al push. Questo guard è ciò che
impedisce di annullarla dopo.

---
{% include-markdown "signature-core.md" %}
