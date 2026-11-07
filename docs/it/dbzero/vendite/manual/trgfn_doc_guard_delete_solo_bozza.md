## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_doc_guard_delete_solo_bozza`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> [vendite.trgfn_dlt_block_ordrig_ddtrig](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig) — il guard gemello, sulle righe
> [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — le righe si toccano solo in bozza
> [script.fn_get_stato_testata_documento](/dbzero/script/funzioni/fn_get_stato_testata_documento) — il lettore dello stato e dell'etichetta
> [vendite.ordini](/dbzero/vendite/tabelle/ordini) · [vendite.ddt](/dbzero/vendite/tabelle/ddt) · [vendite.resi](/dbzero/vendite/tabelle/resi) · [vendite.contratti](/dbzero/vendite/tabelle/contratti)

---

### 🎯 Scopo Principale

**Un documento si elimina solo se è una bozza vuota**: in bozza, e senza righe
attive.

Trigger `BEFORE DELETE` sulle testate di ordine, DDT, reso e contratto, e sulla
bozza di una mail (che non ha righe: per lei vale solo la regola di stato). Se il
documento è uscito dalla bozza, o ha ancora righe, la cancellazione viene
rifiutata.

Eliminare un documento serve a una cosa sola: togliere la bozza **abbandonata**,
quella che si crea per poter aggiungere le righe e che resta vuota. Un documento
uscito dalla bozza si **annulla**, e resta al suo posto con la sua storia. Un
documento in bozza con delle righe è un lavoro iniziato: se non serve più si
annulla, oppure se ne tolgono prima le righe.

---

### ⭐ La regola c'era già: qui cambia solo dove vive

Non è una restrizione nuova. Il backend la applicava già (`elimina_ordine`,
`elimina_ddt`, `elimina_reso`: stato iniziale e zero righe attive), e la
applica ancora, come controllo preventivo.

Il problema era che viveva **solo lì**. La rispetta chi passa da quei servizi, e
la salta chiunque altro: una funzione del database, uno script di bonifica, una
riconciliazione, un backend futuro.

> Una regola applicata da chi la conosce non è una regola: è una consuetudine.

È scesa nel database in due tempi, per decisione di Tid:

* **2026-08-26**: la metà «in bozza», per ordine e DDT;
* **2026-11-06**: la metà «vuota», e reso e contratto. Un reso confermato si
  cancellava lasciando orfani i suoi movimenti di magazzino; il contratto non
  aveva nessuna regola, e prende quella delle altre testate (scartata
  l'alternativa «il contratto non si cancella mai, solo l'annullo»).

---

### ⭐ «Vuota» vuol dire senza righe attive

Una bozza è vuota quando non ha **righe attive**. È lo stesso predicato del
backend e delle capability (`senza_righe`): una bozza che ha solo righe
disattivate si elimina, e quelle righe la seguono nella cascata.

---

### ⛔ Il contratto precedente non si elimina sotto i suoi successori

Un contratto può dichiarare il suo **contratto precedente**
(`parent_contratto_id`). Il precedente non si elimina finché qualche contratto
lo dichiara, nemmeno se è una bozza vuota: i successori perderebbero il
riferimento da cui nascono, senza che nessuno se ne accorga (Tid, 2026-11-07).

A rifiutare è la **chiave esterna** `fk_contratti_parent`, che dal 2026-11-07 è
`ON DELETE NO ACTION`: prima era `SET NULL`, e staccava i successori in silenzio.
Il guard dice prima il perché, con lo stesso predicato della FK e il numero dei
successori. È la stessa coppia del fulfillment delle righe: la FK è la
protezione, il guard la frase.

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
debole: diventa **aggirabile**. Il montaggio lo presidiano il test 10 di
`test-delete-righe-documento-bozza-v1` e il test 1 di
`test-delete-testate-solo-bozza-vuota-v1`.

---

### ⭐ Perché è `SECURITY DEFINER`

La metà «vuota» legge le **righe**, che hanno regole di visibilità per riga
(RLS). E la cascata che segue un `DELETE` permesso **non** passa dalla RLS:
cancella tutte le righe della testata, anche quelle che il chiamante non vede.

Un guard che contasse le righe con gli occhi del chiamante giudicherebbe su una
parte, e la cascata agirebbe sul tutto. Il guard gira quindi con i privilegi del
proprietario, come il lato «in uscita» della provenienza: **come una chiave
esterna, vede anche ciò che il chiamante non vede**. Il `search_path` è fissato
a `pg_catalog, pg_temp`, e ogni nome è scritto per intero.

---

### ⚠️ Fail-closed, e si vede nella condizione

La soglia è scritta `IS DISTINCT FROM 'DRAFT'` e non `<> 'DRAFT'`. Se il
lettore dello stato non restituisse nulla, con `<>` il confronto darebbe
`NULL`, l'`IF` non scatterebbe e **la cancellazione passerebbe**.

Con `IS DISTINCT FROM` il guard rifiuta lo stesso, e il messaggio lo dice
(`sconosciuto`). Su un verbo distruttivo il default è il no.

---

### ℹ️ Che cosa sa il guard, e che cosa chiede ad altri

* **Lo stato e l'etichetta** del documento li chiede al lettore condiviso
  [`fn_get_stato_testata_documento`](/dbzero/script/funzioni/fn_get_stato_testata_documento),
  lo stesso dei guard di riga: la frase del rifiuto nomina il documento allo
  stesso modo in tutti e due.
* **Quale tabella di righe** guardare lo sa il guard, un ramo per testata (scelto
  per schema e tabella). Sono quattro letture statiche; una versione
  parametrizzata costerebbe SQL dinamico per dire la stessa cosa.
* Lo **stato si controlla prima delle righe**, perché i due rimedi sono diversi:
  fuori bozza si annulla, in bozza si tolgono le righe o si annulla.

---

### Codici errore

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_DELETE_DOC_NON_BOZZA` | `CONFLITTO_STATO` | il documento non è più in bozza |
| `E_DELETE_DOC_CON_RIGHE` | `CONFLITTO_STATO` | il documento è in bozza ma ha ancora righe attive |
| `E_DELETE_CONTRATTO_CON_SUCCESSIVI` | `CONFLITTO_STATO` | il contratto è il precedente di altri contratti |
| `E_DOC_TIPO_NON_GESTITO` | `TECNICO` | il trigger è montato su una tabella che la funzione non conosce |

* **Nei segnaposti va l'etichetta del documento** (e, per la bozza, il suo
  stato; per il contratto precedente, il numero dei successori): sono le cose che servono a capire il rifiuto e che cosa fare. Nessun
  nome di tabella, nessun id di riga: quelli viaggiano nel contesto.
* **Nessuna chiave `campo` nel contesto**: su un `CONFLITTO_STATO` non c'è nessun
  campo da accendere in un form, è la *situazione* a non consentire
  l'operazione.

---

### Note operative

* **Fascia `_a10_`** (guard). I `BEFORE ROW` girano in **ordine alfabetico**:
  `a10` precede `trg_*_z90_storico_upd_dlt`, quindi il rifiuto arriva prima che
  la storicizzazione lavori.
* Il rimedio, quando rifiuta, **non è insistere**: si annulla il documento,
  oppure, se è in bozza, se ne tolgono le righe. Per il contratto precedente, se
  il collegamento è sbagliato si corregge prima sui successori.
* **L'indice della FK** (`ix_contratti_parent_contratto_id`, parziale
  `IS NOT NULL`) lo governa `dbops.fk_index_policy`: guard e controllo
  referenziale cercano i successori a ogni cancellazione di un contratto. Se è appena stato emesso per
  sbaglio e il suo stato lo consente, si riporta in bozza.

> 📎 changeSet `20260826-22` (ordine e DDT, insieme a `20260826-20` e
> `20260826-21`), `20260925-72` (la bozza email), `20261106-88` … `20261106-91`
> (la bozza vuota, reso e contratto, il contratto precedente).
