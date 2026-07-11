## 📘 Documentazione Concettuale – Tabella vendite.contratti_indirizzi

>👀 Vedi anche
>
> •[vendite.contratti](/dbzero/vendite/tabelle/contratti)
> •[config.tipi_indirizzi_allowed](/dbzero/config/tabelle/tipi_indirizzi_allowed)
> •[vendite.trgfn_tipi_indirizzi_only_allowed](/dbzero/vendite/funzioni/trgfn_tipi_indirizzi_only_allowed)

### 🎯 Scopo Principale

Snapshot degli indirizzi collegati alla testata di un **contratto**, uno per tipo
(univocità `contratto_id, tipo_indirizzo_id`). Struttura **identica** alle altre
tabelle `*_indirizzi` documento (snapshot JSONB congelato + `origine_indirizzo_id`
/ `origine_soggetto_ruolo_id` soft FK `SET NULL`, `tx_id`).

Introdotta dal brief indirizzi-documenti (2026-07-11) per la **simmetria piena**.

### Regole & Trigger

- Whitelist tipi ammessi per ambito **`CONTRATTI`** (`FATT`, `CON`, `FORNITURA`)
  letta da `config.tipi_indirizzi_allowed` via
  `trg_contratti_indirizzi_a10_ins_upd_only_allowed_tipi` →
  `vendite.trgfn_tipi_indirizzi_only_allowed('CONTRATTI')`.
- Al push **offerta → contratto** (`fn_push_offerta_a_contratto`) gli indirizzi
  dell'offerta vengono copiati 1:1, filtrati sull'ambito `CONTRATTI`.
- Snapshot congelato: modifiche anagrafiche successive non retroagiscono.

### 📘 Shape dello snapshot

Vedi [`vendite.ddt_indirizzi`](/dbzero/vendite/manual/ddt_indirizzi) e la funzione
`script.fn_snapshot_indirizzo` (fonte unica dello shape lato server).
