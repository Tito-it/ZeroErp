## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_doc_guard_delete_solo_bozza`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> [vendite.trgfn_dlt_block_ordrig_ddtrig](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig) — il guard gemello, sulle righe
> [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — le righe si toccano solo in bozza
> [script.fn_get_stato_testata_documento](/dbzero/script/funzioni/fn_get_stato_testata_documento) — il lettore dello stato e dell'etichetta
> [script.fn_doc_stato_iniziale_id](/dbzero/script/funzioni/fn_doc_stato_iniziale_id) — lo stato in cui la testata nasce, dal suo vocabolario
> [vendite.trgfn_offerte_commerciali_rientro_padre](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_rientro_padre) — la revisione d'offerta cancellata riporta la madre
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) · [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) · [vendite.commesse](/dbzero/vendite/tabelle/commesse) ·
> [vendite.ordini](/dbzero/vendite/tabelle/ordini) · [vendite.ddt](/dbzero/vendite/tabelle/ddt) · [vendite.resi](/dbzero/vendite/tabelle/resi) · [vendite.contratti](/dbzero/vendite/tabelle/contratti)

---

### 🎯 Scopo Principale

**Un documento si elimina solo se è una bozza vuota**: nello stato in cui nasce,
e senza contenuto.

Trigger `BEFORE DELETE` sulle testate di preventivo, offerta, contratto, ordine,
DDT, reso e commessa, e sulla bozza di una mail (che non ha righe: per lei vale
solo la regola di stato). Se il documento è uscito dalla bozza, o ha ancora del
contenuto, la cancellazione viene rifiutata.

Eliminare un documento serve a una cosa sola: togliere la bozza **abbandonata**,
quella che si crea per poter aggiungere le righe e che resta vuota. Un documento
uscito dalla bozza si **annulla**, e resta al suo posto con la sua storia. Un
documento in bozza con delle righe è un lavoro iniziato: se non serve più si
annulla, oppure se ne tolgono prima le righe.

---

### ⭐ La regola c'era già: qui cambia solo dove vive

Non è una restrizione nuova. Il backend la applicava già (`elimina_ordine`,
`elimina_ddt`, `elimina_reso`, `elimina_preventivo`: stato iniziale e zero righe
attive; `elimina_offerta`: il solo stato). Da quando la regola è nel database il
backend non la ripete: riporta la frase del database (Tid, 2026-11-08: «perché
ripetere la regola»).

Il problema era che viveva **solo lì**. La rispetta chi passa da quei servizi, e
la salta chiunque altro: una funzione del database, uno script di bonifica, una
riconciliazione, un backend futuro.

> Una regola applicata da chi la conosce non è una regola: è una consuetudine.

È scesa nel database in due tempi, per decisione di Tid:

* **2026-08-26**: la metà «in bozza», per ordine e DDT;
* **2026-11-06**: la metà «vuota», e reso e contratto. Un reso confermato si
  cancellava lasciando orfani i suoi movimenti di magazzino; il contratto non
  aveva nessuna regola, e prende quella delle altre testate (scartata
  l'alternativa «il contratto non si cancella mai, solo l'annullo»);
* **2026-11-08**: preventivo, offerta e commessa. Un preventivo accettato si
  cancellava con un `DELETE` diretto, e un'offerta in bozza si portava via le sue
  eccezioni. La regola è una per tutti i documenti di vendita.

---

### ⭐ «Vuota» vuol dire senza righe attive

Una bozza è vuota quando non ha **righe attive**, fra quelle che il catalogo
delle sorgenti le dichiara (`config.sorgenti.righe_table`). È lo stesso
predicato del backend e delle capability (`senza_righe`): una bozza che ha solo
righe disattivate si elimina, e quelle righe la seguono nella cascata.

* **L'offerta** non ha righe proprie (il contenuto viene dal listino): le sue
  righe sono le **eccezioni**.
* **La commessa** è vuota senza **attività** e senza **documenti collegati**
  (`commesse_sorgenti`). Le attività non hanno `attivo`: ognuna conta. Le due
  chiavi esterne sono `NO ACTION` e rifiuterebbero comunque, con un errore senza
  frase: il guard dice prima il perché.

---

### ⭐ Lo stato in cui si nasce lo dice il vocabolario

La bozza non è un codice scritto qui: è lo **stato iniziale** del vocabolario
della testata (colonna `iniziale`), letto con
[`fn_doc_stato_iniziale_id`](/dbzero/script/funzioni/fn_doc_stato_iniziale_id).
Offerta e commessa nascono in `BOZZA`, le altre testate in `DRAFT`: un letterale
le avrebbe rifiutate sempre. La mail, che non ha un vocabolario, tiene la sua
bozza nel suo ramo.

---

### ⭐ La revisione d'offerta cancellata riporta la madre

Quando nasce una revisione, l'offerta madre diventa **superata**. Se la
revisione, ancora bozza vuota, viene eliminata, la madre torna nello stato
d'emissione, come quando la revisione si annulla: lo fa
[`trgfn_offerte_commerciali_rientro_padre`](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_rientro_padre)
(2026-11-08). La madre, invece, non è mai una bozza, e non si elimina.

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

La soglia è scritta `IS DISTINCT FROM` lo stato iniziale, e non `<>`. Se il
lettore dello stato non restituisse nulla, con `<>` il confronto darebbe
`NULL`, l'`IF` non scatterebbe e **la cancellazione passerebbe**.

Con `IS DISTINCT FROM` il guard rifiuta lo stesso, e il messaggio lo dice
(`sconosciuto`). Rifiuta anche se il vocabolario non dichiarasse lo stato
iniziale. Su un verbo distruttivo il default è il no.

---

### ℹ️ Che cosa sa il guard, e che cosa chiede ad altri

* **Lo stato e l'etichetta** del documento li chiede al lettore condiviso
  [`fn_get_stato_testata_documento`](/dbzero/script/funzioni/fn_get_stato_testata_documento),
  lo stesso dei guard di riga: la frase del rifiuto nomina il documento allo
  stesso modo in tutti e due.
* **Quale tabella di righe** guardare lo sa il guard, un ramo per testata (scelto
  per schema e tabella). Sono sette letture statiche; una versione
  parametrizzata costerebbe SQL dinamico per dire la stessa cosa.
* Lo **stato si controlla prima delle righe**, perché i due rimedi sono diversi:
  fuori bozza si annulla, in bozza si toglie il contenuto o si annulla.

---

### Codici errore

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_DELETE_DOC_NON_BOZZA` | `CONFLITTO_STATO` | il documento non è più in bozza |
| `E_DELETE_DOC_CON_RIGHE` | `CONFLITTO_STATO` | il documento è in bozza ma ha ancora del contenuto: righe o eccezioni attive, attività o documenti collegati. Un codice solo per tutti i documenti (Tid, 2026-11-08): il documento lo nomina l'etichetta |
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
  oppure, se è in bozza, lo si svuota. Per il contratto precedente, se
  il collegamento è sbagliato si corregge prima sui successori.
* **L'indice della FK** (`ix_contratti_parent_contratto_id`, parziale
  `IS NOT NULL`) lo governa `dbops.fk_index_policy`: guard e controllo
  referenziale cercano i successori a ogni cancellazione di un contratto. Se è appena stato emesso per
  sbaglio e il suo stato lo consente, si riporta in bozza.

> 📎 changeSet `20260826-22` (ordine e DDT, insieme a `20260826-20` e
> `20260826-21`), `20260925-72` (la bozza email), `20261106-88` … `20261106-91`
> (la bozza vuota, reso e contratto, il contratto precedente), `20261109-25` …
> `20261109-27` (preventivo, offerta e commessa; lo stato iniziale dal
> vocabolario; la revisione d'offerta cancellata).
