## 📘 Documentazione Concettuale – Tabella `vendite.resi`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.ddt](/dbzero/vendite/tabelle/ddt) (sorgente)
> [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso)
>
> Funzioni:
> [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso)
> [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Testata del **documento reso di vendita**: entità autonoma che registra il rientro di merce da un
DDT consegnato. Il reso è un **ibrido** — le sue righe possono essere *a credito* (verso nota di
credito) o *per ri-consegna* (merce da rifare e ri-spedire). Brief: `brief-db-resi-vendita.md`.

### Regole chiave

- **Sorgente data-driven** (`sorgente_tipo_id` + `sorgente_uid`, `NOT NULL`): in questa slice
  l'unica sorgente è `DDT_VENDITA`, risolta per **`uid`** (`sorgente_uid = ddt.uid`). Predisposto
  per una futura sorgente `FATTURA` senza rework.
- **Solo da DDT CONSEGNATO** — guard `trgfn_resi_guard_ddt_consegnato` all'INSERT
  (`E_RESO_DDT_NON_CONSEGNATO`): «non si rende ciò che non è stato consegnato».
- **Denormalizzati ereditati** dal DDT sorgente via `trgfn_resi_normalize`
  (`billing_account_id`, `destinatario_soggetto_ruolo_id`, `utility_id`, `valuta_id`,
  `emittente_fiscale_id`). `emittente_fiscale_id` è `NOT NULL`.
- **Scope emittente**: RLS `rls_resi_ef_whitelist` + guard scrittura
  `trgfn_resi_guard_emittente_ba` (`z10`, dopo il normalize).
- **Macchina a stati** data-driven (`config.stati_doc_reso` + `transizioni_stati_reso`),
  enforcement `trgfn_resi_guard_transizione`. `DRAFT → CONFERMATO → (ANNULLATO)`.
- **Numero** assegnato alla **CONFERMA** (NULL in DRAFT) da `trgfn_resi_gen_numero` +
  immutabilità `trgfn_v_resi_protect_num`.
- Storico/audit/tx_id auto-provisioning `dbops`.
