# Sicurezza e qualità statica — strumenti, presidi, configurazione

> **Ultimo aggiornamento**: 20 ottobre 2026
>
> **Destinatari**: chi sviluppa su backend, frontend o DB, e chi mette in piedi una macchina.
> La versione descrittiva, per tutti, è la guida [Sicurezza di ZeroErp](../guide/sicurezza.md).
>
> **Vedi anche** — i documenti che possiedono una parte della materia (qui c'è solo la mappa):
>
> * [Architettura Permessi e Autorizzazioni](../guide/architettura-permessi-e-autorizzazioni.md) — aree, livelli, `ZeroERPPermission`
> * [Architettura multi face auth](../guide/architettura-multi-face-auth.md) — login, vesti, freno sui tentativi, RLS come difesa
> * [Contratto GUC APP](../guide/contratto-guc-app.md) — l'identità che arriva al DB, fail-closed
> * [Row Level Security](../postgresql/row-level-security.md) — RLS in PostgreSQL
> * [Configurazione Django](backend/configurazione-django.md) — superficie pubblica, nginx, rate limit, variabili d'ambiente
> * [Linee guida SQL §11](../linee-guida-sql.md) — i divieti dei changeSet e i loro guardrail
> * [Presidi e registri del debito](../guide/presidi-e-registri-del-debito.md) — perché un presidio nasce a zero
> * [Qualità BE/FE — indicatori e lezioni](qualita-be-fe-indicatori.md) — che cosa si rilegge nel tempo, e la scorecard pesata
> * `SECURITY.md` in radice — come si segnala una vulnerabilità

---

## Come si legge

La sicurezza di ZeroErp è fatta di due famiglie di difese, che non si sostituiscono:

* **presidi statici** — guardano il **codice** prima che entri: al commit (pre-commit) e in CI.
  Fermano una classe di errori prima che esista;
* **presidi a runtime** — guardano la **richiesta** mentre gira: nginx, Django, permessi, RLS,
  audit. Fermano chi prova a usare il sistema in un modo non previsto.

⭐ Ogni presidio statico qui elencato **nasce a zero**: i rilievi esistenti si sanano *prima* di
accenderlo, così un rosso vuol dire sempre «l'hai introdotto tu». Il perché, e come si tiene un
registro a cricchetto quando lo zero non è raggiungibile subito, è nella guida
[Presidi e registri del debito](../guide/presidi-e-registri-del-debito.md).

⛔ **La configurazione di ogni strumento vive nel suo file, con il perché scritto lì**
(`ruff.toml`, `.gitleaks.toml`, `.pre-commit-config.yaml`, i workflow). Questo documento dice
**cosa c'è, dove, e come si usa**: non ricopia elenchi di regole né versioni, che divergerebbero
al primo aggiornamento.

---

## Dove gira cosa

| Presidio | Guarda | Al commit | In CI | A mano |
| --- | --- | --- | --- | --- |
| **ruff** | Python: difetti e sicurezza (bandit) | ✅ hook `ruff-check` | ✅ via pre-commit (`ci-validate`) | `ruff check .` |
| **mypy** | Python: tipi fra gli strati (type checker), a cricchetto | — | ✅ `ci-validate`, passo dedicato | vedi sotto |
| **gitleaks** | segreti nei commit | ✅ hook `gitleaks` (staged) | ✅ via pre-commit, sui commit del range | vedi sotto |
| **pip-audit** | dipendenze Python con CVE note | — | ✅ `ci-validate`, passo dedicato | vedi sotto |
| **npm audit** | dipendenze JavaScript, `high`/`critical` | — | ✅ `ci-frontend` | `npm audit --audit-level=high` |
| **Trivy** | immagine Docker (OS + librerie), HIGH/CRITICAL | — | ✅ `ci.yaml` | — |
| **`check --deploy`** | configurazione Django di produzione | — | ✅ `ci-validate`, completo, con l'elenco degli avvisi accettati | vedi sotto |
| **oxlint + eslint** | JavaScript/Vue | — | ✅ `ci-frontend` (`npm run lint`) | `npm run lint` |
| **guard frontend** | le regole del progetto (i `guard:*` di `package.json`) | — | ✅ `ci-frontend` (`npm run guards`) | `npm run guards` |
| **header licenza, chiavi i18n, classi morte** | file nuovi, locales, CSS | ✅ hook locali | ✅ via pre-commit | `pre-commit run <id>` |
| **guardrail SQL/Liquibase** | changeSet e definizioni live | — | ✅ `ci-validate`, un passo per guardrail | `python scripts/guardrail_*.py` |
| **plpgsql_check, postura dei ruoli, pgTAP** | funzioni, GRANT e proprietà, RLS | — | ✅ `ci-validate` | `scripts/testpgtap.sh` |
| **shellcheck, `systemd-analyze`** | script bash, unit dei worker | — | ✅ `ci-validate` | — |
| **test Django di sicurezza** | permessi, superficie, perimetro | — | ✅ `ci-validate` | `python manage.py test` |

Installazione degli hook sulla propria macchina (una volta):

```bash
pip install -c requirements.txt pre-commit     # dal venv degli strumenti (requirements.txt in radice)
pre-commit install                             # scrive .git/hooks/pre-commit
pre-commit run --all-files                     # prova a vuoto
```

⚠️ Gli hook guardano **solo ciò che è in staged**: un `git add` parziale fa girare il cancello su
un commit diverso da quello che si ha sul disco.

---

## ruff — analisi statica del backend

**File**: `ruff.toml` in radice. **Hook**: `ruff-check` (la versione è il `rev` in
`.pre-commit-config.yaml`). La selezione delle regole sta **solo** in `ruff.toml`: l'hook non
porta argomenti, così `ruff check` a mano e il cancello dicono la stessa cosa.

### Le famiglie accese

| Codice | Cosa ferma |
| --- | --- |
| `F` | pyflakes: import morti, nomi non definiti, variabili inutilizzate, ridefinizioni |
| `E9` | errori di sintassi e di I/O |
| `T20` | `print()` nel codice servito da Django (va nel logger) |
| `C4` | costruzioni inutili di `dict`/`list`/`set` |
| `A` | argomenti che ombreggiano un builtin |
| `PIE` | costruzioni ridondanti — fra cui la chiave duplicata in un `dict`/`TypedDict` |
| `G`, `LOG` | uso corretto del logging (`logger.exception` dentro un `except`, e solo lì) |
| **`S`** | **sicurezza** (le regole di Bandit, via flake8-bandit): SQL composto a stringhe, `except: pass`, template senza autoescape, `subprocess`, password cablate, hash deboli, `pickle`/`yaml.load`, ... |
| `B` | bugbear: fra le altre `zip()` senza `strict=` (tronca **in silenzio** alla lista più corta: si scrive `strict=True`, e `strict=False` solo dove la troncatura è voluta, col perché), una funzione nel ciclo che legge la variabile del ciclo, `raise` dentro un `except` senza `from` |
| `DTZ` | flake8-datetimez: `date.today()`, `datetime.now()` senza fuso, `datetime(...)`/`strptime` naive — il giorno e l'ora del **processo** (`TIME_ZONE = 'UTC'`), che non è il fuso dell'azienda. L'«oggi» è `fuso_aziendale.oggi_aziendale()`, l'ora mostrata `locale_formatters`; un naive voluto si marca col motivo ([brief un-solo-fuso-aziendale](work-done/brief-be-db-fe-un-solo-fuso-aziendale.md) B-9) |
| `RUF100` | `# noqa` morti: una direttiva che non sopprime più niente |

### Le eccezioni, e perché

| Voce | Dove | Motivo in breve (il dettaglio è in `ruff.toml`) |
| --- | --- | --- |
| `ignore = ["S101"]` | ovunque | `assert` si usa per restringere il tipo. Il rischio della regola (`python -O` toglie gli assert) è chiuso alla radice: `settings.py` **rifiuta l'avvio** con gli assert spenti. Un **controllo** si scrive `if …: raise`, mai `assert` |
| `T201`, `T203`, `S603`, `S607` | `scripts/**`, `backend/scripts/**` | negli script da riga di comando `print` è l'interfaccia e lanciare `git` dal PATH è il lavoro |
| `T201`, `T203` | `docs/it/dev/*/allegati/*.py` | gli script allegati ai brief (collaudi lanciati a mano con `manage-env.sh shell <`) parlano a chi li lancia con `print` |
| `S` | `**/tests/**`, `test_*.py`, `conftest.py` | nei test `assert` è il linguaggio e le password sono finte per costruzione |
| formattatore | — | **spento**: riformattare tutto renderebbe illeggibile `git blame` |

### Come si usa `# noqa`

* Sempre **con il codice** e **con il motivo**: `# noqa: S608 — colonne da whitelist, valori come parametri`.
  Il motivo dice **da dove arriva** il pezzo interpolato, non «è sicuro»: è ciò che il prossimo
  deve poter ricontrollare.
* Mai un `noqa` nudo, mai sul file intero.
* ⛔ Mai `ruff check --select RUF100 --fix` per pulire i `noqa` morti: con `--select` tutte le
  altre regole risultano spente e ruff toglie **tutti** i `noqa` del repo. Si usa
  `ruff check --fix .` con la configurazione intera.

### Comandi

```bash
ruff check .                          # tutto il repo, configurazione di ruff.toml
ruff check backend/apps/vendite       # un sotto-albero
ruff check --statistics .             # conteggio per regola
ruff rule S608                        # spiegazione di una regola
```

### Allargare la selezione

Si fa con la disciplina scritta in testa a `ruff.toml`: si conta quanti rilievi apre la regola
nuova, si sanano, **poi** si accende. Mai il contrario: un cancello che nasce con un registro
aperto protegge solo ciò che avanza.

---

## mypy — il type checker del backend

**File**: `backend/mypy.ini` (perimetro e regole), `backend/mypy.baseline.json` (il registro),
`scripts/check_mypy_baseline.py` (il cancello). **Dipendenze**: `backend/requirements-dev.in`
→ `requirements-dev.txt` (mypy, `django-stubs`, `djangorestframework-stubs`, `types-bleach`, `types-openpyxl`), nella venv del
backend ma **non** nell'immagine Docker. Il [piano](work-done/piano-be-type-checker.md) che l'ha
acceso ne racconta la storia e lo smaltimento dell'arretrato.

### Perché

La suite del backend è quasi tutta mockata, e un `MagicMock` accetta qualunque attributo e
qualunque firma: un service che chiama un metodo tolto, o passa `None` dove la funzione vuole un
`int`, resta **verde**. mypy vede questi difetti di **giuntura** senza eseguire il codice. Il
caso che lo ha acceso: riallinea e sblocca del prezzo di una riga di commessa chiamavano da sei
mesi un metodo che non esisteva più, e il test lo fabbricava col mock.

### Le scelte

| Voce | Scelta | Perché |
| --- | --- | --- |
| Strumento | mypy con i plugin Django e DRF | il plugin legge settings e modelli: conosce l'ORM. Pylance non ha un plugin Django, e resta spento in VS Code (due checker che dicono cose diverse sono peggio di uno) |
| Perimetro | `apps/` e `zeroerp_backend/`, **esclusi** `tests/` e `migrations/` | i difetti stanno fra gli strati, quindi tutti gli strati; i test controllano mock, le migration sono generate |
| Severità | base + `check_untyped_defs` | senza, mypy salta il corpo delle funzioni non annotate. Niente `strict` |
| Librerie senza tipi | `ignore_missing_imports` **per nome**, in `mypy.ini`, solo per una libreria che non ha stub | globale, un import sbagliato del progetto diventerebbe `Any` in silenzio. Uno stub (`types-…`) è una dipendenza nuova: entra con l'ok di Tid, e la voce si toglie |
| Dove gira | CI, sempre su **tutto** il perimetro; non in pre-commit | una firma cambiata in un file rompe il chiamante in un altro; l'hook vede i soli file in stage e il plugin vuole l'ambiente Django |

### Il registro

A differenza di `ruff`, mypy **è nato con un registro aperto** (decisione di Tid): l'arretrato su
codice scritto senza checker è stato smaltito dopo l'accensione, nei lotti del
[piano](work-done/piano-be-type-checker.md), che ne tiene i numeri. Oggi il registro è **vuoto**,
e il cricchetto non lo lascia risalire: per mypy vale la stessa regola degli altri presidi, un
rosso vuol dire «l'hai introdotto tu».

* La chiave è **per nome**: file + codice (`[arg-type]`) + messaggio, con un conteggio. Mai il
  numero di riga, che cambia a ogni modifica sopra il punto.
* Il cancello è **rosso** su: un rilievo nuovo; una voce del registro che non c'è più (sanata e
  non tolta); un'uscita di mypy che non sa leggere (configurazione rotta, plugin che non parte,
  ambiente Django non caricato o incompleto: le settings rifiutano l'avvio se manca una variabile
  obbligatoria, e mypy esce con un `INTERNAL ERROR`).
* ⚠️ Limite: due rilievi identici nello stesso file sono una chiave col conteggio 2.

Come si sana una voce, se un `--rigenera` ne riporta: si corregge il codice (se è un difetto) o la firma (se l'annotazione era
sbagliata), poi `--aggiorna` toglie la voce. ⛔ `--rigenera` riscrive il registro da zero, quindi
anche **aggiungendo**: solo per una decisione (un aggiornamento di mypy o degli stub), e il diff
lo mostra.

### Comandi

Dalla cartella `backend/`, con la venv del backend e l'ambiente della shell caricato (`env.sh`,
sezione [I file](#i-file)):

```bash
set -a && . ./env.sh && set +a
.venv/bin/python ../scripts/check_mypy_baseline.py              # il cancello, come in CI
.venv/bin/python ../scripts/check_mypy_baseline.py --aggiorna   # toglie le voci sanate
.venv/bin/mypy apps/vendite/services/commesse_service.py        # i rilievi di un file, a mano
```

Le dipendenze si aggiornano con `backend/scripts/update-venv.sh`, che compila e sincronizza
**entrambi** i lock: un `piptools sync` del solo `requirements.txt` disinstallerebbe mypy.

---

## gitleaks — segreti nel repo

**File**: `.gitleaks.toml` (regole), `.gitleaksignore` (falsi positivi storici).
**Hook**: `gitleaks` in `.pre-commit-config.yaml`.

### Come funziona l'hook

* **Al commit**: scansiona l'indice (`--staged`), cioè ciò che si sta per committare.
* **In CI**: `pre-commit run --from-ref … --to-ref …` non ha niente in staged, e con l'`entry`
  ufficiale l'hook passerebbe sempre. Per questo l'`entry` è sovrascritta: se pre-commit esporta il
  range (`PRE_COMMIT_FROM_REF`), si scansionano **i commit del range**. Sono le stesse righe che la
  PR porta.
* `--redact`: il log della CI è pubblico, un segreto trovato non si ristampa lì.

### La regola del progetto

Le regole di default riconoscono i formati noti (chiavi AWS, token GitHub, chiavi private, JWT,
…) ma **non** vedono una `SECRET_KEY` di Django con prefisso `django-insecure-` né una password
umana. `.gitleaks.toml` aggiunge `zeroerp-env-segreto`: qualunque assegnazione
`NOME_CON_SECRET/PASSWORD/TOKEN/KEY=valore` in un file di ambiente (`.env`, `.env.*`,
`internal*.env`, `env.sh`). Sono ammessi i segnaposto `<...>` e i riferimenti `$VAR`. Il modello
`backend/.env.example` è dentro il perimetro di proposito: è tracciato, ed è lì che un valore
vero entrerebbe per distrazione.

### Falsi positivi

* In riga: commento `# gitleaks:allow` sulla riga segnalata.
* Storici, già valutati: impronta in `.gitleaksignore`, con il motivo nel commento.
* ⛔ Mai spegnere una regola intera. Un rilievo **vero** non va in `.gitleaksignore`: si ruota il
  segreto.

### Comandi

```bash
pre-commit run gitleaks                                    # l'indice attuale
pre-commit run gitleaks --from-ref origin/Tito-dev --to-ref HEAD   # i commit del branch
# storia intera (lenta: minuti). Il binario lo installa pre-commit in ~/.cache/pre-commit
gitleaks git --redact .
```

---

## Dipendenze e immagine

* **pip-audit** — `ci-validate`, passo «Audit dipendenze Python»: confronta i pin di
  `backend/requirements.txt` e `requirements.txt` con i database di vulnerabilità note. Ferma la
  PR che porta un pin vulnerabile. Un CVE pubblicato su un pin che **non cambia** non arriva qui
  (il workflow gira sui cambi). A mano:
  `pip-audit --no-deps --disable-pip -r backend/requirements.txt -r requirements.txt`.
* **Trivy** — `ci.yaml`, sull'immagine Docker costruita: fallisce su vulnerabilità HIGH/CRITICAL
  che hanno una correzione disponibile (`ignore-unfixed`).
* **npm** — le correzioni di sicurezza di dipendenze transitive si fissano in
  `frontend/package.json` → `overrides`. **`npm audit --audit-level=high`** in `ci-frontend.yaml`,
  dopo `npm ci`: il gemello di `pip-audit`. Ferma solo
  `high`/`critical`, dipendenze di sviluppo comprese. Come `pip-audit`, un avviso su un lock che
  non cambia non arriva qui (il workflow gira sulle push che toccano `frontend/**`).

---

## `manage.py check --deploy` — la configurazione di produzione

Django ha un insieme di controlli sulla configurazione di produzione (cookie `Secure`, HSTS,
redirect HTTPS, lunghezza della `SECRET_KEY`, `DEBUG`, X-Frame-Options…), e ogni app o libreria
può agganciarne di suoi (drf-spectacular lo fa). In `ci-validate` il passo «Django check --deploy
(completo)» li esegue così:

* **completo**, senza `--tag security`: un controllo di produzione nuovo, portato da una libreria
  o da un aggiornamento di Django, fa rosso senza che nessuno lo debba accendere. Gli avvisi di
  drf-spectacular li presidia anche il registro per nome
  `apps/core/tests/test_schema_openapi_registro.py`;
* **`mail.E001` è silenziato** in `settings.py` (`SILENCED_SYSTEM_CHECKS`), **per progetto**:
  Django non spedisce posta in ZeroErp — tutta la posta passa dal servizio email e da
  `config.email_account` — e la console di `MAILERS` vale in ogni ambiente, produzione compresa.
  Configurare a Django uno SMTP vero aprirebbe un secondo canale fuori dal modello. Il
  silenziamento si toglie il giorno in cui Django dovesse spedire per davvero;
* la `SECRET_KEY` si **genera** nel passo, come in produzione: un segnaposto corto farebbe
  scattare `security.W009`, giustamente;
* HSTS e redirect si impostano ai valori di **produzione** (un anno, redirect acceso): se un
  giorno si spegnessero, `W004`/`W008` tornerebbero rossi;
* un **avviso** (`W`), di qualunque famiglia, non cambia l'uscita di `check` (un errore `E` sì):
  il cancello lo fa un `grep` con l'elenco dei rilievi **accettati**: `W005` (HSTS senza
  sottodomini) e `W021` (HSTS senza preload), spenti **per scelta** e non debito: riguardano il
  dominio intero, non ZeroErp, e il preload è di fatto irreversibile (brief sicurezza §1.3).
  Quell'elenco si **accorcia**, non si allunga per far passare una PR.

### HSTS e redirect HTTPS

Stanno in `settings.py` (variabili `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_SECURE_SSL_REDIRECT`),
non in Nginx: sono versionati e li verifica `check --deploy`.

* **HSTS** è obbligatoria con `DEBUG=0`, senza default. Una macchina con certificato
  auto-firmato dichiara `0` (così `backend-dev`); in produzione si parte da `300` e, verificato,
  si sale a `31536000`. ⛔ Con HSTS acceso e un certificato non valido il browser rifiuta il sito
  senza «procedi comunque», fino alla scadenza.
* **Redirect** acceso di default con `DEBUG=0`. Chi chiama Gunicorn diretto in HTTP riceve un
  301, salvo: `/health` (esente); gli smoke bash, che si dichiarano HTTPS come Nginx (e, come Nginx,
  dichiarano la provenienza `X-Forwarded-For` che il login pretende) includendo
  `backend/scripts/tests/_smoke_https.sh` (presidio: `apps/core/tests/api/test_https_header.py`);
  i test Django, per cui lo spegne il runner.
* Dopo aver cambiato una delle due variabili serve `sudo systemctl restart zeroerp-gunicorn`: un
  `kill -HUP` non rilegge `.env.systemd`.

La **CSP** invece sta in Nginx, perché la pagina HTML non la serve Django:
[configurazione Django](backend/configurazione-django.md), sezione Nginx, con `Referrer-Policy` e
`Permissions-Policy`. Una politica nuova si collauda prima in `Report-Only`.

A mano, con l'ambiente della shell caricato:

```bash
cd backend && set -a && . ./env.sh && set +a
python manage.py check --deploy
```

---

## Frontend

* **oxlint** (`.oxlintrc.json`, categoria `correctness` in errore, plugin eslint/unicorn/oxc/vue)
  e **eslint** (`eslint.config.js`: `recommended`, `vue/flat/essential`,
  `vue/no-undef-properties`). Si lanciano insieme con `npm run lint`; `npm run fix` corregge ciò
  che è correggibile.
* **Guard del progetto** (`npm run guards`, script in `frontend/scripts/`). Quello con valore di
  sicurezza è `guard:pinia`: verifica che i dati degli store marcati `userScoped` si azzerino al
  logout, cioè che il prossimo utente sullo stesso browser non veda i dati del precedente.
* **HTML dinamico**: `v-html` non è usato, e la regola eslint `vue/no-v-html` (in errore) lo tiene
  tale: inserisce HTML senza escape, cioè la strada di uno script iniettato. Un caso vero si
  discute prima, e si marca sul punto con il motivo. Il testo HTML che arriva dall'utente (il corpo
  delle email) si ripulisce **nel backend**, con `bleach` (`html_sanitizer_service`).
* **Token e chiamate**: un solo client HTTP (`core/api.js`) con l'header `Authorization`, il
  refresh su 401 con coda, e il guard delle rotte in `router/index.js`. Le regole di scrittura
  sono in [frontend-standards §Sicurezza](frontend/frontend-standards.md).
* `npm run verify` = lint + guard + test + build: lo stesso giro della CI.

---

## Guardrail DB e test di sicurezza

**Liquibase e SQL** (`scripts/guardrail_*.py`, in `ci-validate`). Quello con valore di sicurezza
diretto è `guardrail_grant_ruolo_batch.py`: nessun `GRANT` a un ruolo che scavalca la RLS dentro
un changeSet. Gli altri, e il perché di ciascuno, in [linee-guida-sql §11](../linee-guida-sql.md).
`guardrail_no_db_migrate.py` è un hook di Claude Code, non della CI: blocca le migrazioni lanciate
da un agente.

**Postura del DB** (`ci-validate`):

* «DB bootstrap» e «Ruoli di sistema - fase post»: i ruoli (`zeroerp_owner`, `zeroerp_job`,
  `zeroerp_app`) e i loro GRANT nascono da `scripts/sql/provision_zeroerp.sql`, lo stesso script
  di un'installazione, e la fase post verifica che il proprietario sia uno solo;
* pgTAP di postura in `db/pgtap/dbops/` e `db/pgtap/maintenance/` (`test-*postura*`): le tabelle
  sono del migratore, l'applicazione non possiede niente, `zeroerp_app` ha solo i privilegi del
  contratto;
* pgTAP in `db/pgtap/rls/`: struttura delle policy in lettura e scrittura
  (`test-rls-policies-structure.sql`, `test-rls-write-policies-structure.sql`) e tabelle scoperte
  (`test-rls-perimetro-scoperto.sql`).

**Test Django** (in `backend/apps/core/tests/`):

| Test | Cosa garantisce |
| --- | --- |
| `test_skip_area_check_registro.py` | registro a cricchetto delle view che saltano il controllo d'area, letto dall'URLconf reale |
| `api/test_permissions_decisione_skip_area.py` | cosa succede davvero quando lo skip è dichiarato |
| `api/test_superficie_pubblica.py` | admin Django assente, root senza redirect, Swagger 404 quando è spento |
| `test_perimetro_emittente_copertura.py` | ogni lista configurabile ha il suo cancello di perimetro, o un'esenzione motivata |
| `middleware/test_jwt_audit_middleware.py` | i GUC d'identità si azzerano a ogni richiesta (nessun trascinamento fra utenti) |
| `middleware/test_sola_lettura_rotte.py` | ogni GET gira in sola lettura, salvo eccezioni dichiarate |

---

## Presidi a runtime — la difesa a strati

Una richiesta attraversa questi strati **in ordine**. Ognuno garantisce una cosa sola, e il
dettaglio sta nel documento che lo possiede.

| # | Strato | Garantisce | Dove sta | Documento |
| --- | --- | --- | --- | --- |
| 1 | **nginx** | unico ingresso HTTPS; rate limit (più stretto su login e reset); 404 su admin e Swagger | vhost + `zeroerp-ratelimit.conf` (fuori dal repo) | [Configurazione Django](backend/configurazione-django.md) |
| 2 | **Django — superficie** | nessun admin, Swagger solo con `API_DOCS_ENABLED`, solo JSON, cookie `Secure` senza DEBUG, IP del client dal solo proxy fidato | `settings.py`, `api_docs_gate.py`, `request_context.get_client_ip` | idem |
| 3 | **Autenticazione** | JWT con rotazione e blacklist del refresh, freno sui tentativi per credenziale e provenienza, throttle per IP, **secondo fattore TOTP** (login a due passi con sfida firmata, anti-replay sul passo a DB, codici di recupero monouso; obbligatorio per credenziale o profilo, sempre per il SUPER_ADMIN), cancello degli obblighi (cambio password, configurazione del secondo fattore), token monouso con hash | `jwt_audit_authentication.py`, `auth_views.py`, `secondo_fattore_token_views.py`, `secondo_fattore_service.py`, `throttling.py`, `cancello_obblighi.py` | [Multi face auth](../guide/architettura-multi-face-auth.md), [Risorse umane e accessi](../guide/risorse-umane-e-accessi.md) |
| 4 | **Permessi** | ogni endpoint dichiara un'area; senza area si nega (fail-closed); TUTTO / LETTURA / BLOCCATO | `ZeroERPPermission` in `core/api/permissions.py` | [Permessi](../guide/architettura-permessi-e-autorizzazioni.md) |
| 5 | **Identità al DB** | i GUC `app.*` si azzerano a ogni richiesta e si impostano dal token; una funzione che li trova vuoti rifiuta | `jwt_audit_middleware.py` | [Contratto GUC APP](../guide/contratto-guc-app.md) |
| 6 | **RLS PostgreSQL** | anche un bug nel backend non fa vedere righe fuori perimetro; i ruoli che la scavalcano non sono usabili dal web | policy nei changeSet, `system_context.connection_role_bypasses_rls` | [RLS](../postgresql/row-level-security.md), [Provisioning ruoli](backend/provisioning-db-roles.md) |
| 7 | **Sola lettura** | una GET non può scrivere, neanche per errore | `sola_lettura_middleware.py` | [api.md](api.md) |
| 8 | **Audit** | chi ha fatto cosa, quando, da quale sessione; log `security.*` per login bloccati e permessi negati | trigger di audit, `session_audit_service`, logger `security` | [Audit e tracciabilità](../guide/audit-e-tracciabilita.md) |

Password: i validatori standard di Django più `ComplexityValidator` (maiuscola, minuscola, cifra,
carattere speciale), in `AUTH_PASSWORD_VALIDATORS`.

---

## Segreti e configurazione

### I file

| File | Tracciato | Contiene |
| --- | --- | --- |
| `backend/.env.example` | ✅ | il **modello**: nomi delle variabili e segnaposto |
| `backend/env.sh` | ⛔ mai | l'ambiente della shell (`set -a && . ./env.sh && set +a`): mypy e `manage.py` a mano |
| `backend/.env.systemd` | ⛔ mai | lo stesso, per il servizio e i timer (senza `export`); lo leggono anche `manage-env.sh` e `manage-test.sh` |
| `db/internal.env`, `internal*.env` | ⛔ mai | credenziali DB per pgTAP e strumenti |
| `git.env` | ✅ | solo segnaposto e la lista degli schemi per la doc |

Li tiene fuori `.gitignore`, ma **`.gitignore` non è un presidio**: non ferma un `git add -f` né un
file che era già tracciato prima della regola. Il presidio è gitleaks.

### Default sicuri in `settings.py`

* `DJANGO_SECRET_KEY` **obbligatoria**, senza ripiego: un ripiego costante sta nel repo, cioè è
  pubblico, e il backend partirebbe lo stesso senza dirlo. Lo stesso vale per
  `DJANGO_FIELD_ENCRYPTION_KEYS`, che in più deve contenere chiavi Fernet valide e non ripetute.
* `DJANGO_DEBUG` **spento** se non è impostato: si accende a mano (`DJANGO_DEBUG=1`) sulla
  macchina che lo vuole.
* `DJANGO_TRUSTED_PROXY_COUNT`, `FRONTEND_URL`, `DB_NAME`/`DB_USER`/`DB_PASSWORD` obbligatorie.
* Il backend **non parte** con `python -O` (assert spenti).

### Le chiavi dei dati cifrati

`crypto_service` cifra i segreti salvati nel DB con le chiavi **Fernet** di
`DJANGO_FIELD_ENCRYPTION_KEYS`, **separate dalla `SECRET_KEY`**: una chiave derivata dalla
`SECRET_KEY` renderebbe illeggibile ogni dato cifrato al primo cambio, cioè la `SECRET_KEY` non
si ruoterebbe mai.

* **La `SECRET_KEY`** firma JWT e sessioni. Cambiarla fa rientrare gli utenti e azzera i
  contatori dei nomi di login inesistenti (`nome_tentato`); i dati cifrati non li tocca.
* **Le chiavi di cifratura** sono un elenco separato da virgola: si cifra con la **prima**, si
  decifra con **tutte** (`MultiFernet`). Chi le conosce può decifrare quei dati.
* Ogni colonna cifrata è iscritta in `crypto_service.CAMPI_CIFRATI`: è l'elenco che la
  rotazione percorre, e l'unico posto in cui si legge quali sono. Una colonna chiusa in
  scrittura all'app si riscrive col suo verbo: per il segreto del secondo fattore
  (`config.auth_totp_device`) è `script.fn_totp_ricifra_segreto`, che sostituisce il segreto
  solo se è ancora quello letto.

Le chiavi si gestiscono con due script in `backend/scripts/`, che tengono allineati i due file
d'ambiente (`env.sh` e `.env.systemd`), non stampano mai una chiave e salvano una copia dei due
file in `backend/var/backup-env/` prima di scriverli.

⚠️ **I comandi qui sotto si lanciano dalla radice del repo** (`~/apps/ZeroErp`). Da dentro
`backend/` il percorso perde il `backend/` iniziale: `scripts/chiave-cifratura-aggiungi.sh`.
Scritto nella forma sbagliata, la shell risponde «File o directory non esistente» e **non
succede niente**: se si riavvia lo stesso, il backend non parte (`Missing env var:
DJANGO_FIELD_ENCRYPTION_KEYS` nel journal, e al login «Accesso non disponibile per un problema
tecnico»). Prima del riavvio conviene controllare che la variabile ci sia:
`grep -c DJANGO_FIELD_ENCRYPTION_KEYS backend/.env.systemd` deve dare `1`.

Rotazione delle chiavi di cifratura:

1. `backend/scripts/chiave-cifratura-aggiungi.sh`: genera una chiave nuova e la mette **in
   testa** all'elenco (le vecchie restano dopo);
2. `backend/scripts/chiave-cifratura-ricifra.sh`: dry-run, conferma, poi
   `manage.py ricifra_campi_cifrati`, che ri-cifra tutto con la prima chiave, **tutto o niente**.
   Se un token non si apre con nessuna chiave, il comando fallisce e non scrive nulla: quel
   segreto va reinserito (la password SMTP dal suo account);
3. `backend/scripts/chiave-cifratura-aggiungi.sh --togli-vecchie`: verifica che la sola prima
   chiave apra tutto, poi toglie le altre;
4. `sudo systemctl restart zeroerp-gunicorn` (i timer rileggono `.env.systemd` a ogni giro).

`backend/.env.systemd` e `backend/env.sh` contengono le chiavi: permessi **600**
(`chmod 600`); lo script lo segnala se non lo sono.

⭐ **Migrazione una-tantum** dei dati cifrati prima del 2026-09-28, su ogni macchina con dati:
`chiave-cifratura-aggiungi.sh`, poi `chiave-cifratura-ricifra.sh --migrazione` (che passa
`--anche-chiave-da-secret-key`), con la `SECRET_KEY` di allora **ancora in uso**, poi il
riavvio. Solo **dopo** si può ruotare la `SECRET_KEY`.

Generazione:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"                                  # SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"     # chiave Fernet
```

---

## Aperto

Qui l'elenco di ciò che, in tema sicurezza, oggi **non** c'è. Il debito aperto del progetto, con
lo stato di ciascuna voce, sta in `.codex/PROJECT_CONTEXT.md` § «Aperto — Media priorità»;
la storia delle voci chiuse in [migliorie generali BE/FE](work-done/migliorie-generali-BE-FE-da-test-valutazione.md) §9.

| Cosa | Stato |
| --- | --- |
| **Rotazione dei segreti** rimasti nella storia del repo (`backend/.env`, e la chiave che era commentata in `settings.py`) | non urgente, decisione di Tid del 2026-09-26: il repo è privato. Con le chiavi di cifratura separate, la `SECRET_KEY` si può ruotare dopo la migrazione dei dati cifrati, sezione [Le chiavi dei dati cifrati](#le-chiavi-dei-dati-cifrati) |
| Dependabot (nessun `.github/dependabot.yml` nel repo) | da decidere |
| Nessun filtro che oscuri i dati sensibili nei log | proposto, senza brief |
| `djangorestframework-simplejwt` senza un manutentore certo | in PROJECT_CONTEXT § «Aperto — Media priorità» |
