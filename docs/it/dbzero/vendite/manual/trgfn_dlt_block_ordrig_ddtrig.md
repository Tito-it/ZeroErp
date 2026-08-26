## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_dlt_block_ordrig_ddtrig`

> 👀 **Vedi anche**
>
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) — dove vive la protezione vera
> [vendite.trgfn_doc_guard_delete_solo_bozza](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza) — il guard gemello, sulla testata
> [script.fn_get_stato_testata_documento](/dbzero/script/funzioni/fn_get_stato_testata_documento) — il lettore che rende possibile il ramo 1

---

### 🎯 Scopo Principale

**Decide se una riga di documento — di un DDT o di un ordine — si può togliere.**

Trigger `BEFORE DELETE` sulle due tabelle. Ha **tre** esiti, non uno, e il terzo
è che la riga si cancella.

| # | Condizione | Esito |
| --- | --- | --- |
| 1 | il documento **non è più in bozza** | rifiuto — `E_DELETE_RIGA_DOC_NON_BOZZA` |
| 2a | sulla riga c'è un **legame di evasione** | rifiuto — `E_DELETE_BLOCKED_FUL` |
| 2b | la riga è citata da un **reso** o da una **riconsegna** | rifiuto — `E_DELETE_RIGA_DOC_REFERENZIATA` |
| 3 | nessuna delle precedenti | ✅ **la riga si toglie** |

⚠️ **L'ordine dei rami è dominio, non stile.** «Il documento è chiuso» è
l'identità della situazione e va detto per primo: dire «esiste un legame di
evasione» su un DDT già consegnato manderebbe a togliere quel legame, che non è
il rimedio.

---

### ⛔ Rev 2026-08-26 — il guard senza uscita

Fino a quella data **ogni ramo di questa funzione sollevava**, e il `RETURN OLD`
in fondo era **irraggiungibile**. Non esisteva nessuna condizione in cui un
`DELETE` riuscisse, su nessuna delle due tabelle: il caso più innocente possibile
— una riga appena creata, senza nessun legame — veniva rifiutato con
`E_DELETE_NOT_ALLOWED`.

⚠️ **E il perimetro era doppio.** Le righe sono in `ON DELETE CASCADE` dalla loro
testata, e un cascade fa scattare i trigger di riga: non falliva solo «elimina
riga», fallivano anche **«elimina DDT»** ed **«elimina ordine»** su qualunque
documento con almeno una riga. Quattro verbi del backend, tutti scritti
sull'assunzione opposta — `ddt_service.elimina_riga` si dichiarava *«HARD DELETE,
solo DRAFT»* e commentava che il trigger «blocca **se** la riga è già collegata a
un ordine via fulfillment». Quel *se* non esisteva.

---

### ⭐ Che fosse un difetto e non una scelta lo dice il modello

Cinque fatti di struttura, nessuna preferenza:

1. **Il guard era un outlier.** Delle sette tabelle `vendite.*_righe`, solo
   queste due avevano un divieto assoluto: `preventivi_righe`, `resi_righe` e
   `contratti_righe` non hanno nessun guard sul `DELETE`, `fatture_righe` e
   `listini_righe` ne hanno uno **condizionale**.
2. **La protezione era già nelle chiavi esterne** (§ qui sotto).
3. **La tracciabilità era già garantita** da `trg_*_z90_storico_upd_dlt`, che è
   `BEFORE DELETE OR UPDATE`: una riga cancellata lascia traccia comunque.
4. **Accanto viveva un secondo ramo morto**:
   `trg_ordini_righe_z90_ricalcola_totali_dlt` è `AFTER DELETE FOR EACH STATEMENT`
   e ricalcola i totali dell'ordine dopo una cancellazione che non poteva
   avvenire. Non era mai girato. Lo schema intorno era costruito assumendo che il
   `DELETE` ci fosse.
5. **Il «delete logico preferito»** che la versione precedente di questa scheda
   indicava come strada **non lo implementava nessuno**: nessun punto del backend
   scrive `attivo = false` su queste due tabelle.

ℹ️ È sopravvissuto per una ragione sola: **nessun test eseguiva un `DELETE` vero**
su queste tabelle, e nessuno nominava il guard o i suoi codici. Il ramo cieco non
era coperto male — non era coperto affatto.

---

### ⭐ Il ramo 2 non è un presidio: è un traduttore

A impedire la cancellazione di una riga già usata a valle **sono le chiavi
esterne**, non questo trigger:

| Figlia | `ON DELETE` | Effetto senza il trigger |
| --- | --- | --- |
| `ordini_righe_fulfillment` | `RESTRICT` | blocca comunque |
| `resi_righe`, `resi_righe_riconsegne` | `NO ACTION` | bloccano comunque |
| `ddt_righe_componenti`, `ordini_righe_componenti` | `CASCADE` | muoiono con la riga, ed è giusto |
| `note_ddt`, `note_ordini` | `CASCADE` | muoiono con la riga, ed è giusto |

Il trigger esiste per **dire perché**, al posto di una violazione tecnica grezza
(`23503`) a metà lavoro. È lo stesso criterio già scritto per le figlie di
`vendite.fatture`.

⚠️ **La conseguenza è che la protezione va sorvegliata dove vive davvero.** Se un
domani una di quelle chiavi venisse degradata a `SET NULL` o `CASCADE`, il
trigger continuerebbe a dire la sua frase nei casi che vede e la protezione
sparirebbe per tutti gli altri percorsi, **in silenzio**. È il test 9 di
`test-delete-righe-documento-bozza-v1` a presidiarlo.

---

### ⚠️ La testata che sparisce, e perché serve un guard gemello

In un `BEFORE DELETE` di riga innescato da `ON DELETE CASCADE` **la testata
risulta già cancellata**; in un `DELETE` diretto sulla riga invece si vede
(verificato il 2026-08-26 con tabelle temporanee).

L'assenza della testata è quindi il segnale **«questo è un cascade»**, e in quel
caso la regola di stato l'ha già applicata
[`trgfn_doc_guard_delete_solo_bozza`](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza)
sulla testata. Qui non si ricontrolla e si prosegue ai legami a valle, che
valgono comunque.

ℹ️ Non è un buco: `ddt_id` e `ordine_id` sono `NOT NULL` con chiave esterna,
quindi una riga orfana non esiste e «assente» non può voler dire altro.

⛔ **I due guard sono una coppia.** Togliendone uno, l'altro non si indebolisce:
diventa **aggirabile**.

---

### ⚠️ Perché lo stato si legge con una `SECURITY DEFINER`

`vendite.ddt` e `vendite.ordini` hanno la RLS attiva; `vendite.ddt_righe` e
`vendite.ordini_righe` **no**. Un chiamante fuori perimetro raggiunge quindi la
riga senza vedere la sua testata: una lettura *invoker* tornerebbe zero righe,
questo guard leggerebbe «testata assente» e lascerebbe passare — **fail-open
proprio per chi sta fuori**.

Per questo la lettura passa da
[`script.fn_get_stato_testata_documento`](/dbzero/script/funzioni/fn_get_stato_testata_documento),
che ha un contratto chiuso: zero righe = la testata non c'è.

⭐ Le tabelle dei legami a valle (`ordini_righe_fulfillment`, `resi_righe`,
`resi_righe_riconsegne`) **non hanno RLS**, quindi i loro conteggi sono un dato e
non la fotografia del perimetro di chi chiama. Se un giorno l'acquisissero, il
guard non perderebbe nulla in silenzio: tornerebbe a fermare la chiave esterna,
com'era prima che il guard esistesse.

---

### Codici errore

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_DELETE_RIGA_DOC_NON_BOZZA` | `CONFLITTO_STATO` | il documento è uscito dalla bozza |
| `E_DELETE_BLOCKED_FUL` | `CONFLITTO_STATO` | la riga è già stata evasa o consegnata |
| `E_DELETE_RIGA_DOC_REFERENZIATA` | `CONFLITTO_STATO` | la riga è citata da un reso o da una riconsegna |
| `E_DELETE_NOT_ALLOWED` | `NON_PERMESSO` | ⚠️ **solo** il ramo «tabella non prevista»: errore di montaggio del trigger |

⭐ **`E_DELETE_NOT_ALLOWED` è uscito dai rami di dominio, ed è una scelta.** Quel
codice è condiviso con altri tre guard (`script.trgfn_delete_block_by_guc`,
`vendite.trgfn_event_log_append_only`, `vendite.trgfn_logs_guard_delete`):
lasciarlo fuori significa che il suo testo non va toccato e quei tre restano
intatti.

⚠️ **`E_DELETE_BLOCKED_FUL` ha perso un segnaposto** nella stessa revisione:
nominava tabella e id — cioè parlava a uno sviluppatore — e ora nomina il
documento. Chi ne cambia di nuovo l'arità deve cercare chi lo solleva, non chi
asserisce sul testo: il sollevatore è **uno solo**, questa funzione.

---

### Note operative

* **Fascia `_a10_`** (guard) su entrambe le tabelle:
  `trg_ddt_righe_a10_block_ddt_dlt` e `trg_ordini_righe_a10_block_dlt`.
* La funzione dispaccia su `TG_TABLE_NAME` e i due rami leggono testate diverse:
  **provarne uno solo lascia l'altro scoperto**, ed è esattamente com'è andata
  finora.
* Presidio: `db/pgtap/vendite/test-delete-righe-documento-bozza-v1.sql`, 10 test.
  I due che contano sono il **3** e il **7** — quelli che verificano che qualcosa
  **riesca**. I test sul rifiuto passavano anche prima, per il motivo sbagliato.

> 📎 changeSet `20260826-21`, insieme a `20260826-20` e `20260826-22`. Decisioni
> di Tid del 2026-08-26: la regola «solo bozza» scende nel DB, e i verbi di
> cancellazione devono funzionare.
