## Documentazione Concettuale -- Funzione `script.fn_get_entita_ruolo_detail`

> Vedi anche
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> * [anagrafiche.vettori](/dbzero/anagrafiche/tabelle/vettori)
> * [anagrafiche.gestori](/dbzero/anagrafiche/tabelle/gestori)
> * [anagrafiche.bank_branches](/dbzero/anagrafiche/tabelle/bank_branches)
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> * [config.utilities](/dbzero/config/tabelle/utilities)
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
>
> Funzione chiamante:
>
> * [script.fn_get_search_detail](/dbzero/script/funzioni/fn_get_search_detail)

La funzione **`script.fn_get_entita_ruolo_detail`** restituisce in JSONB i dati specifici dell'entita' legata a un ruolo. Ogni tipo ruolo ha la propria tabella anagrafica (clienti, fornitori, emittenti_fiscali, ecc.) e la funzione effettua il dispatch in base al `codice_interno` del tipo ruolo.

---

### 🎯 Scopo Principale

* **Dati entita' per ruolo**: dato un `soggetto_ruolo_id`, recupera automaticamente il tipo ruolo e interroga la tabella specifica per quel ruolo.

* **Filtro opzionale per utility**: il parametro `p_utility_id` filtra le righe cliente per una utility specifica. Per tutti gli altri ruoli viene ignorato.

* **Output JSONB uniforme**: tutti i rami restituiscono `{ tipo_ruolo: "...", righe: [...] }` con un array di oggetti contenenti `entita_id` e campi specifici per ruolo.

* **Ampliabile**: per aggiungere un nuovo tipo ruolo con tabella dedicata, basta aggiungere un ramo `WHEN` al `CASE`.

---

### Parametri di Input

| Nome                  | Tipo      | Obbligatorio | Default | Descrizione                                                     |
| --------------------- | --------- | ------------ | ------- | --------------------------------------------------------------- |
| `p_soggetto_ruolo_id` | `BIGINT`  | Si           | —       | ID del record `anagrafiche.soggetti_ruoli`                      |
| `p_utility_id`        | `INTEGER` | No           | `NULL`  | Filtra righe CL per utility specifica; ignorato per altri ruoli |

**Guard**: `p_soggetto_ruolo_id` validato tramite `script.fn_log_and_raise_error` con codice `E_PARAMETRO_INVALIDO`. Se il `soggetto_ruolo_id` non esiste in `anagrafiche.soggetti_ruoli`, viene lanciato `E_GENERICO`.

---

### Valore di Ritorno

JSONB con struttura fissa:

```json
{
  "tipo_ruolo": "CL",
  "righe": [ ... ]
}
```

Il contenuto di `righe` varia per tipo ruolo:

#### CL (Cliente)

N righe per soggetto_ruolo (una per istanza_utility).

| Campo                    | Tipo      | Fonte                                    |
| ------------------------ | --------- | ---------------------------------------- |
| `entita_id`              | `BIGINT`  | `anagrafiche.clienti.id`                 |
| `billing_account_id`     | `BIGINT`  | `anagrafiche.clienti.billing_account_id` |
| `billing_account_codice` | `VARCHAR` | `anagrafiche.billing_account.codice`     |
| `utility_id`             | `INTEGER` | `anagrafiche.clienti.utility_id`         |
| `stato_cliente_id`       | `INTEGER` | `anagrafiche.clienti.stato_cliente_id`   |
| `stato_codice`           | `CHAR`    | `config.stati_cliente.codice_interno`    |
| `stato_descrizione`      | `CHAR`    | `config.stati_cliente.descrizione_breve` |
| `data_attivazione`       | `DATE`    | `anagrafiche.clienti.data_attivazione`   |
| `data_sospensione`       | `DATE`    | `anagrafiche.clienti.data_sospensione`   |
| `data_riattivazione`     | `DATE`    | `anagrafiche.clienti.data_riattivazione` |
| `data_chiusura`          | `DATE`    | `anagrafiche.clienti.data_chiusura`      |

#### FO (Fornitore)

1 riga per soggetto_ruolo (UQ).

| Campo       | Tipo      | Fonte                          |
| ----------- | --------- | ------------------------------ |
| `entita_id` | `BIGINT`  | `anagrafiche.fornitori.id`     |
| `codice`    | `VARCHAR` | `anagrafiche.fornitori.codice` |
| `attivo`    | `BOOLEAN` | `anagrafiche.fornitori.attivo` |

#### EF (Emittente Fiscale)

| Campo         | Tipo      | Fonte                                       |
| ------------- | --------- | ------------------------------------------- |
| `entita_id`   | `BIGINT`  | `anagrafiche.emittenti_fiscali.id`          |
| `codice`      | `VARCHAR` | `anagrafiche.emittenti_fiscali.codice`      |
| `descrizione` | `VARCHAR` | `anagrafiche.emittenti_fiscali.descrizione` |
| `attivo`      | `BOOLEAN` | `anagrafiche.emittenti_fiscali.attivo`      |

#### VT (Vettore)

| Campo         | Tipo      | Fonte                             |
| ------------- | --------- | --------------------------------- |
| `entita_id`   | `BIGINT`  | `anagrafiche.vettori.id`          |
| `codice`      | `VARCHAR` | `anagrafiche.vettori.codice`      |
| `descrizione` | `VARCHAR` | `anagrafiche.vettori.descrizione` |
| `attivo`      | `BOOLEAN` | `anagrafiche.vettori.attivo`      |

#### GE (Gestore)

| Campo         | Tipo     | Fonte                             |
| ------------- | -------- | --------------------------------- |
| `entita_id`   | `BIGINT` | `anagrafiche.gestori.id`          |
| `descrizione` | `CHAR`   | `anagrafiche.gestori.descrizione` |

#### BANK_B (Istituto di Credito)

N filiali per soggetto_ruolo.

| Campo         | Tipo      | Fonte                                   |
| ------------- | --------- | --------------------------------------- |
| `entita_id`   | `BIGINT`  | `anagrafiche.bank_branches.id`          |
| `bank_code`   | `VARCHAR` | `anagrafiche.bank_branches.bank_code`   |
| `branch_code` | `VARCHAR` | `anagrafiche.bank_branches.branch_code` |
| `bic_swift`   | `VARCHAR` | `anagrafiche.bank_branches.bic_swift`   |
| `name`        | `VARCHAR` | `anagrafiche.bank_branches.name`        |
| `attivo`      | `BOOLEAN` | `anagrafiche.bank_branches.attivo`      |

#### RIS_UMANA (Risorsa Umana)

| Campo        | Tipo      | Fonte                                  |
| ------------ | --------- | -------------------------------------- |
| `entita_id`  | `BIGINT`  | `anagrafiche.risorse_umane.id`         |
| `attivo`     | `BOOLEAN` | `anagrafiche.risorse_umane.attivo`     |
| `valido_dal` | `DATE`    | `anagrafiche.risorse_umane.valido_dal` |
| `valido_al`  | `DATE`    | `anagrafiche.risorse_umane.valido_al`  |

#### ELSE (VE, DI, RE, PSP e altri senza tabella)

| Campo               | Tipo     | Fonte                             |
| ------------------- | -------- | --------------------------------- |
| `soggetto_ruolo_id` | `BIGINT` | `anagrafiche.soggetti_ruoli.id`   |
| `meta`              | `JSONB`  | `anagrafiche.soggetti_ruoli.meta` |

---

### Esempi di Utilizzo

```sql
-- 1) Dati entita' per un cliente
SELECT script.fn_get_entita_ruolo_detail(123);

-- 2) Dati entita' cliente filtrati per utility
SELECT script.fn_get_entita_ruolo_detail(123, 5);

-- 3) Uso in fn_get_search_detail (ramo ELSE)
SELECT script.fn_get_entita_ruolo_detail(sr.id, p_utility_id)
FROM anagrafiche.soggetti_ruoli sr
WHERE sr.soggetto_id = '...'::uuid;
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE` + `PARALLEL SAFE` — non modifica dati.
* **Linguaggio**: PL/pgSQL
* **Tipi parametri**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.
* **Error handling**: guard tramite `script.fn_log_and_raise_error` (log persistente + raise).
* **Dispatch**: `CASE` su `codice_interno` (immutabile, protetto da `trgfn_lock_columns`).
* **Ampliabilita'**: aggiungere un ramo `WHEN` al `CASE` per supportare nuovi tipi ruolo con tabella dedicata.

---
