# Brief DB — Codici d'errore per l'email e per l'«accesso riservato», e il «non trovato» del dettaglio ricerca

> **Chi scrive:** sessione backend (`dev/backend-tid`), 2026-10-08. **A chi:** team
> DB (`dev/db-tid`), tramite Tid.
> **Origine:** voci E-4, E-5 ed E-10 di
> [analisi-be-difetti-emersi-verifica-doc-api-core.md](analisi-be-difetti-emersi-verifica-doc-api-core.md).
> La parte che si poteva chiudere coi codici già a catalogo è fatta lato backend
> (2026-10-08, righe E-4/E-5 dell'analisi). Restano i punti per cui **nessun codice
> esistente dice la cosa giusta**: servono righe nuove nel catalogo.
> **Stato:** ⏳ da fare.
> **Da leggere per primo:** §1, poi §2.

## 1. Cosa si chiede

| # | Cosa | Tipo | Bloccante per il BE |
| --- | --- | --- | --- |
| R-1 | Sei codici per i «non trovato» dell'email (`codici_errore.csv` + `messaggi_errore.csv`) | seed `80_data` | sì: rigenerazione delle policy, ripieghi, poi il BE li solleva |
| R-2 | Tre codici per l'«accesso riservato» delle permission | seed `80_data` | sì, come R-1 |
| R-3 | Due codici per le altre condizioni nascoste sotto gli stessi codici email | seed `80_data` | sì, come R-1 — **da confermare con Tid** (§4) |
| R-4 | `script.fn_get_search_detail` dice «non c'è» quando il soggetto, con quel ruolo, non risulta, e il perimetro dei clienti lo fa la **RLS**, non un filtro a mano (§5) — **deciso da Tid il 2026-10-08** | `20_code` + pgTAP | sì per la firma (§5, «Ricaduta sul backend») |

R-1, R-2 e R-3: nessuna funzione DB solleva questi codici, li solleva il backend.
Quindi niente `20_code` e niente pgTAP, solo righe a catalogo. R-4 è l'unica che
tocca una funzione.

## 2. R-1 — I «non trovato» dell'email

Oggi tre **codici-modulo generici** coprono, insieme, validazione, «non trovato» e
conflitti di stato: `E_EMAIL_OP` (email dell'operatore), `E_EMAIL_ADMIN`
(amministrazione delle email) ed `E_OUTBOX` (service della posta in uscita). Sono
tutti `DATO_ERRATO`, quindi **400**. La nota del catalogo su `E_EMAIL_OP` lo dice
già: *«andrebbero spacchettati per verbo — debito noto»*.

L'effetto: chi chiede una bozza, un allegato, un account o un template che non
c'è riceve «hai sbagliato i dati» (400) invece di «non esiste» (404). Per l'email
dell'operatore vale anche per ciò che è **fuori perimetro**: la RLS non lo
restituisce, quindi arriva come inesistente. Di proposito: il 404 non rivela
l'esistenza di una bozza altrui.

| Codice | Classe proposta | Frase (quella che il BE scrive già) | Dove lo solleverà il BE |
| --- | --- | --- | --- |
| `E_EMAIL_BOZZA_NOT_FOUND` | `NON_TROVATO` | Bozza non trovata. | `core/api/email_views.py` (sei punti: lettura, modifica, invio, annullo, caricamento e lista degli allegati), `core/services/email_outbox_service.py` (quattro punti: `update_draft`, `confirm_and_send`, `cancel_draft`, `add_attachment`). Oggi `E_EMAIL_OP` ed `E_OUTBOX` |
| `E_EMAIL_ALLEGATO_NOT_FOUND` | `NON_TROVATO` | Allegato non trovato. | `core/api/email_views.py` (download e rimozione). Oggi `E_EMAIL_OP` |
| `E_EMAIL_ALLEGATO_FILE_MANCANTE` | `TECNICO` | File dell'allegato non disponibile. | `core/api/email_views.py` (download: la riga c'è, il file su storage no). Oggi `E_EMAIL_OP` |
| `E_EMAIL_ACCOUNT_NOT_FOUND` | `NON_TROVATO` | Account email non trovato. | `amm_software/api/email_views.py` (quattro punti: dettaglio, modifica, eliminazione, test). Oggi `E_EMAIL_ADMIN` |
| `E_EMAIL_TEMPLATE_NOT_FOUND` | `NON_TROVATO` | Template email non trovato. | `amm_software/api/email_views.py` (quattro punti: dettaglio, modifica, eliminazione, anteprima). Oggi `E_EMAIL_ADMIN` |
| `E_EMAIL_LOG_NOT_FOUND` | `NON_TROVATO` | Log email non trovato. | `amm_software/api/email_views.py` (dettaglio di una riga del log). Oggi `E_EMAIL_ADMIN` |

Motivo delle classi, sul modello (api.md §«Il criterio che distingue un 404 da un
500: chi può rimediare»):

* `NON_TROVATO`: l'id arriva dall'URL, cioè da una persona che ha chiesto una cosa
  che non c'è. Può rimediare cambiando la richiesta;
* `TECNICO` per il file mancante: la riga dell'allegato esiste, ma il file su
  storage no. È un guasto (storage perso o non montato) e l'operatore non può farci
  niente. Un 404 lo manderebbe a cercare un allegato che per lui c'è.

⚠️ **`E_EMAIL_LOG_NOT_FOUND` non è un doppione di `E_EMAIL_LOG_INESISTENTE`.**
Quello è `TECNICO` di proposito (la sua nota: *«p_email_log_id non arriva mai da
una persona: è l'id che il chiamante ha scritto un istante prima»*). Qui invece
l'id lo sceglie l'amministratore che consulta il log. Stessa tabella, chi sbaglia
è diverso: è la distinzione per cui `E_EMAIL_LOG_INESISTENTE` è nato. Riusarlo
porterebbe un 500 dove serve un 404.

⚠️ **Perché non riusare un codice 404 che esiste già.** Il catalogo ha
`E_ALLEGATO_NOT_FOUND`, ma è quello dell'allegato di una **pratica**: è nato
apposta per togliere un `E_NOT_FOUND` generico usato per entità diverse (*«un 404
che non dice cosa manca non è diagnosticabile a valle»*). Usarlo per l'allegato di
una email rifarebbe quell'accumulo.

## 3. R-2 — L'«accesso riservato» delle permission

Dal 2026-10-08 il backend trasporta il codice di una permission fino al client.
DRF lo mette in `exc.detail.code`, e `drf_exception_handler` ora lo legge (E-5,
parte BE). `ZeroERPPermission` lo usa già per `E_REPARTO_SENZA_PROFILO`.

Tre permission hanno un messaggio mirato ma nessun codice, quindi escono come
`E_PERMISSION_DENIED` («Permesso negato.»):

| Codice | Classe proposta | Frase (quella che il BE scrive già) | Permission (`core/api/permissions.py`) |
| --- | --- | --- | --- |
| `E_ACCESSO_RISERVATO_ADMIN` | `NON_PERMESSO` | Accesso riservato agli amministratori. | `IsAdminZeroERP` |
| `E_ACCESSO_RISERVATO_PORTALE` | `NON_PERMESSO` | Accesso riservato agli utenti portale. | `PortaleBasePermission` |
| `E_ACCESSO_RISERVATO_SHOP` | `NON_PERMESSO` | Accesso riservato ai clienti shop. | `ShopBasePermission` |

Classe `NON_PERMESSO` (403): il diritto manca e non dipende dallo stato. È la
classe di `E_PERMISSION_DENIED` e di `E_REPARTO_SENZA_PROFILO`.

Perché tre codici e non uno: dicono a chi è riservata la porta, e la reazione
della pagina è diversa. Per l'operatore che apre l'amministrazione la risposta è
«chiedi a un amministratore». Per chi arriva sul portale con la veste sbagliata è
«entra con l'altra veste».

## 4. R-3 — Le altre condizioni sotto gli stessi codici (da confermare con Tid)

Censendo i punti del §2 sono emerse altre due condizioni, che **non sono** dati
errati. Le propongo nello stesso giro perché altrimenti `E_OUTBOX` ed `E_EMAIL_OP`
restano accumulatori. Se Tid preferisce un giro a parte, R-1 e R-2 non ne dipendono.

| Codice | Classe proposta | Frase | Dove, oggi |
| --- | --- | --- | --- |
| `E_EMAIL_BOZZA_NON_DRAFT` | `CONFLITTO_STATO` | La bozza non è più modificabile: è già stata inviata o annullata. | `email_outbox_service.py`: «Solo bozze DRAFT sono modificabili / possono essere inviate / annullabili» (tre punti, `E_OUTBOX`) |
| `E_EMAIL_ACCOUNT_NON_CONFIGURATO` | `TECNICO` | Nessun account email configurato. | `email_outbox_service.py` (`confirm_and_send`, `E_OUTBOX`) |

* `CONFLITTO_STATO`: la bozza esiste, ma il suo stato non ammette il verbo. È la
  definizione della classe, ed è la classe del fratello `E_EMAIL_ALLEGATO_NON_BOZZA`
  (gli allegati si toccano solo in bozza);
* `TECNICO`: manca un pezzo di configurazione, e chi invia non può rimediare
  (stesso ragionamento di `E_EMITTENTE_DEFAULT_MISSING`).

Le altre condizioni sotto i tre codici (campo obbligatorio, file troppo grande,
tipo non consentito, campi non ammessi) sono davvero dati errati e restano dove
sono.

## 5. R-4 — Il dettaglio della ricerca universale non dice mai «non c'è» (E-10)

**Il caso.** Nella ricerca universale si apre il dettaglio di un soggetto per un
ruolo (`GET .../search/<soggetto_id>/detail/?tipo_ruolo_id=…`). Il backend chiama
`script.fn_get_search_detail` e, se riceve NULL, risponde 404 `E_SEARCH_NOT_FOUND`
(già a catalogo, `NON_TROVATO`): `core/api/search_view.py`, ramo `if result is None`.

**Il difetto.** La funzione non restituisce mai NULL:

* i rami `CL` e `FO` costruiscono il risultato con `jsonb_agg` su una sottoquery:
  un aggregato senza `GROUP BY` produce **sempre una riga**, anche da zero righe,
  quindi `v_result` è sempre valorizzato;
* il ramo `ELSE` può dare NULL, ma la chiusura
  `RETURN COALESCE(v_result, jsonb_build_object('tipo_ruolo', …, 'righe', '[]'))`
  lo trasforma in una lista vuota.

Così `{"righe": []}` copre quattro situazioni diverse:

1. il soggetto non esiste;
2. il soggetto esiste ma non ha quel ruolo (nessuna riga in `soggetti_ruoli`);
3. *(solo `CL`)* il soggetto ha il ruolo, ma nessuno dei suoi clienti è nel
   perimetro dell'operatore (oggi lo decide il filtro a mano su `v_scope`; con la
   parte (a) qui sotto, la RLS);
4. il soggetto ha il ruolo e righe visibili, ma il filtro `p_utility_id` non ne
   trova nessuna.

**La decisione (Tid, 2026-10-08):** 1, 2 e 3 sono un «non trovato», cioè una
persona che chiede una cosa che per lei non c'è. Il 4 è un risultato vero: la cosa
c'è, e il filtro restringe a zero.

**La richiesta, in due parti.**

*(a) Il perimetro dei clienti lo fa la RLS* (Tid, 2026-10-08: *«soggetti non ha
emittente ma i clienti sì, quindi dovrebbero filtrare per emittente: bisogna
utilizzare le RLS come da progetto quando servono»*).

Il ramo `CL` filtra oggi a mano:
`v_scope := fn_get_emittenti_scope_sr_effettivo(...)` più
`fn_check_ba_visible_for_emittenti(cl.billing_account_id, v_scope)`. Quel filtro è
della rev 2026-08-18, quando `anagrafiche.clienti` non aveva RLS. Dal 2026-09-10
ce l'ha, armata (`20260910-40`/`-41`): tre policy, una per veste del billing
account, con la canonica `_via_efba` per l'operatore. La funzione è
`SECURITY INVOKER`, quindi la RLS vale già dentro di lei. Il filtro a mano è
diventato **una seconda copia della stessa regola**, scritta in un altro modo: due
copie prima o poi rispondono diversamente, e nessun test se ne accorge.

⇒ Si toglie il filtro a mano e il perimetro resta alla RLS, come nel resto del
progetto. Con lui cade `v_scope`, e il parametro `p_emittente_ids` non ha più
niente da restringere.

⚠️ **Da verificare prima di toglierlo**, sul modello e non su un conteggio: che
la RLS dia **lo stesso perimetro** del filtro a mano per ogni veste che chiama la
ricerca (operatore con whitelist, SUPER_ADMIN con l'emittente attivo che
restringe, batch senza utente). Se una veste vede di più o di meno, va detto qui
prima di cambiare.

⚠️ **La gemella:** `script.fn_search_soggetti_universale` (la lista della stessa
ricerca) ha lo stesso filtro a mano, con lo stesso `v_scope` e lo stesso
`p_emittente_ids`. Il perimetro sono tutte e due (api.md, «se la funzione ha
gemelle, il perimetro sono tutte»): stesso giro.

*(b) «Non c'è» quando il soggetto non risulta.* La funzione restituisce **NULL**
nei casi 1-3, e la struttura con `righe` (anche vuota) solo nel caso 4. In
pratica, una verifica d'esistenza prima del `CASE`, sullo stesso perimetro delle
righe ma **senza** il filtro utility:

* esiste una riga di `soggetti_ruoli` per (`p_soggetto_id`, `p_tipo_ruolo_id`);
* per `CL`, almeno un cliente di quel soggetto-ruolo **è visibile**: con (a) vuol
  dire semplicemente che la RLS ne restituisce almeno uno.

Altrimenti `RETURN NULL`. La `COALESCE` finale cade: arrivati in fondo, il soggetto
c'è.

⭐ **Perché NULL e non un raise.** Il backend traduce già NULL in 404 con il codice
giusto, e la funzione resta una lettura che non scrive nel diario errori a ogni
id sbagliato. Se il team DB preferisce sollevare `E_SEARCH_NOT_FOUND` con
`fn_log_and_raise_error` (come fa per `E_TIPO_RUOLO_NON_TROVATO` poche righe sopra),
va bene lo stesso: il codice arriva al client uguale. Basta che sia **una** delle
due, scritta nel `COMMENT`.

⚠️ **Inesistente e fuori perimetro escono uguali, di proposito**: il 404 non deve
rivelare che esiste un cliente di un altro emittente (stessa regola del billing
account in F-6). Con la RLS viene da sé: la riga fuori perimetro semplicemente
non c'è.

**Fornitori e altri ruoli.** `soggetti`, `soggetti_ruoli` e `fornitori` non hanno
un emittente nel modello, e non hanno RLS: lì non c'è un perimetro da applicare, e
il «non trovato» copre i casi 1 e 2. Il `COMMENT` di oggi lo chiama «residuo»: con
(a) va riscritto come scelta di modello (chi non ha emittente non si filtra per
emittente), oppure, se Tid vuole un perimetro anche sui fornitori, è una domanda
di modello a parte, non di questa funzione.

**Ricaduta sul backend** (la fa la sessione BE, non il team DB): se
`p_emittente_ids` esce dalla firma delle due funzioni, il backend smette di
passarlo (`core/db/search_repository.py`, due chiamate; `core/api/search_view.py`,
dove oggi lo calcola con `PermissionResolver.get_emittenti_sr_ids`). Le due firme
vanno cambiate **nello stesso giro** in cui il backend si allinea, e il binding si
prova con una chiamata vera: i test con repository finto non vedono una firma
cambiata.

**pgTAP**, con i soggetti **costruiti** nel test (nessun confronto con i dati
presenti):

* soggetto inesistente → NULL;
* soggetto senza quel ruolo → NULL;
* cliente di un altro emittente, operatore con perimetro ristretto (GUC impostate nel test) → NULL, per effetto della RLS;
* la lista (`fn_search_soggetti_universale`) con lo stesso operatore non mostra quel cliente: stesso perimetro della funzione di dettaglio;
* cliente visibile, `p_utility_id` di un'utility che non ha → `righe = []`, non NULL;
* cliente visibile senza filtro → righe presenti (il caso che c'era già);
* ramo `ELSE` con soggetto-ruolo esistente → una riga, come oggi.

**Unico consumatore** di entrambe: `core/db/search_repository.py`
(`get_search_detail`, che tratta già NULL come «non trovato», e la lista).

## 6. Cosa fa il backend dopo l'apply

1. `genera_error_policies` (il modulo generato prende le classi), poi il
   `--check` del test di divergenza;
2. un messaggio di ripiego senza segnaposto per ogni codice nuovo
   (`error_messages_fallback.py`);
3. gli `ErrorManager.require` dei punti del §2 e del §4 passano al codice nuovo.
   Per la bozza (dieci punti in due file) se ne valuta l'estrazione (regola del 2,
   da dichiarare a Tid prima di farla);
4. le tre permission del §3 mettono `self.code`;
5. test: un caso per codice; per le permission, il percorso fino all'envelope;
6. doc: `api_email.md`, `error-handling-api.md` (tolto il «Difetto noto» residuo),
   righe E-4/E-5 dell'analisi chiuse;
7. R-4: il ramo 404 c'è già. Se la firma perde `p_emittente_ids`, il repository e
   la view smettono di passarlo (vedi §5). Si aggiunge un test sul DB vero
   (`ZEROERP_TEST_DB_E2E`) per i casi 1, 2 e 4, perché quello di oggi
   (`test_search_view.py`) prova il 404 con un repository finto, ed è verde anche
   con la funzione che non dà mai NULL. Si aggiorna la doc dell'endpoint.

## 7. Nota per il team DB

* Causa e soluzione le scrive il team DB, come per ogni codice. Dal lato BE un
  suggerimento: per `E_EMAIL_ALLEGATO_FILE_MANCANTE` ed
  `E_EMAIL_ACCOUNT_NON_CONFIGURATO` la soluzione è per chi gestisce la macchina
  (storage degli allegati, casella mittente), non per l'operatore.
* I nomi sono proposte. Se il catalogo ha una convenzione che li vuole diversi,
  vale quella: il backend li legge dal catalogo rigenerato.

## 8. Consegne

*(da compilare dal team DB)*
