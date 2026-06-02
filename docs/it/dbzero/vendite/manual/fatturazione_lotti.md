## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_lotti`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)  
> • [config.utilities](/dbzero/config/tabelle/utilities)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
### 🎯 Scopo Principale
(latest review 23-01-2026)
`vendite.fatturazione_lotti` rappresenta il **lotto di fatturazione**, ovvero il contenitore operativo
che fissa i **parametri di calcolo** (competenza, utility, tipo documento, BA, emittente fiscale) e consente la gestione
coerente di **ricalcoli**, **job** e **processi successivi** (emissione, invio, statistiche).

---

### Campi chiave (semantica)

* **Identita` lotto**: `id`, `lock_batch_id` (uuid), `codice`.
* **Parametri di calcolo**: `competenza_mese`, `utility_id`, `tipo_doc_fiscale_id`, `billing_account_id`, `emittente_soggetto_ruolo_id`, `area_geografica_id` (opz.).
* **Tipo lotto**: `tipo_lotto` (MASSIVO | GIORNALIERO).
* **Stati**:
  * `stato_lotto` (IN_ESECUZIONE | COMPLETATO | ERRORE)
  * `stato_doc_fiscale_id` (FK -> `config.stati_doc_fiscale`)
  * `stato_operativo` (APERTO | CHIUSO | ERRORE)
* **Governance**: `meta`, `storicizza`, `tx_id`, audit `data_*`/`user_*`.

---

### Relazioni principali

* **1 lotto → N fatture** tramite `vendite.fatturazione_lotti_fatture`.
* Collegamento a **utility** e **tipo documento** per raggruppamento e policy documento.

---

### Scope emittente e RLS (2026-06-01)

* `emittente_soggetto_ruolo_id` è ora **NOT NULL** (sanazione changeSet
  `20260601-18`: backfill via `fn_resolve_lotto_utility_emittente` + `SET NOT NULL`).
* **RLS in lettura** (Ondata 1, `ENABLE` no-FORCE in `20260601-38`): policy
  `rls_fatturazione_lotti_ef_whitelist` — l'operatore vede solo i lotti con
  emittente nella propria whitelist, via adapter SR
  [`fn_scope_ef_whitelist_via_sr`](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_sr)
  (gate `ruolo_applicativo = 'OPERATORE'`).
* **Scrittura**: write-guard `trg_fatturazione_lotti_a10_guard_emittente_scope_ins_upd`
  (`trgfn_guard_emittente_scope`, modalità `soggetto_ruolo`).

---

### Best practice operative

* Usare `lock_batch_id` come chiave di lock per processi concorrenti.
* Conservare il lotto come riferimento **stabile** per ricalcoli e audit.
* Allineare i parametri di lotto con la funzione di calcolo (competenza, BA, utility, tipo documento).

---

{% include-markdown "signature-core.md" %}
