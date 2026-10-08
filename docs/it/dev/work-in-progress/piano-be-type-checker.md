# Piano — type checker del backend (D2-b)

> Nato il **2026-10-08** dalla decisione di Tid su **D2-b** di
> [migliorie-generali-BE-FE-da-test-valutazione.md](migliorie-generali-BE-FE-da-test-valutazione.md):
> il progetto **vuole** un type checker, acceso **a cricchetto**.
> Stato: 🟡 **piano in approvazione** — S2 e le tre dipendenze approvate il
> 2026-10-08; L0 (§4.2) in attesa di Tid. Niente è ancora nel repo: nessuna
> dipendenza installata nella venv del backend, nessun file di configurazione.

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

**A — Un building block, due consumatori (regola del 2, da approvare).**
In `apps/vendite/services/` una funzione sola che, data una riga di commessa,
**costruisce gli argomenti** del resolver (articolo, uom, data con il fallback
`data_attivita` → `competenza_mese`, BA, utility, emittente, contesto kit dal
`meta`) e **traduce il risultato** nei campi snapshot della riga (prezzo più i
dieci campi di provenienza). La usano il push (`_resolve_pricing_audit`) e
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

### 4.3 Due domande che la proposta non decide (Tid)

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

## 5. Lotti

| Lotto | Cosa | Prova |
| --- | --- | --- |
| **L0** | Il difetto di §4, nella forma di §4.2 (A-D) | i test sul DB vero di §4.2 rossi prima, verdi dopo |
| **L1** | Accensione: `requirements-dev.in/.txt` (S2), `backend/mypy.ini` (S1/S5), `scripts/check_mypy_baseline.py` + `backend/mypy.baseline.json` (S4), passo CI (S6), documentazione (§6) | tre mutazioni, tre rossi: un rilievo nuovo, una voce sanata e non tolta, un'uscita illeggibile |
| **L2** | Smaltimento dei rilievi che sono **difetti di per sé**, qualunque sia il file: chiamate ad attributi inesistenti (`[attr-defined]`), uso del valore di una funzione che non restituisce niente (`[func-returns-value]`), funzioni che possono uscire senza `return` (`[return]`), `None` non gestito (`[union-attr]`, `[index]`) | il registro scende; per ogni difetto vero un test che lo costruisce |
| **L3+** | Il resto, **per app**, partendo da quelle con i service più centrali (vendite, core). Ogni voce si giudica: difetto (si corregge il codice) o annotazione sbagliata (si corregge la firma) | il registro scende |

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
