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
(latest review 12-11-2026)
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
  * `stato_doc_fiscale_id` (FK -> `config.stati_doc_fiscale`, **sempre valorizzato**): il lotto
    nasce nello stato iniziale del vocabolario, che mette il trigger della nascita
    (`trg_fatturazione_lotti_a05_stato_iniziale_ins`) quando l'`INSERT` non lo dice; un altro
    stato alla nascita è rifiutato. Gli altri stati si raggiungono dalla matrice, coi verbi del lotto.
  * `stato_operativo` (APERTO | CHIUSO | ERRORE)
* **Riapertura** (dal 03-08-2026): `riaperto_il` (timestamptz, `NULL` = mai
  riaperto) — istante in cui il lotto è stato riportato in bozza **di proposito**
  da [`fn_riporta_lotto_a_draft`](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft).
  Serve a distinguere **«riaperto»** da **«rotto»**: senza, l'unico modo di far
  ripartire il lotto sarebbe marcarlo in ERRORE, cioè dire una cosa falsa che i
  cruscotti mostrerebbero in rosso. ⚠️ **Non è uno stato** e non sostituisce
  nessuno dei tre sopra; va riportata a vuoto quando il lotto avanza oltre la
  bozza, o il lotto rifarebbe lo stesso passo all'infinito.
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

### 🔄 rev 2026-08-25 — `data_documento`, la data dichiarata

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-4**, **DB-11**).

Nuova colonna `data_documento date NULL`, **facoltativa**.

| valore | effetto |
| --- | --- |
| `NULL` | nessuno ha dichiarato niente: vince la `politica_data_documento` del **registro** |
| valorizzata | vince lei, per **tutti** i documenti del lotto, qualunque sia il loro registro |

⚠️ **Il `NULL` significa qualcosa, e per questo la colonna non ha default.** Il
`NULL` è il caso **normale**: un default — anche `script.fn_data_operativa()` —
trasformerebbe il silenzio in una dichiarazione, con la conseguenza che la
politica del registro non verrebbe più letta da nessuno.

#### Ci atterrano due cose

1. la data facoltativa alla **creazione del lotto** (BE-1 / FE-1);
2. la data digitata nel dialog **«Rendi definitive»**, scritta da
   [`fn_imposta_data_documento_lotto`](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto)
   prima di numerare — che è anche il modo di rimediare a un rifiuto del cancello
   di monotonia.

⭐ È la colonna che rende vera la frase *«una data sola per l'intero atto»*: un
lotto può contenere documenti di registri con politiche diverse, e senza una
dichiarazione unica un atto solo produrrebbe date diverse.

#### ⚠️ Scriverla non è una scrittura muta

Quattro trigger di questa tabella non hanno `UPDATE OF`, quindi scattano su
qualunque `UPDATE` — compreso questo:

* `trgfn_guard_emittente_scope` — ⭐ **ed è voluto**: chi non ha il lotto nel
  proprio perimetro non ne cambia la data;
* audit `data_update` / `user_update`;
* `tx_id`;
* **storico** — ⭐ la ridichiarazione di una data fiscale lascia traccia.

---

{% include-markdown "signature-core.md" %}
