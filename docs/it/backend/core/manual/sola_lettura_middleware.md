# SolaLetturaMiddleware (Core Django)

## Scopo

Far girare ogni richiesta `GET` e `HEAD` delle API dentro una transazione di **sola lettura** garantita dal DB: una scrittura tentata dalla view fallisce, qualunque codice la tenti, e arriva come `E_SCRITTURA_IN_LETTURA`.

## Contesto

Fino al 2026-09-25 «una lettura non scrive» era una classificazione del backend
(il metodo HTTP): se un endpoint `GET` chiamava un service che scrive, il DB
eseguiva. Ora lo impedisce PostgreSQL: `SET TRANSACTION READ ONLY` vale anche
dentro una funzione `SECURITY DEFINER`, perché è una regola della
**transazione**, non del ruolo
(brief-be-letture-in-transazione-sola-lettura).

* **Dove sta.** `apps/core/middleware/sola_lettura_middleware.py`, **ultimo** in
  `settings.MIDDLEWARE`. Apre il blocco in `process_view`, subito prima della
  view, e lo chiude in `__call__`, dopo che la view ha risposto (errore
  compreso). Vale per tutte le view: `DomainAPIView`, `AdminAPIView`, `APIView`
  semplici.
* **Il blocco** è il BB `apps/core/db/sola_lettura.py::transazione_sola_lettura`,
  lo stesso dei tool dell'assistente AI: il middleware decide solo *quando*
  aprirlo.
* **Cosa resta fuori.** Tutti gli altri middleware, e in particolare
  `RequestLogMiddleware`, che scrive `dbops.request_log` dopo la risposta.
  Le GUC (`set_config`) non sono scritture; il `tx_id` e il diario degli errori
  (`script.fn_log_error_only`) scrivono via dblink, su un'altra connessione.
* **Per transazione, mai per sessione.** Con `CONN_MAX_AGE` la connessione
  passa alla richiesta dopo, magari una `POST`: la sola lettura finisce con la
  transazione.
* ⚠️ **Il blocco si chiude con un COMMIT**, anche se non c'è niente da
  confermare: con un ROLLBACK le GUC impostate durante la richiesta (utente,
  emittente) tornerebbero indietro, e `RequestLogMiddleware` le legge dopo. Su
  una transazione interrotta da un errore PostgreSQL annulla comunque.

## Cosa succede se una GET scrive

PostgreSQL ferma la scrittura con `25006`. Il BB la traduce **alla sorgente**:

| | |
| --- | --- |
| Risposta | HTTP 500, `E_SCRITTURA_IN_LETTURA` (classe `TECNICO`), «Modifica dati non permessa.» |
| Log | `sola_lettura.scrittura_in_lettura chi=<modulo.View> sql=…` (logger `apps.core.db.sola_lettura`) |
| Transazione | marcata da annullare |

È un `ServiceError` e non un `DatabaseError`: nessuno dei punti che traducono
gli errori DB (api.md, «I cinque punti di traduzione») lo può riscrivere col suo
ripiego. Non è un permesso mancante (quello è `E_PERMESSO_NEGATO`): è un difetto
del codice, una lettura che scrive.

## Le eccezioni si dichiarano

Una `GET` che **deve** scrivere sulla connessione della richiesta lo dichiara
sulla view, con il motivo:

```python
class MiaView(DomainAPIView):
    scrittura_in_get = "scrive il contatore delle visualizzazioni"
```

Un attributo vuoto o non testuale non vale. Il presidio le elenca **per nome**
(`_ECCEZIONI_DICHIARATE`): al 2026-09-25 non ce n'è nessuna — la suite intera
col DB vero non ha trovato GET che scrivono.

## Quando non si apre

| Caso | Perché |
| --- | --- |
| metodo diverso da `GET`/`HEAD`, o rotta fuori da `/api/` | fuori dal perimetro (l'unica rotta fuori da `/api/` è `health`) |
| view con `scrittura_in_get` | eccezione dichiarata |
| connessione vietata (`SimpleTestCase`) | solo nei test unitari: la view è mockata e non tocca il DB |
| transazione già aperta | la sola lettura si imposta solo come prima istruzione. In una richiesta vera non succede; succede nei test che avvolgono il client in `transaction.atomic()` |

## Risposte in streaming

Il contenuto di una `FileResponse` o `StreamingHttpResponse` si produce dopo la
chiusura del blocco. Al 2026-09-25 c'è una sola `FileResponse`
(`EmailAllegatoDownloadView`): fa tutte le letture DB nella view e poi legge solo
dal filesystem. Una risposta in streaming che legga dal DB **durante** lo
streaming va dichiarata qui.

## Dipendenze

* `apps/core/db/sola_lettura.py` — il blocco e la traduzione del `25006`
* `apps/core/services/error_policies_generated.py` — `E_SCRITTURA_IN_LETTURA` → `TECNICO`

## Test

* `apps/core/tests/db/test_sola_lettura_middleware_db.py` — sul DB vero, view
  fabbricate e catena intera: una GET che scrive è fermata (presidio 1), la GET e
  la HEAD leggono in sola lettura, la POST dopo una GET scrive (presidio 3),
  l'eccezione dichiarata
* `apps/core/tests/middleware/test_sola_lettura_rotte.py` — nessuna GET delle API
  resta fuori, dalle rotte registrate (presidio 2); il middleware è l'ultimo
* `apps/core/tests/db/test_sola_lettura_db.py` — il BB: blocco, traduzione, connessione dopo il blocco
