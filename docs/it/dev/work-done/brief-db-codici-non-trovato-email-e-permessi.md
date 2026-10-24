# Brief DB — Codici d'errore per l'email e per l'«accesso riservato», e il «non trovato» del dettaglio ricerca

> **Chi scrive:** sessione backend (`dev/backend-tid`), 2026-10-08. **A chi:** team
> DB (`dev/db-tid`), tramite Tid.
> **Origine:** voci E-4, E-5 ed E-10 di
> [analisi-be-difetti-emersi-verifica-doc-api-core.md](../work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md).
> La parte che si poteva chiudere coi codici già a catalogo è fatta lato backend
> (2026-10-08, righe E-4/E-5 dell'analisi). Restano i punti per cui **nessun codice
> esistente dice la cosa giusta**: servono righe nuove nel catalogo.
> **Stato (2026-10-10):** ✅ R-1…R-4: DB applicato il 2026-10-08, pgTAP verdi
> (Tid); giro BE fatto il 2026-10-09 (§9). ✅ **R-5…R-9: giro DB applicato da Tid
> il 2026-10-10, pgTAP verdi** (Tid: «migrazione applicata e test verdi»; §14): 8 changeSet
> `20261010-08…-15`, 4 codici a catalogo (id 1239-1242), la colonna
> `config.tipi_ruoli.entita_esistenza`, 1 pgTAP nuovo e 4 riallineati. R-8 è
> **superato dal modello** (Q-5, Tid 2026-10-10). Partito dopo l'apply di
> [brief-db-esecutivi-ba-coppia](brief-db-esecutivi-ba-coppia.md) giro 1 e 2, come
> deciso (Q-4). ✅ **Backend fatto il 2026-10-10** (§15): tutti i punti del §14.6. ✅ **Chiuso e archiviato il
> 2026-10-10** su richiesta di Tid.
> **Da leggere per primo:** §1, poi il §14 (consegne del giro R-5…R-9).

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

**Stato delle richieste** (2026-10-09). Le prime quattro sono nate col brief, le
altre dal giro BE (§10-§12), tutte approvate da Tid:

| # | Cosa | Dove | Stato |
| --- | --- | --- | --- |
| R-1, R-2, R-3 | Undici codici a catalogo | §2-§4 | ✅ applicato 2026-10-08; BE fatto 2026-10-09 |
| R-4 | «Non c'è» del dettaglio, perimetro dalla RLS | §5 | ✅ applicato 2026-10-08; BE fatto 2026-10-09 |
| R-5 | Ritiro di `p_emittente_ids` e di `fn_get_emittenti_scope_sr_effettivo` | §10, §14 | ✅ applicato 2026-10-10, pgTAP verdi |
| R-6 | Regola unica di «il soggetto-ruolo si mostra» su una colonna nuova di `tipi_ruoli` (Q-1), con `ricerca_visibile` nel DB (Q-2) | §11, §13, §14 | ✅ applicato 2026-10-10, pgTAP verdi; ricaduta BE §14.6 |
| R-7 | Tre codici email a catalogo | §12.2, §14 | ✅ applicato 2026-10-10 (id 1240-1242); ricaduta BE §14.6 |
| R-8 | `attivo` del soggetto nella check, lista e dettaglio d'accordo | §12.3, §13 | ✅ **superato dal modello** (Q-5, Tid 2026-10-10): cade anche il filtro morto della lista |
| R-9 | Builder pgTAP fino al cliente | §12.4, §14 | ✅ applicato 2026-10-10, pgTAP verdi; copie Python al BE §14.6 |

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

*(team DB, 2026-10-08)* — **applicato da Tid il 2026-10-08, pgTAP verdi** (compreso `script/test-search-soggetti-universale`, che pre-apply non era provabile: §8.4).

### 8.1 Cosa c'è

| Richiesta | Dove | Note |
| --- | --- | --- |
| R-1, R-2, R-3 | `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv` (id 1211-1221) | undici righe in coda, causa e soluzione scritte; nessun changeSet nuovo, li rilegge il mirror |
| R-4 (BB) | `20_code/script/20261008-01-create-fn-check-soggetto-ruolo-visibile` | la regola «il soggetto-ruolo si mostra a chi guarda», una volta sola |
| R-4 (b) + (a) | `20_code/script/20261008-02-update-fn-get-search-detail-non-trovato` | NULL nei casi 1-3, perimetro dalla RLS |
| R-4 (a), gemella | `20_code/script/20261008-03-update-fn-search-soggetti-universale-perimetro-rls` | stesso filtro di riga del dettaglio, perimetro dalla RLS |
| pgTAP | `script/test-search-scope-interno-v1` (riscritto, 21 test), `script/test-search-soggetti-universale` (24, 26 e la scelta del soggetto) | vedi §8.4 |
| Doc | `dbzero/script/manual/fn_get_search_detail.md`, `fn_search_soggetti_universale.md` | |

### 8.2 Le scelte che il brief lasciava al team DB

* **Un nome cambiato.** `E_EMAIL_BOZZA_NON_DRAFT` è diventato **`E_EMAIL_NON_BOZZA`**:
  «bozza» e «DRAFT» sono la stessa parola, e i fratelli si chiamano già
  `E_EMAIL_ALLEGATO_NON_BOZZA` e `E_RIGA_DOC_NON_BOZZA`. **Il BE usi questo nome.**
  Frase: «Questa mail non è più in bozza: non si può più modificare, inviare o
  annullare.» (copre i tre verbi dei tre punti di `email_outbox_service.py`).
  Gli altri dieci nomi e tutte le classi sono quelli proposti.
* **R-3 l'ho fatto nello stesso giro**, come proponeva il §4: Tid ha detto «da
  eseguire» sul brief intero. Se preferisce separarlo, le due righe si tolgono dai
  CSV prima dell'apply e R-1/R-2 non ne risentono.
* **NULL e non un raise** per il «non c'è» (§5 ⭐), scritto nel `COMMENT`.
* **`p_emittente_ids` resta in firma, superato e non letto.** La regola di casa: un
  parametro che non serve più non si toglie cambiando la firma; si dichiara, e il
  ritiro lo decide Tid col backend. Così **nessuna ricaduta obbligata sul BE in
  questo giro**: le firme sono byte-identiche (provato), il repository può
  continuare a passarlo. Il ritiro, quando Tid lo decide, è un `DROP` + `CREATE`
  delle due firme nello stesso giro in cui il BE smette di passarlo (§5,
  «Ricaduta sul backend»).
* **Regola del 2.** Lista e dettaglio devono dire la stessa cosa su chi si vede, e
  il brief lo chiedeva anche come test. Invece di due `EXISTS` scritti in due
  funzioni, la regola sta in `script.fn_check_soggetto_ruolo_visibile` (SQL,
  `SECURITY INVOKER`, così la RLS vale con l'identità di chi chiama): la lista la
  usa come filtro di riga, il dettaglio come verifica d'esistenza. Il perimetro
  vero resta nella policy; la check chiede solo «ne resta almeno uno?».

### 8.3 La verifica del perimetro (il ⚠️ del §5)

Letta sul corpo delle funzioni, non su un conteggio.

* **Operatore con whitelist, super admin, emittente attivo: stesso perimetro.** Il
  filtro a mano era `fn_check_ba_visible_for_emittenti(ba, fn_get_emittenti_scope_sr_ids(utente) ∩ p_emittente_ids)`;
  la policy `rls_clienti_ef_whitelist` è `fn_scope_ef_whitelist_via_efba(utente, ba)`,
  che chiama la **stessa** `fn_check_ba_visible_for_emittenti` sullo **stesso**
  `fn_get_emittenti_scope_sr_ids` (NULL → tutto, `'{}'` → niente). L'emittente
  attivo restringe dentro `fn_get_emittenti_scope_pk_ids`, per tutte e due. E il
  backend passava come `p_emittente_ids` proprio `fn_get_emittenti_scope_sr_ids(utente)`
  (`PermissionResolver.get_emittenti_sr_ids`): l'intersezione non toglieva niente.
* **Batch senza utente** con veste OPERATORE: niente, prima e dopo.
* **Due differenze, tutte e due dalla parte del modello:**
  - `CLIENTE_PORTALE` e `SHOP_CUSTOMER`: prima niente (nessuna identità
    OPERATORE → `'{}'`), ora i clienti del proprio billing account, come su ogni
    tabella protetta. L'endpoint della ricerca è dell'operatore, quindi oggi non
    si vede;
  - proprietario e `BYPASSRLS`: prima niente (utente vuoto), ora tutto.
* **La colonna `emittente_ragione_sociale`** della lista: cade la condizione sullo
  scope nella `ON`. Il suo compito (chi vede solo A legge «A», non «A, B») lo fa la
  RLS sulla `LEFT JOIN` di `clienti`, ed è equivalente per costruzione: la policy
  ammette un cliente se `fn_get_ba_emittente_sr_id(ba)` sta nello scope, e la
  colonna è proprio `fn_get_ba_emittente_sr_id` di quel billing account.

⛔ **Un effetto collaterale, dichiarato.** Un soggetto-ruolo CL senza **nessun**
cliente prima compariva al super admin nella lista (con scope NULL il filtro non
si accendeva) e il dettaglio rispondeva righe vuote; ora non compare a nessuno, e
il dettaglio è NULL. È la regola del §5 (b) applicata senza eccezioni: «per CL,
almeno un cliente visibile».

### 8.4 Prove fatte (pre-apply, scratch `zeroerp_ci`, SQL estratto dagli YAML)

| Prova | Esito |
| --- | --- |
| SQL estratto dei tre changeSet in transazione annullata | ✅ passa; una funzione per nome; `pg_get_function_identity_arguments` e `pg_get_function_result` **identici** al vivo (nessun overload, nessun cambio di contratto); `zeroerp_app` ha `EXECUTE` sul BB |
| `plpgsql_check` sulle due funzioni | ✅ zero `error`; restano i warning già presenti (`PERFORM` VOLATILE del log errori) e `unused parameter "p_emittente_ids"`, che è il superato dichiarato |
| `script/test-search-scope-interno-v1` | ✅ **21/21 con** l'SQL estratto; **16/21 senza** (rossi 9, 11, 12, 13, 19): i test nuovi distinguono il comportamento vecchio dal nuovo |
| `script/test-ba-emittente-risoluzione-v1`, `script/test-scope-emittenti-fail-closed-v1` | ✅ 14/14 e 12/12, prima e dopo |
| `dbops/test-riferimenti-morti-v1`, `dbops/test-postura-proprietario-rls-v1` | ✅ 9/9 e 6/6, prima e dopo |
| Upsert **completo** dei due CSV (tutte le righe) in transazione, poi `config/test-codici-errore-identita`, `config/test-codici-errore-obsoleto-dal`, `dbops/test-vw-codici-errore-motivo-nominato`, `script/test-catalogo-messaggi-errore-completo`, `config/test-costanti-catalogo-citate-dal-codice-v1`, `script/test-fn-get-messaggio-fallback-lingua` | ✅ tutti verdi; nessuna riga dei CSV rifiuta (il mirror è risvegliabile) |
| Guardrail statici (letterali, `runOnChange`, preCondition/seed, trigger d'automazione, grant batch, preambolo pgTAP) | ✅ |

⚠️ **`script/test-search-soggetti-universale` non è provato pre-apply.** Pesca i
soggetti dai dati: sullo scratch muore al test 7 sia prima sia dopo
(`ERRORE_FIXTURE` già in `baseline-rossi-scratch.tsv` e `baseline-rossi-ci.tsv`),
e su dbdev non posso creare funzioni. Le modifiche: 24 e 26 ora pinnano che il
parametro superato non decide; il soggetto pescato deve passare
`fn_check_soggetto_ruolo_visibile` (un CL fuori perimetro ha ora dettaglio NULL,
e 12-15 leggerebbero NULL). Il file usa il BB nuovo, quindi prima dell'apply muore
su «la funzione non esiste»: va lanciato **dopo** l'apply, su dbdev.

⚠️ `test-search-scope-interno-v1` resta `pgtap-runner: owner` (per la fixture),
ma accende `FORCE ROW LEVEL SECURITY` su `anagrafiche.clienti` dentro la propria
transazione prima delle asserzioni sulle ricerche (con `lock_timeout`), così
l'owner subisce le policy come l'app. Il `ROLLBACK` lo spegne.

### 8.5 Residui dichiarati

* **`script.fn_get_emittenti_scope_sr_effettivo` resta senza chiamanti.** Era nata
  per queste due ricerche (rev 2026-08-18) e nessun'altra funzione, né il backend,
  la usa. La provano ancora `test-search-scope-interno-v1` (test 1-7) e
  `test-scope-emittenti-fail-closed-v1` (10-11). Non l'ho ritirata: si decide
  insieme al ritiro di `p_emittente_ids`, che è la stessa storia. Domanda a Tid.
* **`p_emittente_ids` in firma, superato** (§8.2): ritiro da decidere con il BE.
* La lista filtra `s.attivo = true`, il dettaglio no. Non è perimetro e non era
  chiesto: lo segnalo solo, un soggetto disattivo si apre ancora dal dettaglio se
  qualcuno ne conosce l'id.

### 8.6 Per il backend, dopo l'apply

Il §6 vale com'è, con due correzioni:

* al punto 3, il codice della bozza non più in bozza è **`E_EMAIL_NON_BOZZA`**;
* al punto 7, **la firma non cambia**: repository e view possono continuare a
  passare `p_emittente_ids` (non è letto). Il test sul DB vero per i casi 1, 2 e 4
  resta da fare: oggi il 404 è provato solo col repository finto.

## 9. Giro BE

*(sessione backend, 2026-10-09)*

### 9.1 Cosa c'è

| Passo §6 | Esito |
| --- | --- |
| 1-2. Policy generate e ripieghi | ✅ erano già in HEAD |
| 3. Codici nuovi nei punti del §2 e del §4 | ✅ tutti; `E_EMAIL_NON_BOZZA` col nome del §8.2 |
| 3. Regola del 2 (ok Tid, 2026-10-09) | ✅ `EmailOutboxService.get_bozza` (sul BB `o_not_found`) per la bozza: dieci punti diventano una sede. Le quattro view che chiamano un verbo (modifica, invio, annullo, upload) **non rileggono più** la bozza, che il verbo già legge e controlla. `_richiedi_bozza` per i tre verbi «solo in bozza»; `_allegato_o_404` (core) e `_account_o_404` / `_template_o_404` (admin). L'eliminazione di account e template legge prima di cancellare, come già faceva il test SMTP. I messaggi vengono da `USER_MESSAGE_FALLBACK`, non sono riscritti a mano |
| 4. `self.code` nelle tre permission | ✅ |
| 5. Test | ✅ `test_email_outbox_service` n. 18-20, `test_email_views_fase6` n. 20-22, nuovo `test_email_e_permessi_codici_mirati` (le permission sul percorso DRF intero, fino all'envelope) |
| 6. Doc | ✅ `api_email.md` (§Codici d'errore), `error-handling-api.md`, `api_search_universale.md`; E-4, E-5 ed E-10 chiuse nell'analisi |
| 7. R-4 | ✅ firma invariata (§8.6), nuovo `core/tests/db/test_search_detail_non_trovato_db.py` sul DB vero: casi 1 e 2 → `None`, caso 4 → `righe: []`, più la contro-prova del cliente visibile |

Prove: suite `apps.core` + `apps.amm_software` con `ZEROERP_TEST_DB_E2E=1`
(1951 test, verdi); mypy a cricchetto, nessun rilievo nuovo; ruff pulito sui file
toccati.

### 9.2 Cosa è emerso, fuori dal perimetro del brief

* **«Nessuna azienda attiva»** (`core/api/email_views.py`, preparazione della
  bozza, oggi `E_EMAIL_OP`). ⚠️ Correzione di questo stesso paragrafo: lo avevo
  detto «non un dato errato». Il catalogo ha già il codice di questa condizione,
  ed è `DATO_ERRATO` **di proposito**: `E_EMITTENTE_NON_RISOLTO` (*«Nessun
  emittente fiscale attivo: seleziona l'emittente in alto…»*), che la nota dice
  *«un codice solo per N tabelle: è la condizione ad essere una»*. È la modalità
  «Tutti gli emittenti» del super admin, che è di sola lettura, e il rimedio è
  della persona. ✅ **Fatto il 2026-10-09** (ok Tid): il BE usa
  `E_EMITTENTE_NON_RISOLTO`, status 400 invariato, frase del catalogo, senza
  campo. Nessuna riga nuova a catalogo. Con questo si è ritirata da sola
  l'unica esenzione del presidio C2 (`test_ui_action_e_canale_campi`), che
  valeva solo finché ogni sito del codice mandava il campo.
* Due condizioni vicine, sotto gli stessi accumulatori: «Template '…' non
  trovato» della preparazione della bozza (`E_OUTBOX`, da `resolve_and_render`)
  e «Path allegato non valido» (`email_allegati_storage.percorso_allegato`,
  `E_EMAIL_OP`: il percorso arriva dal database, non da una persona).
* **CL e FO non si comportano allo stesso modo nel dettaglio.** Letto sul
  modello: un soggetto-ruolo può esistere senza la riga della sua entità, per
  tutti e due i ruoli. Per FO, `uq_fornitori_soggetto_ruolo_id` dice 0..1 e
  nessun trigger la pretende; per CL il soggetto-ruolo nasce prima di istanza,
  billing account e cliente. La check `fn_check_soggetto_ruolo_visibile` tratta
  però i due casi in modo diverso, perché scrive `'CL'` come letterale: CL
  senza clienti dà NULL, FO senza fornitore dà `righe: []` e compare in lista.
  Lo stesso varrebbe per VT (`vettori`) e BANK_B (`bank_branches`).
  ⇒ Proposta, sul catalogo che c'è già: `config.tipi_ruoli.entita_tabella` dice
  per ogni ruolo qual è la sua entità (CL → `vw_clienti_codice_ba`, FO →
  `fornitori`, VT → `vettori`, BANK_B → `bank_branches`, EF →
  `emittenti_fiscali`). Regola unica: un soggetto-ruolo si mostra se ha
  **almeno una riga della sua entità visibile a chi guarda**; un ruolo senza
  entità si mostra se esiste. Il perimetro resta alla RLS di ciascuna entità
  (per CL quella di `clienti`, a patto che la vista sia `security_invoker`), e
  il letterale `'CL'` esce dalla check. ✅ Approvata da Tid il 2026-10-09:
  richiesta **R-6** al §11. ⚠️ Per il team DB: la tabella diventa un
  dato, quindi serve SQL dinamico, e la check gira come filtro di riga della
  lista. Va misurato con EXPLAIN se la regola si applica per riga o una volta
  per ruolo.
* **La riga di `anagrafiche.clienti` nei test sul DB vero si scrive a mano**, dopo
  `dbops.fn_pgtap_crea_cliente_ba`, in più file di test (con questo).
  Un builder che arrivi fino al cliente sarebbe un lavoro del team DB.

### 9.3 Decisioni ancora aperte (Tid)

Tutte raccolte, con proposta, nel §12.

## 10. R-5 — Ritiro di `p_emittente_ids` e di `fn_get_emittenti_scope_sr_effettivo`

*(sessione backend → team DB, 2026-10-09; ritiro approvato da Tid «se non sono
più utilizzate da nessuno»)*

**Chi le usa, verificato il 2026-10-09:**

* `p_emittente_ids` (in `fn_search_soggetti_universale` e
  `fn_get_search_detail`): non lo legge nessuna delle due funzioni (§8.2). Il
  backend **ha smesso di passarlo** il 2026-10-09 (`core/db/search_repository.py`
  e `core/api/search_view.py`; test `test_search_view` riallineati). Era l'unico
  chiamante, quindi oggi non lo passa nessuno;
* `script.fn_get_emittenti_scope_sr_effettivo`: nessuna funzione la chiama (la
  doc auto-generata di `fn_search_soggetti_universale` la nomina solo in un
  commento), e il backend nemmeno. La provano ancora due pgTAP:
  `script/test-search-scope-interno-v1` (test 1-7) e
  `script/test-scope-emittenti-fail-closed-v1` (test 10-11).

**Cosa si chiede:**

1. `DROP` delle due firme vecchie e `CREATE` senza `p_emittente_ids`, insieme
   ai `COMMENT`, che oggi lo dichiarano superato;
2. `DROP` di `script.fn_get_emittenti_scope_sr_effettivo`;
3. pgTAP: togliere i test che provano la funzione ritirata (1-7 di
   `test-search-scope-interno-v1`, 10-11 di
   `test-scope-emittenti-fail-closed-v1`) e quelli che pinnano il parametro
   superato (8-11 di `test-search-scope-interno-v1`, 24 e 26 di
   `test-search-soggetti-universale`), riallineando i `plan()`;
4. doc `manual/` delle due funzioni.

Il presidio BE del vecchio trasporto a tre stati
(`core/tests/db/test_search_repository_scope.py`) è stato riscritto il
2026-10-09: ora prova che il repository **non** manda `p_emittente_ids`.

**Ricaduta sul backend:** nessuna. Il repository chiama già per nome senza
`p_emittente_ids`, quindi funziona con la firma vecchia (il parametro ha
`DEFAULT NULL`) e con quella nuova. Dopo l'apply basta rilanciare
`core/tests/db/test_search_detail_non_trovato_db.py` sul DB vero, per provare il
binding.

## 11. R-6 — Una regola sola per «il soggetto-ruolo si mostra»

*(sessione backend → team DB, 2026-10-09; opzione approvata da Tid)*

> ⚠️ **Forma corretta dal §13** (Tid, 2026-10-09): la regola non legge
> `entita_tabella` ma una **colonna nuova** di `tipi_ruoli` che accetta solo
> tabelle (Q-1); `ricerca_visibile` entra nella stessa regola del DB (Q-2); lo
> stato dell'entità non decide (Q-3). Dove questo paragrafo dice
> `entita_tabella`, vale il §13.

**Il difetto.** `script.fn_check_soggetto_ruolo_visibile` (§8.2) scrive `'CL'`
come letterale. Così due stati che il modello ammette allo stesso modo hanno
due risposte:

| Soggetto-ruolo | Lista | Dettaglio |
| --- | --- | --- |
| CL senza nessun cliente | non compare | NULL → 404 |
| FO senza la riga in `fornitori` | compare | `righe: []` |

Che il modello li ammetta tutti e due lo dice la struttura, non un conteggio.
Per FO, `uq_fornitori_soggetto_ruolo_id` dice 0..1 e nessun trigger di
`soggetti_ruoli` crea o pretende la riga. Per CL il soggetto-ruolo nasce prima
di istanza, billing account e cliente (è anche l'ordine dei builder pgTAP).
Lo stesso vale per VT (`vettori`) e BANK_B (`bank_branches`).

**La richiesta.** La regola si legge dal catalogo che già dice qual è l'entità
di ogni ruolo, `config.tipi_ruoli.entita_tabella` (la usa già
`fn_search_soggetti_universale` per cercare sul codice dell'entità):

* ruolo **con** `entita_tabella` → il soggetto-ruolo si mostra se ha **almeno
  una riga della sua entità visibile a chi guarda**. Il perimetro lo fa la RLS
  di quell'entità, quando ce l'ha;
* ruolo **senza** `entita_tabella` → si mostra se il soggetto-ruolo esiste.

Il letterale `'CL'` esce dalla check, e lista e dettaglio restano d'accordo
per costruzione (la check è già la loro sede unica). Il caso FO senza
fornitore diventa un «non trovato», come CL senza clienti.

**Da verificare prima, sul modello:**

* l'entità di CL è la **vista** `anagrafiche.vw_clienti_codice_ba`. La doc
  auto-generata (2026-10-09) la dà `security_invoker=on` su `clienti`, quindi la
  RLS di `clienti` vale anche passando dalla vista. Una riga per cliente, come
  la check di oggi;
* `entita_tabella` è un dato, quindi serve SQL dinamico (`EXECUTE format(...)`
  su una `regclass` già validata da `trgfn_tipi_ruoli_guard_entita_ref`). La
  check è anche il filtro di riga della lista: va misurato con `EXPLAIN` sul DB
  vero se conviene risolverla una volta per ruolo (il ruolo è uno per
  chiamata) invece che per riga;
* `emittenti_fiscali` per EF e `bank_branches` per BANK_B: dire se un
  soggetto-ruolo senza la sua riga deve sparire anche lì (per EF il ramo
  `ELSE` del dettaglio oggi mostra una riga).

**pgTAP**, con i soggetti costruiti nel test: FO senza fornitore → dettaglio
NULL e assente dalla lista; FO col fornitore → righe; VT senza vettore → NULL;
un ruolo senza `entita_tabella` → presente; CL invariato (i casi 12-20 di
`test-search-scope-interno-v1`).

**Ricaduta sul backend:** nessuna nel codice (NULL → 404 c'è già). Dopo
l'apply si aggiunge a `core/tests/db/test_search_detail_non_trovato_db.py` il
caso FO senza fornitore, e si aggiorna `api_search_universale.md`.

## 12. Tutto ciò che resta, in un posto solo

*(sessione backend, 2026-10-09: elenco completo delle voci nate da questo
brief, ciascuna con la proposta. Prima stavano sparse in fondo ai messaggi.)*

### 12.1 Fatte dal BE il 2026-10-09 (codici già a catalogo)

* «Nessun account email configurato» nella **preparazione** di una bozza e in
  ogni mail di sistema (`EmailDispatchService.resolve_and_render`, sotto
  `E_OUTBOX` / `E_EMAIL`, 400) → `E_EMAIL_ACCOUNT_NON_CONFIGURATO` (500), lo
  stesso codice dell'invio di una bozza: è la stessa condizione;
* «Account non trovato» del test SMTP (`EmailDispatchService.test_connection`,
  `E_EMAIL`, 400) → `E_EMAIL_ACCOUNT_NOT_FOUND` (404), come il dettaglio
  dell'account.

Test: `test_email_service` n. 6 e 8b.

### 12.2 R-7 — Tre codici nuovi a catalogo (team DB, seed `80_data`) — ✅ approvato da Tid il 2026-10-09

Restano sotto gli accumulatori tre condizioni che non sono dati errati:

| Codice proposto | Classe | Frase proposta | Dove, oggi |
| --- | --- | --- | --- |
| `E_EMAIL_TEMPLATE_NON_CONFIGURATO` | `TECNICO` | Nessun template email configurato per questo invio. | `email_service.resolve_and_render` («Template email '…' non trovato», `E_EMAIL` / `E_OUTBOX`, 400): mail di sistema (reset password, inviti, approvazioni prezzo) e preparazione della bozza |
| `E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO` | `TECNICO` | Percorso dell'allegato non valido. | `email_allegati_storage.percorso_allegato` («Path allegato non valido», `E_EMAIL_OP`, 400): download, invio SMTP; la cancellazione lo scrive nel log e prosegue |
| `E_EMAIL_ALLEGATI_LIMITE` | `CONFLITTO_STATO` | La mail ha già il numero massimo di allegati: togline uno per aggiungerne un altro. | `email_outbox_service.add_attachment` («Numero massimo allegati raggiunto», `E_OUTBOX`, 400) |

Motivi, sul modello:

* **template**: il codice del template lo sceglie il **programma** (le mail di
  sistema lo scrivono nel codice; la preparazione della bozza non ha un
  chiamante nel frontend). La risoluzione ha già il suo ripiego (reparto →
  sistema, lingua): se non trova niente, manca la configurazione, e chi chiede
  la mail non può rimediare. Stesso ragionamento di
  `E_EMAIL_ACCOUNT_NON_CONFIGURATO`. ⚠️ Non è `E_EMAIL_TEMPLATE_NOT_FOUND`
  (404): quello è l'id che l'amministratore sceglie dal pannello;
* **percorso**: il `file_path` arriva dal **database**, non da una persona. Un
  percorso che esce dalla radice è un dato corrotto o manomesso: un guasto, e
  un evento da guardare. ⚠️ Non è `E_EMAIL_ALLEGATO_FILE_MANCANTE`: quello è un
  file che manca, questo un percorso che non deve esistere;
* **limite allegati**: il file che l'operatore manda va bene; è la mail a essere
  piena. Non c'è un campo da correggere, c'è uno stato (api.md, «Scegliere fra
  409 e 400»). Gli altri due rifiuti dell'upload (tipo e dimensione del file)
  sono invece dati errati e restano `E_OUTBOX`.

**Dopo l'apply (BE):** i tre punti passano ai codici nuovi. Con template e
account dotati del loro codice, il parametro `error_code` di
`resolve_and_render` non serve più e si toglie. Un test per codice.

### 12.3 R-8 — `attivo` del soggetto: lista e dettaglio dicano la stessa cosa (team DB) — ✅ approvato da Tid il 2026-10-09

`fn_search_soggetti_universale` filtra `s.attivo = true`, mentre
`fn_get_search_detail` non lo fa (§8.5): un soggetto disattivato non compare in
lista, ma il suo dettaglio si apre se se ne conosce l'id. Il dettaglio lo
chiama un solo consumatore, il drawer della ricerca, e sempre da una riga della
lista.

⇒ **Proposta:** la condizione `attivo` entra in
`script.fn_check_soggetto_ruolo_visibile`, la sede unica di «chi si vede» per
lista e dettaglio, ed esce dal `WHERE` della lista. Un soggetto disattivato dà
404 anche nel dettaglio. Si fa nello stesso giro di R-6, che riscrive la stessa
check. pgTAP: soggetto disattivato → assente dalla lista e dettaglio NULL.

### 12.4 R-9 — Un builder pgTAP che arrivi fino al cliente (team DB) — ✅ approvato da Tid il 2026-10-09

`dbops.fn_pgtap_crea_cliente_ba` si ferma al billing account. La riga di
`anagrafiche.clienti` la scrive a mano ogni test che serve un cliente: più
file Python sul DB vero (`test_ricerca_liste_db`,
`test_search_detail_non_trovato_db`, …), più i pgTAP (es.
`test-search-scope-interno-v1`). Le copie sono già diverse fra loro: stato `PR`
in una, `AT` più la data di attivazione in un'altra (con `AT` senza data il
trigger rifiuta).

⇒ **Proposta (regola del 2):** `dbops.fn_pgtap_crea_cliente(...)`, che chiama
`fn_pgtap_crea_cliente_ba` e scrive la riga di `clienti` con uno stato ammesso,
e ritorna anche `cliente_id`. Il ritiro delle copie nei test Python lo fa poi il
BE, nello stesso giro.

### 12.5 Regola del 2 sull'account di invio — ✅ fatto il 2026-10-09 (ok Tid)

«Risolvi l'account, o 500 `E_EMAIL_ACCOUNT_NON_CONFIGURATO`» era scritto in due
punti, `resolve_and_render` e `confirm_and_send`. Ora la sede è una sola,
`EmailDispatchService.account_di_invio(unita_organizzativa_id)`, registrata nel
catalogo BB. Il rilancio batch (`send_pending_emails`) non la usa, di
proposito: lui non rifiuta, segna la mail `FAILED` e prosegue. Il test
«senza account la bozza resta DRAFT» ora gira col dispatcher **vero**, per
provare la regola invece di un rifiuto fabbricato dal mock.

### 12.6 In attesa del team DB (già richieste)

* **R-5** (§10): ritiro di `p_emittente_ids` e di
  `fn_get_emittenti_scope_sr_effettivo`. Il BE ha già smesso di passarlo.
* **R-6** (§11): regola unica su `entita_tabella`, insieme a R-8.
* **R-7** (§12.2): tre codici email a catalogo.
* **R-8** (§12.3): `attivo` del soggetto nella check.
* **R-9** (§12.4): builder pgTAP fino al cliente.

## 13. Rilievi del team DB prima del giro R-5…R-9

*(team DB, 2026-10-09: analisi del brief sul modello, prima di scrivere codice.
Le domande si chiudono una alla volta con Tid; la risposta si scrive accanto.)*

### 13.1 Domande aperte (Tid)

| # | Domanda | Riguarda | Risposta |
| --- | --- | --- | --- |
| Q-1 | `entita_tabella` nasce per dire **dove si cerca il codice**; R-6 le fa dire anche **quale entità fa esistere il soggetto-ruolo**. Va bene un significato doppio (dichiarato nel `COMMENT` e presidiato), o serve una colonna separata? | R-6 | ✅ Tid, 2026-10-09: **colonna separata** (nome da fissare, es. `entita_esistenza`), che accetta **solo tabelle** (`relkind = 'r'`, niente viste: la RLS è quella della tabella, e il caso «vista senza `security_invoker`» non può nascere). Valore per ruolo: CL → `anagrafiche.clienti`, FO → `fornitori`, VT → `vettori`, BANK_B → `bank_branches`, EF → `emittenti_fiscali`; vuota → il soggetto-ruolo si mostra se esiste. `entita_tabella` resta alla sola ricerca del codice. La stessa tabella la leggono la verifica d'esistenza e le righe del dettaglio |
| Q-2 | `ricerca_visibile` lo controlla solo il backend (`_require_tipo_ruolo_id`); le due funzioni DB accettano qualunque ruolo. Entra nella regola di «chi si vede» del DB, o resta un filtro del menu a tendina dichiarato tale? (Decide anche la domanda su EF del §11, che oggi ha `ricerca_visibile = false`.) | R-6 | ✅ Tid, 2026-10-09: **entra nel DB.** `fn_search_soggetti_universale` e `fn_get_search_detail` rifiutano da sole un ruolo con `ricerca_visibile = false` (codice a catalogo scelto dal team DB: il ruolo lo sceglie il programma dal menu, quindi è un chiamante sbagliato, non un dato di una persona). **Ricaduta BE:** il controllo `is_tipo_ruolo_visibile` di `_require_tipo_ruolo_id` si ritira nello stesso giro (sarebbe una seconda copia); il menu a tendina (`LookupTipiRuoliView`) continua a leggere la colonna. La domanda su EF del §11 cade: non è ricercabile |
| Q-3 | Con R-8 conta l'`attivo` del **soggetto**. E quello dell'**entità**? Un fornitore con la sola riga `fornitori.attivo = false`, o un cliente chiuso, si mostra? | R-8 | ✅ Tid, 2026-10-09: **conta solo il soggetto.** Soggetto disattivato = anagrafica da non usare più → sparisce; cliente chiuso o fornitore disattivato = rapporto finito ma da consultare (fatture da incassare, resi, contestazioni) → **si trova**, e il dettaglio ne mostra lo stato. Lo stato dell'entità non entra nella check, e il `COMMENT` lo dice. pgTAP: cliente chiuso → in lista e nel dettaglio, con lo stato; fornitore con `attivo = false` → idem |
| Q-5 | *(emersa scrivendo, 2026-10-10)* R-8 chiede di mettere `soggetti.attivo` nella regola unica. Il modello però non ammette un soggetto-ruolo col soggetto disattivato: non si disattiva un soggetto che ha ruoli (`trg_soggetti_a10_soggetti_ruoli_block_deact_upd`, `soggetti_ruoli` non ha un suo `attivo`, quindi conta ogni riga) e non si dà un ruolo a un soggetto disattivato (`trg_soggetti_ruoli_a10_soggetti_require_attivo_ins_upd`). R-8 serve ancora? | R-8 | ✅ Tid, 2026-10-10: **no, superato dal modello.** `attivo` non entra nella regola, ed esce anche il filtro `s.attivo = true` della lista, che non poteva scattare. L'invariante la tengono i due trigger; se `soggetti_ruoli` avrà un suo stato, la domanda si riapre lì. Nessun pgTAP: il caso non si costruisce |
| Q-4 | R-9 e la riga a catalogo di R-7 si fanno **dopo** l'apply di `brief-db-esecutivi-ba-coppia` (FK composta `clienti` → billing account, id dei messaggi già a 1235), o in parallelo? | R-7, R-9 | ✅ Tid, 2026-10-09: **tutto dopo** l'apply di ba-coppia, R-5…R-9 in un giro. Quali passi sono indipendenti, se si cambia idea: nota in testa al brief |

### 13.2 Rilievi tecnici (li risolve il team DB, nessuna decisione)

* **R-6, forma del codice.** Il ruolo è un parametro della chiamata: la tabella
  dell'entità si risolve **una volta**, e non serve un `EXPLAIN` per deciderlo
  (regola zero). Con `EXECUTE` la check smette di essere `LANGUAGE sql`
  inlineabile e girerebbe per riga nella lista; scrivere l'`EXISTS` dentro la
  lista rifarebbe due copie. ⇒ BB che, dato il ruolo, rende il **predicato**, e
  lista e dettaglio lo compongono nel proprio SQL dinamico.
* **R-6, seconda copia nel dettaglio.** I rami `CASE 'CL'`/`'FO'` di
  `fn_get_search_detail` leggono `clienti` e `fornitori` diretti; la verifica
  d'esistenza leggerebbe `vw_clienti_codice_ba`. Oggi coincidono per testo, non
  per costruzione: si allineano nello stesso giro.
* **R-6, presidio** (forma decisa con Q-1). La colonna nuova accetta solo
  tabelle, con `soggetto_ruolo_id`: guard sul modello di
  `trgfn_tipi_ruoli_guard_entita_ref`. Nessuna vista, quindi nessun rischio di
  una vista senza `security_invoker` che spegne il perimetro.
* **R-6, RLS delle entità.** `fornitori`, `vettori`, `bank_branches` non hanno
  RLS (la `scope_policy` `FORNITORE_OWNERSHIP` non è armata su una tabella): per
  loro «visibile a chi guarda» vuol dire «esiste».
* **R-5, censimento completo** oltre al §10: `GRANT EXECUTE` sulle firme nuove
  (o verifica del loop di `ci_apply`); pagine `manual/` —
  `fn_get_emittenti_scope_sr_effettivo.md` da cancellare, link in
  `fn_check_ba_visible_for_emittenti.md` e `fn_search_soggetti_universale.md`;
  commenti nel corpo di `fn_search_soggetti_universale` che la nominano; pgTAP
  che citano le firme vecchie (`has_function`, privilegi) cercati per firma; il
  fail-closed di `fn_get_emittenti_scope_sr_ids` deve restare provato altrove
  quando cadono i test 10-11 di `test-scope-emittenti-fail-closed-v1`.
* **R-9, copie pgTAP.** La copia a mano della riga `clienti` in
  `test-search-scope-interno-v1` la ritira il team DB nello stesso giro del
  builder (regola del 2); il §12.4 nomina solo le copie Python.
* ⚠️ **Agganci con ba-coppia, giro 2 (team DB, 2026-10-10).** Dopo l'apply del giro 1,
  [brief-db-esecutivi-ba-coppia](brief-db-esecutivi-ba-coppia.md) ha un secondo giro (§10.4
  di quel brief), deciso da Tid il 2026-10-10:
  * **R-9 va dopo il giro 2**, non solo dopo il giro 1: il giro 2 riscrive
    `anagrafiche.trgfn_clienti_sync_utility_from_ba` sul BB nuovo
    `script.fn_cliente_dal_billing_account` (ruolo e utility del cliente, se mancano, li
    mette il BA; se dissentono, `E_DOC_CLIENTE_DIVERSO_DA_BA`). Il builder potra' passare
    solo il BA;
  * **R-7: gli id 1237 e 1238 di `messaggi_errore.csv` li prende il giro 2**
    (`E_DOC_CLIENTE_DIVERSO_DA_BA`, `E_DOC_SORGENTE_NON_TROVATA`): R-7 parte da 1239, da
    ricontare sul file al momento di scrivere;
  * R-5, R-6 e R-8 restano indipendenti.

## 14. Consegne del giro R-5…R-9

*(team DB, 2026-10-10)* — scritto e provato pre-apply; **applicato da Tid il 2026-10-10,
pgTAP verdi** (Tid: «migrazione applicata e test verdi»).

### 14.1 Cosa c'è

| Richiesta | Dove | Note |
| --- | --- | --- |
| R-6 (Q-1) | `00_schema/config/20261010-08-alter-tipi-ruoli-add-entita-esistenza` | colonna `entita_esistenza text`, CHECK di forma `schema.tabella`; `COMMENT` nuovo anche su `entita_tabella` («solo ricerca del codice») |
| R-6 (Q-1) | `20_code/config/20261010-09-update-trgfn-tipi-ruoli-guard-entita-esistenza` | il guard valida la colonna nuova: tabella esistente (relkind `r`/`p`, **mai una vista**) con `soggetto_ruolo_id`; il trigger scatta anche su `UPDATE OF entita_esistenza` |
| R-6 (Q-1) | `80_data/sql/config/tipi_ruoli.csv` + mirror `20250812-02` | CL → `anagrafiche.clienti`, FO → `fornitori`, VT → `vettori`, BANK_B → `bank_branches`, EF → `emittenti_fiscali`; gli altri `NULL` |
| R-6, Q-2, Q-3, Q-5 (BB) | `20_code/script/20261010-10-create-fn-predicato-soggetto-ruolo-visibile` | la regola unica: valida il tipo ruolo e rende il predicato su `soggetti_ruoli` |
| R-5, R-6, Q-2 | `20_code/script/20261010-11-update-fn-get-search-detail-regola-unica` | firma senza `p_emittente_ids` (DROP + CREATE); verifica d'esistenza col predicato |
| R-5, R-6, Q-2, Q-5 | `20_code/script/20261010-12-update-fn-search-soggetti-universale-regola-unica` | firma senza `p_emittente_ids` (era il **terzo** parametro); filtro di riga col predicato; via `s.attivo = true` |
| R-6 (regola del 2) | `20_code/script/20261010-13-drop-fn-check-soggetto-ruolo-visibile` | ritirata la check col letterale `'CL'` |
| R-5 | `20_code/script/20261010-14-drop-fn-get-emittenti-scope-sr-effettivo` | ritirata |
| R-9 | `20_code/dbops/20261010-15-create-fn-pgtap-crea-cliente` | builder fino alla riga di `clienti`, con lo stato (default AT) e le date che lo stato pretende |
| Q-2, R-7 | `codici_errore.csv` + `messaggi_errore.csv` (id 1239-1242) | `E_TIPO_RUOLO_NON_RICERCABILE`, `E_EMAIL_TEMPLATE_NON_CONFIGURATO`, `E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO`, `E_EMAIL_ALLEGATI_LIMITE`; causa e soluzione scritte; nessun changeSet nuovo, li rilegge il mirror |
| pgTAP | `script/test-search-regola-unica-visibile-v1` (**nuovo**, 17 test) | catalogo, regola su FO/VT/RE con soggetti costruiti, stato dell'entità, ruolo non ricercabile |
| pgTAP | `script/test-search-scope-interno-v1` (21 → 10), `script/test-scope-emittenti-fail-closed-v1` (12 → 11), `script/test-search-soggetti-universale` (26 → 22), `anagrafiche/test-fn-get-evento-stato-corrente-cliente-v1` (fixture) | riallineati: §14.2 |
| Doc `manual/` | `script/fn_predicato_soggetto_ruolo_visibile.md` (nuova), `fn_get_search_detail.md`, `fn_search_soggetti_universale.md`, `fn_check_ba_visible_for_emittenti.md`, `config/tipi_ruoli.md`, `config/trgfn_tipi_ruoli_guard_entita_ref.md` | cancellata `script/fn_get_emittenti_scope_sr_effettivo.md` (oggetto ritirato); `fn_check_soggetto_ruolo_visibile` non aveva una pagina |

### 14.2 Le scelte del team DB

* **Il BB rende un predicato, non risponde sì/no** (rilievo del §13.2). Il ruolo è
  uno per chiamata: la regola si risolve una volta ed entra nell'SQL dinamico di lista
  e dettaglio. Una check per riga farebbe un `EXECUTE` per ogni riga della lista;
  l'`EXISTS` scritto nelle due funzioni sarebbe stato due copie. Il predicato nomina
  l'alias di `soggetti_ruoli` del chiamante (validato come identificatore, quotato con
  `%I`) e la tabella dal catalogo quotata `%I.%I`, senza passare da `regclass::text`.
* **Il BB valida anche il tipo ruolo.** NULL o `<= 0`, inesistente, non ricercabile
  sono la stessa domanda, e la facevano lista e dettaglio con due guardie diverse
  (la lista non verificava nemmeno l'esistenza: un ruolo inesistente dava zero righe).
  Ora la fa il BB, una volta. Effetto: la lista su un ruolo inesistente solleva
  `E_TIPO_RUOLO_NON_TROVATO`.
* **`E_TIPO_RUOLO_NON_RICERCABILE` è `NON_TROVATO` (404)**, come il fratello
  `E_TIPO_RUOLO_NON_TROVATO`: l'id arriva dall'URL, e per la ricerca universale quel
  ruolo «non c'è». Al Q-2 avevo detto «chiamante sbagliato», che faceva pensare a
  `TECNICO`; ma chi manda la richiesta può rimediare cambiandola (api.md, «chi può
  rimediare»), e i due fratelli devono rispondere uguale.
* **`entita_esistenza` è `text` + CHECK di forma, non `regclass`**: un OID non segue
  una `DROP` e nel seed dipende dalla macchina. ⚠️ Il guard è BEFORE ROW e parla
  **prima** del CHECK: il CHECK resta la rete per le strade che non passano dai
  trigger (il pgTAP lo prova con `anagrafiche.Clienti`, che il guard risolve e la
  forma rifiuta).
* **Il trigger del guard andava allargato**: scattava su `UPDATE OF entita_tabella,
  entita_colonna_codice`, quindi l'UPDATE della sola colonna nuova lo saltava.
  Trovato dal pgTAP nuovo (test 3-4) nella prova; ridefinito in `-09` (trigger
  scritto a mano in `20260311-08`, non generato da `ci_apply`).
* **I rami `CL` e `FO` del dettaglio restano**: danno la forma delle righe di ciascun
  ruolo, non decidono chi si vede. Leggono `clienti` e `fornitori`, le tabelle che il
  catalogo dà a quei ruoli: la coincidenza la pinna il test 2 del pgTAP nuovo
  (rilievo «seconda copia nel dettaglio» del §13.2).
* **R-5: `p_emittente_ids` esce dalla firma.** Nel dettaglio era l'ultimo; nella lista
  era il **terzo**, e una chiamata per posizione con un `NULL` in terza posizione
  oggi passerebbe `p_limit`. Il backend chiama per nome; i pgTAP che chiamavano per
  posizione sono riallineati.
* **R-5: la proprietà dei test ritirati non si perde.** I test 10-11 di
  `test-scope-emittenti-fail-closed-v1` provavano «utente NULL = nessun accesso» sulla
  funzione ritirata, che era un involucro della canonica: ora il test 10 lo prova su
  `fn_get_emittenti_scope_sr_ids(NULL)`, che nessun test asseriva direttamente.
* **R-9: il builder** (`dbops.fn_pgtap_crea_cliente`, stessi tre parametri di
  `fn_pgtap_crea_cliente_ba` più lo stato) scrive la riga di `clienti` con ruolo e
  istanza del BA (la utility la copia il trigger del giro 2 di ba-coppia), attivazione
  oggi salvo pre-contratto e annullato, chiusura oggi per gli stati di macro `CH`.
  Utility di default: la prima che non richiede il PDP. Senza `RETURNING`, come il suo
  fratello. **Copie pgTAP ritirate**: `test-search-scope-interno-v1` e
  `test-fn-get-evento-stato-corrente-cliente-v1` (erano esattamente «builder del BA +
  INSERT a mano»). **Restano**, censite: le INSERT di `test-un-ba-un-cliente-v1`,
  `test-clienti-sync-utility-pdp-policy`, `test-esecutivi-ba-coppia-v1` e
  `rls/test-rls-clienti` (la riga di `clienti` è il **soggetto** del test: vincoli,
  guard, RLS in scrittura); `create-cliente`, `test-fn-update-cliente-v1`,
  `test-istanza-cliente-chain`, `test-simula-subentro`, `test-fn-disdetta-cliente`
  (costruiscono una catena loro, con PDP o con colonne che il builder non scrive).
* **R-7**: nella causa di `E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO` è scritto che è anche
  un caso da guardare per la sicurezza (un percorso che esce dall'archivio non nasce
  usando l'applicazione).

### 14.3 Effetti voluti, dichiarati

* **Un fornitore senza la sua riga in `fornitori`** (e un vettore senza `vettori`, una
  banca senza `bank_branches`) **non compare più** nella lista e il suo dettaglio è
  `NULL` (404). È la regola di R-6: prima compariva con `righe: []`.
* **Un ruolo non ricercabile** (emittente fiscale, gestore, risorsa umana, PSP,
  processo automatico) lo rifiuta il DB. Il backend lo rifiutava già: cambia il codice
  (da `E_SEARCH_VALIDATION` 400 a `E_TIPO_RUOLO_NON_RICERCABILE` 404), quando il BE
  ritira il suo controllo (§14.6).
* **La lista su un tipo ruolo inesistente** solleva `E_TIPO_RUOLO_NON_TROVATO` invece
  di rispondere zero righe.
* Cliente chiuso e fornitore disattivato **si ritrovano**, col loro stato (Q-3): era già
  così, ora è scritto e provato.

### 14.4 Prove fatte (pre-apply, scratch `zeroerp_ci` allineato a `20261010-07`, SQL estratto dagli YAML in transazione annullata)

| Prova | Esito |
| --- | --- |
| SQL estratto degli otto changeSet + `sqlCheck` delle preCondition | ✅ passa; preCondition come attese (1, 1, 0, 0, 1) |
| Firme dopo il giro | ✅ una funzione per nome; `fn_get_search_detail(uuid,integer,integer)`, `fn_search_soggetti_universale(text,integer,integer,integer,text,text)`, `RETURNS TABLE` invariato; `zeroerp_app` ha `EXECUTE` su BB e builder |
| `plpgsql_check` su BB, dettaglio, lista, builder, guard | ✅ zero `error` |
| Upsert **completo** dei CSV `tipi_ruoli`, `codici_errore`, `messaggi_errore` | ✅ tutte le righe scrivibili (12, 1023, 1019) |
| Predicato per ogni ruolo ricercabile | ✅ CL/FO/VT/BANK_B → `EXISTS` sulla loro tabella; VE/DI/RE → `true` |
| `script/test-search-regola-unica-visibile-v1` | ✅ 17/17. **Mutazione** (predicato sempre `true`): rossi 6, 7, 10, 16, 17, cioè esattamente i test che distinguono la regola nuova |
| `script/test-search-scope-interno-v1` | ✅ 10/10 |
| `script/test-scope-emittenti-fail-closed-v1`, `script/test-ba-emittente-risoluzione-v1`, `anagrafiche/test-fn-get-evento-stato-corrente-cliente-v1` | ✅ 11/11, 14/14, 8/8 |
| Presidi trasversali, prima e dopo: `dbops/test-riferimenti-morti-v1`, `config/test-codici-errore-identita`, `config/test-codici-errore-obsoleto-dal`, `dbops/test-vw-codici-errore-motivo-nominato`, `script/test-catalogo-messaggi-errore-completo`, `config/test-costanti-catalogo-citate-dal-codice-v1`, `script/test-fn-get-messaggio-fallback-lingua`, `dbops/test-postura-proprietario-rls-v1`, `script/test-rubinetto-primo-motivo-v1` | ✅ tutti verdi, prima e dopo |
| Guardrail statici (letterali, `runOnChange`, preCondition/seed, trigger d'automazione, grant batch, preambolo pgTAP, timestamp, v1 congelato) | ✅ |

⚠️ **`script/test-search-soggetti-universale` sullo scratch muore al test 7**, prima e
dopo (dopo l'apply, su dbdev, verde nella corsa di Tid): pesca i soggetti dai dati, e lo scratch non ha clienti (`ERRORE_FIXTURE` già in
`baseline-rossi-scratch.tsv` e `baseline-rossi-ci.tsv`). Va lanciato **su dbdev dopo
l'apply**: le modifiche sono le chiamate per posizione senza il `NULL` in terza
posizione, la fixture su CL per nome, e via i test 23-26.

⚠️ Le prove non coprono la corsa come `zeroerp_app` e l'apply vero: sono di Tid.

### 14.5 Residui dichiarati

* Le nove INSERT a mano su `clienti` che restano nei pgTAP (§14.2): non sono copie
  della fixture, e restano dove sono.
* Fuori perimetro: nella lista il tetto di 10.000 righe è un `LIMIT` nella prima CTE
  **senza `ORDER BY`**. Oltre 10.000 corrispondenze, `total_count` e le pagine vengono
  da un sottoinsieme qualunque. Non è nato in questo giro: ha un brief suo, aperto il
  2026-10-10 su richiesta di Tid,
  [brief-db-ricerca-universale-tetto-10000](brief-db-ricerca-universale-tetto-10000.md)
  (voce D23 del registro).

### 14.6 Per il backend, dopo l'apply

1. **Q-2**: ritirare il controllo `is_tipo_ruolo_visibile` di `_require_tipo_ruolo_id`
   (`core/api/search_view.py`, `core/db/search_repository.py`): sarebbe una seconda
   copia della regola del DB. Il menu a tendina (`LookupTipiRuoliView`,
   `list_tipi_ruoli_visibili`) continua a leggere la colonna. I test che si aspettano
   `E_SEARCH_VALIDATION` per un ruolo non ricercabile passano a
   `E_TIPO_RUOLO_NON_RICERCABILE` (404).
2. **Catalogo**: `genera_error_policies` e i messaggi di ripiego per i quattro codici
   nuovi (`E_TIPO_RUOLO_NON_RICERCABILE`, `E_EMAIL_TEMPLATE_NON_CONFIGURATO`,
   `E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO`, `E_EMAIL_ALLEGATI_LIMITE`).
3. **R-7**: i tre punti del §12.2 passano ai codici nuovi; il parametro `error_code` di
   `resolve_and_render` si toglie. Un test per codice.
4. **R-9**: le copie della riga di `clienti` in `test_ricerca_liste_db` e
   `test_search_detail_non_trovato_db` passano a `dbops.fn_pgtap_crea_cliente(...)`
   (rende anche `cliente_id`).
5. **R-6**: in `test_search_detail_non_trovato_db` il caso «fornitore senza la riga in
   `fornitori`» → `None`; rilanciare il file sul DB vero anche per provare il binding
   delle firme senza `p_emittente_ids`.
6. **Doc**: `api_search_universale.md` — la regola su `entita_esistenza`, i codici
   `E_TIPO_RUOLO_NON_RICERCABILE` ed `E_TIPO_RUOLO_NON_TROVATO` (anche dalla lista), le
   firme senza `p_emittente_ids`.

## 15. Giro BE del §14.6 (sessione backend, 2026-10-10)

> ✅ **Fatti tutti e sei i punti del §14.6.** Nessuna richiesta nuova al team DB.

| Punto §14.6 | Esito |
| --- | --- |
| 1. Q-2 | ritirato `SearchRepository.is_tipo_ruolo_visibile` e il controllo in `_require_tipo_ruolo_id`: esistenza e `ricerca_visibile` li dice il DB (404 `E_TIPO_RUOLO_NON_RICERCABILE` / `E_TIPO_RUOLO_NON_TROVATO`). Il parametro resta obbligatorio e ora e' limitato a `integer` (`qp_int_optional`): andava a `p_tipo_ruolo_id integer`, e un bigint sarebbe stato un 500. `test_search_view` 6 e 17 riscritti (la view passa il ruolo, il tetto resta un 400) |
| 2. Catalogo | policy rigenerate; ripieghi per i quattro codici |
| 3. R-7 | `E_EMAIL_TEMPLATE_NON_CONFIGURATO` (`resolve_and_render`; il parametro `error_code` e' uscito, e con lui l'ultimo punto di `E_EMAIL` in `email_service`), `E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO` (`percorso_allegato`), `E_EMAIL_ALLEGATI_LIMITE` (`add_attachment`). Un test per codice: `test_email_outbox_service` 21-23, piu' il 5 di `test_email_service` che ora asserisce il codice |
| 4. R-9 | `test_ricerca_liste_db` e `test_search_detail_non_trovato_db` passano a `dbops.fn_pgtap_crea_cliente` (stato `PR` nel primo, come la riga che sostituisce). Nessun'altra INSERT a mano su `clienti` nei test Python |
| 5. R-6 | `test_search_detail_non_trovato_db`: fornitore senza la riga in `fornitori` → `None`, con la contro-prova del fornitore che la riga ce l'ha; ruolo non ricercabile rifiutato dal DB su lista e dettaglio; binding delle firme senza `p_emittente_ids` provato sul DB vero (7/7). La sonda del file era `fn_check_soggetto_ruolo_visibile`, ritirata: ora e' il BB nuovo — con la vecchia il file sarebbe stato **saltato in silenzio** |
| 6. Doc | `api_search_universale.md` (regola su `entita_esistenza`, codici, firme), `api_email.md` (i tre codici, catene di ripiego) |
