# Piano — type checker del backend (D2-b)

> Nato il **2026-10-08** dalla decisione di Tid su **D2-b** di
> [migliorie-generali-BE-FE-da-test-valutazione.md](migliorie-generali-BE-FE-da-test-valutazione.md):
> il progetto **vuole** un type checker, acceso **a cricchetto**.
> Stato: 🟡 **piano da approvare**. Niente è ancora nel repo: nessuna
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

### S2 — Dove stanno le dipendenze **(Tid)**

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
`djangorestframework-stubs`. ⛔ Regola di casa: entrano solo con l'ok di Tid.

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

⛔ **Non si ripara dentro questo piano.** Il prezzo passa dal `PricingService`
(regola di casa: mai lookup diretti sui listini), e scegliere con cosa
sostituire `test_resolver` è una decisione sul modello del prezzo: lotto L0,
con l'ok di Tid sul merito.

## 5. Lotti

| Lotto | Cosa | Prova |
| --- | --- | --- |
| **L0** | Il difetto di §4: `fn_riallinea_prezzo`/`fn_sblocca_prezzo` sul resolver vero. Il test smette di fabbricare il metodo, e se ne aggiunge uno sul DB vero (`richiedi_db_provvisto`) che la chiamata la fa davvero | il test nuovo rosso prima del fix, verde dopo |
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
