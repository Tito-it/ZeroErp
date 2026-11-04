## 📘 Documentazione Concettuale – Funzione `dbops.fn_storico_risolvi_scope`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.storico_scope_policy](/dbzero/dbops/tabelle/storico_scope_policy) — la mappa che la funzione segue
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — dove il soggetto-ruolo diventa emittente fiscale
>
> Approfondimento funzioni:
>
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — il chiamante, che congela la risposta nella shadow
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — l'emittente di un billing account, per i modi `BA` e `COPPIA`
> * [script.fn_get_ba_id_da_coppia](/dbzero/script/funzioni/fn_get_ba_id_da_coppia) — il billing account di una coppia, la stessa risposta della policy dei dati precontrattuali
> * [dbops.fn_storico_backfill_scope](/dbzero/dbops/funzioni/fn_storico_backfill_scope) — l'altro chiamante, sulle versioni già scritte
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la sezione «Di chi è una versione»

---

### 🎯 Scopo Principale

Data una madre storicizzata e una sua riga in forma `jsonb`, restituisce l'emittente fiscale a cui
quella riga appartiene, seguendo la strada dichiarata in `dbops.storico_scope_policy`. Il trigger
di storico scrive quel valore nella shadow, dove resta congelato.

La riga è quella che il trigger ha già in mano: la funzione non va a cercarla, la legge
dall'argomento.

---

### Che cosa fa, modo per modo

| `modo` | La funzione… |
| --- | --- |
| `EF` | legge la colonna e la restituisce |
| `SR` | legge la colonna e cerca l'emittente fiscale con quel soggetto-ruolo |
| `BA` | legge il billing account, ne prende l'unico emittente con la regola di `script.fn_get_ba_emittente_sr_id` (il legame specifico; senza legame, in sessione l'emittente dell'operatore, altrimenti quello di default) e lo converte in emittente fiscale |
| `COPPIA` | legge le due colonne dichiarate, cerca il billing account di quella coppia e ne prende l'emittente come nel modo `BA` |
| `PADRE` | legge la chiave verso il padre, **carica la riga del padre** per `id` e **si richiama** sulla riga di mappa del padre: una catena a più salti si risolve da sola |
| `NESSUNO` | restituisce vuoto |

Una madre **senza riga di mappa** restituisce vuoto come un `NESSUNO`: la vede il presidio della
mappa, non questa funzione.

---

### ⭐ Il padre che non c'è più si legge dal suo archivio

In un `DELETE` a cascata il padre sparisce prima che il figlio scriva la sua versione finale:
caricarlo per `id` non trova niente. Il modello lo ammette (le shadow non hanno FK), e la funzione
ripiega sull'**ultima versione del padre nello storico**, che porta ancora l'emittente: leggere
l'archivio del padre è leggere il passato, non il presente. La colonna che lega la versione al
padre è quella dell'automazione (`<tabella>_id`, o l'override `STORICO_FK`).

Nelle shadow condivise fra due madri omonime il ripiego legge solo le versioni dello schema del
padre, più quelle ancora senza origine. Se nemmeno l'archivio conosce il padre, la risposta è
vuota.

Il tipo vero della colonna `id` del padre si legge dal catalogo e si usa per il confronto, così
la ricerca usa l'indice.

---

### ⭐ Gira come il proprietario

La chiama il trigger, che gira **come chi sta scrivendo** la madre, cioè l'applicazione sotto row
level security. Il padre di un satellite può non essere visibile a chi scrive: con i suoi permessi
la risalita non troverebbe niente, e la versione nascerebbe senza scope, cioè invisibile a tutti.

Catturare lo scope è un atto di sistema: la funzione è `SECURITY DEFINER` del proprietario delle
tabelle, con `search_path` ristretto ai cataloghi e ogni oggetto nominato con lo schema.
⚠️ Attraversa la RLS perché il proprietario della funzione possiede anche i padri e la RLS del
progetto è `ENABLE` senza `FORCE`: non lo si presume, lo asserisce il pgTAP. Non è una porta
aperta: restituisce un solo numero, derivato da una riga che il chiamante ha già. L'esecuzione è
concessa all'applicazione e tolta a `PUBLIC`.

---

### ⚠️ Non solleva, tranne su un ciclo

Una madre non mappata, una colonna vuota, un padre sparito senza archivio, un padre dichiarato che
non esiste o non ha `id`: la risposta è **vuota**. La storicizzazione non deve fermare la scrittura
della madre per un difetto della mappa, e lo scope vuoto è **chiuso** (con la shadow armata la
versione non si vede) e **visibile** al presidio.

L'unico caso in cui solleva è una catena `PADRE` che supera il tetto di profondità: una catena
legittima è corta, una che non finisce gira in cerchio.

---

### Codici errore

* `E_STORICO_SCOPE_CATENA_CICLICA` — la catena `PADRE` della mappa supera il tetto di profondità:
  la mappa contiene un ciclo.

---

### Test

* `db/pgtap/dbops/test-storico-scope-policy-v1.sql` — la postura (`SECURITY DEFINER`, `search_path`
  fissato, il proprietario possiede ogni padre in RLS, esecuzione all'applicazione e non a `PUBLIC`)
  e il comportamento sui valori: `EF`, `SR`, `BA` in sessione e senza, `COPPIA` con e senza billing
  account, `PADRE` a due salti su tabelle temporanee con tre tipi di `id`, FK vuota, padre sparito,
  `NESSUNO`, madre non mappata, il ciclo che solleva.
* `db/pgtap/storico/test-storico-scope-congelato-v1.sql` — il ripiego sull'archivio del padre in un
  `DELETE` a cascata.

---

### Note di migrazione

* 2026-09-11 — nasce con lo scope congelato (`brief-db-rls-storico-scope-congelato`, §4b).
* 2026-10-09 — il modo `COPPIA` (`brief-db-istanza-nasce-col-ba`).
* 2026-10-21 — il billing account della coppia lo dice `script.fn_get_ba_id_da_coppia`, la stessa
  funzione della policy dei dati precontrattuali: prima la stessa domanda era scritta in due posti.

---

{% include-markdown "signature-core.md" %}
