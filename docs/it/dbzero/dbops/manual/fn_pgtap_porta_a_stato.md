## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_porta_a_stato`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine) · [dbops.fn_pgtap_crea_preventivo](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo) — le testate di fixture che questa funzione fa camminare
>
> • [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — il lock che rende necessaria la forma «bozza, righe, transizioni»
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-righe-e-componenti-debiti-residui` (§1, D-1)

---
### 🎯 Scopo Principale

(rev 2026-10-24)

**Portare una testata di fixture nello stato voluto, per le strade vere.** Il
test crea la testata in bozza (dal 2026-10-24 un documento nasce solo nel suo
stato iniziale), le scrive le righe, poi chiede lo stato: la funzione cerca nella matrice delle transizioni il percorso più corto
dallo stato corrente a quello voluto e lo percorre, un cambio di stato per passo.

```sql
-- l'ordine nasce DRAFT, prende le righe, poi:
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', o.id, 'CONFERMATO') FROM tmp_ordine o;

-- dentro un blocco, o per non stampare una riga fuori dal TAP:
DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_prev), 'ACCETTATO');
END $x$;
```

Ritorna il `codice_interno` dello stato raggiunto.

**Le testate che conosce**: preventivo, offerta, contratto, ordine, DDT, reso,
commessa, fattura, il **lotto di fatturazione** (rev `20261024-22` e `-30`) e la
**versione di listino** (rev `20261028-24`).

* **La versione di listino**: ATTIVA dal verbo `vendite.fn_attiva_versione_listino`
  (chiude anche le versioni precedenti che si sovrappongono); CHIUSA, passaggio di
  processo, da `vendite.fn_chiudi_versioni_listino_scadute`, che vuole la fine validità
  già passata: la scrive il test prima di chiederla.

* **La fattura** usa la matrice `config.stati_doc_fiscale_transizioni` con i soli
  passaggi della fattura singola (`solo_lotto = false`).
* **Il lotto** usa la stessa matrice con i soli passaggi del lotto
  (`solo_fattura = false`), e solo quando è **vuoto**: un lotto con fatture si muove
  col verbo del dominio `vendite.fn_sync_lotto_fatture_stato`, perché il controllo
  di coerenza lotto/fatture lo fermerebbe al primo passo. Il filtro per tipo di
  lotto lo applica il controllo del lotto, al passo.

---
### 🧭 Perché esiste

Dal 2026-10-08 le righe d'ordine e di preventivo si scrivono solo con il
documento in bozza. Circa cinquanta pgTAP costruivano la testata **già** fuori
bozza (un ordine confermato, un preventivo accettato) e poi ci mettevano le
righe: un documento che il modello non sa produrre, e che ora il lock rifiuta.
La forma giusta è quella della produzione — bozza, righe, transizioni — e
«quali cambi di stato, in che ordine» scritto cinquanta volte sarebbe la stessa
regola in cinquanta copie: ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **Il percorso** lo decide la matrice della testata, solo le transizioni e gli
  stati attivi. A parità di lunghezza vince il percorso con gli id di stato minori:
  una scelta fissa, non quella del piano.
* **Ogni passo** passa dai guard di transizione veri: righe presenti, aliquote,
  prezzi autorizzati, emettibilità. Un documento che non si potrebbe confermare,
  la funzione non lo conferma — e il test lo scopre lì, con il motivo vero.
* Le transizioni **automatiche** (per esempio `ACCETTATO → EVASO` del
  preventivo) valgono come le manuali: la matrice le dichiara, e il guard decide
  se il documento le regge.

---
### 🚫 Quando NON si usa

* Una testata che resta in bozza.
* Una transizione che è **il caso del test**: lì il cambio di stato si scrive
  esplicito, perché è proprio quello che il test prova.

---
### ⛔ Niente ritorni muti

Una testata che non conosce, uno
stato che il catalogo non ha, nessun percorso nella matrice, una testata che non
c'è o non si vede, un cambio di stato che non tocca una riga: in tutti questi
casi solleva un'eccezione. Una fixture che non arriva dove deve non può passare
per buona.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

> 📎 changeSet `20261008-94`, `20261024-22` (tutte le testate), `20261024-30` (il
> lotto). Presidi: `db/pgtap/vendite/test-righe-e-componenti-debiti-residui-v1.sql`
> (test 1-3, 9), i presidi dei builder `db/pgtap/dbops/test-fn-pgtap-crea-*-v1.sql`
> (il lotto: `test-fn-pgtap-crea-lotto-v1.sql`, test 7).
