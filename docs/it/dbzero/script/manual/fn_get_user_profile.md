## Documentazione Concettuale -- Funzione `script.fn_get_user_profile`

> Vedi anche
>
> Funzioni correlate:
>
> [script.fn_get_soggetto_dati_by_ruolo](/dbzero/script/funzioni/fn_get_soggetto_dati_by_ruolo)
> [script.fn_get_user_permissions_map](/dbzero/script/funzioni/fn_get_user_permissions_map)
> [script.fn_get_user_actions_map](/dbzero/script/funzioni/fn_get_user_actions_map)
> [script.fn_get_user_object_permissions_map](/dbzero/script/funzioni/fn_get_user_object_permissions_map)
> [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin)
> [script.fn_current_identita_context](/dbzero/script/funzioni/fn_current_identita_context)
>
> Approfondimento tabelle:
>
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
>
> Guide:
>
> [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth) §4.7 GUC + §13.7 bug multi-veste top-level

La funzione **`script.fn_get_user_profile(p_auth_user_id)`** restituisce un
**JSONB** con il profilo completo dell'utente loggato.

E' l'entrypoint DB del profilo utente esposto da `GET /api/v1/core/me/`.
La funzione aggrega in una sola chiamata:

- dati `auth_user`
- ruolo sistema ricostruito (ADMIN / OPERATIVO)
- flag `is_super_admin` context-aware
- campo top-level `ruolo_applicativo` GUC-aware (veste del JWT corrente)
- dettaglio risorsa umana
- soggetto anagrafico
- emittente fiscale risolto
- mappa permessi area (context-aware)
- mappa azioni abilitate (context-aware)
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
| nessuna `identita_digitali` OPERATORE | `E_ADMIN_VALIDAZIONE` | user non collegato a risorsa |
| identita attivo=false o ruolo DISABILITATO | `E_UTENTE_DISABILITATO` | login bloccato |
| nessun record `risorse_umane` | `E_ADMIN_VALIDAZIONE` | catena utente incompleta |
| `risorse_umane.attivo = false` | `E_UTENTE_DISABILITATO` | utente disattivato |
| `CURRENT_DATE < valido_dal` (identita o ru) | `E_UTENTE_NON_ATTIVO` | utente non ancora attivo |
| `CURRENT_DATE > valido_al` (identita o ru) | `E_UTENTE_SCADUTO` | utente scaduto |

Tutti i guard usano `script.fn_log_and_raise_error`.

**Nota** (post PR-B 21-04-2026): la funzione richiede ancora un'identita
OPERATORE attiva per completare (e' pensata per lo scoped operatore +
metadata emittente/RU). Utenti single-veste CLIENTE_PORTALE /
SHOP_CUSTOMER / FORNITORE_PORTALE non hanno un profilo full qui: il BE
usa endpoint dedicati o fallback. Se in futuro si estende `/me/` a
single-veste non-operatore, il guard va reso condizionale.

---
### Struttura del JSONB

La funzione restituisce un JSONB con 10 chiavi principali (post Fase 7
2026-04-29: rimossa la chiave legacy `ruolo_sistema`).

1. `utente`
2. `is_super_admin` — context-aware (post PR-B)
3. `ruolo_applicativo` — top-level GUC-aware (post PR-B)
4. `risorse_umane`
5. `soggetto`
6. `emittente`
7. `permessi_area` — context-aware (post PR-B)
8. `azioni_abilitate` — context-aware (post PR-B)
9. `permessi_oggetto`
10. `deve_cambiare_password`

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
  "is_super_admin": true,
  "ruolo_applicativo": "OPERATORE",
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

#### `is_super_admin`

Boolean prodotto da `script.fn_is_super_admin(p_auth_user_id)`.
**Context-aware** (post PR-B 21-04-2026): se la GUC
`app.ruolo_applicativo` e' popolata e diversa da `OPERATORE`, ritorna
`false` (fail-closed — il bypass SUPER_ADMIN non si attiva in contesti
portale/shop). Se la GUC non e' popolata, applica la logica legacy:
EXISTS identita OPERATORE attiva con binding SUPER_ADMIN attivo.

#### `ruolo_applicativo` (top-level)

Stringa che riflette la **veste del JWT corrente**. **GUC-first**
(post PR-B 21-04-2026, migration `20260421-05`):

```sql
v_ruolo_applicativo_out := COALESCE(
    NULLIF(current_setting('app.ruolo_applicativo', true), ''),
    v_ruolo_applicativo::text  -- fallback: identita OPERATORE
);
```

Priorita':

1. **GUC `app.ruolo_applicativo`** — popolata dal middleware BE
   `JwtAuditAuthentication` su ogni request autenticata. Riflette la
   veste scelta dall'utente al login (OPERATORE / CLIENTE_PORTALE /
   SHOP_CUSTOMER / FORNITORE_PORTALE / API_CLIENT).
2. **Fallback** — valore dell'identita OPERATORE gia' caricata dalla
   query iniziale (single round-trip DB). Utilizzato per chiamate
   fuori request HTTP (cron, tool CLI, psql).

**Pre-PR-B**: il campo esponeva sempre il `ruolo_applicativo`
dell'identita OPERATORE, causando il bug §13.7 per utenti multi-veste
loggati su canale portale (top-level=`OPERATORE` invece di
`CLIENTE_PORTALE`, guard FE non redirigeva a `/portale`).

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
`script.fn_get_user_permissions_map(p_auth_user_id)`. **Context-aware**
(post PR-B 21-04-2026, migration `20260421-04-03`): se GUC
`app.ruolo_applicativo` popolata e `!= OPERATORE`, tutti i valori sono
`BLOCCATO` (fail-closed — i resolver permessi sono OPERATORE-only).

#### `azioni_abilitate`

Mappa `{permission_codename: boolean}` prodotta da
`script.fn_get_user_actions_map(p_auth_user_id)`. **Context-aware**
(post PR-B 21-04-2026, migration `20260421-04-04`): se GUC
`app.ruolo_applicativo` popolata e `!= OPERATORE`, tutti i valori sono
`false`.

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
   `auth_user + identita_digitali (OPERATORE) + risorse_umane + qualifica + UO`
3. Guard su identita attiva, ruolo, validita' e stato attivo
4. Calcolo `is_super_admin` via `fn_is_super_admin` (context-aware)
5. Calcolo top-level `ruolo_applicativo` via COALESCE GUC / fallback
   identita OPERATORE (context-aware post PR-B)
6. Costruzione blocco `risorse_umane`
7. Costruzione blocco `soggetto` via `fn_get_soggetto_dati_by_ruolo`
8. Risoluzione emittente con priorita':
   - whitelist personale `config.user_emittenti_fiscali`
   - fallback gestore globale `emittenti_fiscali_billing_account`
9. Composizione finale con `jsonb_build_object`

### Context-awareness (post PR-B 21-04-2026)

Dopo il merge di PR-B (SSO multi-veste + shop B2C), l'utente puo' avere
N identita attive e scegliere la veste al login. 4 campi del profilo
sono stati resi context-aware tramite la GUC `app.ruolo_applicativo`
(popolata dal middleware BE `JwtAuditAuthentication`):

| Campo | Migration | Comportamento se GUC != OPERATORE |
|-------|-----------|------------------------------------|
| `is_super_admin` | `20260421-03` | `false` |
| `ruolo_applicativo` (top-level) | `20260421-05` | valore GUC letterale |
| `permessi_area` | `20260421-04-03` | `{area: BLOCCATO}` per ogni area |
| `azioni_abilitate` | `20260421-04-04` | `{azione: false}` per ogni azione |

Tutti i campi implementano **fail-soft su GUC mancante**: se la GUC
non e' popolata (test pgTAP, psql manuale, cron), applicano la logica
legacy basata sull'identita OPERATORE dell'utente. Il contratto del
JSONB non cambia, solo la derivazione dei valori.

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
