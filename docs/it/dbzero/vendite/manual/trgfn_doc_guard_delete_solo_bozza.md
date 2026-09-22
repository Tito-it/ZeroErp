## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_doc_guard_delete_solo_bozza`

> 👀 **Vedi anche**
>
> [vendite.trgfn_dlt_block_ordrig_ddtrig](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig) — il guard gemello, sulle righe
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)

---

### 🎯 Scopo Principale

**Un documento si elimina solo finché è in bozza.**

Trigger `BEFORE DELETE` sulle testate di DDT e ordine. Se il documento è uscito
dalla bozza, la cancellazione viene rifiutata: la strada è l'annullamento, che
lascia il documento e la sua storia al loro posto.

---

### ⭐ La regola c'era già: qui cambia solo dove vive

Non è una restrizione nuova. `_STATI_MODIFICABILI = {'DRAFT'}` era già scritto
in `ddt_service` e in `ordini_service`, e `elimina_ddt` / `elimina_ordine` lo
applicavano.

Il problema era che viveva **solo lì**. Una regola in due `frozenset` Python la
rispetta chi passa da quei due servizi, e la salta chiunque altro: una funzione
del database, uno script di bonifica, una riconciliazione, un backend futuro.

> Una regola applicata da chi la conosce non è una regola: è una consuetudine.

Decisione di Tid, 2026-08-26: scende nel database.

---

### ⛔ E chiude una porta di servizio: il cascade

Questo è il motivo per cui il guard **non è opzionale**, ed è la parte meno
evidente.

Le righe di documento sono in `ON DELETE CASCADE` dalla loro testata. In un
`BEFORE DELETE` di riga innescato da un cascade **la testata risulta già
cancellata** — verificato il 2026-08-26 con tabelle temporanee: in un `DELETE`
diretto sulla riga la testata si vede, in un cascade no.

Il guard di riga non può quindi leggerne lo stato, e la sua unica risposta
corretta è *«di questo risponde la testata»*. Senza un guard **sulla** testata,
cancellare il documento diventerebbe il modo di cancellare le righe di un
documento chiuso senza che nessuno abbia controllato niente.

⭐ **I due guard sono una coppia.** Togliendone uno, l'altro non diventa più
debole: diventa **aggirabile**. È il test 10 di
`test-delete-righe-documento-bozza-v1` a presidiare il montaggio di entrambi.

---

### ⚠️ Fail-closed, e si vede nella condizione

La soglia è scritta `IS DISTINCT FROM 'DRAFT'` e non `<> 'DRAFT'`. Se il
vocabolario degli stati non restituisse nulla — una riga di stato mancante, che
la chiave esterna non dovrebbe permettere — con `<>` il confronto darebbe `NULL`,
l'`IF` non scatterebbe e **la cancellazione passerebbe**.

Con `IS DISTINCT FROM` il guard rifiuta lo stesso, e il messaggio lo dice
(`sconosciuto`). Su un verbo distruttivo il default è il no.

---

### ℹ️ Perché non è una funzione generica — e perché quella delle righe sì

Il progetto ha l'idioma delle trigger function parametrizzate
(`dbops.trgfn_child_requires_active_parent`), e qui **non paga**: le due testate
hanno tabelle di stato diverse (`config.stati_doc_ddt`, `config.stati_doc_ordini`)
e colonne diverse (`stato_doc_ddt_id`, `stato_doc_ordine_id`). Una versione
generica richiederebbe SQL dinamico su **due** assi per coprire **due** casi.

⭐ Sulle **righe** invece la generica esiste dal 2026-09-22
([`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza)),
e non contraddice questa scelta: lì la conoscenza del documento non sta nel
trigger ma nel lettore
[`fn_get_stato_testata_documento`](/dbzero/script/funzioni/fn_get_stato_testata_documento),
che dispaccia sul tipo — il trigger legge la colonna FK con `to_jsonb` e non
compone SQL. Con tre tabelle di righe e tre documenti, e due copie parziali
della stessa regola già a DB, il building block era la forma giusta.

Qui si tiene la forma del guard gemello, che già dispaccia su
`TG_TABLE_NAME`: funzioni della stessa famiglia che si leggono allo stesso
modo.

---

### Codici errore

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_DELETE_DOC_NON_BOZZA` | `CONFLITTO_STATO` | il documento non è più in bozza |
| `E_DOC_TIPO_NON_GESTITO` | `TECNICO` | il trigger è montato su una tabella che la funzione non conosce |

* **Nei segnaposti vanno l'etichetta del documento e il suo stato**: sono le due
  cose che servono a capire perché il rifiuto e cosa fare. Nessun nome di
  tabella, nessun id di riga — quelli viaggiano nel contesto.
* **Nessuna chiave `campo` nel contesto**: su un `CONFLITTO_STATO` non c'è nessun
  campo da accendere in un form — è la *situazione* a non consentire
  l'operazione.

---

### Note operative

* **Fascia `_a10_`** (guard). Sulle due testate non esiste nessun altro `BEFORE
  DELETE` oltre a `trg_*_z90_storico_upd_dlt`, e i `BEFORE ROW` girano in **ordine
  alfabetico**: `a10` precede `z90`, quindi il rifiuto arriva prima che la
  storicizzazione lavori.
* **Nessuna lettura sotto RLS**: lo stato sta su `OLD`, cioè sulla riga che il
  chiamante sta già cancellando, e il vocabolario `config.stati_doc_*` non ha
  regole di visibilità per riga. È la differenza con i guard di riga (il
  traduttore dei legami e il BB «solo in bozza»), che devono leggere una
  **tabella diversa** e per questo passano da una
  [`SECURITY DEFINER`](/dbzero/script/funzioni/fn_get_stato_testata_documento).
* Il rimedio, quando rifiuta, **non è insistere**: si annulla il documento. Se è
  appena stato emesso per sbaglio e il suo stato lo consente, si riporta in bozza
  e poi si elimina.

> 📎 changeSet `20260826-22`, insieme a `20260826-20` e `20260826-21`. Decisioni
> di Tid del 2026-08-26: la regola «solo bozza» scende nel DB, e i verbi di
> cancellazione devono funzionare.
