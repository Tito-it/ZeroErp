## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_attivita_guard_prezzo_rettifica()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> • [vendite.resi_righe_accrediti](/dbzero/vendite/tabelle/resi_righe_accrediti)
>
Approfondimento funzioni:
> • [vendite.fn_accredita_riga_reso](/dbzero/vendite/funzioni/fn_accredita_riga_reso)
> • [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
> • [vendite.trgfn_commesse_attivita_guard_quantita_immutabile](/dbzero/vendite/funzioni/trgfn_commesse_attivita_guard_quantita_immutabile)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — decisione di Tid del 2026-08-20, brief nota di credito §42.2)

**Il prezzo di una riga `RETTIFICA` non è un dato da tenere aggiornato: è una citazione.**

Quando `fn_accredita_riga_reso` crea la riga di rettifica, il prezzo lo **copia** dalla riga
di fattura che sta rettificando — non lo ricalcola e non lo rilegge dal listino. È la
condizione perché la nota di credito corrisponda al documento che dichiara di correggere.
Cambiare quel prezzo significa accreditare al cliente un importo diverso da quello che gli è
stato fatturato.

Il guard blocca il **cambiamento** di `prezzo_snapshot` o `prezzo_bloccato` su ogni riga con
`tipo_movimento = 'RETTIFICA'`.

---

### Aggancio

Trigger `trg_commesse_attivita_a10_guard_prezzo_rettifica_upd` — fase `_a10_`,
`BEFORE UPDATE OF prezzo_snapshot, prezzo_bloccato` su `vendite.commesse_attivita`,
`FOR EACH ROW`.

---

### ⚠️ Perché sta nel database e non nel backend

Perché quel prezzo si scrive con un `UPDATE` **diretto** (`update_attivita_prezzo` nel
repository), non passando da una funzione madre. Un controllo applicativo sarebbe quindi una
convenzione, non un blocco: chiunque scrivesse quella colonna per un'altra strada — un altro
repository, uno script, una correzione manuale — lo aggirerebbe senza accorgersene.

È la stessa ragione per cui `tipo_movimento` è una colonna con CHECK e non una chiave dentro
un JSONB di meta: ciò che deve valere sempre va messo dove nessuno può non passarci.

---

### Regole applicate

Blocca quando **entrambe**:

1. `OLD.tipo_movimento = 'RETTIFICA'`;
2. `prezzo_snapshot` **oppure** `prezzo_bloccato` cambia (`IS DISTINCT FROM`).

⭐ **Blocca il cambiamento, non la scrittura.** Un `UPDATE` che riscrive lo stesso valore
passa: è ciò che permette all'`ON CONFLICT DO UPDATE` di `fn_upsert_commessa_attivita` di
ripassare sulla riga senza rompersi.

---

### ⚠️ Non dipende dallo stato di emissione — a differenza del gemello

Il guard sulla quantità agisce solo su righe già emesse. Questo agisce **in qualunque
stato**, e la differenza è voluta:

* il gemello protegge **un fatto già uscito**;
* questo protegge **una citazione**, che è sbagliata anche prima di uscire — anzi
  soprattutto prima, perché è lì che i tre percorsi di pricing (riallinea, variazione
  eccezionale, sblocca) la toccherebbero.

---

### ⛔ Nessun bypass di manutenzione

Il gemello sulla quantità riconosce la GUC `zeroerp.maintenance_reset_lotto_draft`. Questo
**no**, deliberatamente: è stato verificato che il reset lotto (`fn_cleanup_fatture_by_ids`)
scrive su questa tabella soltanto `stato_emissione`, quindi non incontra mai questo guard.

Una porta di servizio sul prezzo di una nota di credito dev'essere una decisione, mai
un'eredità copiata dal guard accanto.

⚠️ `prezzo_da_riallineare` **non** è fra le colonne guardate: è stato misurato che nessun
percorso lo porta a `true` su una rettifica. È un'assunzione basata su una misura, quindi va
riverificata se nascono nuovi percorsi di pricing.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE` (936) | Cambio di `prezzo_snapshot` o `prezzo_bloccato` su riga `RETTIFICA` |

Sollevato via `script.fn_log_and_raise_error`; il context riporta **entrambi** i prezzi in
versione vecchia e nuova (`prezzo_old`/`prezzo_new`, `bloccato_old`/`bloccato_new`), così il
log dice quale delle due colonne è stata toccata.

---

{% include-markdown "signature-core.md" %}
