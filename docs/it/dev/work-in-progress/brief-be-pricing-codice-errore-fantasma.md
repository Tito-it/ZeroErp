# Brief BE — il pricing riporta un codice che il database non solleva da aprile

**Chi scrive:** DB (`dev/db-tid`), 2026-08-19.
**Destinatario:** team BE, branch `dev/backend-tid`.
**Cosa chiede:** capire perché `pricing_service` scrive
`E_PREZZO_LISTINO_NON_TROVATO` — un codice che `vendite.fn_resolve_prezzo_listino_v2`
**non può più sollevare** — e farlo smettere.
**Perimetro:** `apps/vendite/services/pricing_service.py`,
`apps/core/services/error_manager.py`. **Nessuna modifica DB richiesta.**
**Origine:** trovato istruendo una domanda del
[brief-ddt-righe-senza-prezzo](brief-ddt-righe-senza-prezzo.md) §7 R-10 / registro F-4.
Il difetto non c'entra col DDT: **tocca ogni dominio che chiama il pricing** —
preventivi, ordini, contratti, offerte, DDT.

> **In una riga.** Per lo stesso identico fallimento il backend scrive **due**
> righe di log a 55 millisecondi di distanza: prima quella giusta
> (`E_CATEGORIA_LISTINO_NON_MAPPATA`), poi una con un codice che il database ha
> smesso di poter produrre il **14 aprile 2026**. E i due codici mandano
> l'operatore a riparare due cose diverse, di cui una non è rotta.

---

## 1. Il fatto

`vendite.fn_resolve_prezzo_listino_v2` solleva `E_PREZZO_LISTINO_NON_TROVATO` in
un punto solo — lo STADIO 2, quando il billing account non ha categoria:

```sql
IF v_categoria_cliente_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_resolve_prezzo_listino_v2', 'E_PREZZO_LISTINO_NON_TROVATO',
        jsonb_build_object('motivo', 'BA senza categoria_cliente_id e senza contratto attivo', ...));
```

⛔ **Quella condizione non può più essere vera.**
`anagrafiche.billing_account.categoria_cliente_id` è **NOT NULL** dal
**2026-04-14** — changeset `00_schema/anagrafiche/20260414-03`, il backfill che
assegnò STANDARD ai BA scoperti e poi chiuse la colonna. Verificato sul DB vivo:
`pg_attribute.attnotnull = true`; il `DROP NOT NULL` esiste solo nel blocco
`rollback` del changeset. Se il BA esiste, la categoria c'è; se non esiste, la
funzione è già uscita prima con `E_PARAMETRO_INVALIDO`.

Il ramo è quindi **strutturalmente irraggiungibile**. E il log lo conferma.

## 2. La misura

`dbops.error_log`, tutto lo storico:

| chi ha scritto la riga | `E_PREZZO_LISTINO_NON_TROVATO` | `E_CATEGORIA_LISTINO_NON_MAPPATA` |
|---|---|---|
| `area='vendite'` (il database) | **0** | 21 |
| `area='backend'` (`pricing_service.resolve`) | **587** | **587** |

E le due popolazioni non sono indipendenti. Accoppiando ogni riga
`E_PREZZO_LISTINO_NON_TROVATO` con la riga `E_CATEGORIA_LISTINO_NON_MAPPATA` che
ha **contesto identico** e timestamp entro 2 secondi:

| | |
|---|---|
| coppie trovate | **587 su 587** — nessuna riga resta spaiata |
| ordine di scrittura | **sempre** prima `E_CATEGORIA_LISTINO_NON_MAPPATA` |
| distanza media | **0,055 s** |
| `function_name` | `pricing_service.resolve` per **entrambe** |

55 millisecondi escludono una seconda azione dell'operatore: è **la stessa
richiesta** che produce due scritture in sequenza.

## 3. Che cosa è successo davvero, in un caso reale

Riga di log più recente, contesto `ba_id=100`, `utility_id=7`,
`data_riferimento=2026-06-01`. Interrogando il database sugli stessi parametri:

* il BA 100 **ha** la categoria (`STANDARD`, id 1) → il ramo del §1 non scatta;
* non ha contratto attivo per quella utility a quella data → si va allo STADIO 2;
* `anagrafiche.categorie_clienti_listini` per (categoria 1, utility 7, quella
  data) ha **0 righe**.

La condizione vera è dunque `E_CATEGORIA_LISTINO_NON_MAPPATA`: *manca la mappa
categoria → listino*. È il codice della prima delle due righe di log. La seconda
dice un'altra cosa.

## 4. Perché non è cosmetico

I due codici portano all'operatore **due istruzioni diverse**, e una manda a
guardare dove non c'è niente da guardare:

| codice | `soluzione` a catalogo |
|---|---|
| `E_CATEGORIA_LISTINO_NON_MAPPATA` (375) | *«Aggiungere la mappa in `categorie_clienti_listini` oppure assegnare un contratto individuale al BA.»* — **è la riparazione vera** |
| `E_PREZZO_LISTINO_NON_TROVATO` (141) | *«Verificare listini, associazioni e versioni attive per articolo/uom/data.»* — manda sui listini, che sono a posto |

E c'è il danno di secondo ordine, quello che il cantiere dei codici errore
inseguiva: **un codice ritirato di fatto continua a circolare**. Chi domani
misurerà «quali errori produce il pricing» leggerà 587 occorrenze di un codice
che il DB non emette dal 14 aprile, e ne trarrà conclusioni su una funzione che
non l'ha mai sollevato.

⭐ È la stessa forma di difetto di
[brief-be-rinomina-codici-known-markers](../work-done/brief-be-rinomina-codici-known-markers.md)
§2, in un altro file: *«il database dice una cosa, l'API ne dice un'altra, e la
differenza non si vede da nessuna parte»*. Lì il perimetro era
`pratiche_service.py`; qui è `pricing_service.py`. Il cantiere
[classe dei codici errore](../work-done/brief-db-be-classe-codici-errore.md) si è
chiuso il 2026-08-08 — questa è una **ricaduta**, non un residuo.

## 5. Che cosa ho già escluso (per non farvelo rifare)

* **Non è il match testuale.** Il marker dichiarato per
  `E_PREZZO_LISTINO_NON_TROVATO` in `_KNOWN_DB_ERROR_MARKERS` è la stringa
  *«Nessun prezzo listino risolto per articolo»*. Nessun altro messaggio del
  catalogo la contiene — verificato su `messaggi_errore.csv` **e** sulla tabella
  viva `config.messaggi_errore` (CSV e DB coincidono, nessuna divergenza).
  Neanche `causa` e `soluzione` degli altri codici la contengono.
* **Non è un resolver vecchio rimasto in giro.** In tutto il database esiste una
  sola funzione `*resolve_prezzo*`: `fn_resolve_prezzo_listino_v2`. La v1 non
  c'è più.
* **Non è l'endpoint diagnostico** `/pricing/diagnose/`: non registra quei codici
  (ispeziona la configurazione e risponde, non logga).
* **Non è un secondo `raise_error` dentro `raise_from_database_error`**: quel
  percorso logga una volta sola, e il ciclo dei marker fa `break` al primo match.
* **Non è un altro chiamante che rilogga**: `function_name='pricing_service.resolve'`
  è passato da un solo punto del codice.

Resta quindi da capire **perché lo stesso fallimento entra due volte** in quel
punto nella stessa richiesta, e perché il secondo passaggio esce con un codice
diverso dal primo. È lavoro che vuole un debugger sul BE, e per quello serve
qualcuno di casa lì.

## 6. Ipotesi da verificare (non verificate: sono spunti, non conclusioni)

1. **Doppia risoluzione nella stessa richiesta con parametri diversi.** Il
   contesto loggato — `articolo_id`, `uom_id`, `ba_id`, `utility_id`,
   `data_riferimento`, `articolo_padre_contesto` — **non contiene
   `classe_utenza_id` né `listino_versione_id_preferito`**. Due tentativi che
   differiscono solo per quei due parametri risulterebbero **indistinguibili nel
   log**, pur potendo fallire a stadi diversi. Se esiste una catena di ripiego
   («prova con la classe, poi senza»), è il primo posto dove guardare.
2. **`structured_db_error_code` che non trova il canale `CONSTRAINT`** e fa
   ricadere il match sul testo in uno dei due passaggi.
3. Se l'ipotesi 1 regge, la correzione utile non è solo il codice giusto: è
   **aggiungere al contesto i due parametri mancanti**, altrimenti il prossimo
   che indagherà avrà lo stesso log ambiguo che ho avuto io.

## 7. Definizione di «fatto»

* [ ] `E_PREZZO_LISTINO_NON_TROVATO` non viene più scritto per un fallimento che
      è `E_CATEGORIA_LISTINO_NON_MAPPATA`;
* [ ] lo stesso fallimento produce **una** riga di log, non due;
* [ ] il contesto loggato dal pricing include `classe_utenza_id` e
      `listino_versione_id_preferito` (§6.3);
* [ ] deciso che fare del codice 141: se nessuno può più sollevarlo, o si ritira
      con `obsoleto_dal` (pattern del catalogo) oppure si dichiara a quale
      condizione futura serva. **Decisione DB**, la prendiamo noi quando il BE
      conferma di non produrlo più — vedi §8.

## 8. Il lato DB, per completezza

Il ramo del §1 **resta nel codice** e diventerà un «esito» nel nucleo puro
previsto dalla slice A del
[brief-ddt-righe-senza-prezzo](brief-ddt-righe-senza-prezzo.md) §9 — **con un
commento che dice che oggi è irraggiungibile e perché**. Non si cancella: se un
domani la NOT NULL cadesse, il comportamento giusto è già scritto. Ma non resta
neanche muto, che è l'errore che questo giro ha trovato **due volte** nello
stesso pomeriggio (l'altro è in `script.fn_check_ddt_emittibile`, §7 R-5 di quel
brief).

⚠️ **Il ritiro del codice 141 non si fa prima** che il BE smetta di produrlo:
`obsoleto_dal` su un codice che l'API sta ancora emettendo romperebbe la
risoluzione del messaggio a runtime.
