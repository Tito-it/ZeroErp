## 📘 Documentazione Concettuale – Funzione `dbops.fn_storico_backfill_scope`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.storico_scope_policy](/dbzero/dbops/tabelle/storico_scope_policy) — la mappa con cui si risolve l'emittente delle versioni
>
> Approfondimento funzioni:
>
> * [dbops.fn_storico_risolvi_scope](/dbzero/dbops/funzioni/fn_storico_risolvi_scope) — chi risolve l'emittente, qui dallo snapshot
> * [dbops.fn_storico_arma_scope](/dbzero/dbops/funzioni/fn_storico_arma_scope) — chi mette le colonne che questa funzione riempie
> * [dbops.fn_storico_backfill_scope_tutte](/dbzero/dbops/funzioni/fn_storico_backfill_scope_tutte) — la applica a ogni madre
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la sezione «Di chi è una versione»

---

### 🎯 Scopo Principale

Attribuisce origine e scope alle versioni già scritte della shadow di una madre: alle versioni
senza `origine_schema` assegna lo schema della madre e l'emittente risolto dallo snapshot della
versione. Quando nessuna versione resta senza origine, porta `origine_schema` a `NOT NULL`.

È una migrazione del pregresso, non una rete: le versioni nuove le scrive il trigger già complete.
Si può rieseguire senza danno, perché tocca solo le versioni ancora senza origine.

---

### ⭐ Le shadow condivise: di chi è questa versione?

Due madri omonime scrivono nella stessa shadow, e una versione legacy non dice da quale delle due
viene. Lo snapshot però è la riga intera, e le sue chiavi sono le colonne della madre al momento
della scrittura: una versione si attribuisce alla madre di cui porta almeno una **colonna
esclusiva**, una colonna che l'altra madre non ha.

* le versioni che non portano nessuna colonna esclusiva restano senza origine, e la colonna resta
  nullable. Il conteggio delle versioni senza origine sta nel risultato e nell'audit; nessun pgTAP
  lo presidia;
* due madri con le **stesse** colonne non hanno colonne esclusive: la funzione non attribuisce
  niente e lo dice con un `WARN` (`NON_ATTRIBUIBILE`).

Una shadow è condivisa quando un'altra madre con lo stesso nome, in un altro schema, porta il
trigger di storico.

---

### ⚠️ Il limite dichiarato

Lo scope si risolve dallo snapshot, ma per i modi `PADRE` il resolver risale al padre **com'è
oggi** — o, se il padre non è più vivo, alla sua ultima versione nello storico. Il passato si legge
in parte con il presente: è il limite del backfill, non della regola. Dove né il padre né il suo
archivio rispondono, la versione resta senza scope e, sulla shadow armata, non si vede.

---

### Gli esiti

| Esito | Quando |
| --- | --- |
| `NO_SHADOW` | la madre o la sua shadow non esistono |
| `SENZA_COLONNE` | la shadow non ha ancora le colonne dello scope: prima serve `fn_storico_arma_scope` (`WARN` nell'audit) |
| `NON_ATTRIBUIBILE` | shadow condivisa fra madri con le stesse colonne (`WARN`) |
| `AGGIORNATA` | ha attribuito almeno una versione |
| `NIENTE_DA_FARE` | non c'era niente da attribuire |

Il risultato riporta anche quante versioni ha aggiornato, quante restano senza origine e se ha
messo il `NOT NULL`. L'audit si scrive solo se la funzione ha fatto qualcosa.

⚠️ Il `NOT NULL` lo mette solo se l'utente corrente ha i privilegi del proprietario della shadow
(il proprietario, un suo membro con `INHERIT`, un superuser: il controllo è sui privilegi, non sul
nome del ruolo): altrimenti le versioni si attribuiscono lo stesso e la colonna resta nullable.

---

### Test

Nessun pgTAP chiama la funzione. `db/pgtap/storico/test-storico-scope-congelato-v1.sql` prova la
forma che il backfill completa, sulle versioni scritte dal trigger: ogni versione porta lo schema
della propria madre.

---

### Note di migrazione

* 2026-09-11 — nasce con lo scope congelato (`brief-db-rls-storico-scope-congelato`, §4b e §5), per
  attribuire le versioni scritte prima di quel giorno. Letto sul database di sviluppo dopo l'apply
  di quel giorno (fatto datato): tutte le versioni attribuite, e tutte le shadow con madre passate a
  `origine_schema NOT NULL`, comprese le condivise.
* 2026-11-08 — il proprietario si riconosce dai privilegi (appartenenza con `INHERIT`, o superuser),
  non più dal nome del ruolo.

---

{% include-markdown "signature-core.md" %}
