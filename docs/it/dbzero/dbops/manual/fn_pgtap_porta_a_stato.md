## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_porta_a_stato`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) — la mappa delle testate: colonna di stato, vocabolario, matrice
> * [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo) — la porta che chiude il cambio di stato al verbo
> * [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) — l'azione e la natura (manuale o di processo) di un passaggio
> * [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) — lo stato voluto, per codice
> * [dbops.fn_pgtap_concedi_azione](/dbzero/dbops/funzioni/fn_pgtap_concedi_azione) — l'azione del passaggio concessa all'operatore del contesto
> * [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — il lock che rende necessaria la forma «bozza, righe, transizioni»
> * [vendite.fn_chiudi_versioni_listino_scadute](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute) — il verbo di processo che chiude una versione di listino
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Porta una testata di fixture dallo stato corrente allo stato voluto, per le strade vere: cerca
nella matrice dei passaggi della testata il percorso più corto e lo percorre un passo alla
volta, ogni passo dal verbo del documento. Restituisce il codice dello stato raggiunto, che è
sempre quello chiesto: se il passaggio non è avvenuto, solleva.

Il test crea la testata (che nasce nel suo stato iniziale), le scrive in bozza ciò che i
passaggi pretendono — righe, indirizzi, prezzi — poi chiede lo stato.

---

### ⭐ Perché esiste

Le righe dei documenti di vendita si scrivono solo con il documento in bozza, e un documento
nasce solo nel suo stato iniziale. Molti pgTAP costruivano la testata **già** fuori bozza (un
ordine confermato, un preventivo accettato) e poi ci mettevano le righe: un documento che il
modello non sa produrre, e che il lock rifiuta. La forma giusta è quella della produzione —
bozza, righe, transizioni — e «quali cambi di stato, in che ordine», scritto in ogni test,
sarebbe la stessa regola in decine di copie: ha una sede.

---

### Le testate che conosce

Quelle della mappa comune [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello):
preventivo, offerta, contratto, ordine, bolla, reso, commessa, fattura, lotto di fatturazione e
versione di listino. Oggi hanno **tutte** la porta, cioè il cambio di stato si fa solo dal loro
verbo; la fixture lo legge dal catalogo (il trigger della porta montato sulla tabella), non da
un elenco.

| Testata | Ogni passo è | Passaggi del percorso |
| --- | --- | --- |
| bolla, preventivo, ordine, contratto, commessa | il verbo di cambio di stato del documento | solo i manuali |
| offerta | il verbo di cambio di stato, con una motivazione della fixture dove il passaggio la chiede (rifiuto, annulli) | solo i manuali |
| reso | la conferma o l'annullo del reso | solo i manuali |
| fattura | il verbo di processo della fattura | manuali e di processo, i soli della fattura singola |
| lotto di fatturazione | il verbo del lotto sui passaggi manuali, il passo della pipeline sugli altri | manuali e di processo, i soli del lotto |
| versione di listino | l'attivazione (che chiude anche le versioni precedenti sovrapposte) o la chiusura delle scadute | manuali e di processo |

Gli stati di **processo** delle testate della prima metà non sono nel percorso: si
costruiscono facendo accadere la causa. L'ordine evaso o parzialmente evaso si costruisce
evadendo ([dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine));
l'offerta superata creando una revisione; l'annullo di un'offerta con legami passa dal suo
verbo d'annullo, non da qui.

Alcuni stati vogliono un dato che il test scrive prima di chiederli: il contratto cessato
vuole la fine validità arrivata; la versione di listino chiusa vuole la fine validità già
passata. Il lotto si porta avanti **vuoto**: un lotto con fatture si muove col giro del
dominio.

Una testata con la porta di cui la fixture non conosce il verbo si ferma.

---

### Che cosa decide la matrice e che cosa decidono i verbi

* **Il percorso** lo decide la matrice della testata: solo passaggi e stati attivi, senza
  rivisitare uno stato. A parità di lunghezza vince il percorso con gli id di stato minori: una
  scelta fissa, non quella del piano.
* **L'azione** che un passaggio chiede viene **concessa** all'operatore del contesto prima del
  passo: la fixture porta lo stato, non prova il permesso.
* **Ogni passo** passa dai controlli veri: righe presenti, aliquote, prezzi autorizzati,
  emettibilità. Un documento che non si potrebbe confermare la fixture non lo conferma, e il
  test lo scopre lì, con il motivo vero.

---

### Quando non si usa

* Una testata che resta in bozza.
* Una transizione che è **il caso del test**: lì il cambio di stato si chiama esplicito, perché
  è proprio quello che il test prova.

---

### ⚠️ Quali errori parla, e dove tace

Si ferma con un'eccezione su: una testata che la mappa non conosce, un id non valido, uno stato
che il vocabolario non ha fra gli attivi, una testata che non c'è o non si vede, nessun
percorso nella matrice, una porta senza verbo noto, e uno **stato raggiunto diverso da quello
chiesto**. Gli errori di un passo sono quelli del verbo.

⭐ Lo stato raggiunto si **confronta** con quello chiesto, per ogni testata: un verbo che non
porta dove deve è un errore del test, non uno stato da restituire come se fosse quello voluto.
Il caso che lo rende necessario è la **chiusura di una versione di listino**: il verbo di
processo chiude tutte le versioni attive scadute che l'operatore vede, non solo quella chiesta,
e se la versione chiesta non è scaduta non la tocca e non dice niente. La fixture allora
solleva, nominando lo stato rimasto (attiva); il test scrive prima la fine validità passata. ⚠️
Il verbo resta globale: chiudendo la versione chiesta chiude anche le altre versioni scadute
del test.

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/vendite/test-righe-e-componenti-debiti-residui-v1.sql` — l'ordine in bozza con le
  righe arriva a confermato per la matrice; uno stato che il catalogo non ha e un documento che
  la fixture non conosce sono eccezioni, non ritorni muti.
* `db/pgtap/dbops/test-fn-pgtap-porta-a-stato-v1.sql` — una versione di listino senza fine,
  chiesta chiusa, solleva e nomina lo stato rimasto; con la fine passata arriva a chiusa; una
  testata già nello stato chiesto lo restituisce senza passi.
* `db/pgtap/dbops/test-fn-pgtap-crea-lotto-v1.sql` — il lotto vuoto raggiunge lo stato chiesto,
  e lo stato tornato è quello vero.
* I presidi dei builder di documento (`db/pgtap/dbops/test-fn-pgtap-crea-*-v1.sql`) la usano per
  ogni stato oltre la bozza.

---

### Note di migrazione

* 2026-10-08 — nasce per ordine e preventivo, quando le righe diventano scrivibili solo in bozza
  (`brief-db-righe-e-componenti-debiti-residui`, D-1).
* 2026-10-24 — tutte le testate con una matrice, e il lotto di fatturazione vuoto
  (`brief-modello-documento-vendita` N-1, R-4).
* 2026-10-25 — la mappa comune delle testate, e sotto la porta ogni passo dal verbo con l'azione
  concessa; preventivo e ordine passano sotto la porta (`brief-modello-documento-vendita` §7-§9).
* 2026-10-26 — contratto, offerta e commessa sotto la porta (§11, §13, §14).
* 2026-10-27 — fattura e lotto sotto la porta, con i passaggi di processo (§15).
* 2026-10-28 — la versione di listino sotto la porta (§16).
* 2026-11-08 — lo stato raggiunto si confronta con quello chiesto: se il passaggio non è
  avvenuto solleva, invece di restituire lo stato di prima.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
