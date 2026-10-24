# Piano — type checker del backend (D2-b)

> Nato il **2026-10-08** dalla decisione di Tid su **D2-b** di
> [migliorie-generali-BE-FE-da-test-valutazione.md](migliorie-generali-BE-FE-da-test-valutazione.md):
> il progetto **vuole** un type checker, acceso **a cricchetto**.
> Stato: ✅ **Piano chiuso il 2026-10-09.** L0-L3 chiusi e committati (`0ffe7b7c3` L0-L2,
> `ebc54fc56` L3). S2 e le tre dipendenze approvate il 2026-10-08. ✅ Il caso NaN è chiuso:
> registro a **0** il 2026-10-09. ✅ Gli stub `types-bleach`/`types-openpyxl` installati lo
> stesso giorno (ok di Tid, §5.1). ✅ La divergenza di `catalogo_service` era già chiusa
> (§5.2).
> ✅ **L0 chiuso il 2026-10-08** (§4.5). ✅ **L1 chiuso il 2026-10-09** (§5.1):
> mypy acceso in CI, registro alla nascita **620** rilievi. ✅ **L2 chiuso il
> 2026-10-09** (§5.2): registro a **558**. ✅ **L3 chiuso il 2026-10-09**
> (§5.3): registro a **2**, entrambi il caso NaN di `_number_formatting`: deciso
> da Tid il 2026-10-09 (opzione C, la generazione si ferma). ✅ **Chiuso lo stesso
> giorno**, DB e BE: registro a **0** —
> [brief-db-valore-numerico-non-finito-nei-documenti.md](../work-done/brief-db-valore-numerico-non-finito-nei-documenti.md) §7.

## 1. Perché

La suite backend è quasi tutta **mockata**: un `MagicMock` accetta qualunque
attributo e qualunque firma, quindi un service che chiama un metodo rinominato,
o che passa `None` dove la funzione accanto vuole un `int`, resta **verde**.
Sono i difetti di **giuntura** fra due pezzi, quelli che D9 dice che la suite
non può vedere. Un type checker li vede **senza eseguire il codice**, su tutto
il codice e non sui soli rami che un test percorre.

È anche ciò che dà senso a una regola che oggi c'è già e non serve a niente:
`PROJECT_CONTEXT.md` §«Error handling» prescrive
`assert value is not None  # sempre dopo require, per il type checker`, e il
type checker non esiste.

## 2. Le scelte

Le scelte segnate ⭐ sono quelle che propongo; quelle segnate **(Tid)**
aspettano un sì esplicito prima di partire.

### S1 — Lo strumento: `mypy` col plugin Django ⭐

`mypy` + `django-stubs` + `djangorestframework-stubs`. Il plugin legge le
settings e i modelli, quindi conosce l'ORM (`objects`, i campi, i manager) e la
`Request` di DRF. Pyright (Pylance) non ha un plugin Django: sull'ORM vede solo
`Any`, cioè non vede proprio la parte che ci interessa.

⚠️ Gli stub seguono la versione di Django e DRF (`django-stubs` 6.1.x per
Django 6.1): si aggiornano **insieme** a loro, ed è un vincolo da scrivere nel
file dei requisiti, accanto al pin.

### S2 — Dove stanno le dipendenze ✅ approvata da Tid il 2026-10-08

Il plugin **importa** le settings e il codice del progetto, quindi `mypy` deve
girare nella **venv del backend**, non in quella degli strumenti
(`requirements.txt` in radice, che è un'altra venv). Ma in
`backend/requirements.in` finirebbe nell'immagine Docker di produzione, dove non
serve.

⭐ Proposta: un file nuovo **`backend/requirements-dev.in`**, compilato in
`backend/requirements-dev.txt` con `-c requirements.txt` (vincolato al lock del
backend, così le versioni comuni non divergono). Si installa nella venv del
backend e nel job CI; il `Dockerfile` non lo vede. Va registrato nella tabella
«Fonte unica» di `.codex/AGENTS.md` e nei `paths:` di `ci-validate.yaml`.

Dipendenze nuove: `mypy`, `django-stubs` (porta con sé `django-stubs-ext`),
`djangorestframework-stubs`. ✅ Ok di Tid il 2026-10-08 (la regola di casa lo chiede per ogni dipendenza nuova).

### S3 — Il perimetro: tutto il codice applicativo, dal primo giorno ⭐

`apps/**` e `zeroerp_backend/**`, esclusi `tests/` e `migrations/`.

La D2-b originale diceva «i soli `apps/*/services/`», ma il motivo per
restringere non regge sul modello: le giunture stanno **fra** gli strati
(view → service → repository), e un cancello sui soli service non vede la view
che gli passa il tipo sbagliato. Con un registro a cricchetto (S4) il perimetro
largo **non costa** al cancello: l'arretrato entra nel registro e il codice
nuovo nasce pulito ovunque.

Esclusi:

- **`tests/`**: controllano i mock, cioè oggetti che per costruzione accettano
  tutto. I rilievi sarebbero rumore.
- **`migrations/`**: codice generato.

### S4 — Il registro a cricchetto ⭐

Lo stesso meccanismo di `check-datatable-baseline.mjs` e di
`test_schema_openapi_registro.py`:

- **`backend/mypy.baseline.json`**: i rilievi accettati, **per nome** e
  **senza numero di riga**. Chiave: `file` + codice di errore (`[arg-type]`) +
  messaggio. Il numero di riga cambia a ogni modifica sopra il punto, e un
  registro che usa le righe diventa rosso per una riga vuota aggiunta. Si
  conta quante volte compare la stessa chiave nello stesso file.
- **`scripts/check_mypy_baseline.py`**: lancia `mypy`, confronta col registro
  ed è **rosso** in tre casi:
  1. un rilievo nuovo (codice nuovo che nasce sporco);
  2. un rilievo nel registro che non c'è più (sanato ma non tolto: il registro
     deve **scendere**, non restare largo);
  3. un'uscita di `mypy` che lo script non sa leggere (il caso «verde perché
     non ha capito niente»).
- Un'opzione `--aggiorna` riscrive il registro **solo togliendo** voci; per
  aggiungerne serve rifarlo da zero, e si vede nel diff.

⚠️ Il limite, dichiarato come per il registro OpenAPI: una voce nel registro
copre **tutte** le occorrenze uguali nello stesso file. Il conteggio per chiave
lo riduce, non lo annulla.

### S5 — La severità ⭐

La configurazione di base di `mypy`, più **`check_untyped_defs = True`**. Senza,
`mypy` **salta il corpo** delle funzioni senza annotazioni: proprio dove una
giuntura è meno dichiarata. Niente `--strict`: chiederebbe di annotare tutto
subito, ed è un altro lavoro.

`ignore_missing_imports` per le sole librerie senza tipi, **elencate per
nome** in `backend/mypy.ini`. Non globale, altrimenti un import sbagliato del
progetto diventa `Any` senza nessun avviso.

### S6 — Dove gira ⭐

- **CI**: passo in `ci-validate.yaml`, nel job che ha già la venv del backend e
  l'ambiente Django (accanto a «Django check»). Gira sempre su **tutto** il
  perimetro: il registro è globale, e un controllo sui soli file cambiati non
  vedrebbe un file non toccato rotto dalla firma cambiata in un altro.
- **A mano**: `python scripts/check_mypy_baseline.py`, dalla venv del backend.
- **Non** in pre-commit, per ora: l'hook gira sui soli file in stage (vedi la
  memoria sull'hook) e il plugin Django vuole l'ambiente completo. Si
  riconsidera quando il registro è piccolo.
- **VS Code**: `python.analysis.typeCheckingMode` resta spento. Pylance è un
  secondo checker con regole diverse, e due checker che dicono cose diverse
  sullo stesso codice sono peggio di uno.

## 3. Fatti datati — 2026-10-08

> ⚠️ Sono **fatti**, non motivi: nessuna scelta di §2 dipende da questi numeri.
> Misurati in una venv temporanea (fuori dal repo) con `mypy` 2.4.0,
> `django-stubs` 6.1.2, `djangorestframework-stubs` 3.18.1, plugin attivo,
> l'ambiente del job CI, sul commit `ad97625ff` più le modifiche di D1-f/D3-b.

| Perimetro | File | Rilievi | File con rilievi |
| --- | --- | --- | --- |
| `apps/*/services/` | 197 | 189 | 58 |
| tutto S3, severità base | 606 | 612 | 142 |
| tutto S3, con `check_untyped_defs` (S5) | 606 | **622** | 144 |

Il grosso è `[arg-type]` (384 su 612), e nelle view la forma più comune è
`int | None` passato dove si aspetta `int` (48). Sono **misti**: in parte
difetti veri, in parte annotazioni sbagliate (la firma dice `int` e il chiamante
ha ragione a passare `None`). Si giudicano uno per uno nei lotti, non per
categoria.

## 4. Un difetto vero, trovato misurando 🔴

`apps/vendite/services/commesse_service.py`, in **`fn_riallinea_prezzo`**
(riga 1257) e **`fn_sblocca_prezzo`** (riga 1405), chiama
`ListiniRepository().test_resolver(...)`. Il metodo **non esiste**: è stato
tolto da `apps/vendite/db/listini_repository.py` il **2026-04-15** (commit
`58bfd7871`). Le due funzioni sono servite da due endpoint vivi
(`vendite/api/views.py:3040` e `:3087`, riallinea e sblocca il prezzo di
un'attività di commessa), quindi la chiamata finisce in `AttributeError`, cioè
un **500**, da sei mesi.

Il test `test_commesse_service.py` è **verde per costruzione**: patcha
`ListiniRepository` con un mock e dichiara
`mock_list_repo.return_value.test_resolver.return_value = {…}`, cioè fabbrica
il metodo che manca. È esattamente il difetto che §1 descrive.

### 4.1 Letto il codice intorno: il metodo mancante è il primo di cinque difetti

Ricostruito il 2026-10-08 sul codice e sulla doc auto-generata
(`fn_resolve_prezzo_listino_v2`, `commesse_attivita`). Gli endpoint sono vivi
anche a video: `CommessaGestioneDrawer.vue` (righe 696 e 742).

| # | Difetto | Conseguenza |
| --- | --- | --- |
| **P1** | `test_resolver` non esiste più | 500 su riallinea e sblocca |
| **P2** | Anche con il metodo giusto il codice legge `resolver_result["prezzo"]`, ma il resolver restituisce **`prezzo_finale`** | sostituire il solo metodo darebbe un `KeyError`: un altro 500 |
| **P3** | Riallinea e sblocca scrivono il **solo prezzo**: lo snapshot di provenienza (`listino_versione_id`, `listino_riga_id`, `prezzo_base_snapshot`, `origine_prezzo`, variazione, promo, contratto, categoria, classe utenza) resta quello **vecchio** | la riga dice un prezzo nuovo con la provenienza del prezzo vecchio. E, poiché `listino_versione_id` non si aggiorna, la domanda «la versione è cambiata, confermi?» si ripresenterebbe **a ogni** riallineamento |
| **P4** | Il push sorgente → commessa **non scrive** `listino_versione_id` (né `listino_riga_id`): `CommessaAttivitaInput` ha il campo, `_build_attivita_input` non lo passa, anche se il resolver lo restituisce | sulle righe nate da un push la versione originale è `NULL`, quindi il guard «versione cambiata» di riallinea è **morto**: non scatta mai |
| **P5** | Riallinea e sblocca chiamano il resolver **senza** `articolo_padre_contesto`; il push lo passa (dal `meta` della riga, `componente_di`). E la data: il push usa `data_attivita` **o** `competenza_mese`, riallinea solo `data_attivita` | il componente di un kit verrebbe riprezzato come articolo **sciolto**, cioè col prezzo sbagliato; una riga senza `data_attivita` non si riallineerebbe |

⭐ Il motivo comune di P3, P4 e P5 è uno: **due percorsi che fanno la stessa
cosa** (dare un prezzo a una riga di commessa dal resolver), scritti due volte
e divergenti. È la regola del 2.

### 4.2 La proposta (L0)

**A — Un building block, due consumatori (regola del 2, approvata da Tid il 2026-10-08).**
In `apps/vendite/services/` una funzione sola che, data una riga di commessa,
**costruisce gli argomenti** del resolver (articolo, uom, data con il fallback
`data_attivita` → `competenza_mese`, BA, utility, emittente, contesto kit dal
`meta`) e **traduce il risultato** nei campi snapshot della riga (prezzo più i
nove campi di provenienza). La usano il push (`_resolve_pricing_audit`) e
riallinea/sblocca. Le due letture attuali si ritirano nello stesso giro.

**B — Riallinea e sblocca passano dal `PricingService`.**
`resolve_prezzo` (quello che solleva: un prezzo non risolvibile qui è un errore,
non un'assenza), con gli argomenti costruiti da A. Chiude P1, P2 e P5.

**C — Lo snapshot si riscrive intero.**
`update_attivita_prezzo` accetta i campi di provenienza e li scrive con il
prezzo, sia sulla riga sia, per prezzo e blocco, su `attivita_fatturabili` come
oggi. Chiude P3: dopo un riallineamento la riga dice da dove viene il prezzo
nuovo, e la versione registrata è quella nuova.

**D — Il push scrive la versione listino.**
`_build_attivita_input` passa `listino_versione_id` e `listino_riga_id` dal
risultato del resolver. Chiude P4: il guard «versione cambiata» torna vivo.
⚠️ Sul `listino_riga_id` c'è il trigger che vuole la riga di listino
**attiva**: il resolver restituisce solo righe attive, quindi è coerente, ma va
provato nel test.

**Test, sul DB vero (`richiedi_db_provvisto`).**
- La riga di commessa con un prezzo da listino, il listino che cambia versione,
  il riallineamento: prima chiede conferma, poi scrive il prezzo **e** la
  versione nuova; un secondo riallineamento non chiede più niente.
- Lo sblocco di una riga bloccata: prezzo ricalcolato e snapshot riscritto.
- Il componente di un kit: prezzo del kit, non quello sciolto.
- Il test mockato attuale smette di fabbricare `test_resolver`.

⚠️ I soggetti del test (listino, versioni, commessa, riga) vanno
**fabbricati** dal test, non cercati nei dati esistenti (regola del verde per
sottrazione).

### 4.3 Due domande che la proposta non decide — ✅ decise da Tid il 2026-10-08

✅ **1: sì** — `MANUALE` e provenienza da listino azzerata. ✅ **2: backend** —
la regola resta nel service, con la `UPDATE` del repository.

1. **La variazione eccezionale** (`fn_variazione_prezzo_eccezionale`) blocca un
   prezzo scritto a mano ma lascia lo snapshot di provenienza del listino: la
   riga dice «origine: CATEGORIA» con un prezzo che il listino non ha mai dato.
   Il set di `origine_prezzo` prevede `MANUALE`. Va scritto `MANUALE` (e
   azzerata la provenienza da listino) quando si varia a mano?
2. **Dove sta la regola.** Oggi il prezzo di una riga di commessa si scrive con
   una `UPDATE` diretta dal repository (lo dice anche il commento del trigger
   `trgfn_commesse_attivita_guard_prezzo_rettifica`). La proposta resta così,
   lato backend. Se invece il riallineamento deve diventare una funzione DB
   (`fn_riallinea_prezzo_attivita`, DB-first), è un brief al team DB e il
   lotto L0 lo aspetta.

### 4.4 Un punto aperto, trovato facendo L0 ✅ (Tid)

`commesse_attivita.listino_riga_id` resta **fuori** dalla provenienza, e non per
dimenticanza. Su quella colonna il guard `trgfn_listini_righe_guard_stato`
considera la riga di listino **propagata**, cioè non più modificabile: scriverla
cambia il comportamento dei listini, non solo l'audit della commessa. E la madre
del push, `fn_upsert_commessa_attivita`, non ha un parametro per riceverla:
oggi **nessun** percorso la scrive, quindi per i listini una riga usata da una
commessa non risulta mai «propagata».

Scriverla dal solo riallineamento (che usa una `UPDATE`) sarebbe un'altra
asimmetria. La domanda per Tid: una riga di listino che ha dato il prezzo a una
riga di commessa deve diventare immutabile? Se sì, è un brief al team DB (il
parametro nella madre del push) e poi una riga nel building block.

✅ **Deciso da Tid il 2026-10-08: sì.** Brief al team DB:
[brief-db-riga-listino-propagata-dalla-commessa.md](../work-done/brief-db-riga-listino-propagata-dalla-commessa.md).
Il seguito BE sta in quel brief (§5), non in questo piano. ✅ **Chiuso il
2026-10-09** (DB e BE, §7 del brief): `listino_riga_id` è nella provenienza.

### 4.5 ✅ L0 fatto — 2026-10-08

- **Building block** `apps/vendite/services/prezzo_riga_commessa.py`
  (`argomenti_resolver`, `provenienza_da_resolver`, `provenienza_manuale`,
  `origine_ammessa`), registrato nel catalogo BB backend. Le colonne di
  provenienza hanno sede unica in `CommesseRepository.COLONNE_PROVENIENZA_PREZZO`.
- **Push**: `_resolve_pricing_audit` passa dal BB e scrive anche
  `listino_versione_id` (P4); la whitelist delle origini è traslocata nel BB.
- **Riallinea e sblocca**: `PricingService.resolve_prezzo` con gli argomenti
  del BB, `prezzo_finale`, contesto kit e ripiego della data (P1, P2, P5).
- **Variazione eccezionale**: origine `MANUALE`, provenienza da listino a `NULL`.
- **Repository**: `update_attivita_prezzo(…, provenienza=)` scrive prezzo e
  provenienza e propaga le 8 colonne di audit ad `attivita_fatturabili` (P3);
  rifiuta una provenienza con colonne diverse. `get_attivita_pricing` legge
  anche `competenza_mese`.
- **Test**: `test_prezzo_riga_commessa.py` (6, funzioni pure),
  `test_commesse_service.py` (i tre test che fabbricavano `test_resolver` ora
  sostituiscono il `PricingService` con la forma vera della risposta, più 2
  nuovi), `test_commesse_source_handlers.py` (versione di listino sull'input),
  e **`tests/db/test_prezzo_riga_commessa_db.py`** sul DB vero: mondo costruito
  con i builder dei pgTAP, tre casi (conferma di versione e versione scritta,
  manuale poi sblocco, componente di kit).
  Provato **per mutazione**, tre mutazioni e tre rossi: il service di prima
  (`AttributeError: test_resolver`, 3 errori), il contesto kit tolto (1 rosso),
  la versione non scritta (3 rossi). Suite backend intera verde (6.301 test).
- **mypy** (venv temporanea, configurazione di §3): sui quattro file toccati i
  due `[attr-defined]` di `test_resolver` spariscono e non ne nascono di nuovi.
- **Documenti**: `api_commesse_pricing.md`, guide `gestione-listini.md` §7.2-7.4
  e `gestione-commesse.md`.

## 5. Lotti

| Lotto | Cosa | Prova |
| --- | --- | --- |
| **L0** ✅ | Il difetto di §4, nella forma di §4.2 (A-D) — fatto il 2026-10-08 (§4.5) | i test sul DB vero di §4.2 rossi prima, verdi dopo |
| **L1** ✅ | Accensione: `requirements-dev.in/.txt` (S2), `backend/mypy.ini` (S1/S5), `scripts/check_mypy_baseline.py` + `backend/mypy.baseline.json` (S4), passo CI (S6), documentazione (§6) | tre mutazioni, tre rossi: un rilievo nuovo, una voce sanata e non tolta, un'uscita illeggibile |
| **L2** ✅ | Smaltimento dei rilievi che sono **difetti di per sé**, qualunque sia il file: chiamate ad attributi inesistenti (`[attr-defined]`), uso del valore di una funzione che non restituisce niente (`[func-returns-value]`), funzioni che possono uscire senza `return` (`[return]`), `None` non gestito (`[union-attr]`, `[index]`) | il registro scende; per ogni difetto vero un test che lo costruisce |
| **L3** ✅ | Il resto: convenzione `dict[str, Any]`, correzioni alla radice, quattro lotti paralleli, BB dell'utente autenticato — fatto il 2026-10-09 (§5.3) | il registro scende a 2; un test per ogni difetto vero |

### 5.1 ✅ L1 fatto — 2026-10-09

- **Dipendenze** (S2): `backend/requirements-dev.in` → `requirements-dev.txt`
  (`-c requirements.txt`; mypy 2.4.0, django-stubs 6.1.2,
  djangorestframework-stubs 3.18.1), installate nella venv del backend.
  `backend/scripts/update-venv.sh` compila e sincronizza **entrambi** i lock:
  il `piptools sync` del solo `requirements.txt` le avrebbe disinstallate.
- **Configurazione** (S1, S3, S5): `backend/mypy.ini`. Le librerie senza tipi
  elencate per nome sono `bleach`, `openpyxl`, `weasyprint`: per le prime due
  esistono stub (`types-bleach`, `types-openpyxl`), che sarebbero dipendenze
  nuove — da decidere (Tid). ✅ **Ok di Tid il 2026-10-09**: entrano in
  `requirements-dev.in` col tetto della versione della libreria (bleach 6.4,
  openpyxl 3.1.5; portano con sé `types-html5lib` e `types-webencodings`), e le
  due voci di `mypy.ini` sono tolte. Registro invariato a 0; provato per
  mutazione che mypy ora legge gli stub (un argomento inesistente di
  `openpyxl.Workbook` e il tipo di ritorno di `bleach.clean` sono rilievi).
  `weasyprint` resta esentato: non ha stub.
- **Registro e cancello** (S4): `backend/mypy.baseline.json` (620 rilievi in 144
  file) e `scripts/check_mypy_baseline.py` (`--aggiorna` toglie soltanto,
  `--rigenera` riscrive da zero). Provato per mutazione: rilievo nuovo → rosso;
  voce sanata e non tolta → rosso, e `--aggiorna` la toglie; plugin che non
  parte → rosso «illeggibile» (uscita 2); `--aggiorna` con un rilievo nuovo →
  rifiuta; ambiente Django non caricato → rosso «illeggibile».
- **CI** (S6): passo «Type checker (mypy, a cricchetto)» in `ci-validate.yaml`,
  dopo `check --deploy`; `requirements-dev.txt` nella cache pip del job.
- **Documenti**: `sicurezza-e-qualita-statica.md` §mypy (sede), `AGENTS.md`
  (fonte unica dei requisiti dev, riga «Sicurezza e qualità statica»),
  `PROJECT_CONTEXT.md` (la riga dell'`assert`), `api.md` §Test, registro
  migliorie (D2-b in §9).

✅ Il registro era stato generato su un working tree con lavoro in parallelo: il rischio è chiuso, perché quel lavoro è entrato nello stesso commit (`0ffe7b7c3`) e il cancello era verde sull'albero committato.

### 5.2 ✅ L2 fatto — 2026-10-09

Tutti i rilievi delle cinque categorie di L2 (`attr-defined`,
`func-returns-value`, `return`, `union-attr`, `index`), **56** al 2026-10-09,
giudicati uno per uno. Il registro scende da 620 a **558** (−62: alcune
correzioni hanno sanato anche rilievi di altre categorie sullo stesso punto).

**Esito del giudizio: nessuno dei 56 era un errore a runtime oggi** — il
difetto vero di questa famiglia era `test_resolver`, già chiuso in L0. Erano
annotazioni imprecise o forme che il checker non sa seguire:

| Forma | Correzione | Dove |
| --- | --- | --- |
| `assert x is not None` mancante dopo `ErrorManager.require` (la regola di `PROJECT_CONTEXT.md`) | aggiunto | `definizioni_service` (3), `multi_veste_token_serializer`, `_helpers.sql_order_clause`, `listini_service`, `titoli_iva_service`, `preventivi_views`, `views_ordini` |
| Sentinella `MISSING` confrontata con `is` (mypy non restringe) | `isinstance(…, MissingType)` | `catalogo_service` (2) |
| Attributi dichiarativi delle view impostati dalle fabbriche (`area_funzionale`, `model_permission`, `<metodo>_permission`) | **annotazioni senza valore** su `DomainAPIView`: a runtime la classe non li ha, e `getattr(…, None)` / il fail-closed restano identici; `make_note_views` restituisce `type[DomainAPIView]` | `base_views`, `partitioned_note_views` (sanano 16 rilievi in 9 file) |
| Attributi dinamici su request ed eccezione | `setattr` con `# noqa: B010` e il motivo (ruff vuole il punto, mypy lo rifiuta) | `request_context_middleware`, `user_language_middleware`, `pipeline_step_executor` |
| Dedup con `set.add` dentro una comprehension | `list(dict.fromkeys(ids))` | `gestione_service`, `vendite_service` |
| Lambda che costruisce una lista di `None` per i suoi effetti | funzione `_delete_files` | `email_outbox_service` |
| Funzione che solleva sempre annotata `-> None` | `-> NoReturn` | `template_versioni_admin_service._raise_invalid_margin` |
| Mixin che usa il contratto di `SimpleRateThrottle` senza ereditarlo | eredita da `SimpleRateThrottle` (MRO invariato: il suo `get_ident` vince ancora) | `throttling._ClientIpIdentMixin` |
| Serializer della porta tipato come `BaseSerializer` | `_serializer_porta()` → `type[MultiVesteTokenSerializer]` (lo garantisce il guard di `post`); import locale ridondante tolto | `auth_views` |
| Produttori di dict eterogenei annotati `dict[str, object]` | `dict[str, Any]` (solo i quattro di L2; la convenzione generale è L3) | `fn_dash_*` (3), `numera_lotto` |
| Nome che esiste in Django ma non negli stub | `# type: ignore[attr-defined]` col motivo | `user_language_middleware` |

🔴 **Trovato strada facendo, e un `# type: ignore` che non ignorava niente:** in
`user_language_middleware` c'era `# type: ignore[attr-defined]` su una **riga
propria**, cioè su nessuna istruzione. Tolto con la correzione.

✅ **Una divergenza di regola — chiusa** (la nota qui sotto è lo stato al
momento di L2): la copia del service è stata **ritirata** nello stesso
`0ffe7b7c3`, la regola ha una sede sola (il guard comune del DB), e
`core/tests/db/test_date_validita_guard_comune_db` (caso 7) prova sia il rifiuto
sia il periodo di un giorno solo. Verificato il 2026-10-09.
Com'era: `catalogo_service.
_validate_date_interval` rifiuta `valido_al <= valido_dal` (pretende `>`), mentre
il guard comune del DB `script.trgfn_guard_date_validita` rifiuta solo
`valido_al < valido_dal`. Un periodo di **un giorno solo** passa il DB e lo
rifiuta il backend, sulle tabelle del catalogo che usano quel controllo (4
chiamate). Due copie della stessa regola, già divergenti: la sede è il DB, e la
copia nel service andrebbe tolta — è una decisione sul modello.

**Verifiche**: `ruff` pulito; cancello verde a 558; suite backend intera
(6.315 test) verde tranne due test sul DB vero che falliscono identici anche su
`HEAD` (provato in un worktree pulito), quindi non dipendono da L2. Verificati il
2026-10-09 (⚠️ la prima lettura, «un test che cerca i soggetti nei dati», era
**sbagliata**):

- `test_resi_create_db` — la fixture costruiva l'ordine già CONFERMATO e poi gli
  aggiungeva la riga: dal `20261008-90` (lock fuori bozza sulle righe d'ordine,
  applicato su dbdev la notte del 2026-10-08, non ancora nel branch) il DB lo
  rifiuta. `ORD2026-0000001` era l'ordine del test stesso. ✅ Corretta la
  fixture: bozza → riga → transizione DRAFT → CONFERMATO della matrice, una
  forma valida con e senza il lock nuovo.
- `test_giornale_trasversale_perimetro` 1 — **difetto vero del backend**, non del
  test: il filtro per giorno del giornale confronta un `timestamptz` con
  `%s::date`, e la sessione di Django è UTC. Il «giorno» è quindi il giorno
  UTC: fra le 00:00 e le 02:00 italiane «oggi» non contiene gli eventi appena
  scritti. Il test era rosso perché lanciato a mezzanotte e mezza. È la stessa
  famiglia che `script.fn_data_operativa` ha chiuso sul DB per la data
  documento: vedi
  [brief-be-db-fe-un-solo-fuso-aziendale.md](brief-be-db-fe-un-solo-fuso-aziendale.md).

### 5.3 ✅ L3 — 2026-10-09: da 557 a 2

**Convenzione decisa nel giro** (la maggioranza del codice, 2.242 usi contro
245): gli envelope JSON sono `dict[str, Any]`, non `dict[str, object]`. I 41 file
della minoranza sono stati allineati, con gli esempi di `api.md`.

**Correzioni alla radice** (un punto condiviso, molti rilievi):
`ErrorManager.require(condition: object)` (la condizione si valuta per verità);
`success_response` e l'`handler` di `handle_post_json`/`handle_detail_patch`
accettano `Mapping` (un `TypedDict` non è un `dict[str, Any]`) e `success_response`
anche lista e `None`; `validate_order_params` con `@overload` (con un `order_by`
presente la colonna torna presente); `create_with_dedup` generica;
`order_dir: str | None` nei repository di pagamenti e listini (`sql_order_clause`
accetta già `None`); `execute_dynamic_update(row_id: int | str | UUID)`;
`get_handler(handler_code: str | None)`; `cast(<Row>, …)` al confine dei
repository; `Mapping[str, Any]` sui parametri che solo leggono una riga tipata;
`GroupAttivitaInput`/`AttivitaDaFatturare` allineati al DB (`NOT NULL`); classi
derivate da basi costruite da fabbriche: `# type: ignore[valid-type, misc,
name-defined]` motivato sulla sola riga `class`.

**Il resto**, file per file, in quattro lotti paralleli (catalogo e listini;
core; servizi di vendite; il resto) con le stesse regole: niente cambi di
comportamento, i difetti si segnalano. Due `# type: ignore` preesistenti avevano
il **codice sbagliato** (magazzino, commesse) e non ignoravano niente.

🔴 **Difetti veri trovati, e corretti** (con test, provati per mutazione):

- `vendite/api/views_listini.py` `ApiListiniAlertScadenze`: passava la `request`
  a `qp_int_strict` invece del valore → 400 `giorni_invalid` a **ogni** chiamata
  dal 2026-04-12; il badge di `AlertScadenzeWidget` non si accendeva mai.
- `vendite/services/approvazioni_prezzo_service.py`: la pratica di approvazione
  prezzo di un preventivo leggeva `numero_documento`, che la testata non ha
  (`numero`), e si descriveva con l'id interno. Il test lo fabbricava col mock.
- `vendite/api/views_pricing.py` (resolve e diagnose): l'obbligo di
  `data_riferimento` si giudicava sul valore grezzo, e `""` passava.
- `documenti/api/sorgente_documenti_views.py`: la fabbrica accettava
  `emetti_call` senza `emetti_response_key` (risposta con la chiave `null`);
  ora la combinazione incoerente si rifiuta all'import. Nessun dominio di oggi la
  usava.

✅ **Seguito del 2026-10-09 (ok di Tid):** building block
`utente_autenticato` / `utente_autenticato_id` in `core/api/endpoint_helpers.py`
(catalogo BB), 45 sedi in 12 file; `cambia_stato` di DDT e ordini con un valore
non testuale → 400; `views_contatti_ruolo` col BB `qp_int_optional` → 400;
`soggetti_repository` senza i default cablati `"IT"`/`"SU"`/`"LN"` (`None` = il
default di `config.parameters`, risolto dalla funzione DB); `views_pricing` con
l'helper `_data_riferimento_obbligatoria` (regola del 2), che ora nomina il campo
anche in `diagnose`. Test per ciascuno. Registro **47 → 2**; suite intera verde
(6.340 test).

✅ **Difetti trovati (lo stato è nel paragrafo sopra; il primo chiuso il 2026-10-09 dal brief NaN, §7):**

- `documenti/services/context_builders/_number_formatting.py` (righe 96, 101):
  `-d.as_tuple().exponent` su NaN/Infinity è una stringa → `TypeError` (500) se
  un contesto documento porta un `numeric` NaN. Va deciso cosa mostrare.
- `vendite/services/ddt_service.py` e `ordini_service.py` `cambia_stato`:
  `(stato_codice or "").strip()` con un numero nel JSON → `AttributeError` (500
  invece di 400).
- `anagrafiche/api/views_contatti_ruolo.py` (≈ riga 57): `int(istanza_str)`
  grezzo, un valore non numerico è un 500.
- `anagrafiche/db/soggetti_repository.py`: i default `"IT"`/`"SU"`/`"LN"` di
  `crea_soggetto_pf/pg` sono cablati, mentre la funzione DB ha già `DEFAULT NULL`
  + `COALESCE` su `config.parameters`; il service li scavalca sempre. Da valutare
  se toglierli (`None` = il default del DB).
- `vendite/api/views_pricing.py`: dopo la correzione i due blocchi
  «`data_riferimento` obbligatoria» sono identici — regola del 2, estrazione da
  approvare.

✅ **Restavano 47 rilievi nel registro** (stato prima del seguito qui sopra):

- **45** sono `request.user.id` / `request.user` (`int | None`, `User |
  AnonymousUser`) passati dove serve l'utente autenticato. A runtime l'utente
  c'è sempre (`ZeroERPPermission` rifiuta l'anonimo), ma il tipo non lo sa.
  Proposta (regola del 2, ✅ **approvata e fatta** il 2026-10-09, vedi il seguito sopra): un building block in
  `apps/core/api/endpoint_helpers.py`, `utente_autenticato(request) -> User` e
  `utente_autenticato_id(request) -> int`, che solleva `NotAuthenticated` (401)
  sull'anonimo invece di lasciar passare `None`; le sedi (12 file) passano al BB.
- **2** sono il difetto NaN qui sopra (✅ sanati il 2026-10-09: registro a 0).

**Verifiche**: cancello verde a 47; `ruff` pulito; suite backend intera (6.327
test) verde tranne il rosso notturno noto del giornale (brief sul fuso).

⭐ L'ordine L2 → L3 è sulla **natura** del rilievo, non sul conteggio: un
`[attr-defined]` è quasi sempre un 500 in attesa, un `[arg-type]` quasi sempre
una firma da precisare.

## 6. Documentazione da aggiornare in L1

- [sicurezza-e-qualita-statica.md](../sicurezza-e-qualita-statica.md): una
  sezione `mypy` accanto a quella di `ruff` (tabella «Dove gira cosa», comandi,
  come si toglie una voce dal registro).
- `.codex/AGENTS.md`: `backend/requirements-dev.in` nella tabella «Fonte
  unica»; «mypy» nella riga «Sicurezza: strumenti» di «Dove sta cosa».
- `.codex/PROJECT_CONTEXT.md` §«Error handling»: la riga dell'`assert` resta,
  e acquista un riferimento al checker vero.
- [api.md](../api.md) §Test: una riga sul perché un test mockato non sostituisce
  il checker (il caso di §4 come esempio).
- Il registro migliorie: D2-b passa in §9 alla chiusura di L1.

## 7. Cosa questo piano non fa

- Non annota il codice esistente: smaltisce rilievi, non aggiunge tipi dove
  `mypy` non li chiede.
- Non controlla i test (S3).
- Non tocca il DB né il frontend.
