## Documentazione Concettuale -- Funzione `script.fn_get_user_profile`

> Vedi anche
>
> Funzioni correlate:
>
> [script.fn_get_soggetto_dati_by_ruolo](/dbzero/script/funzioni/fn_get_soggetto_dati_by_ruolo)
> [script.fn_get_user_permissions_map](/dbzero/script/funzioni/fn_get_user_permissions_map)
> [script.fn_get_user_actions_map](/dbzero/script/funzioni/fn_get_user_actions_map)
> [script.fn_get_user_object_permissions_map](/dbzero/script/funzioni/fn_get_user_object_permissions_map)
>
> Approfondimento tabelle:
>
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)

La funzione **`script.fn_get_user_profile(p_auth_user_id)`** restituisce un
**JSONB** con il profilo completo dell'utente loggato.

E' l'entrypoint DB del profilo utente esposto da `GET /api/v1/core/me/`.
La funzione aggrega in una sola chiamata:

- dati `auth_user`
- ruolo sistema
- dettaglio risorsa umana
- soggetto anagrafico
- emittente fiscale risolto
- mappa permessi area
- mappa azioni abilitate
- mappa override oggetto attivi
- flag `deve_cambiare_password`

---
### Scopo Principale

- **Profilo utente completo in una chiamata**
- **Payload JSONB stabile ed estendibile**
- **Riuso delle funzioni di dominio** per soggetto e mappe permessi
- **Riduzione query interne**: dalla revisione `20260410-16` la lettura di
  `auth_user + risorse_umane_auth_user + risorse_umane + lookup qualifica/UO`
  viene eseguita in una sola `SELECT`

---
### Parametri di Input

| Nome | Tipo | Obbligatorio | Descrizione |
|------|------|:------------:|-------------|
| `p_auth_user_id` | `anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE` | Si | ID utente Django (`auth_user.id`), deve essere `> 0` |

### Guard di validazione

| Condizione | Codice errore | Effetto |
|------------|---------------|---------|
| `p_auth_user_id` NULL o `<= 0` | `E_ADMIN_VALIDAZIONE` | blocco immediato |
| `auth_user` inesistente | `E_ADMIN_VALIDAZIONE` | profilo non costruibile |
| nessun record `risorse_umane_auth_user` | `E_ADMIN_VALIDAZIONE` | utente non collegato a risorsa |
| `ruolo_sistema = DISABILITATO` | `E_UTENTE_DISABILITATO` | login bloccato |
| nessun record `risorse_umane` | `E_ADMIN_VALIDAZIONE` | catena utente incompleta |
| `risorse_umane.attivo = false` | `E_UTENTE_DISABILITATO` | utente disattivato |
| `CURRENT_DATE < valido_dal` | `E_UTENTE_NON_ATTIVO` | utente non ancora attivo |
| `CURRENT_DATE > valido_al` | `E_UTENTE_SCADUTO` | utente scaduto |

Tutti i guard usano `script.fn_log_and_raise_error`.

---
### Struttura del JSONB

La funzione restituisce un JSONB con 9 chiavi principali:

1. `utente`
2. `ruolo_sistema`
3. `risorse_umane`
4. `soggetto`
5. `emittente`
6. `permessi_area`
7. `azioni_abilitate`
8. `permessi_oggetto`
9. `deve_cambiare_password`

### Esempio di output

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
    "unita_organizzativa_id": 3,
    "valido_dal": "2024-01-01",
    "valido_al": null,
    "attivo": true
  },
  "soggetto": { "...output di fn_get_soggetto_dati_by_ruolo..." },
  "emittente": { "...campi emittente + output soggetto emittente..." },
  "permessi_area": {
    "anagrafiche": "TUTTO",
    "vendite": "LETTURA"
  },
  "azioni_abilitate": {
    "genera_fatture_lotti": true
  },
  "permessi_oggetto": {
    "vendite.fattura": "LETTURA"
  },
  "deve_cambiare_password": false
}
```

---
### Dettaglio blocchi

#### `utente`

JSONB costruito da `django.auth_user`:

- `auth_user_id`
- `username`
- `first_name`
- `last_name`
- `email`

#### `risorse_umane`

JSONB costruito da `anagrafiche.risorse_umane` con lookup su:

- `config.qualifiche`
- `config.unita_organizzative`

Include:

- `risorsa_umana_id`
- `risorse_umane_auth_user_id`
- `soggetto_ruolo_id`
- `qualifica_id`
- `qualifica_codice`
- `qualifica_codice_interno`
- `qualifica_descrizione`
- `unita_organizzativa_id`
- `unita_organizzativa_codice`
- `unita_organizzativa_codice_interno`
- `unita_organizzativa_descrizione`
- `valido_dal`
- `valido_al`
- `attivo`

#### `soggetto`

E' l'output completo di `script.fn_get_soggetto_dati_by_ruolo(v_soggetto_ruolo_id)`
convertito in JSONB.

#### `emittente`

Se risolto, il blocco contiene:

- `emittente_fiscale_id`
- `emittente_fiscale_uid`
- `emittente_codice`
- `emittente_descrizione`
- `user_emittente_fiscale_id`
- `regime_fiscale_rf`
- `valuta_id`

piu' tutti i campi soggetto dell'emittente, ottenuti ancora tramite
`fn_get_soggetto_dati_by_ruolo`.

Se nessun emittente e' disponibile, il valore e' `null`.

#### `permessi_area`

Mappa `{schema_db: livello}` prodotta da
`script.fn_get_user_permissions_map(p_auth_user_id)`.

#### `azioni_abilitate`

Mappa `{permission_codename: boolean}` prodotta da
`script.fn_get_user_actions_map(p_auth_user_id)`.

#### `permessi_oggetto`

Mappa `{app_label.model_name: livello}` prodotta da
`script.fn_get_user_object_permissions_map(p_auth_user_id)`.

Contiene solo gli override oggetto attivi espliciti.

#### `deve_cambiare_password`

Boolean derivato da
`anagrafiche.risorse_umane_auth_user.deve_cambiare_password`,
normalizzato con `COALESCE(..., false)`.

---
### Flusso Logico Interno

1. Guard su `p_auth_user_id`
2. Query unica per leggere:
   `auth_user + risorse_umane_auth_user + risorse_umane + qualifica + UO`
3. Guard su ruolo, validita' e stato attivo
4. Costruzione blocco `risorse_umane`
5. Costruzione blocco `soggetto` via `fn_get_soggetto_dati_by_ruolo`
6. Risoluzione emittente con priorita':
   - whitelist personale `config.user_emittenti_fiscali`
   - fallback gestore globale `emittenti_fiscali_billing_account`
7. Composizione finale con `jsonb_build_object`

---
### Ottimizzazioni introdotte

La revisione `20260410-16` ha ridotto il costo della funzione in due punti:

- **query iniziale accorpata**
  prima i blocchi `auth_user`, `risorse_umane_auth_user` e `risorse_umane`
  venivano letti in query separate
- **risoluzione emittente in un solo blocco SQL**
  con priorita' `whitelist -> fallback`, evitando due rami separati di lookup

Il refactor resta retrocompatibile sul payload: cambia l'implementazione,
non il contratto del JSONB.

---
### Esempi

```sql
-- Profilo completo
SELECT script.fn_get_user_profile(1);

-- Solo la mappa permessi area
SELECT script.fn_get_user_profile(1) -> 'permessi_area';

-- Solo la mappa override oggetto
SELECT script.fn_get_user_profile(1) -> 'permessi_oggetto';

-- Solo il blocco emittente
SELECT script.fn_get_user_profile(1) -> 'emittente';
```
