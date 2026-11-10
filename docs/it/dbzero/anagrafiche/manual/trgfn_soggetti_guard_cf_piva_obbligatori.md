## 📘 Documentazione Funzione – `anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
**Tabelle anagrafiche / config:**
>
[`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti)
> [`config.tipi_soggetto_dettaglio`](/dbzero/config/tabelle/tipi_soggetto_dettaglio)
>
**Funzioni / trigger correlati:**
>
[`anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch) — valida il **formato** di CF/P.IVA
> [`anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile`](/dbzero/anagrafiche/manual/trgfn_soggetti_guard_id_fiscale_immutabile) — impedisce il **cambio** di CF/P.IVA già scritti
> [`script.fn_validate_cf_piva_it`](/dbzero/script/funzioni/fn_validate_cf_piva_it) — validazione formato italiano
> [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale
(latest review 28-02-26)
La funzione **`anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori`** e una **trigger function di tipo "guard"** che:

* controlla gli **inserimenti / aggiornamenti** sulla tabella
  [`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti),
* verificando che i campi **codice_fiscale** e **partita_iva** siano valorizzati
  quando il `tipo_soggetto_dettaglio` lo richiede.

Questa funzione complementa la validazione di **formato** effettuata da
[`trgfn_soggetti_valida_cf_piva_dispatch`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch):

| Funzione                                    | Cosa valida    |
| ------------------------------------------- | -------------- |
| `trgfn_soggetti_valida_cf_piva_dispatch`    | **Formato** (struttura alfanumerica, check digit) |
| `trgfn_soggetti_guard_cf_piva_obbligatori`  | **Presenza** (campo non NULL quando obbligatorio) |
| [`trgfn_soggetti_guard_id_fiscale_immutabile`](/dbzero/anagrafiche/manual/trgfn_soggetti_guard_id_fiscale_immutabile) | **Cambio** (un valore già scritto non si cambia né si svuota, salvo il SUPER_ADMIN; dal 2026-11-09) |

I concern sono separati → trigger separati. La presenza la controlla questo guard, il cambio di un valore già scritto il guard sull'immutabilità.

---

### Collegamenti principali

* **Tabelle coinvolte direttamente:**

  * [`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti) — tabella su cui e definito il trigger.
  * [`config.tipi_soggetto_dettaglio`](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — contiene i flag `piva_obbligatoria` e `cf_obbligatorio`.

* **Funzioni di supporto:**

  * [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error) — centralizza logging + raise exception.

---

### 🧾 Firma della funzione e trigger associato

**Funzione (schema `anagrafiche`):**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori()
RETURNS trigger
LANGUAGE plpgsql;
```

**Trigger su `anagrafiche.soggetti`:**

```sql
CREATE OR REPLACE TRIGGER trg_soggetti_a10_guard_cf_piva_obbligatori_ins_upd
    BEFORE INSERT OR UPDATE OF tipo_soggetto_dettaglio_id, partita_iva, codice_fiscale
    ON anagrafiche.soggetti
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori();
```

📌 *Il trigger scatta:*

* *sempre in INSERT*
* *in UPDATE se cambia `tipo_soggetto_dettaglio_id`, `partita_iva` o `codice_fiscale`*

---

### Contesto e parametri logici

Essendo una trigger function, non ha parametri espliciti. Utilizza:

| Elemento                             | Descrizione                                                       |
| ------------------------------------ | ----------------------------------------------------------------- |
| `NEW.tipo_soggetto_dettaglio_id`     | Tipo dettaglio del soggetto (FK verso `config.tipi_soggetto_dettaglio`) |
| `NEW.partita_iva`                    | Partita IVA del soggetto (puo essere NULL)                        |
| `NEW.codice_fiscale`                 | Codice Fiscale del soggetto (puo essere NULL)                     |

---

### Logica di funzionamento (semplificata)

1️⃣ Se `NEW.tipo_soggetto_dettaglio_id IS NULL` → **skip** → `RETURN NEW`.
Non e possibile validare senza un tipo dettaglio configurato.

2️⃣ Lookup su `config.tipi_soggetto_dettaglio`:
recupera `piva_obbligatoria` e `cf_obbligatorio` per il tipo dettaglio del soggetto.

3️⃣ Se `piva_obbligatoria = true AND NEW.partita_iva IS NULL`:
→ errore **`E_PIVA_OBBLIGATORIA`** — la P.IVA e richiesta ma non valorizzata.

4️⃣ Se `cf_obbligatorio = true AND NEW.codice_fiscale IS NULL`:
→ errore **`E_CF_OBBLIGATORIO`** — il CF e richiesto ma non valorizzato.

5️⃣ Se entrambi i controlli passano → `RETURN NEW`.

---

### Esempi specifici

#### ✔ Privato (PR) con CF, senza P.IVA

* PR: `cf_obbligatorio = true`, `piva_obbligatoria = false`
* CF valorizzato → controllo CF **OK**
* P.IVA NULL → non obbligatoria → **OK**

#### ❌ Privato (PR) senza CF

* PR: `cf_obbligatorio = true`
* CF NULL → **BLOCCATO** (E_CF_OBBLIGATORIO)

#### ✔ Ditta Individuale (DI) con CF e P.IVA

* DI: `cf_obbligatorio = true`, `piva_obbligatoria = true`
* Entrambi valorizzati → **OK**

#### ❌ Ditta Individuale (DI) senza P.IVA

* DI: `piva_obbligatoria = true`
* P.IVA NULL → **BLOCCATO** (E_PIVA_OBBLIGATORIA)

#### ❌ Societa di Capitali (SC) senza P.IVA

* SC: `piva_obbligatoria = true`
* P.IVA NULL → **BLOCCATO** (E_PIVA_OBBLIGATORIA)

#### ✔ Soggetto con tipo_soggetto_dettaglio_id NULL

* Nessun tipo configurato → skip validazione → **OK**
* Utile per soggetti in fase di creazione o migrazione.

---

### ⚠️ Note Tecniche

* La funzione e **coerente con il pattern "guard"** usato in Zero ERP (fase `_a10_`, fail-fast).
* Non modifica i dati, si limita a validarli.
* La validazione di **presenza** (questa funzione) e separata dalla validazione di **formato** (`trgfn_soggetti_valida_cf_piva_dispatch`). Entrambi i trigger sono attivi sulla stessa tabella.
* I flag `piva_obbligatoria` e `cf_obbligatorio` sono su `config.tipi_soggetto_dettaglio`, non su `config.tipi_ruoli`, perche l'obbligo dipende dalla **natura del soggetto**, non dal ruolo.
* CHECK constraints su `tipi_soggetto_dettaglio` impediscono combinazioni incoerenti:
  * `piva_obbligatoria = true` richiede `formato_piva <> 'NON_APPLICABILE'`
  * `cf_obbligatorio = true` richiede `formato_cf <> 'NON_APPLICABILE'`
* In caso di errore, il messaggio e gestito da `script.fn_log_and_raise_error` che garantisce logging centralizzato.

---

### 🏁 Best Practice

✔ Configurare `piva_obbligatoria` e `cf_obbligatorio` su `config.tipi_soggetto_dettaglio` per ogni tipo soggetto.
✔ Assicurarsi che i formati siano coerenti (non impostare obbligo se formato = `NON_APPLICABILE`).
✔ Nei test (pgTAP) validare:

* Inserimento con dati fiscali presenti quando obbligatori → OK
* Inserimento senza CF quando obbligatorio → errore
* Inserimento senza P.IVA quando obbligatoria → errore
* Inserimento con `tipo_soggetto_dettaglio_id = NULL` → skip (nessun errore)

---

### Configurazione attuale

| Tipo Soggetto      | codice_interno | piva_obbligatoria | cf_obbligatorio |
| ------------------- | -------------- | ----------------- | --------------- |
| Privato             | PR             | false             | true            |
| Ditta Individuale   | DI             | true              | true            |
| Societa di Capitali | SC             | true              | true            |
| Societa di Persone  | SP             | true              | true            |
| Ente Non Commerc.   | ENC            | true              | true            |

---

📅 *Aggiornato: 28/02/2026*

{% include-markdown "signature-core.md" %}
