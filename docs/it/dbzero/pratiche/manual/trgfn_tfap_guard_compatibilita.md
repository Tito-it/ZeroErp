## 📘 Documentazione Funzione – `pratiche.trgfn_tfap_guard_compatibilita`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione)
> [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi)
> [pratiche.trgfn_tfhe_guard_no_proiezione](/dbzero/pratiche/funzioni/trgfn_tfhe_guard_no_proiezione)
> [pratiche.trgfn_flussi_guard_esito_classe](/dbzero/pratiche/funzioni/trgfn_flussi_guard_esito_classe)

---
### 🎯 Scopo Principale
(review 06-07-2026 — GUIDA D4, brief-db-guida-avanza-esito-proiettato)

Guard **config-time** (`BEFORE INSERT OR UPDATE` su
`pratiche.template_flussi_avanzamento_proiezione`) che protegge la coerenza del binding di
avanzamento su proiezione. Due invarianti:

1. **Solo step non-DOMINIO** (D-B3, codice `TEMPLATE_FLUSSO_PROIEZIONE_STEP_DOMINIO`, 517):
   la proiezione produce **verdetti** (`is_verdetto=true`); uno step `modalita_esito='DOMINIO'`
   vuole esiti di **ramo**, e li rifiuterebbe a runtime via
   `pratiche.trgfn_flussi_guard_esito_classe` (504) **dentro il best-effort** → il milestone non
   avanzerebbe **mai**, in silenzio. Meglio bloccarlo alla configurazione.
2. **Mutua esclusione** con `template_flussi_handler_eventi` `COMPLETATO` **attivo** (D-B10,
   codice `TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER`, 518): uno step o è **projection-driven**
   o è **handler-driven** sul COMPLETATO, **mai entrambi**. Altrimenti l'avanzamento standalone
   (DB) completerebbe il flusso **saltando** l'handler Python → azione di dominio persa in
   silenzio (la divergenza che GUIDA elimina).

---

### Note operative

* Il conflitto (2) si valuta fra binding **entrambi attivi**: un handler `attivo=false` non
  dispatcha, quindi il **cutover** dell'inversione può **disattivarlo** senza `DELETE`, e poi
  inserire il binding G2 (l'ordine atomico è: disattiva handler → inserisci binding).
* Guard **speculare**: `pratiche.trgfn_tfhe_guard_no_proiezione` presidia il lato opposto
  (aggiunta di un handler `COMPLETATO` a uno step che ha già un binding di avanzamento).
* Errori sollevati via `script.fn_log_and_raise_error` (codici 517/518 in
  `config.messaggi_errore`).

---

{% include-markdown "signature-core.md" %}
