# Brief DB — Sei codici d'errore da mettere a catalogo e la lista dei parametri di livello puro

> **Chi scrive:** sessione backend (`dev/backend-tid`), 2026-10-07. **A chi:** team
> DB (`dev/db-tid`), tramite Tid.
> **Origine:** §7 di
> [analisi-be-difetti-emersi-verifica-doc-api-core.md](analisi-be-difetti-emersi-verifica-doc-api-core.md)
> (voci E-1, E-2, E-5, F-5). Fino a oggi quelle richieste stavano solo nell'analisi:
> questo brief le porta al team (ok di Tid, 2026-10-07).
> **Stato:** ⏳ da fare. Nessun lavoro BE in attesa **dentro** il giro DB: il BE
> agisce dopo l'apply (§5).

## 1. Cosa si chiede

| # | Cosa | Tipo | Bloccante per il BE |
| --- | --- | --- | --- |
| R-1 | Sei codici nel catalogo (`codici_errore.csv` + `messaggi_errore.csv`) | seed `80_data` | sì: rigenerazione delle policy e ripieghi |
| R-2 | `script.fn_list_parameters_for_user` mostra solo override **di livello puro** | `20_code` | no |
| D-1 | `E_USER_DISABILITATO`: ritirarlo, o dargli un significato nuovo | **domanda a Tid**, poi seed | no |

## 2. R-1 — Sei codici usati dal backend e assenti dal catalogo

Il backend li solleva, ma non sono nel catalogo. Effetto, oggi:

* i due `*_NOT_FOUND` non hanno classe: il traduttore li tratta come «codice
  `E_*` sconosciuto» e risponde **400** «Errore di validazione.» invece di 404;
* gli altri quattro non hanno una riga a catalogo: chi legge `dbops.error_log` o la
  colonna `ultimo_errore` di una coda trova un codice che il catalogo non conosce
  (né frase, né causa, né soluzione).

Li ha trovati il guardrail `test_error_codes_declared_guardrail`, esteso il
2026-10-07 a ogni literal `E_*` del backend (E-2). Oggi stanno nel suo registro del
debito `_DEBITO`, che deve calare.

| Codice | Classe proposta | Frase (quella che il BE scrive già) | Chi lo solleva |
| --- | --- | --- | --- |
| `E_ANAG_CONTO_NOT_FOUND` | `NON_TROVATO` | Conto bancario non trovato nel registro. | `anagrafiche/services/conti_bancari_service.py` (`conto_bancario_id` inesistente) |
| `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` | `NON_TROVATO` | Associazione conto bancario non trovata. | idem (DELETE di un legame inesistente o di un altro proprietario) |
| `E_GUC_RESET_FAILED` | `TECNICO` | Errore interno di sicurezza sessione. | `core/middleware/jwt_audit_middleware.py` (reset delle GUC a inizio richiesta fallito: fail-closed) |
| `E_DB_ROLE_UNSAFE` | `TECNICO` | Errore interno di sicurezza sessione. | idem (la connessione web gira su un ruolo `BYPASSRLS`: richiesta rifiutata) |
| `E_CODA_JOB_STANTIO` | `TECNICO` | Esecuzione interrotta (worker morto o kill): recuperata dal reaper. | `core/services/coda_lavori/repository.py` (`reap_stale`, in `ultimo_errore`) |
| `E_STAMPA_JOB_STANTIO` | `TECNICO` | Render interrotto (worker morto o kill): recuperato dal reaper. | `vendite/db/pipeline_repository.py` (`reset_stale_stampe_in_corso`, in `ultimo_errore`) |

Motivo delle classi, sul modello:

* `NON_TROVATO` — la cosa indicata non esiste: è la definizione della classe (api.md
  §Tassonomia), ed è la classe di `E_ANAG_NOT_FOUND`, il gemello che lo stesso
  service usa per il soggetto;
* `TECNICO` — guasto o pezzo configurato male: l'operatore non può rimediare. I due
  del middleware sono configurazione della macchina; i due dei reaper sono un worker
  morto, e il lavoro è già stato rimesso in coda o chiuso dal reaper stesso.

⚠️ Causa e soluzione le scrive il team DB, come per ogni codice. Due suggerimenti
dal lato BE, per i due del middleware: la soluzione è per chi gestisce la macchina
(GUC: verificare la connessione e il log `jwt_audit_middleware.guc_reset_at_start_failed`;
ruolo: `DB_USER` del web non deve essere il ruolo batch), non per l'operatore.

**Test DB:** quelli che il catalogo ha già (ogni codice ha classe e messaggio,
convenzione `E_`). Nessun pgTAP nuovo: nessuna funzione DB solleva questi codici.

## 3. R-2 — La lista dei parametri mostra solo override di livello puro

`config.parameter_overrides` ha sei dimensioni (`django_user_id`, `django_group_id`,
`emittente_fiscale_id`, `categoria_cliente_id`, `session_key`, `function_name`).
L'unicità è sull'insieme e nessun `CHECK` vieta una riga che ne valorizza più d'una:
**il modello ammette le righe miste**.

Dal 2026-09-28 (F-5) il backend **scrive e cancella** solo override di livello puro
(tutte le altre dimensioni `NULL`, `parameter_repository._altre_dimensioni_nulle`).
`script.fn_list_parameters_for_user` invece li **legge** così (doc auto-gen, oggi):

| Join | Filtra | Manca |
| --- | --- | --- |
| `po_us` (utente) | solo `django_user_id` | gruppo, emittente, categoria, sessione, funzione |
| `po_em` (emittente) | utente e gruppo `NULL` | categoria, sessione, funzione |
| `po_cat` (categoria) | tutte le altre `NULL` | — (è il modello da seguire) |

Effetti: una riga mista compare in lista come «override personale» (o d'emittente)
con un `id` che la DELETE del backend (pura) rifiuta con 404; con più righe miste
dello stesso utente il `LEFT JOIN po_us` può **duplicare** la riga del parametro.

**Si chiede:** `po_us` e `po_em` escludono tutte le altre dimensioni, come `po_cat`.
Lo stesso vale per la `COALESCE` di `resolved_value` che riusa `po_us`.

⚠️ **Fuori da questa richiesta**, e da decidere con Tid prima: la cascata di
risoluzione (`fn_get_parameter_full`) — se le righe miste debbano esistere e come
pesino. Qui si allinea solo la **lista** a ciò che il backend scrive.

**Test DB:** un pgTAP che **costruisce** una riga mista (utente + categoria) e una
pura per lo stesso parametro e utente, e prova che la lista mostra la pura, una riga
sola per parametro, con l'`id` della pura. Il caso si costruisce: sul DB di oggi
potrebbe non esserci nessuna riga mista, e il test non deve dipenderne.

## 4. D-1 — `E_USER_DISABILITATO` (domanda a Tid)

Il codice è a catalogo (`NON_PERMESSO`), ma dal 2026-10-02 nessuno lo solleva: col
ritiro di `DISABILITATO` (R-DB-1 del brief area Accessi) una veste spenta è
`attivo = false` col suo tipo, e chi ha solo vesti spente lo nega il livello d'area.
Due strade:

* **ritirarlo** (`obsoleto_dal`), come ogni codice che nessuno nomina più;
* **riusarlo** come codice di «nessuna veste accesa», se si vuole che quel diniego
  abbia una frase sua invece del 403 generico. ⚠️ Sarebbe un riuso per una
  condizione nuova: api.md §«Il rubinetto degli accumulatori» chiede un codice
  nuovo, non uno vecchio con un significato diverso.

Raccomandazione del BE: **ritirarlo**. Se serve un messaggio per «nessuna veste
accesa», nasce un codice suo.

## 5. Cosa fa il backend dopo l'apply

* R-1: `./manage-env.sh genera_error_policies`; frasi di ripiego in
  `error_messages_fallback.py` per i sei; via le sei voci da `_DEBITO` del guardrail
  (fallisce finché restano); per i due `*_NOT_FOUND` i test di
  `test_conti_bancari_service` controllano anche lo status 404; doc
  `api_conti_bancari_ruolo.md`, `api_conti_bancari_soggetto.md`,
  `jwt_audit_middleware.md`, api.md §codici middleware-level. Chiude **E-1**.
* R-2: nessuna modifica BE; si toglie la riga «lato DB» di F-5 dall'analisi.
* D-1: se ritirato, nessuna modifica BE (nessun punto di chiamata lo nomina).

## 6. Nota per il team DB

Il 2026-10-07 il cancello `test_error_codes_db_policy_guardrail` (DB vero) è rosso
su `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`, nominato da
`script.fn_check_listino_congelabile` sul DB di sviluppo e **assente dal repo**
(né CSV né changeSet). Sembra un giro DB applicato e non ancora mergiato: non è di
questo brief, ma il BE non può rigenerare le policy (R-1) finché il DB è avanti
rispetto a git sul catalogo.

## 7. Consegne

*(da compilare dal team DB)*
