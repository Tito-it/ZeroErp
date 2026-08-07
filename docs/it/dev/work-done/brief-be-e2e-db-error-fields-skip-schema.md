# Brief BE — i 3 e2e di `test_db_error_fields` si appoggiano a una coincidenza

**Chi scrive:** DB (`dev/db-tid`), 2026-08-05.
**Cosa chiede:** un guard di `SkipTest` nel `setUpClass` e due righe di docstring.
**Perimetro:** `backend/apps/core/tests/services/test_db_error_fields.py`, nient'altro.
**Origine:** [brief-db-codice-errore-strutturato](../work-done/brief-db-codice-errore-strutturato.md) §6.

> ✅ **Non c'è niente di rotto.** Gli 11 test sono verdi, i 3 end-to-end girano
> davvero contro un database vero e la giuntura DB → psycopg è verificata. Questo
> brief riguarda **perché** funzionano, che non è il motivo che sembra.

---

## 1. Il meccanismo, che non è quello che ci si aspetta

Nell'output del run compare questa riga:

```
Skipping setup of unused database(s): default, system_fatturazione.
```

Django crea il database di test usa-e-getta **solo se almeno un test dichiara di
averne bisogno** — `django.test.TestCase`, `TransactionTestCase`, o un attributo
`databases = [...]`. Censito su `backend/apps`:

| Base class | Occorrenze |
|---|---:|
| `unittest.TestCase` | 114 |
| `django.test.SimpleTestCase` | 86 |
| `django.test.TestCase` / `TransactionTestCase` | **0** |

Zero. È la conseguenza diretta della regola di `AGENTS.md` — *«i test devono
funzionare in CI senza dipendere da un DB reale accessibile»* — ed è una buona
regola.

Effetto collaterale: **il runner non prepara nessun database di test**, quindi
`django.db.connection` resta puntata a quella **configurata**, cioè al database
di sviluppo con lo schema Liquibase completo. Ed è esattamente per questo che i
3 e2e trovano `script.fn_log_and_raise_error` e passano.

⚠️ Se invece il database di test venisse creato, sarebbe **vuoto delle nostre
cose**: Django ci applica solo le proprie migration, non Liquibase. Le funzioni
PL/pgSQL non ci sarebbero.

---

## 2. Quando si romperà, e su chi cadrà

Basta **un** test, in una qualunque app, che dichiari un database. Da quel
momento il runner ne crea uno per **tutta la suite**, e i 3 e2e si ritrovano a
interrogare un database dove le nostre funzioni non esistono:

```
ERRORE: la funzione script.fn_log_and_raise_error(...) non esiste
```

Il `setUpClass` attuale non lo intercetta: controlla che il database sia
**raggiungibile** (`connection.ensure_connection()`), non che ci sia lo
**schema**. Quindi non salta — entra, esegue, e fallisce.

Il punto non è la rottura in sé, è **su chi cade**: su chi ha scritto quel
`TestCase`, in una PR che con il codice errore strutturato non c'entra nulla, con
un messaggio che non gli dice niente. Ed è la stessa forma di difetto che il
brief principale racconta da tre giorni — **qualcosa che funziona per una ragione
che nessuno ha progettato**, come il codice errore che arrivava perché il driver
allega al testo lo statement chiamante.

---

## 3. Cosa chiediamo

### 3.1 Il guard, nel `setUpClass` dopo `ensure_connection()`

Non serve a farli girare (girano): serve a far dire **cos'è successo** il giorno
in cui non gireranno più.

```python
        # ⚠️ Raggiungibile != provvisto. Se il runner ha creato il database di
        # test usa-e-getta (accade appena UN test della suite dichiara un
        # database), quel database ha solo le migration Django: le funzioni
        # PL/pgSQL non ci sono. Senza questo controllo il test non salta —
        # fallisce con «la funzione non esiste», addosso a chi ha scritto quel
        # TestCase e in una PR che non c'entra.
        with connection.cursor() as cur:
            cur.execute(
                "SELECT to_regprocedure('script.fn_log_and_raise_error"
                "(text,text,text,jsonb,uuid,text[])') IS NOT NULL"
            )
            row = cur.fetchone()
        assert row is not None
        if not row[0]:
            raise unittest.SkipTest(
                "schema Liquibase assente nel database dei test: il runner ne ha "
                "creato uno usa-e-getta (qualche test dichiara un database). "
                "Vedi brief-be-e2e-db-error-fields-skip-schema.md"
            )
```

### 3.2 Due righe nel docstring della classe

Il docstring oggi spiega benissimo **perché sono opt-in** (il probe a import-time
che faceva 469 rossi altrove: ottima nota, va tenuta). Manca il **perché
funzionano**: che dipendono dal fatto che nessun test dichiari un database.

### 3.3 Nota a margine — non aggiungere test che scrivono, in quel file

Poiché la connessione è quella vera, un test che **scrive** scriverebbe sul
database di sviluppo. I tre attuali no: provocano solo un errore dentro un
`transaction.atomic()` che viene annullato. Vale la pena scriverlo lì accanto,
perché il prossimo che aggiunge un caso in quel file non ha modo di saperlo.

---

## 4. Cosa abbiamo già fatto noi

| | |
|---|---|
| **CI** | `ZEROERP_TEST_DB_E2E: "1"` aggiunto allo step «Django tests» di `ci-validate.yaml`. Là il database c'è ed è appena stato provvisto da Liquibase + `manage.py migrate`, quindi i 3 e2e **girano a ogni PR** invece che quando qualcuno si ricorda di lanciarli. La giuntura DB → psycopg passa così da «verificata a mano» a «presidiata». |
| **AGENTS.md** | la dipendenza implicita è scritta accanto alla regola sui test Django, così chi sta per aggiungere un `django.test.TestCase` trova l'avviso **prima**, non dopo. |

Con il guard del §3.1 il giro si chiude: in CI girano, e se un giorno non potranno
più girare lo diranno con una frase leggibile invece di un errore criptico.

---

## 5. ✅ Fatto — BE, 2026-08-05

Tutto quanto chiesto, in `test_db_error_fields.py` e in nessun altro file.

| § | Cosa | |
|---|---|---|
| 3.1 | guard di schema in `setUpClass`, dopo `ensure_connection()` | `to_regprocedure(...) IS NOT NULL` → `SkipTest` col messaggio che rimanda a questo brief |
| 3.2 | docstring: **perché** funzionano | la dipendenza da «nessun test dichiara un database» è scritta per esteso, accanto alla nota sul probe a import-time che già c'era |
| 3.3 | nota «niente test che scrivono» | scritta nel docstring, col perché: la connessione è quella vera |

Aggiunto anche il rimando al fatto che in CI girano a ogni PR — chi legge il
docstring trova sia come lanciarli a mano sia dove girano da soli.

### Il guard è stato provato, non solo scritto

Un guard che non si è mai visto scattare è una supposizione. Simulato il caso
puntando la connessione a un database esistente ma senza schema
(`DB_NAME=postgres`, con l'opt-in acceso):

```
setUpClass (…DbErrorFieldsEndToEndTests) ... skipped 'schema Liquibase assente
nel database dei test: il runner ne ha creato uno usa-e-getta (qualche test
dichiara un database). Vedi brief-be-e2e-db-error-fields-skip-schema.md'
```

Salta con la frase giusta invece di fallire con «la funzione non esiste» — che
era esattamente il punto del §2.

### La premessa, ri-misurata

Il §1 dice «zero test dichiarano un database». Verificato in modo che regga:
non con una grep su `TestCase` — `class X(TestCase)` non dice **quale**
`TestCase`, e contando così ne risultavano 353 — ma sugli **import**. In
`backend/apps`, `from django.test import` porta solo `SimpleTestCase` (86),
`Client` (53), `override_settings` (9), `RequestFactory` (5): **mai** `TestCase`
né `TransactionTestCase`, e **zero** `databases = [...]`. La premessa regge, e i
numeri del brief tornano.

| Esito | |
|---|---|
| opt-in acceso | 11/11 verdi, i 3 e2e girano davvero |
| default | 8 verdi + classe skipped |
| schema assente (simulato) | classe skipped col messaggio parlante |
| suite intera | 3575 verdi |
