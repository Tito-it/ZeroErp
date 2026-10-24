# Configurazione GitHub — branch, CI e pubblicazione

> **Ultimo aggiornamento**: 24 ottobre 2026
>
> **Destinatari**: chi sviluppa su ZeroERP (DB, backend, frontend) e chi deve capire perché una corsa della CI è rossa
>
> **Vedi anche**:
>
> * [Mappa mentale semplice di Git](/dev/github/mappa-mentale-semplice-di-git) — i comandi del flusso di tutti i giorni
> * [pgTAP — come si scrive un test, «Girano in CI?»](/guide/pgtap-come-si-scrive-un-test) — quando gira la suite DB e la sua baseline
> * [Linee guida SQL, §11](/linee-guida-sql) — i divieti dei changeSet che si rompono solo in CI
> * [Sicurezza e qualità statica](/dev/sicurezza-e-qualita-statica) — gli strumenti che la CI lancia (pre-commit, gitleaks, pip-audit, mypy, `check --deploy`)
> * [Presidi e registri del debito, §5](/guide/presidi-e-registri-del-debito) — che cosa fare se un cancello della CI diventa rosso

---

## In una frase

Si lavora su due branch personali, si integra su `Tito-dev` con una pull request, si rilascia su
`main` con una pull request da `Tito-dev`. La CI controlla ogni passaggio, ma **non lo blocca**:
il repository non ha branch protetti (vedi [Impostazioni del repository](#impostazioni-del-repository)).

---

## Il flusso dei branch

```text
dev/db-tid ──────┐  PR
                 ├──────►  Tito-dev  ──── PR ────►  main
dev/backend-tid ─┘         (integrazione)           (rilascio: sito della doc + immagine Docker)
```

| Branch            | Chi ci lavora                       | Come si muove                                                                 |
| ----------------- | ----------------------------------- | ----------------------------------------------------------------------------- |
| `dev/db-tid`      | il lavoro sul database              | PR verso `Tito-dev`; dopo il merge si riallinea a `Tito-dev`                   |
| `dev/backend-tid` | backend e frontend                  | come sopra                                                                    |
| `Tito-dev`        | nessuno direttamente: è il centro   | riceve le PR dei due branch di lavoro; da qui parte la PR verso `main`        |
| `main`            | nessuno direttamente: è il rilascio | riceve solo la PR da `Tito-dev`                                               |

I comandi per riallinearsi, integrare e risolvere i conflitti sono nella
[Mappa mentale semplice di Git](/dev/github/mappa-mentale-semplice-di-git).

---

## I tre workflow

Stanno in `.github/workflows/`. Ognuno si sveglia solo se il cambiamento tocca i suoi percorsi
(`paths:`): i percorsi esatti sono nell'intestazione `on:` di ogni file.

| Workflow            | Si sveglia su                                                     | Percorsi                                                                                     |
| ------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `ci-validate.yaml`  | PR verso `Tito-dev` o `main`; push su `Tito-dev`                  | `db/`, `backend/`, `scripts/`, `requirements.txt`, `.python-version`, `.pre-commit-config.yaml` |
| `ci-frontend.yaml`  | PR verso `Tito-dev` o `main`; push su `Tito-dev`                  | `frontend/`, `scripts/check_i18n_keys.py`                                                    |
| `ci.yaml`           | push su `main`; oppure a mano («Run workflow»), su qualsiasi branch | `db/`, `backend/`, `docs/`, `scripts/`, `Dockerfile`, dipendenze Python                       |

Ogni workflow si sveglia anche quando cambia il suo stesso file.

### `ci-validate.yaml` — il cancello di backend e database

Tira su un PostgreSQL con PostGIS **vuoto** e costruisce il database da zero, come un'installazione
nuova. Due job:

* **`validate`**, in quest'ordine:
  1. dipendenze del backend, `pip-audit`, `pre-commit` sui soli file cambiati;
  2. i guardrail statici sui changeSet (`scripts/guardrail_*.py`: `runOnChange`, prima generazione
     congelata, preambolo pgTAP, letterali SQL, timestamp senza fuso, `preCondition` sui seed, DDL
     sui trigger generati, `GRANT` ai ruoli batch) — l'elenco con la regola di ognuno è in
     [linee-guida-sql §11](/linee-guida-sql) e nella tabella dei divieti di `.codex/AGENTS.md`;
  3. il database: ruoli di sistema dal provisioning, poi Liquibase **due volte** — la passata
     principale e la passata `ci_apply`, che monta i trigger delle automazioni (vedi la
     [guida delle automazioni, §9](/guide/automazione-db));
  4. i controlli sul database costruito: naming, codici d'errore, riferimenti morti;
  5. Django: `check`, `check --deploy`, mypy a cricchetto, `migrate` dello schema `django`, i test;
  6. la **suite pgTAP**, solo sulle PR verso `main` e sui push a `Tito-dev` che toccano `db/` o
     `scripts/`, confrontata con la baseline `db/pgtap/baseline-rossi-ci.tsv`.
* **`validate-deploy`**: `shellcheck` sugli script di `backend/bin/`, gli unit systemd dei worker
  resi dall'installer e verificati, la prova del ramo che li accende.

⚠️ La suite pgTAP non si ferma se un passo precedente è rosso (per esempio i test Django): gira
comunque, purché la passata `ci_apply` sia riuscita. Un cancello non zittisce l'altro, e il job
resta rosso lo stesso.

### `ci-frontend.yaml` — il cancello del frontend

Senza database, sotto il minuto: `npm ci`, `npm audit`, lint (oxlint + eslint), i guard di
`package.json`, i test (vitest), la build (vite), la parità delle chiavi i18n. La versione di Node
la legge da `frontend/package.json`.

### `ci.yaml` — il rilascio

Gira sui push a `main`, cioè al merge della PR da `Tito-dev`. Due job:

* **`build`**: ricostruisce il database da zero (stessi passi di `ci-validate`), genera la doc
  auto-generata dal database vivo (`scripts/gen_db_docs.py`), applica le firme, costruisce il sito
  (`scripts/build_docs_zensical.py`) e lo **pubblica**;
* **`docker`**: costruisce l'immagine, la **pubblica** su GHCR, la scansiona con Trivy e la avvia
  per uno smoke test.

Lanciato a mano su un altro branch, `ci.yaml` costruisce l'immagine senza pubblicarla.

---

## Quando gira che cosa

| Evento                                         | `ci-validate`                      | pgTAP                            | `ci-frontend`          | `ci.yaml`  |
| ---------------------------------------------- | ---------------------------------- | -------------------------------- | ---------------------- | ---------- |
| PR `dev/*` → `Tito-dev`                        | ✅ se tocca i suoi percorsi         | ❌                               | ✅ se tocca `frontend/` | ❌         |
| push su `Tito-dev` (il merge di quella PR)     | ✅ se tocca i suoi percorsi         | ✅ solo se cambia `db/` o `scripts/` | ✅ se tocca `frontend/` | ❌         |
| PR `Tito-dev` → `main`                         | ✅ se tocca i suoi percorsi         | ✅ sempre                         | ✅ se tocca `frontend/` | ❌         |
| push su `main` (il merge di quella PR)         | ❌                                 | —                                | ❌                     | ✅ rilascio |

⚠️ Un push su `Tito-dev` che tocca solo `backend/` non fa girare i pgTAP: un rosso del database
introdotto lì si vede alla prima push successiva che tocca `db/`, oppure alla PR verso `main`.

Le corse si guardano con `gh run list --workflow <file>` o nella scheda **Actions** del repository.
Sulle PR una corsa nuova annulla la precedente; sui push ogni corsa arriva in fondo, perché è il
verdetto di uno stato di integrazione che è esistito.

---

## Impostazioni del repository

Lette dal repository `Tito-it/ZeroErp` il 2026-10-24 (`gh api repos/Tito-it/ZeroErp`):

| Impostazione                                        | Valore         | Perché conta                                                                                   |
| --------------------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------- |
| visibilità                                          | privato        | —                                                                                              |
| branch di default                                   | `main`         | —                                                                                              |
| «Automatically delete head branches»                | **spento** ✅   | acceso, al merge di una PR GitHub cancellerebbe il branch di partenza: anche `Tito-dev` quando è la testa della PR verso `main` ([trappole](/dev/trappole)) |
| protezione di `main` e `Tito-dev`                   | **nessuna** ⚠️  | vedi sotto                                                                                     |
| metodi di merge                                     | merge, squash, rebase tutti ammessi | le PR del flusso si chiudono con **merge commit**                         |

⚠️ **I branch non sono protetti.** Sul piano GitHub di un repository privato gratuito le regole
di protezione e i *ruleset* non sono disponibili (l'API risponde «Upgrade to GitHub Pro or make this
repository public»). Le conseguenze:

* una CI rossa **non impedisce** il merge di una PR: il cancello è la disciplina di guardare la
  corsa prima di premere «Merge»;
* nessuno impedisce un push diretto su `Tito-dev` o su `main`: il flusso passa sempre da una PR.

Per attivarla serve una delle due: il piano **GitHub Pro** sull'account proprietario, oppure il
repository **pubblico**. È una decisione di Tid, aperta.

**Che cosa si attiva, quando si potrà** — su `main` e su `Tito-dev`:

| Regola                                   | Perché                                                                                     |
| ---------------------------------------- | ------------------------------------------------------------------------------------------ |
| niente cancellazione del branch          | è la trappola del branch cancellato dopo il merge, chiusa anche se l'opzione si riaccende   |
| niente force-push                        | la storia dell'integrazione e del rilascio non si riscrive                                  |
| merge solo da pull request               | chiude il push diretto                                                                      |
| approvazioni richieste: zero             | lo sviluppatore è uno solo e si approva da sé: una revisione obbligatoria bloccherebbe ogni PR |

⚠️ **I controlli obbligatori della CI vanno scelti con cura.** I workflow si svegliano solo sui loro
percorsi: un controllo marcato «required» che su una PR non parte resta *in attesa* per sempre, e
la PR non si chiude più. O si richiedono solo controlli che girano su ogni PR, o i workflow
imparano a dare un esito anche quando non hanno niente da fare.

---

## Segreti

I segreti stanno in **Settings → Secrets and variables → Actions**. Qui ci sono solo i **nomi**: i
valori non si scrivono in nessun documento.

| Segreto                                   | Lo usa                                            | A che cosa serve                                                        |
| ----------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------- |
| `POSTGRES_ADMIN_PASSWORD`                 | `ci-validate.yaml`                                | la password del superuser del PostgreSQL usa-e-getta della corsa         |
| `ACTIONS_DEPLOY_KEY`                      | `ci.yaml`                                         | la chiave che pubblica il sito su `Tito-it/ZeroERP-Docs`                 |
| `GITHUB_TOKEN`                            | `ci.yaml` (automatico, non si configura)          | il push dell'immagine su GHCR                                            |

Sono gli unici. Un segreto che nessun workflow legge si cancella: un segreto morto è una
credenziale in giro senza un motivo. La pubblicazione su S3 è stata disattivata, e con lei i suoi
segreti e i passi commentati di `ci.yaml`.

Le altre password dei workflow (ruoli `zeroerp_owner`, `zeroerp_app`, chiavi Django) sono
**letterali segnaposto**: valgono solo per il database che vive dentro il runner per la durata
della corsa.

---

## Dove si pubblica

| Che cosa             | Dove                                                                 | Quando                    |
| -------------------- | -------------------------------------------------------------------- | ------------------------- |
| sito della doc       | branch `gh-pages` del repository `Tito-it/ZeroERP-Docs` (GitHub Pages) | a ogni push su `main`     |
| immagine Docker      | `ghcr.io/<owner>/zeroerp`, con i tag `:<sha>` e `:latest`             | a ogni push su `main`     |

La doc auto-generata del database (`docs/it/dbzero/<schema>/tabelle|views|funzioni`) è rigenerata
da `ci.yaml` sul database costruito in quella corsa, in modalità ridotta: sul sito le pagine portano
la parte scritta a mano (`manual/`), la versione completa con le definizioni è quella committata nel
repository. Dettaglio in [Generatore della documentazione DB](/dbzero/tools/gen_db_docs).

---

## Quando una corsa è rossa

1. Si apre la corsa e si guarda il **primo** passo rosso: i successivi spesso sono conseguenze.
2. Un **guardrail** rosso nomina il file e la regola: la regola sta in
   [linee-guida-sql §11](/linee-guida-sql).
3. La **suite pgTAP** rossa scrive in fondo al log la riga `❌ REGRESSIONI` con i file nuovi rispetto
   alla baseline: o è una regressione da correggere, o un file che va nella baseline con la sua
   ragione scritta ([pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test)).
4. Un rosso che non riguarda il proprio lato (per esempio un test backend rosso su una PR solo DB)
   si segnala a chi tocca invece di forzare il merge: il metodo è in
   [Presidi e registri del debito, §5](/guide/presidi-e-registri-del-debito).

---

{% include-markdown "signature-core.md" %}
