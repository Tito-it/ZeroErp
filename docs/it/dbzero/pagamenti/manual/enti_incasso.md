## 📘 Documentazione Concettuale – Tabella `pagamenti.enti_incasso`

### 🎯 Scopo Principale
La tabella `pagamenti.enti_incasso` rappresenta i canali di provenienza dei flussi di incasso (banca, poste, PSP, altro), collegando il canale ai riferimenti anagrafici e operativi necessari all'import e riconciliazione.

### 🧩 Relazioni e vincoli principali
- FK verso `pagamenti.centri_riscossione` (`centro_riscossione_id`).
- FK verso `anagrafiche.soggetti_ruoli` (`soggetto_ruolo_id`).
- FK verso `anagrafiche.bank_branches` (`bank_branch_id`).
- `tipo` ammesso: `BANCA`, `POSTE`, `PSP`, `ALTRO`.
- Se `tipo = BANCA`, `bank_branch_id` e` obbligatorio; negli altri casi deve essere `NULL`.
- Vincolo applicativo PSP tramite trigger:
  - `pagamenti.trgfn_enti_incasso_guard_psp()`

### 📝 Note operative
- Per `tipo = PSP` il `soggetto_ruolo_id` deve essere coerente con ruolo `PSP` e censito in `anagrafiche.psp`.
- `regole_match` puo` contenere configurazioni per matching automatico movimenti.

{% include-markdown "signature-core.md" %}
