## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_commessa_attivita`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_commessa](/dbzero/dbops/funzioni/fn_pgtap_crea_commessa) — la commessa su cui scriverla
>
> • [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) — la madre che la scrive
>
> • [dbops.fn_pgtap_crea_articolo](/dbzero/dbops/funzioni/fn_pgtap_crea_articolo) — l'articolo, costruito
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-rls-documenti-costruiti` (giro 3) · changeSet `20261015-23` (richiesta del team BE)

---
### 🎯 Scopo Principale

(rev 2026-10-07; rev 2026-10-15: articolo e listino dal chiamante; rev 2026-10-24: sorgente, stati, quantità e periodo)

**Un'attività approvata su una commessa già costruita**, scritta dalla **madre del
dominio**: `APPROVATA` e `NON_EMESSA`, quantità 1, prezzo snapshot fisso (default 10), con
la commessa come sorgente. È la forma da cui l'emissione delle attività fatturabili la
prende.

```sql
CREATE TEMP TABLE tmp_a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_c));
-- un'altra, con un prezzo scelto:
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_c), 25);
-- con un articolo costruito prima (coi suoi flag) e la provenienza del prezzo:
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id         => (SELECT commessa_id FROM tmp_c),
    p_articolo_id         => (SELECT articolo_id FROM tmp_art),
    p_listino_versione_id => (SELECT listino_versione_id FROM tmp_l),
    p_listino_riga_id     => (SELECT riga_id FROM tmp_r));
```

---
### 🧭 Perché esiste

Un'attività di commessa si scriveva a mano in molti pgTAP, con articolo, unità di misura e
istanza pescati dal database; altri chiamavano la madre ricopiando una ventina di
argomenti. Era la stessa regola scritta più volte (regola del 2): ora ha una sede.

---
### 🔗 Il confine: cosa decide il builder, cosa decide il chiamante

Il builder decide il **contesto**; il chiamante sceglie l'**oggetto** e la **provenienza del
prezzo**. Tutto il resto (tipo movimento, quantità negative, rettifiche, oneri, contratto,
promo) passa dalla madre: un builder con tutti i parametri della madre sarebbe una seconda
madre.

| Chi | Cosa |
| --- | --- |
| builder | l'istanza di utility (quella del billing account della commessa), la **chiave del segmento** (dal costruttore del dominio) |
| chiamante | il prezzo (default 10), l'**articolo** (`p_articolo_id`), la **versione** (`p_listino_versione_id`) e la **riga di listino** (`p_listino_riga_id`); dal 2026-10-24 la **sorgente** (codice, chiave del documento, riga; default la commessa stessa), la **quantità** (default 1), gli **stati** di approvazione ed emissione (default `APPROVATA`, `NON_EMESSA`) e il **periodo** (default quello della commessa, o il mese corrente) |

* **L'articolo**: se il chiamante non lo passa, il builder lo costruisce
  (`fn_pgtap_crea_articolo`, non gestito a magazzino; da zero il catalogo è vuoto). Se serve
  un articolo con certi flag (la tipologia di un listino, una natura), il chiamante lo
  costruisce **prima** e lo passa: dal guard A-10 un articolo già usato non cambia più i flag
  strutturali, e quello costruito dal builder è già usato quando il test lo riceve.
* **La riga di listino**: se c'è, l'unità di misura è la **sua**, e se mancano articolo e
  versione si prendono da lei.
* **La versione da sola**: la riga è «registrata sotto quella versione», senza riga di
  listino.
* ⛔ La **coerenza** fra articolo, riga e versione non la controlla il builder: la tiene la
  tabella ([vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga)),
  per tutti, test compresi.
* **La sorgente** (rev 2026-10-24): l'attività che la push di una riga di un documento avrebbe
  scritto. La chiave del segmento la compone **il dominio**, con `script.fn_segment_key` (il
  solo costruttore), dal codice della sorgente, dalla chiave del documento e dalla riga.
  Ricopiarne il formato a mano è ciò che aveva rotto sedici pgTAP il 2026-10-20, quando la
  grammatica dei documenti era cambiata. Una sorgente senza la chiave del documento viene
  rifiutata.
* **L'attività** la scrive `vendite.fn_upsert_commessa_attivita`.

---
### 🚫 Cosa NON scrive

* **L'emissione e il legame con la fattura**: sono il caso del test. La catena
  dell'applicazione è: legame della commessa alla sorgente, stato `PRONTA_FATTURAZIONE`,
  `vendite.fn_emit_attivita_fatturabili_da_commessa`. Il legame fra attività fatturabile e
  riga di fattura lo scrive il backend (pipeline di fatturazione), e un test lo fa con lo
  stesso `UPDATE`.
* **Promo, contratto, variazioni**: il prezzo è uno snapshot fisso passato dal chiamante.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`). Una commessa, un articolo o una riga di
listino che non esistono vengono rifiutati per nome.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-commessa-attivita-v1.sql` (14 casi) pinna il
**contratto**: l'attività è sulla commessa, approvata e non emessa, con l'istanza del
billing account e la competenza della commessa, il prezzo è quello chiesto, **l'emissione
la prende**, una commessa inesistente parla; e (dal 2026-10-15) l'articolo passato arriva
coi suoi flag, la riga di listino dà la sua unità di misura, articolo e versione, la sola
versione registra la riga senza riga di listino, un articolo o una riga di listino
inesistenti parlano; e (dal 2026-10-24) con la sorgente la chiave è quella del costruttore
del dominio, quantità, stati e periodo sono quelli dichiarati, una sorgente senza chiave parla.
