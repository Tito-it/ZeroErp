## Documentazione Concettuale -- Funzione `script.fn_get_user_profile`

> Vedi anche
>
> Funzione base:
>
> * [script.fn_get_soggetto_dati_by_ruolo](/dbzero/script/funzioni/fn_get_soggetto_dati_by_ruolo)
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> * [config.qualifiche](/dbzero/config/tabelle/qualifiche)
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
>
> Approfondimento viste modello:
>
> * [anagrafiche.vw_risorse_umane_dettaglio](/dbzero/anagrafiche/views/vw_risorse_umane_dettaglio)

La funzione **`script.fn_get_user_profile(p_auth_user_id INTEGER)`** restituisce un **JSONB** con il profilo completo dell'utente loggato: dati auth_user, ruolo sistema, risorse umane (con qualifica e unita' organizzativa risolte), soggetto anagrafico (con dati societari se presenti), e emittente fiscale associato.

E' progettata come **unico punto di accesso** per l'endpoint `GET /api/v1/core/me/` del frontend, aggregando in una singola chiamata DB tutti i dati necessari per il profilo utente.

---

### 🎯 Scopo Principale

* **Profilo utente completo in una chiamata**: evita al backend di orchestrare query multiple per comporre il profilo.

* **5 blocchi JSONB** strutturati:
  1. `utente` — dati da `auth_user`
  2. `ruolo_sistema` — enum dalla tabella ponte
  3. `risorse_umane` — dettaglio risorsa umana con qualifica e UO risolti
  4. `soggetto` — dati anagrafici completi (delegati a `fn_get_soggetto_dati_by_ruolo`)
  5. `emittente` — dati emittente fiscale + soggetto della ditta (`null` se non associato)

* **Riuso di fn_get_soggetto_dati_by_ruolo**: i blocchi `soggetto` e `emittente` sono generati dalla stessa funzione, garantendo output uniforme con tutti gli ID e le descrizioni risolte.

* **Risoluzione emittente intelligente**: prima cerca nella whitelist `user_emittenti_fiscali` (primo attivo), poi fallback su emittente unico attivo se la whitelist e' vuota.

---

### Parametri di Input

| Nome             | Tipo      | Obbligatorio | Descrizione                                              |
| ---------------- | --------- | ------------ | -------------------------------------------------------- |
| `p_auth_user_id` | `INTEGER` | Si           | ID dell'utente Django (`auth_user.id`). Deve essere > 0. |

**Guard**: se `NULL` o `<= 0`, lancia `invalid_parameter_value`. Se l'utente non esiste o non ha record ponte `risorse_umane_auth_user`, lancia `no_data_found`.

---

### Valore di Ritorno

La funzione restituisce un **JSONB** con la seguente struttura:

```json
{
  "utente": {
    "auth_user_id": 1,
    "username": "mtitini",
    "first_name": "Michele",
    "last_name": "Titini",
    "email": "m@example.com"
  },
  "ruolo_sistema": "ADMIN",
  "risorse_umane": {
    "risorsa_umana_id": 5,
    "risorse_umane_auth_user_id": 3,
    "soggetto_ruolo_id": 12,
    "qualifica_id": 2,
    "qualifica_codice": "DEV",
    "qualifica_codice_interno": "SVILUPPATORE",
    "qualifica_descrizione": "Sviluppatore",
    "unita_organizzativa_id": 3,
    "unita_organizzativa_codice": "IT",
    "unita_organizzativa_codice_interno": "INFORMATICA",
    "unita_organizzativa_descrizione": "Information Technology",
    "valido_dal": "2024-01-01",
    "valido_al": null,
    "attivo": true
  },
  "soggetto": { "...output di fn_get_soggetto_dati_by_ruolo..." },
  "emittente": { "...campi emittente + output di fn_get_soggetto_dati_by_ruolo..." }
}
```

#### Dettaglio blocco `utente`

| Chiave         | Tipo      | Fonte                  |
| -------------- | --------- | ---------------------- |
| `auth_user_id` | `INTEGER` | `auth_user.id`         |
| `username`     | `VARCHAR` | `auth_user.username`   |
| `first_name`   | `VARCHAR` | `auth_user.first_name` |
| `last_name`    | `VARCHAR` | `auth_user.last_name`  |
| `email`        | `VARCHAR` | `auth_user.email`      |

#### Dettaglio blocco `risorse_umane`

| Chiave                               | Tipo      | Fonte                                                  |
| ------------------------------------ | --------- | ------------------------------------------------------ |
| `risorsa_umana_id`                   | `BIGINT`  | `risorse_umane.id`                                     |
| `risorse_umane_auth_user_id`         | `BIGINT`  | `risorse_umane_auth_user.id`                           |
| `soggetto_ruolo_id`                  | `BIGINT`  | `risorse_umane.soggetto_ruolo_id`                      |
| `qualifica_id`                       | `INTEGER` | `risorse_umane.qualifica_id`                           |
| `qualifica_codice`                   | `VARCHAR` | `config.qualifiche.codice`                             |
| `qualifica_codice_interno`           | `VARCHAR` | `config.qualifiche.codice_interno`                     |
| `qualifica_descrizione`              | `TEXT`    | `config.qualifiche.descrizione`                        |
| `unita_organizzativa_id`             | `INTEGER` | `risorse_umane.unita_organizzativa_id` (nullable)      |
| `unita_organizzativa_codice`         | `VARCHAR` | `config.unita_organizzative.codice` (nullable)         |
| `unita_organizzativa_codice_interno` | `VARCHAR` | `config.unita_organizzative.codice_interno` (nullable) |
| `unita_organizzativa_descrizione`    | `TEXT`    | `config.unita_organizzative.descrizione` (nullable)    |
| `valido_dal`                         | `DATE`    | `risorse_umane.valido_dal`                             |
| `valido_al`                          | `DATE`    | `risorse_umane.valido_al` (nullable)                   |
| `attivo`                             | `BOOLEAN` | `risorse_umane.attivo`                                 |

#### Dettaglio blocco `soggetto`

Output completo di `fn_get_soggetto_dati_by_ruolo(risorse_umane.soggetto_ruolo_id)`, convertito in JSONB tramite `row_to_json`. Vedi documentazione della funzione base per l'elenco completo delle 42 colonne.

#### Dettaglio blocco `emittente`

Se un emittente fiscale e' associato all'utente, il blocco contiene:

**Campi specifici emittente:**

| Chiave                      | Tipo      | Fonte                                          |
| --------------------------- | --------- | ---------------------------------------------- |
| `emittente_fiscale_id`      | `BIGINT`  | `emittenti_fiscali.id`                         |
| `emittente_fiscale_uid`     | `UUID`    | `emittenti_fiscali.uid`                        |
| `emittente_codice`          | `VARCHAR` | `emittenti_fiscali.codice`                     |
| `emittente_descrizione`     | `VARCHAR` | `emittenti_fiscali.descrizione`                |
| `user_emittente_fiscale_id` | `BIGINT`  | `user_emittenti_fiscali.id` (null se fallback) |
| `regime_fiscale_rf`         | `VARCHAR` | `emittenti_fiscali.regime_fiscale_rf`          |
| `valuta_id`                 | `INTEGER` | `emittenti_fiscali.valuta_id`                  |

**Campi soggetto emittente:** tutti i campi di `fn_get_soggetto_dati_by_ruolo(emittenti_fiscali.soggetto_ruolo_id)`, mergiati nello stesso oggetto JSON.

Se nessun emittente e' associato, `emittente` e' `null`.

---

### Flusso Logico Interno

1. **Validazione parametro**: guard su `NULL` e `<= 0`.

2. **Blocco utente**: lettura da `auth_user` (id, username, first_name, last_name, email). Se utente non esiste → `no_data_found`.

3. **Risorse umane**: risoluzione catena `risorse_umane_auth_user` → `risorse_umane` con LEFT JOIN su `qualifiche` e `unita_organizzative`. Se nessun record ponte → `no_data_found`.

4. **Blocco soggetto**: chiamata a `fn_get_soggetto_dati_by_ruolo(soggetto_ruolo_id)` e conversione in JSONB.

5. **Risoluzione emittente**:
   - **Whitelist**: cerca il primo `user_emittenti_fiscali` attivo per l'utente (ordine id), con JOIN su `emittenti_fiscali` attivo.
   - **Fallback**: se whitelist vuota, cerca un emittente unico attivo (`HAVING COUNT(*) = 1`). Se ci sono piu' emittenti attivi senza whitelist, nessuno viene selezionato (ambiguo).
   - Se trovato: lettura campi emittente + `fn_get_soggetto_dati_by_ruolo(ef.soggetto_ruolo_id)`, merge in unico oggetto JSONB.
   - Se non trovato: `emittente = null`.

6. **Composizione finale**: `jsonb_build_object` con le 5 chiavi.

---

### Esempi di Utilizzo

```sql
-- 1) Profilo completo dell'utente con id=1
SELECT script.fn_get_user_profile(1);

-- 2) Estrarre solo il blocco soggetto
SELECT script.fn_get_user_profile(1) -> 'soggetto';

-- 3) Username e ragione sociale emittente
SELECT
    script.fn_get_user_profile(1) -> 'utente' ->> 'username' AS username,
    script.fn_get_user_profile(1) -> 'emittente' ->> 'ragione_sociale_completa' AS ditta;

-- 4) Uso dal backend Django (endpoint /api/v1/core/me/)
-- cursor.execute("SELECT script.fn_get_user_profile(%s)", [request.user.id])
-- row = cursor.fetchone()
-- return row[0]  # JSONB → dict Python
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE` — non modifica dati.
* **Linguaggio**: PL/pgSQL
* **Output**: JSONB (flessibile, estendibile senza modifiche alla signature).
* **Dipendenza**: `script.fn_get_soggetto_dati_by_ruolo` (deve esistere).
* **Errori**: `invalid_parameter_value` per input invalido, `no_data_found` per utente/risorsa umana inesistente.

---
