## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_or_create_vendite_contabile`
### 🎯 Scopo Principale
Recuperare una testata contabile vendite esistente oppure crearne una nuova,
con possibilita` di collegarla al lotto fatturazione tramite tabella ponte.

### Regole principali
* Valida parametri obbligatori (`centro_riscossione_id`, `data_contabile`, stato).
> ⚠️ **Dal 2026-08-22 `p_compensazione_id` non esiste più**, e con lui il ramo di
> riuso «una testata per atto» e la mutua esclusione con `p_lotto_id`. ⭐ Girato
> il verso del legame (D15-e) è l'**atto** a tenere l'id della sua contabile:
> chiederla qui voleva dire far nascere la testata **sapendo già di chi sarebbe
> stata**, cioè il verso opposto a come funziona il processo. L'unicità *«una
> contabile per atto»* vive su `uq_sistemazioni_contabile`, e le sistemazioni
> creano la loro distinta **da sé** — questa funzione è costruita per
> **condividere**, e due rimborsi nello stesso giorno riuserebbero la stessa
> testata.
>
> 🔴 La firma è cambiata: la funzione è stata **eliminata e ricreata**, perché
> una sostituzione con parametri diversi affianca un **overload** e con i valori
> di default le chiamate diventano ambigue.

⛔ *(storico, non più valido)* Supportava `p_compensazione_id` opzionale:
  * se valorizzato, identifica in modo univoco la testata contabile
  * non e` compatibile con `p_lotto_id`.
* Risolve lo stato da `pagamenti.vendite_contabili_stati.codice_interno`.
* Se trova una testata coerente, la riusa.
* Se non la trova, crea una nuova testata.
* Se `p_lotto_id` e` valorizzato, inserisce il link in `pagamenti.vendite_contabili_lotti`.

### Esempio d’uso
```sql
SELECT pagamenti.fn_get_or_create_vendite_contabile(
  p_centro_riscossione_id => 1,
  p_data_contabile => current_date,
  p_ente_incasso_id => NULL,
  p_lotto_id => 123,
  p_codice_stato_interno => 'BOZZA'
);
```


### ⭐ La distinta manuale è **per operatore** (2026-08-21)

Sul ramo manuale la chiave di riuso comprende **chi sta lavorando**, oltre a
centro, ente, date e stato. Una distinta `MANUALE` è il **lotto di lavoro di una
persona**, non «tutti gli incassi di lunedì»: due operatori che inseriscono nello
stesso giorno e sullo stesso canale ottengono **due distinte diverse**.

⭐ Era stata chiesta una funzione di blocco perché non si pestassero i piedi: con
questo raggruppamento **la contesa non esiste**, e il blocco non si costruisce.

⚠️ Sulle altre due origini la chiave resta quella di prima: una distinta
`GENERATA` non è il lotto di lavoro di nessuno, e una `AUTOMATICA` è il file.

ℹ️ «Chi sta lavorando» si legge con la **stessa espressione** con cui il trigger di
audit valorizza `user_insert`. Non è un dettaglio: la chiave di riuso confronta
proprio quella colonna, e se le due divergessero la funzione creerebbe una distinta
nuova a ogni riga inserita, **in silenzio**.

### `p_origine` — obbligatorio nei fatti, con un default onesto

Il default è `GENERATA`, perché chi chiama **senza dirlo** è uno script. ⚠️ Un
chiamante che inserisca una distinta manuale dimenticando il parametro la vedrebbe
risultare «prodotta dal sistema»: è il prezzo del default, accettato perché la
strada giusta — questa funzione — è l'unica che il progetto ammette.

### ⚠️ La firma è cambiata (otto parametri → nove)

Il changeSet che l'ha introdotta fa **DROP + CREATE**, non un `CREATE OR REPLACE`:
con i default su sette parametri, due versioni affiancate renderebbero le chiamate
**ambigue**, e l'errore arriverebbe al primo giro di fatturazione invece che al
migrate.

{% include-markdown "signature-core.md" %}
