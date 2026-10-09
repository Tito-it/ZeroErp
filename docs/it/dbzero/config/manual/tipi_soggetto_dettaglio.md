# 📚 Tabella `config.tipi_soggetto_dettaglio`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:   
>
[config.tipi_soggetto](/dbzero/config/tabelle/tipi_soggetto)      
> [config.stati](/dbzero/config/tabelle/stati)      
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
---

La tabella **`config.tipi_soggetto_dettaglio`** definisce le **tipologie dettagliate** di soggetto (persone fisiche, giuridiche, enti, ecc.) in base al **paese** di appartenenza, specificando i **formati** validi per Codice Fiscale e Partita IVA.

---
### 🎯 Scopo Principale
* **Gestione Internazionale**
  Permette di adattare la validazione di CF/P.IVA alle regole di ciascuno Stato (`stato_iso2`).
* **Estendibilità**
  Il collegamento a `config.tipi_soggetto` garantisce macro-categorie estensibili (Fisico, Giuridico, Ente, …).
* **Controllo Applicativo**
  Centralizza il formato di CF/P.IVA, evitando logiche duplicate nel backend.

---

### Collegamenti

* **FK →** `config.tipi_soggetto(tipo_soggetto_id)`
  Definisce la macro-tipologia.
* **FK →** `config.stati(codice_iso2)`
  Specifica il Paese di riferimento per il formato.
* **Estensione su** `anagrafiche.soggetti.tipo_soggetto_dettaglio_id`
  Associa ogni soggetto al dettaglio corretto, eliminata la colonna `tipo_soggetto`, è stato aggiunto in `anagrafiche.soggetti` la colonna `tipo_soggetto_dettaglio_id`.


---

### Vantaggi Operativi

* Evita hard‑coding dei formati di CF/P.IVA nel codice applicativo.
* Facilita l’aggiunta di nuovi paesi o categorie nominative.
* Garantisce coerenza tra DB e validazione backend.

---






# 📘 Integrazione – Tabella `config.tipi_soggetto_dettaglio`

*(Aggiornamento del 2025-12-03)*

Questa integrazione documenta le modifiche introdotte oggi sulla tabella **`config.tipi_soggetto_dettaglio`**, in particolare riguardo i formati CF/P.IVA e la coerenza con la policy sui dati societari.

---

## 🆕 Nuovi Vincoli Introdotti

### Formati ammessi per CF e P.IVA

Le colonne:

* `formato_cf`
* `formato_piva`

non possono più essere `NULL` e devono rispettare uno dei seguenti formati:

* `NON_APPLICABILE`
* `NUM_<N>`     → solo cifre, lunghezza N
* `ALFA_<N>`    → solo lettere A–Z, lunghezza N
* `ALFANUM_<N>` → lettere + cifre, lunghezza N

Esempi validi:

```
NUM_11
ALFANUM_16
ALFA_10
NON_APPLICABILE
```

Tali vincoli garantiscono che i pattern siano omogenei e validabili in modo generico.

---

## Coerenza con `dati_societari_policy`

È stato introdotto il vincolo:

* Se `formato_piva = 'NON_APPLICABILE'` → `dati_societari_policy = 'NONE'`
* Se `formato_piva <> 'NON_APPLICABILE'` → `dati_societari_policy ∈ ('OPTIONAL', 'REQUIRED')`

🔍 **Significato funzionale:**

* Se un tipo soggetto non prevede la Partita IVA, allora i dati societari non possono essere richiesti.
* Se il tipo soggetto prevede una P.IVA (qualsiasi formato), allora i dati societari devono essere almeno opzionali.

---

## `sesso_policy`: quando il sesso serve (dal 2026-10-09)

Ogni natura dice se il sesso del soggetto e' **obbligatorio**, **facoltativo** o
**vietato**. Lo legge il guard `anagrafiche.trgfn_soggetti_guard_sesso_policy`
(vedi la tabella [soggetti](/dbzero/anagrafiche/manual/soggetti)).

| Natura | `sesso_policy` |
| --- | --- |
| PR, privato | `REQUIRED` |
| DI, ditta individuale | `OPTIONAL` |
| SP, SC, ENC | `NONE` |

Il CHECK `chk_tipi_soggetto_dettaglio_sesso_policy_natura` impedisce alla
configurazione di dire il falso: **solo una persona fisica** (natura base `PF`)
puo' avere una policy diversa da `NONE`, e una persona fisica non puo' averla
`NONE`.

**Un solo tipo per le due policy.** `dati_societari_policy` e `sesso_policy`
rispondono alla stessa domanda — «quanto e' richiesto questo dato, per questa
natura?» — e usano lo stesso tipo, `config.presenza_policy_enum`
(`NONE` / `OPTIONAL` / `REQUIRED`). Fino al 2026-10-09 i dati societari avevano un
tipo loro, `config.dati_societari_policy_enum`, con gli stessi valori: e' stato
ritirato quando la domanda si e' presentata la seconda volta.
Brief: brief-db-sesso-senza-default.

---

## Implicazioni funzionali

### ✔ Validazione CF/P.IVA

La funzione:

* `script.fn_validate_cf_piva_it()`

ora lavora utilizzando:

* `formato_cf <> 'NON_APPLICABILE'`
* `formato_piva <> 'NON_APPLICABILE'`

come discriminante per l'attivazione della validazione.

### ✔ Controllo Paese

La validazione rimane agganciata al dispatcher:

* `anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch`

che applica la validazione solo se `stato_iso2 = 'IT'`.

---

## Benefici Architetturali

* Eliminazione di valori improvvisati nei campi CF/P.IVA.
* Base solida per l'internazionalizzazione futura.
* Maggiore robustezza nelle validazioni fiscali.
* Pulizia semantica tra tipi soggetto, dettagli fiscali e contesto nazionale.

---

## 5️⃣ Estratto dei Vincoli (per completezza)

```sql
CHECK (
  formato_cf = 'NON_APPLICABILE' OR
  formato_cf ~ '^(NUM|ALFA|ALFANUM)_[0-9]{1,2}$'
);

CHECK (
  formato_piva = 'NON_APPLICABILE' OR
  formato_piva ~ '^(NUM|ALFA|ALFANUM)_[0-9]{1,2}$'
);

CHECK (
  (formato_piva = 'NON_APPLICABILE' AND dati_societari_policy = 'NONE') OR
  (formato_piva <> 'NON_APPLICABILE' AND dati_societari_policy IN ('OPTIONAL','REQUIRED'))
);
```

---

## Nota finale

Queste modifiche rappresentano un consolidamento fondamentale per la gestione internazionale dei tipi di soggetto, rendendo il modello più controllato e predittivo.

---

# 📘 Integrazione – Obbligatorieta CF/P.IVA per tipo soggetto

*(Aggiornamento del 2026-02-28)*

Questa integrazione documenta le nuove colonne **`piva_obbligatoria`** e **`cf_obbligatorio`** aggiunte alla tabella `config.tipi_soggetto_dettaglio`.

---

## 🆕 Nuove Colonne

| Colonna             | Tipo    | Default | Descrizione                                                |
| ------------------- | ------- | ------- | ---------------------------------------------------------- |
| `piva_obbligatoria` | boolean | false   | Se `true`, il soggetto deve avere `partita_iva` valorizzata |
| `cf_obbligatorio`   | boolean | false   | Se `true`, il soggetto deve avere `codice_fiscale` valorizzato |

### Vincoli di coerenza

Le nuove colonne hanno CHECK constraints che impediscono combinazioni incoerenti:

```sql
-- Non si puo rendere obbligatoria la P.IVA se il formato e NON_APPLICABILE
CHECK (piva_obbligatoria = false OR formato_piva <> 'NON_APPLICABILE')

-- Non si puo rendere obbligatorio il CF se il formato e NON_APPLICABILE
CHECK (cf_obbligatorio = false OR formato_cf <> 'NON_APPLICABILE')
```

---

## Configurazione attuale

| Tipo Soggetto       | codice_interno | piva_obbligatoria | cf_obbligatorio |
| ------------------- | -------------- | ----------------- | --------------- |
| Privato             | PR             | false             | true            |
| Ditta Individuale   | DI             | true              | true            |
| Societa di Capitali | SC             | true              | true            |
| Societa di Persone  | SP             | true              | true            |
| Ente Non Commerc.   | ENC            | true              | true            |

🔍 **Significato funzionale:**

* Un **Privato** deve avere il Codice Fiscale ma non necessariamente la P.IVA.
* Tutti gli altri tipi (DI, SC, SP, ENC) richiedono **entrambi** i dati fiscali.

---

## Trigger di enforcement

La validazione e applicata dal trigger guard:

* [`anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cf_piva_obbligatori)

Scatta in **BEFORE INSERT/UPDATE** su `anagrafiche.soggetti` quando cambiano:
`tipo_soggetto_dettaglio_id`, `partita_iva` o `codice_fiscale`.

Messaggi di errore:

* `E_PIVA_OBBLIGATORIA` (id 202) — P.IVA mancante quando obbligatoria
* `E_CF_OBBLIGATORIO` (id 203) — CF mancante quando obbligatorio

---

## Relazione con la validazione di formato

Questa feature e **complementare** alla validazione di formato esistente:

| Livello      | Funzione                                      | Cosa controlla                    |
| ------------ | --------------------------------------------- | --------------------------------- |
| **Presenza** | `trgfn_soggetti_guard_cf_piva_obbligatori`    | Campo non NULL quando obbligatorio |
| **Formato**  | `trgfn_soggetti_valida_cf_piva_dispatch`       | Struttura corretta (lunghezza, check digit) |

L'ordine di esecuzione e: prima il guard di presenza (fase `_a10_`), poi la validazione di formato.

---

📅 *Aggiornato: 28/02/2026*
