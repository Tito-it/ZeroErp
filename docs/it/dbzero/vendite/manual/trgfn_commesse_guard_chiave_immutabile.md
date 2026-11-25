## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_commesse_guard_chiave_immutabile`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) · [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — la commessa e le attività collegate
>
> Approfondimento funzioni:
>
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — costruisce la chiave a 10 dimensioni
> * [vendite.fn_resolve_termini_pagamento](/dbzero/vendite/funzioni/fn_resolve_termini_pagamento) — legge le condizioni dalla commessa
> * [vendite.fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta) — la porta del reset del lotto: la GUC e il proprietario

---
### 🎯 Scopo Principale

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

### La porta del reset del lotto

Il guard lascia passare la scrittura quando la **porta del reset del lotto** è aperta. La legge
[`vendite.fn_porta_reset_lotto_aperta`](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta), che
risponde sì solo se la GUC `zeroerp.maintenance_reset_lotto_draft` è accesa **e** chi scrive è il
proprietario della tabella.

La GUC la accende solo la pulizia del lotto,
[`vendite.fn_cleanup_fatture_by_ids`](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids), riservata
al proprietario, e la spegne prima di uscire: la porta è aperta solo mentre la pulizia lavora. ⛔ Per
l'applicazione la porta è sempre chiusa: accendere la GUC da sé e scrivere diretta non apre niente.

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

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — con la GUC accesa dall'applicazione
  la porta resta chiusa.

---

### Note di migrazione

* 2026-11-25 — la porta del reset si legge da `vendite.fn_porta_reset_lotto_aperta` e chiede anche
  il proprietario; prima bastava la GUC, che l'applicazione poteva accendere da sé
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7).

---

{% include-markdown "signature-core.md" %}
