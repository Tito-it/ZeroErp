## Documentazione Concettuale -- Funzione `script.fn_get_soggetto_dati_by_ruolo`

> Vedi anche
>
> Approfondimento viste modello:
>
> * [anagrafiche.vw_soggetti_ruoli_dettaglio](/dbzero/anagrafiche/views/vw_soggetti_ruoli_dettaglio)
> * [anagrafiche.vw_dati_societari](/dbzero/anagrafiche/views/vw_dati_societari)
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> * [config.tipi_soggetto](/dbzero/config/tabelle/tipi_soggetto)
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)
> * [config.titoli_cortesia](/dbzero/config/tabelle/titoli_cortesia)
> * [config.forme_giuridiche](/dbzero/config/tabelle/forme_giuridiche)
> * [config.province](/dbzero/config/tabelle/province)
>
> Funzione consumatrice:
>
> * [script.fn_get_user_profile](/dbzero/script/funzioni/fn_get_user_profile)

La funzione **`script.fn_get_soggetto_dati_by_ruolo(p_soggetto_ruolo_id BIGINT)`** restituisce un record tabellare con i **dati anagrafici fondamentali** di un soggetto a partire dal suo `soggetto_ruolo_id`, includendo tipo ruolo, tipo soggetto, titolo cortesia e, se presenti, i **dati societari completi**.

E' progettata come **punto di accesso generico** per ottenere una fotografia completa di un soggetto in un determinato ruolo, con tutti gli ID delle tabelle collegate inclusi per consentire navigazione e lookup dal frontend.

---

### Scopo Principale

* **Aggregazione trasversale**: combina in un unico record le informazioni che altrimenti richiederebbero join multipli su 8 tabelle (soggetti_ruoli, soggetti, tipi_ruoli, tipi_soggetto_dettaglio, tipi_soggetto, titoli_cortesia, dati_societari, forme_giuridiche, province).

* **Tutti gli ID inclusi**: ogni FK del soggetto e' esposta (`stato_id`, `comune_id`, `titolo_cortesia_id`, `tipo_soggetto_dettaglio_id`, `default_contatto_id`, `dati_societari_id`, `forma_giuridica_id`, `id_prov_iscri_rea`) per consentire lookup e navigazione dal frontend senza query aggiuntive.

* **Descrizioni risolte**: tipo ruolo (codice, codice_interno, descrizione), tipo soggetto (id, descrizione, codice_interno), titolo cortesia (descrizione, descrizione_breve), forma giuridica (codice, descrizione), provincia REA (sigla).

* **Dati societari condizionali**: il flag `has_dati_societari` indica se il soggetto ha un record in `anagrafiche.dati_societari`; i campi societari sono `NULL` se assenti.

* **Base per funzioni composite**: utilizzata da `fn_get_user_profile` per i blocchi soggetto ed emittente, garantendo un output uniforme.

---

### Parametri di Input

| Nome                   | Tipo     | Obbligatorio | Descrizione                                           |
| ---------------------- | -------- | ------------ | ----------------------------------------------------- |
| `p_soggetto_ruolo_id`  | `BIGINT` | Si           | ID del record `anagrafiche.soggetti_ruoli`. Deve essere > 0. |

**Guard**: se `NULL` o `<= 0`, la funzione lancia `invalid_parameter_value`.

---

### Valore di Ritorno

La funzione restituisce una **tabella** (`RETURNS TABLE`) con le seguenti colonne raggruppate per sezione:

#### Identita' ruolo

| Colonna                     | Tipo      | Fonte                              |
| --------------------------- | --------- | ---------------------------------- |
| `soggetto_ruolo_id`         | `BIGINT`  | `soggetti_ruoli.id` (= input)      |
| `soggetto_id`               | `UUID`    | `soggetti.id`                      |
| `tipo_ruolo_id`             | `INTEGER` | `soggetti_ruoli.tipo_ruolo_id`     |
| `tipo_ruolo_codice`         | `VARCHAR` | `config.tipi_ruoli.codice`         |
| `tipo_ruolo_codice_interno` | `VARCHAR` | `config.tipi_ruoli.codice_interno` |
| `tipo_ruolo_descrizione`    | `VARCHAR` | `config.tipi_ruoli.descrizione`    |

#### Dati anagrafici soggetto

| Colonna                      | Tipo      | Fonte                              |
| ---------------------------- | --------- | ---------------------------------- |
| `soggetto_codice`            | `TEXT`    | `soggetti.codice`                  |
| `ragione_sociale`            | `TEXT`    | `soggetti.ragione_sociale`         |
| `ragione_sociale_completa`   | `TEXT`    | `soggetti.ragione_sociale_completa` (generato) |
| `cognome`                    | `TEXT`    | `soggetti.cognome`                 |
| `nome`                       | `TEXT`    | `soggetti.nome`                    |
| `codice_fiscale`             | `TEXT`    | `soggetti.codice_fiscale`          |
| `partita_iva`                | `TEXT`    | `soggetti.partita_iva`             |
| `id_fiscale_univoco_cf_piva` | `TEXT`    | `soggetti.id_fiscale_univoco_cf_piva` (generato) |
| `sesso`                      | `CHAR(1)` | `soggetti.sesso`                  |
| `data_nascita`               | `DATE`    | `soggetti.data_nascita`           |
| `soggetto_attivo`            | `BOOLEAN` | `soggetti.attivo`                 |

#### FK e ID collegati al soggetto

| Colonna                      | Tipo      | Fonte                                  |
| ---------------------------- | --------- | -------------------------------------- |
| `stato_id`                   | `INTEGER` | `soggetti.stato_id` (FK config.stati)  |
| `comune_id`                  | `INTEGER` | `soggetti.comune_id` (FK config.comuni)|
| `titolo_cortesia_id`         | `INTEGER` | `soggetti.titolo_cortesia_id`          |
| `tipo_soggetto_dettaglio_id` | `BIGINT`  | `soggetti.tipo_soggetto_dettaglio_id`  |
| `default_contatto_id`        | `BIGINT`  | `soggetti.default_contatto_id`         |

#### Tipo soggetto (risolto)

| Colonna                       | Tipo      | Fonte                                       |
| ----------------------------- | --------- | ------------------------------------------- |
| `tipo_soggetto_id`            | `VARCHAR` | `config.tipi_soggetto.id` (PF/PG/ENTE)     |
| `tipo_soggetto_descrizione`   | `TEXT`    | `config.tipi_soggetto.descrizione`          |
| `tipo_soggetto_codice_interno`| `VARCHAR` | `config.tipi_soggetto_dettaglio.codice_interno` |

#### Titolo cortesia (risolto)

| Colonna                            | Tipo   | Fonte                                    |
| ---------------------------------- | ------ | ---------------------------------------- |
| `titolo_cortesia_descrizione`      | `TEXT` | `config.titoli_cortesia.descrizione`     |
| `titolo_cortesia_descrizione_breve`| `TEXT` | `config.titoli_cortesia.descrizione_breve`|

#### Dati societari (nullable)

| Colonna                     | Tipo      | Fonte                                       |
| --------------------------- | --------- | ------------------------------------------- |
| `has_dati_societari`        | `BOOLEAN` | `dati_societari.id IS NOT NULL`             |
| `dati_societari_id`         | `BIGINT`  | `dati_societari.id`                         |
| `forma_giuridica_id`        | `INTEGER` | `dati_societari.forma_giuridica_id`         |
| `forma_giuridica_codice`    | `TEXT`    | `config.forme_giuridiche.codice`            |
| `forma_giuridica_descrizione`| `TEXT`   | `config.forme_giuridiche.descrizione`       |
| `id_prov_iscri_rea`         | `INTEGER` | `dati_societari.id_prov_iscri_rea`          |
| `provincia_iscri_rea_sigla` | `TEXT`    | `config.province.sigla`                     |
| `iscrizione_rea`            | `VARCHAR` | `dati_societari.iscrizione_rea`             |
| `capitale_sociale`          | `NUMERIC` | `dati_societari.capitale_sociale`           |
| `socio_unico`               | `TEXT`    | `dati_societari.socio_unico` (enum -> text) |
| `liquidazione`              | `TEXT`    | `dati_societari.liquidazione` (enum -> text)|
| `destinatario_fe`           | `VARCHAR` | `dati_societari.destinatario_fe`            |
| `pec_fatturazione`          | `VARCHAR` | `dati_societari.pec_fatturazione`           |
| `codice_sdi`                | `VARCHAR` | `dati_societari.codice_sdi`                 |
| `data_costituzione`         | `DATE`    | `dati_societari.data_costituzione`          |

Se il `soggetto_ruolo_id` non esiste, la funzione restituisce **zero righe** (nessun errore).

---

### Strategia di Join

```
soggetti_ruoli sr
  INNER JOIN soggetti s                        ON s.id = sr.soggetto_id
  INNER JOIN config.tipi_ruoli tr              ON tr.id = sr.tipo_ruolo_id
  LEFT  JOIN config.tipi_soggetto_dettaglio td ON td.id = s.tipo_soggetto_dettaglio_id
  LEFT  JOIN config.tipi_soggetto ts           ON ts.id = td.tipo_soggetto_id
  LEFT  JOIN config.titoli_cortesia tc         ON tc.id = s.titolo_cortesia_id
  LEFT  JOIN dati_societari ds                 ON ds.soggetto_id = s.id
  LEFT  JOIN config.forme_giuridiche fg        ON fg.id = ds.forma_giuridica_id
  LEFT  JOIN config.province pr                ON pr.id = ds.id_prov_iscri_rea
```

I join `INNER` garantiscono che il record esista; i `LEFT` rendono opzionali tipo soggetto, titolo cortesia e dati societari.

---

### Esempi di Utilizzo

```sql
-- 1) Dati completi di un soggetto dato il suo ruolo
SELECT * FROM script.fn_get_soggetto_dati_by_ruolo(12);

-- 2) Solo i dati societari (se presenti)
SELECT has_dati_societari, dati_societari_id,
       forma_giuridica_codice, codice_sdi, pec_fatturazione
FROM script.fn_get_soggetto_dati_by_ruolo(25);

-- 3) Uso in fn_get_user_profile (composizione JSONB)
SELECT row_to_json(t.*)::jsonb
FROM script.fn_get_soggetto_dati_by_ruolo(12) t;
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE` — non modifica dati, puo' essere usata in contesti read-only.
* **Linguaggio**: PL/pgSQL
* **Tipi colonne**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.

---
