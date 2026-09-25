# Brief BE — Ogni lettura in una transazione di sola lettura

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-24. **A chi:** team backend.
> **Origine:** approfondimento del §8 di
> [brief-db-area-funzionale-assistente-ai.md](../work-done/brief-db-area-funzionale-assistente-ai.md).
> **Decisione di Tid, 2026-09-24:** si fa **fra le prime cose**, insieme al brief
> dell'assistente AI.
>
> **In una riga:** oggi «una lettura non scrive» è una promessa del codice. Con
> ogni `GET` eseguita dentro `SET TRANSACTION READ ONLY` diventa una **garanzia
> del DB**: una scrittura dentro una lettura fallisce, chiunque la tenti.
>
> ⇒ **Al backend:** un building block che apre la transazione di sola lettura,
> montato su tutte le `GET`/`HEAD` delle API, e riusato dai tool dell'assistente.
> ⇒ **Al DB:** un codice di errore registrato (§5).
>
> ⭐ **Stato al 2026-09-25:** il building block **esiste** —
> `apps/core/db/sola_lettura.py::transazione_sola_lettura`, nato col brief
> dell'assistente (§5.3.1 di quello), col presidio su DB vero
> `core/tests/db/test_sola_lettura_db.py` (che copre anche il §4 punto 3: la
> connessione dopo il blocco non è in sola lettura). Lo usano i tool
> dell'assistente. **Restano** il montaggio su tutte le `GET`/`HEAD`, i
> presìdi 1 e 2 del §4 e le eccezioni del §2.2.
> 🟢 **Il codice del §5 è su dbdev** (2026-09-25; ⏳ scratch `zeroerp_ci` e
> commit): il backend può rigenerare i due moduli dei codici (§5.1).

---

## 1. Il problema

Il livello `LETTURA` significa «vedo i dati, non eseguo azioni», e oggi lo impone
**solo il backend**: il DB calcola i livelli (`fn_resolve_livello_area`,
`fn_check_azione_processo`) ma nessuna policy e nessuna funzione li applica
(brief dell'assistente, §3.2).

Dentro il backend, poi, «questa è una lettura» è **una classificazione**: il metodo
HTTP dell'endpoint, o il tipo dichiarato di un tool. Se un endpoint `GET` chiama un
service che scrive — per svista, o perché il service è cambiato dopo — nessuno se
ne accorge: la connessione dell'app ha i privilegi di scrittura, e il DB esegue.

## 2. La richiesta

**Ogni richiesta `GET` e `HEAD` alle API gira dentro una transazione aperta con
`SET TRANSACTION READ ONLY`.** Una scrittura tentata lì dentro fallisce con
`25006` (`read_only_sql_transaction`) — anche dentro una funzione
`SECURITY DEFINER`, perché è una regola della **transazione**, non del ruolo.

### 2.1 Vincoli

1. ⛔ **Per transazione, mai per sessione.** Con `CONN_MAX_AGE` (600 s di default)
   le connessioni si riusano: un `SET SESSION CHARACTERISTICS` passerebbe alla
   richiesta successiva, magari una `POST`. Si apre un blocco atomico, la prima
   istruzione è `SET TRANSACTION READ ONLY`, e la transazione si chiude con la
   richiesta.
2. **Copre tutte le view**, non solo le `DomainAPIView`: anche `AdminAPIView` e le
   `APIView` semplici. Dove si monta (middleware o classe base comune) lo decide il
   backend; il presidio del §4 verifica che non resti fuori nessuna view.
3. **Il log della richiesta resta fuori.** `RequestLogMiddleware` scrive
   `dbops.request_log` **dopo** la risposta: deve restare dopo la chiusura della
   transazione di sola lettura. Idem per ogni scrittura di osservabilità che
   avviene dopo la view.
4. **Le variabili di sessione non sono scritture.** `set_config` (le GUC di
   identità, lingua, emittente) funziona dentro una transazione di sola lettura:
   l'autenticazione può restare dove sta.
5. **Il `tx_id` non è un problema**: `dbops.fn_get_or_create_session_tx_id` lo
   genera via dblink, cioè su un'altra connessione.
6. ⚠️ **Le risposte in streaming** (`StreamingHttpResponse`, `FileResponse`:
   `core/api/email_views.py`, `documenti/services/document_generation_service.py`)
   producono il contenuto **dopo** che la view ha restituito la risposta, quindi
   fuori dalla transazione. Per ciascuna si dichiara se legge dal DB durante lo
   streaming e, se sì, come la si porta dentro.

### 2.2 Le eccezioni si dichiarano, non si scoprono

Una `GET` che **deve** scrivere sulla connessione della richiesta (se esiste) lo
dichiara sulla view con un attributo e il **motivo** scritto accanto; il test del
§4 le elenca **per nome**. Una `GET` che scrive senza dichiararlo è un difetto: o
la scrittura esce dalla `GET`, o si dichiara.

⭐ **Il modo per trovarle è accendere il meccanismo e far girare tutta la suite**:
ogni `25006` è una `GET` che oggi scrive. È un risultato dell'intervento, non un
suo costo. (Verificato il 2026-09-24 sul percorso comune: autenticazione, `tx_id`
e `request_log` non scrivono sulla connessione della richiesta dentro la view.
Sui singoli service di lettura non si è guardato: lo dice la suite.)

### 2.3 L'assistente AI usa lo stesso blocco

Il brief dell'assistente (§5.3 punto 3) chiede la stessa cosa per i tool di
lettura e per le anteprime dei tool di scrittura, che girano **dentro** una `POST`.
⇒ Il meccanismo nasce come **building block** (un context manager, per esempio),
registrato nel catalogo BB backend, e lo usano **sia** il montaggio sulle `GET`
**sia** il ciclo dei tool. Due implementazioni della stessa regola sono la
divergenza che la regola del 2 previene.

## 3. Cosa garantisce, e cosa no

| | |
| --- | --- |
| ✅ **Garantisce** | che una richiesta classificata come lettura **non scriva nulla** sul DB, qualunque cosa faccia il codice che chiama |
| ⛔ **Non garantisce** | che il backend **autorizzi** correttamente una scrittura: un `POST` con il permesso dichiarato male passa ancora. Quello è il compito del [brief-db-permesso-nel-verbo-di-scrittura.md](brief-db-permesso-nel-verbo-di-scrittura.md) |

## 4. I presìdi

1. **Una `GET` che scrive viene fermata** — una view di prova, **fabbricata nel
   test**, che tenta un `INSERT` in una `GET`: risposta con il codice del §5 e
   **nessuna riga** scritta.
2. **Nessuna view resta fuori** — il test percorre le rotte registrate e, per ogni
   `GET`, verifica che il meccanismo sia montato, salvo le eccezioni del §2.2
   elencate per nome. L'elenco si ricava dalle rotte, non da una lista scritta a
   mano.
3. **La connessione non si porta dietro la sola lettura** — due richieste sulla
   stessa connessione, una `GET` e poi una `POST`: la `POST` scrive.

## 5. Richiesta al DB — un codice di errore

Il `25006` va tradotto in un codice registrato, famiglia **TECNICO**: non è un
errore dell'operatore, è un difetto del codice (una lettura che scrive). Risposta
HTTP 500, con il nome della view nel log.

Proposta: **`E_SCRITTURA_IN_LETTURA`**, messaggio *«Operazione di sola lettura che
ha tentato una scrittura: {vista}»*. Lo registra il team DB nel catalogo dei
messaggi, secondo
[Messaggi di Errore e Generazione Log](../../guide/Messaggi-di-Errore-e-Generazione-Log.md);
il backend lo usa solo dopo che è registrato.

### 5.1 Com'è registrato (DB, 2026-09-25)

| Dove | Cosa |
| --- | --- |
| `codici_errore.csv` | `E_SCRITTURA_IN_LETTURA`, classe `TECNICO` (500) |
| `messaggi_errore.csv` (id 1138) | «Modifica dati non permessa.», con causa (una lettura che scrive: difetto dell'applicazione, non dei permessi) e soluzione (segnalarlo indicando la pagina) |

⚠️ **Rispetto alla proposta: frase chiusa, senza `{vista}`.** Il nome della view
serve a chi sviluppa e va **nel log** (come dice il §5 stesso); e
`error_messages_fallback.py` tiene solo i messaggi senza `%s`, quindi con il
segnaposto il ripiego del backend resterebbe senza testo. ⛔ Il testo **non**
parla di autorizzazioni: «permessi insufficienti» è già `E_PERMESSO_NEGATO`, e
un operatore che lo leggesse chiederebbe un permesso all'amministratore, che non
risolve niente.

Nessun changeSet nuovo: il codice lo alza solo il backend, entra con il carico
dei due CSV. ✅ Caricato su dbdev (Tid, 2026-09-25); ⏳ scratch.

**Al backend:** rigenerare `error_policies_generated.py` ed
`error_messages_fallback.py`; poi la traduzione del `25006` in
`transazione_sola_lettura`, con il nome della view nel log.

## 6. Perimetro e rischio

| | |
| --- | --- |
| **Backend** | un building block, il suo montaggio sulle `GET`/`HEAD`, la traduzione del `25006`, tre presìdi, le eventuali eccezioni dichiarate |
| **DB** | un codice di errore |
| **Rischio** | le `GET` che oggi scrivono smettono di funzionare. È voluto, e la suite le trova tutte **prima** del merge (§2.2) |
| **Reversibile** | sì: il meccanismo si smonta in un punto solo |

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-24 | DB | Brief scritto dall'approfondimento del §8 del brief dell'assistente AI; decisione di Tid: fra le prime cose |
| 2026-09-25 | backend | Building block `transazione_sola_lettura` scritto e usato dai tool dell'assistente (regola del 2, ok Tid). Il montaggio sulle `GET` resta da fare |
| 2026-09-25 | DB | §5 scritto: `E_SCRITTURA_IN_LETTURA` (`TECNICO`) e messaggio 1138 «Modifica dati non permessa.», frase chiusa e senza «autorizzazioni» (§5.1). Non applicato |
| 2026-09-25 | Tid | Codice caricato su dbdev |
