# API Amministrazione Software

## Scopo

Documentazione completa delle API REST del modulo **Amm. Software** (Amministrazione).
Questi endpoint gestiscono utenti (operatori), permessi individuali, profili reparto
e lookup di supporto.

## Contesto

Il modulo Amm. Software e' il pannello di controllo per l'amministratore di sistema.
Permette di creare operatori, assegnare ruoli, configurare override di permessi per
singolo utente e definire profili di accesso per reparto (unita' organizzativa).

Tutti gli endpoint richiedono autenticazione JWT con ruolo **ADMIN** (`AdminAPIView`).
Post-cutover multi-face il check ADMIN delega a `PermissionResolver.is_super_admin`
(binding `SUPER_ADMIN` su `config.profili_accesso_bindings`, profilo seed id 9100).
L'endpoint lista utenti ha throttling search attivo (`is_search_endpoint = True`).

Le risposte seguono l'envelope standard `{ "data": {...}, "meta": {...} }`.

Base URL: `/api/v1/amm-software/`

> **Note di evoluzione 2026-04-29 (Fasi 0-2 multi-face)**:
>
> - **Fase 0** (LANDED): nuovo endpoint summary mapping BA in `anagrafiche`
>   (vedi [api_emittenti_fiscali.md §5.4](../../anagrafiche/manual/api_emittenti_fiscali.md)).
>   Niente impatto su `amm-software`.
> - **Fase 1** (BE LANDED, attesa fn DB `script.fn_get_operatore_detail`):
>   - PATCH/POST `/operatori/`: contratto pubblico **rifiuta** `ruolo_sistema`
>     legacy → usa `is_super_admin` + `attivo` (vedi §1.2 e §1.4).
>   - GET dettaglio: 6 nuovi campi capability (`can_invite`/`invite_reason`,
>     `can_disable`/`disable_reason`, `can_demote_super_admin`/`demote_reason`)
>     piu' `is_super_admin`, `ruolo_applicativo`, `last_login`,
>     `invito_inviato_at`, `deve_cambiare_password`, `emittenti_descrizione`.
>   - Endpoint `disabilita`: nuovo errore `E_PROFILO_ULTIMO_SUPER_ADMIN`
>     (HTTP 409) tradotto dal trigger DB.
>   - ~~Nuovo endpoint `riattiva`~~ — ritirato il 2026-10-04 (D-3, vedi §1.6).
> - **Fase 2** (LANDED): scope emittenti dichiarativo via
>   `script.fn_get_user_emittenti_scope` / `fn_change_user_emittenti_scope`
>   (vedi §2.5/§2.6). Shape `{scope_mode, emittenti_ids, ...capability}`,
>   `MULTI` chiuso applicativamente post Q2.
> - **Fase 3** (LANDED): form-defaults emittente fiscale via `ParameterService`
>   (cascata user->group->emittente->default). Nuovi endpoint:
>   `GET /emittenti-fiscali/form-defaults/` (§5.1) +
>   `GET /lookup/rounding-modes/` (§4.5). Seed `config.parameters` 3 chiavi:
>   `EMITTENTE_DEFAULT_BOLLO_AUTO`/`_BOLLO_SOGLIA`/`_ROUNDING_POLICY`. Il
>   campo `attivo` non passa per parameters (default DB gia' `true`).
>   Pattern allineato a `ApiArticoliFormDefaults` (catalogo Fase 8).
> - **Fase 5** (LANDED): audit hardening + email log lookup. Nuovi endpoint:
>   `GET /lookup/audit-sources/` (§4.6, da `script.vw_audit_sources`) +
>   `GET /lookup/email-log-stati/` (§4.7, lookup statico Python — ritirato il
  2026-09-26, ora `/core/email/log/stati/`). Refactor
>   `audit-log` list response: nuovo shape per riga (`code`/`storico_id`/
>   `area_funzionale`/`audit: {summary, diff}`), build dinamico UNION ALL
>   dalla vista (rimozione `_AUDIT_TABLES` hardcoded), summary calcolato
>   inline via `script.fn_audit_summary` (no N+1). 4 codici errore stabili
>   registrati: `E_AUDIT_SUMMARY_PARAM_NON_VALIDO`/`_SOURCE_NON_TROVATO`/
>   `_SNAPSHOT_NON_TROVATO`/`E_OPERATORE_SCOPE_PARAM_NON_VALIDO` (refactor
>   guard Fase 2 da RAISE 22023 a code stabile).

---

## 1. Utenti

### 1.1 GET /api/v1/amm-software/operatori/ -- Lista utenti

Restituisce la lista paginata degli operatori con filtri opzionali: la prima
scheda dell'area «Accessi» (§1-bis). ⭐ Dal 2026-10-02 una riga e' una credenziale
di categoria `OPERATORE` (`script.fn_categoria_accesso`, la regola che decide il
tab), e la veste mostrata e' quella di riferimento (`script.fn_veste_di_riferimento`:
l'accesa, altrimenti la spenta piu' recente). Ogni riga porta `veste_attiva`: un
operatore disattivato resta in elenco col tipo `OPERATORE` e `veste_attiva = false`
(R-DB-1: «disabilitato» si legge dallo stato, non dal ruolo).

**Parametri query string:**

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | no | Ricerca libera sulle colonne che il catalogo della lista `anagrafiche.operatori` accende per l'operatore (le decide il catalogo, non il codice: `ricerca_full` nella configurazione della lista). Sotto 3 caratteri non filtra (nessun 400). Ogni riga porta anche `soggetto_ragione_sociale` (ragione sociale completa del soggetto, `null` senza soggetto) |
| `is_super_admin` | bool | no | Filtra sul binding SUPER_ADMIN: `true`/`false`; ogni altro valore è un 400 `E_VALIDATION_INPUT` (dal 2026-10-20: prima `1`/`yes`/`on` = vero e tutto il resto falso, in silenzio) |
| `unita_organizzativa_id` | int | no | Filtra per unita' organizzativa |
| `is_active` | bool | no | Filtra per stato attivo della credenziale (stessa lettura di `is_super_admin`) |
| `includi_di_prova` | bool | no | `true` mostra anche gli utenti di prova (etichetta del provisioning di sviluppo); assente o `false` li nasconde. Booleano rigoroso: un valore non booleano e' un 400 sul campo |
| `limit` | int | no | Numero massimo risultati (default 25, max 200) |
| `offset` | int | no | Offset per paginazione (default 0) |
| `order_by` | string | no | Colonna di ordinamento: `last_name`, `soggetto_cognome`, `username`, `is_super_admin`, `ruolo_applicativo`, `is_active`, `unita_organizzativa_nome`, `override_count`, `valido_dal`, `valido_al` (NULL = senza scadenza, ordinata come infinito). Senza `order_by`: `soggetto_cognome`, poi `username`, ASC. Fuori whitelist → **400** `E_VALIDATION_INPUT` (dal 2026-10-20) |
| `order_dir` | string | no | `ASC` o `DESC` (altro valore: 400). Senza `order_dir` le colonne data (`valido_dal`, `valido_al`) partono DESC, le altre ASC |

**Risposta:**

```json
{
  "data": {
    "count": 42,
    "results": [
      {
        "auth_user_id": 1,
        "username": "mtitini",
        "email": "m.titini@example.com",
        "first_name": "Michele",
        "last_name": "Titini",
        "soggetto_cognome": "Titini",
        "soggetto_nome": "Michele",
        "soggetto_ragione_sociale": "Titini Michele",
        "is_super_admin": true,
        "ruolo_applicativo": "OPERATORE",
        "veste_attiva": true,
        "is_active": true,
        "unita_organizzativa_id": 2,
        "unita_organizzativa_nome": "Sviluppo",
        "risorsa_umana_id": 5,
        "attivo": true,
        "valido_dal": "2026-01-15",
        "valido_al": null,
        "altre_vesti": ["SHOP_CUSTOMER"],
        "emittenti_descrizione": "Azienda SRL",
        "override_count": 3,
        "di_prova": false
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

- `veste_attiva`: stato della veste OPERATORE di riferimento; `is_active` e' della credenziale (tutte le vesti); `attivo` della risorsa umana.
- `altre_vesti`: i tipi delle altre vesti **accese** della credenziale.
- `override_count`: override dei permessi scritti (`script.vw_override_operatore_area`).
- `di_prova`: la credenziale porta l'etichetta di prova (`dbops.credenziali_di_prova`); compare solo con `includi_di_prova=true`.

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/?search=titini&is_super_admin=true&limit=10"
```

---

### 1.2 POST /api/v1/amm-software/operatori/ -- Crea utente

Crea un nuovo operatore completo: credenziale, soggetto persona fisica, risorsa
umana e veste `OPERATORE`. La creazione e' orchestrata dalla funzione DB
`anagrafiche.fn_crea_operatore_v2`.

**Contract Fase 1 multi-face**: il payload accetta `is_super_admin` (booleano).
Il campo legacy `ruolo_sistema` e' **rifiutato** con `E_AMM_VALIDAZIONE`.

**Payload JSON:**

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `cognome` | string | si* | Cognome operatore (*solo se `soggetto_id` non valorizzato) |
| `nome` | string | si* | Nome operatore (*solo se `soggetto_id` non valorizzato) |
| `codice_fiscale` | string | si* | Codice fiscale italiano (*solo se `soggetto_id` non valorizzato) |
| `username` | string | si | Username per login |
| `email` | string | si | Email operatore |
| `qualifica_id` | int | si | ID qualifica (da lookup) |
| `is_super_admin` | bool | no | `true` per binding profilo SUPER_ADMIN, default `false` |
| `soggetto_id` | UUID | no | Se valorizzato: associa soggetto esistente (flusso B). Se assente: crea soggetto PF nuovo (flusso A) |
| `unita_organizzativa_id` | int | no | ID unita' organizzativa di appartenenza |
| `data_nascita` | string | no | Data nascita (formato `YYYY-MM-DD`) |
| `sesso` | string | no* | `M`, `F` o `X`. **Nessun default** (2026-10-09): nel flusso A il soggetto nuovo e' un privato, e senza sesso il guard del DB rifiuta con `E_SESSO_OBBLIGATORIO` (campo `sesso`), prima del consenso al riuso. Nel flusso B non si legge |
| `valido_dal` | string | no | Data inizio validita' (default data corrente) |
| `valido_al` | string | no | Data fine validita' |
| `comune_nascita_id` | int | no | ID comune di nascita |
| `indirizzo_resid_dettaglio_id` | int | no | ID dettaglio indirizzo residenza |
| `indirizzo_domfisc_dettaglio_id` | int | no | ID dettaglio indirizzo domicilio fiscale |
| `riusa_auth_user_id` | int | no | Il **consenso al riuso**: l'id della credenziale gia' esistente per l'email, che l'admin ha visto e confermato (vedi sotto). Al primo tentativo non si manda |

**Note sul contract**:

- **Niente `ruolo_sistema`**: il payload con la chiave legacy viene rifiutato
  prima di chiamare il repo. La promotion ad ADMIN passa da `is_super_admin: true`.
- **Niente `password`**: la sceglie la persona attivando l'invito (regola
  unica dell'invito). **Niente `attivo`**: la veste `OPERATORE` nasce
  **spenta** e la accende l'attivazione dell'invito.
- **Email gia' di una credenziale** (una persona, una credenziale): la
  credenziale si **riusa**, con username e password suoi; la risposta lo dice
  (`credenziale_riusata`, `username` effettivo). Il riuso vuole il **consenso**,
  in due tempi:
  1. il primo tentativo, senza `riusa_auth_user_id`, risponde **409
     `E_CREDENZIALE_DA_CONFERMARE`** con `ui_action = confirm_and_retry`;
  2. il pannello legge la credenziale (§1.2-bis), la mostra all'admin e, se
     conferma, ripete con `riusa_auth_user_id` = l'id letto. Se nel frattempo
     la credenziale e' cambiata, il DB chiede di nuovo.

  Se l'email e' di una credenziale di un'**altra persona fisica** la risposta
  e' **400 `E_CREDENZIALE_ALTRA_PERSONA`** (campo `email`): non si conferma, si
  corregge l'email.
- **Niente `ruolo_applicativo`**: per il drawer admin-software e' implicitamente
  `OPERATORE`. Le vesti `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`
  nascono da flussi di invito dedicati (vedi `api_invito_portale_shop.md`).

**Risposta:** dettaglio utente creato (stesso formato di GET dettaglio §1.3),
piu' `credenziale_riusata`.

**Esempio curl:**

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "cognome": "Rossi",
    "nome": "Mario",
    "codice_fiscale": "RSSMRA85M01H501Z",
    "username": "mrossi",
    "email": "m.rossi@example.com",
    "qualifica_id": 1,
    "is_super_admin": false,
    "unita_organizzativa_id": 2
  }' \
  "https://host/api/v1/amm-software/operatori/"
```

---

### 1.2-bis GET /api/v1/amm-software/operatori/credenziale-per-email/ -- Credenziale di un'email

I dati del dialog di conferma del riuso (§1.2): la credenziale che porta
l'email, con username e vesti. Legge `script.fn_get_credenziale_per_email`, la
**stessa** lettura con cui la madre compone il rifiuto
`E_CREDENZIALE_DA_CONFERMARE`: dialog e rifiuto dicono la stessa cosa. Solo
SUPER_ADMIN (`AdminAPIView`; a DB nessun guard, decisione di Tid del
2026-09-27).

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `email` | string | no | L'email del modulo di creazione. Maiuscole e spazi non contano; assente o vuota = nessuna credenziale |

**Risposta:** `data.credenziale` = `{auth_user_id, username, vesti}` oppure
`null` se l'email non ha credenziale (anche vuota o assente: nessun 400).
`vesti` e' in ordine di id, ogni voce `{ruolo_applicativo, attivo, soggetto}`;
lista vuota se la credenziale non ha vesti. Due credenziali con la stessa email
→ 500 `E_CREDENZIALE_EMAIL_AMBIGUA`.

```json
{"data": {"credenziale": {"auth_user_id": 42, "username": "mario.rossi",
  "vesti": [{"ruolo_applicativo": "CLIENTE_PORTALE", "attivo": true, "soggetto": "Rossi Srl"}]}}}
```

---

### 1.3 GET /api/v1/amm-software/operatori/{id}/ -- Dettaglio utente

Restituisce il dettaglio completo di un utente, inclusi conteggi override
permessi, emittenti associati, **stato multi-face** (Fase 1) e le **capability**
data-driven per le azioni del drawer (quattro terne `can_*`/`*_reason`/`*_reason_key`).

Il dettaglio e' generato da `script.fn_get_operatore_detail(p_auth_user_id)`
(single source of truth lato DB, idioma lookup-by-id: 0 righe per id non valido).

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "auth_user_id": 1,
    "username": "mtitini",
    "email": "m.titini@example.com",
    "first_name": "Michele",
    "last_name": "Titini",
    "soggetto_cognome": "Titini",
    "soggetto_nome": "Michele",
    "soggetto_id": "8a1f...uuid",
    "ragione_sociale_completa": "Titini Michele",
    "codice_fiscale": "RSSMRA80A01H501U",
    "is_super_admin": true,
    "ruolo_applicativo": "OPERATORE",
    "is_active": true,
    "attivo": true,
    "unita_organizzativa_id": 2,
    "unita_organizzativa_nome": "Sviluppo",
    "risorsa_umana_id": 5,
    "valido_dal": "2026-01-15",
    "valido_al": null,
    "last_login": "2026-04-29T08:30:00+00:00",
    "invito_inviato_at": "2026-01-15T09:15:00+00:00",
    "deve_cambiare_password": false,
    "override_aree_count": 3,
    "override_azioni_count": 1,
    "emittenti_count": 2,
    "emittenti_descrizione": "Azienda SRL, Sede Roma",
    "veste_attiva": true,
    "can_invite": false,
    "invite_reason": "VESTE_GIA_ATTIVA",
    "invite_reason_key": "amministrazione.operatori.invito_reason.veste_gia_attiva",
    "can_disable": false,
    "disable_reason": "ULTIMO_SUPER_ADMIN",
    "disable_reason_key": "amministrazione.operatori.disabilita_reason.ultimo_super_admin",
    "can_demote_super_admin": false,
    "demote_reason": "ULTIMO_SUPER_ADMIN",
    "demote_reason_key": "amministrazione.operatori.rimuovi_super_admin_reason.ultimo_super_admin",
    "can_set_valido_al": false,
    "valido_al_reason": "ULTIMO_SUPER_ADMIN",
    "valido_al_reason_key": "amministrazione.operatori.valido_al_reason.ultimo_super_admin"
  },
  "meta": { "request_id": "..." }
}
```

**Campi multi-face (Fase 1):**

| Campo | Tipo | Descrizione |
|---|---|---|
| `is_super_admin` | bool | `true` se l'identita ha binding `SUPER_ADMIN` attivo (`config.profili_accesso_bindings`, profilo seed id 9100) |
| `ruolo_applicativo` | string | Il tipo della veste OPERATORE di riferimento. ⛔ Dal 2026-10-02 mai `DISABILITATO`: spenta, la veste tiene il tipo (`veste_attiva = false`) |
| `veste_attiva` | bool \| null | Lo stato della veste OPERATORE di riferimento (R-9) |
| `last_login` | timestamptz \| null | Ultimo login (`auth_user.last_login`); NULL se mai loggato |
| `invito_inviato_at` | timestamptz \| null | Quando e' stato spedito l'ultimo invito (`identita_digitali.invito_inviato_at`) |
| `deve_cambiare_password` | bool | Force-reset password al prossimo login |
| `emittenti_descrizione` | string \| null | Lista descrizioni emittenti scope, concatenate con virgola+spazio |

**Capability data-driven (Fase 1):**

| Campo | Tipo | Descrizione |
|---|---|---|
| `can_invite` | bool | True se l'operatore e' invitabile (nessuna veste OPERATORE gia' accesa, una sola veste OPERATORE, veste nella sua finestra, email presente). Delega a `script.fn_check_operatore_invitabile` |
| `invite_reason` / `invite_reason_key` | string \| null | Codice macchina del primo motivo (`UTENTE_NON_TROVATO`, `SENZA_VESTE_OPERATORE`, `VESTE_GIA_ATTIVA`, `PIU_VESTI_SPENTE`, `VESTE_FUORI_FINESTRA`, `SENZA_EMAIL`) e chiave i18n della frase; NULL quando `can_invite=true` |
| `can_disable` | bool | False se e' l'unico super admin attivo. Preview di `script.fn_check_ultimo_super_admin_attivo`; **non e' una garanzia** (race tra sessioni: il trigger DB resta l'autorita') |
| `disable_reason` / `disable_reason_key` | string \| null | `ULTIMO_SUPER_ADMIN` e la sua chiave i18n quando `can_disable=false` |
| `can_demote_super_admin` | bool \| null | Stesso check di `can_disable` ma per la rimozione del binding SUPER_ADMIN. **NULL** se l'operatore non e' SUPER_ADMIN (azione non applicabile -> il FE nasconde l'azione) |
| `demote_reason` / `demote_reason_key` | string \| null | Motivo quando `can_demote_super_admin=false` |
| `can_set_valido_al` | bool | Si puo' mettere una data di fine al rapporto (`valido_al`). Stessa condizione di `can_disable` (l'ultimo SUPER_ADMIN senza scadenza); chi ha gia' una data di fine risponde `true` |
| `valido_al_reason` / `valido_al_reason_key` | string \| null | Motivo quando `can_set_valido_al=false` |

> I `*_reason` sono **codici macchina**, non frasi: il testo lo compone il FE
> dalla `*_reason_key` (api.md §«Capability di riga»).

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/"
```

---

### 1.4 PATCH /api/v1/amm-software/operatori/{id}/ -- Aggiorna utente

Aggiorna i campi modificabili di un utente. Solo i campi presenti nel payload vengono modificati.
Dopo la modifica, la cache permessi dell'utente viene invalidata.

**Contract Fase 1 multi-face**: il payload accetta `is_super_admin` + `attivo`.
Il campo legacy `ruolo_sistema` e' **rifiutato** con `E_AMM_VALIDAZIONE`. I due
flag sono ortogonali, e nessuno dei due si traduce in `ruolo_sistema`:

- `attivo: false` è **«Disabilita»** (§1.5, dal 2026-10-04): la stessa scrittura —
  veste OPERATORE di riferimento spenta, risorsa umana chiusa con
  `valido_al = oggi`, sync di `is_active` — eseguita dopo gli altri campi del
  payload (un `valido_al` nello stesso payload lo sovrascrive la chiusura).
  Fino a quel giorno l'interruttore lasciava `valido_al` com'era. Sulla veste:
  **solo** `attivo`, il tipo resta (R-DB-1, 2026-10-02 — prima lo spegnimento scriveva
  `DISABILITATO`, e la tabella oggi lo rifiuta con `E_RUOLO_APPLICATIVO_RITIRATO`).
  ⛔ **Non la riaccende** (D-3, 2026-10-04): una veste spenta si riattiva col
  reinvio dell'invito (§«Invito operatore»), e la accende la persona attivando
  il link.
- `is_super_admin` lega o slega il profilo SUPER_ADMIN sulla stessa veste
- payload senza `is_super_admin` ne' `attivo` → nessuno dei due tocchi

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON (tutti opzionali):**

| Campo | Tipo | Descrizione |
|---|---|---|
| `email` | string | Nuovo indirizzo email |
| `first_name` | string | Nuovo nome (auth_user) |
| `last_name` | string | Nuovo cognome (auth_user) |
| `is_super_admin` | bool | `true` per binding profilo SUPER_ADMIN, `false` per rimuoverlo. Solo booleano JSON |
| `attivo` | bool | Solo booleano JSON. Stato della veste OPERATORE (`veste_attiva` del dettaglio). Conta solo come transizione: `false` su una veste accesa la spegne come «Disabilita» (risorsa umana chiusa a oggi); `false` su una veste già spenta e `true` su una accesa non cambiano niente; `true` su una veste spenta → 400 `E_AMM_VALIDAZIONE` (`field: attivo`) |
| `unita_organizzativa_id` | int | Nuova unita' organizzativa |
| `valido_al` | string \| null | Data fine del rapporto (formato `YYYY-MM-DD`): `null` la toglie, chiave assente non la tocca |

**Regole:**

- Il payload con `ruolo_sistema` viene rifiutato con `E_AMM_VALIDAZIONE` (HTTP 400).
- Una chiave fuori dalla tabella sopra e un corpo senza campi → 400
  `E_AMM_VALIDAZIONE` (dal 2026-10-20: prima la chiave si scartava e il corpo
  vuoto rispondeva 200 senza scrivere).
- `attivo` e `is_super_admin` vogliono un booleano JSON: `"true"`, `"false"`,
  `1`, `0` sono un 400 `E_AMM_VALIDAZIONE` col campo (2026-10-20: prima un
  valore non booleano passava in silenzio e il PATCH rispondeva 200 senza
  toccare niente).
- `is_super_admin: true` su un accesso che ha gia' un altro profilo legato
  (un'identita' ne lega uno solo) → 400 `E_AMM_VALIDAZIONE`, `field:
  is_super_admin`: va tolto prima quel profilo.
- ⛔ `attivo: true` su una veste spenta (disabilitata, o mai attivata) viene
  rifiutato con `E_AMM_VALIDAZIONE` (HTTP 400, `field: attivo`), senza
  scrivere niente (D-3, 2026-10-04): l'accesso si riattiva col reinvio
  dell'invito. Fino a quel giorno lo riaccendeva subito, all'insaputa della
  persona.
- Se la modifica equivale alla rimozione dell'**ultimo super admin attivo**,
  il trigger DB `trgfn_profili_accesso_bindings_guard_ultimo_super_admin`
  blocca con `E_PROFILO_ULTIMO_SUPER_ADMIN` (HTTP 409) — vedi sezione "Errori".
- Se `is_super_admin` viene modificato, o la veste si spegne (dentro
  «Disabilita»), viene chiamata `anagrafiche.fn_sync_auth_user_is_active` per
  sincronizzare `auth_user.is_active`
- La cache permessi dell'utente viene invalidata dopo ogni modifica
- `attivo: false` (l'interruttore «Accesso attivo») spegne come §1.5: invalida
  gli inviti pendenti e chiude le sessioni della **sola veste operatore** nella
  stessa transazione, e la cache si invalida a commit avvenuto (A-5, D-5,
  2026-10-02 — prima solo la cache). ⛔ **Solo se la veste passa da accesa a
  spenta** (`veste_attiva` del dettaglio): il drawer manda `attivo` a ogni
  salvataggio, e salvare un operatore già spento non invalida l'invito spedito
  per riaccenderlo (D-3), e non richiude la risorsa umana che l'invito ha
  riaperto. `attivo: true` su una veste accesa o un payload senza `attivo` non
  chiudono sessioni

**Risposta:** dettaglio utente aggiornato (stesso formato di GET §1.3).

**Esempio curl:**

```bash
curl -X PATCH -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"is_super_admin": true, "unita_organizzativa_id": 3}' \
  "https://host/api/v1/amm-software/operatori/1/"
```

---

### 1.5 POST /api/v1/amm-software/operatori/{id}/disabilita/ -- Disabilita utente

Disabilita un utente: la veste OPERATORE di riferimento `attivo=false` (il tipo
resta, R-DB-1), la sua risorsa umana `attivo=false`+`valido_al=oggi`. Sincronizza `auth_user.is_active`,
invalida la cache permessi a commit avvenuto, invalida gli **inviti operatore
pendenti** di quella veste (A-5, 2026-10-02: prima un invito in volo poteva
ancora riaccenderla) e mette in blacklist le sessioni della **sola veste
operatore** (refresh JWT col claim `identita_id` di quella veste), nella stessa
transazione: una chiusura fallita annulla anche la disabilitazione. Le sessioni delle altre vesti della credenziale (shop,
portale) restano aperte (D-5, 2026-10-02 — prima si chiudevano **tutte**).

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload:** nessuno.

**Guard "ultimo super admin"**: il preview lato Python legge `can_disable`
dal detail (Fase 1) ed evita il round-trip se l'utente e' l'unico SA attivo
(short-circuit con `E_PROFILO_ULTIMO_SUPER_ADMIN`). In caso di race tra
sessioni, il trigger DB `trgfn_profili_accesso_bindings_guard_ultimo_super_admin`
e' l'autorita' finale: il service traduce il `DatabaseError` in
`ServiceError(E_PROFILO_ULTIMO_SUPER_ADMIN)` preservando il code per
l'envelope errore (HTTP 409).

**Regole:**

- Ordine disattivazione: figlio (`identita_digitali`) prima del padre
  (`risorse_umane`) per rispettare il framework ATTIVO del DB.
- Chiama `anagrafiche.fn_sync_auth_user_is_active` per sincronizzare
  `auth_user.is_active`.
- Invalida la cache permessi dell'utente (a commit avvenuto).
- Blacklist dei refresh JWT della **sola veste operatore**; una chiusura
  fallita annulla anche la disabilitazione.

> ✅ Chiuso M-5 (2026-10-02): si spegne la sola veste operatore e si chiudono
> le sole sue sessioni; le vesti portale e shop della stessa credenziale
> restano come sono, connesse.

**Risposta:** dettaglio utente aggiornato (con `attivo=false`,
`veste_attiva=false`, `ruolo_applicativo="OPERATORE"`; `is_active` resta `true`
se la credenziale ha un'altra veste accesa).

**Esempio curl:**

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/disabilita/"
```

---

### 1.6 ~~POST /api/v1/amm-software/operatori/{id}/riattiva/~~ -- Ritirato (D-3)

⛔ **Ritirato il 2026-10-04** (decisione D-3 di Tid, piano accessi L-5): la rotta
non esiste più, e nemmeno la riattivazione via PATCH `attivo: true` (§1.4).
Un operatore spento si riattiva col **reinvio dell'invito**
(`POST operatori/{id}/reinvia-invito/`, [api_invito_operatore.md](../../core/manual/api_invito_operatore.md)):

- il gesto dell'amministratore riapre la **risorsa umana** (il rapporto:
  `attivo=true`, `valido_al=NULL`, `valido_dal` intatto) nella transazione
  dell'emissione del token;
- la **veste** (la porta) resta spenta finché la persona non attiva il link;
  chi ha già una password lo fa con un clic (token CROSS).

Il perché: nessuna veste torna attiva senza che la persona lo sappia.
L'endpoint ritirato riscriveva anche `valido_dal = oggi`, perdendo l'inizio
del rapporto. Il binding SUPER_ADMIN, come prima, non si ripristina da sé.

---

> ⛔ **Tutte le rotte `operatori/{id}/…` valgono per le sole credenziali di
> categoria `OPERATORE`** (dal 2026-10-02): un cliente del portale o l'utente
> tecnico di un processo rispondono `E_AMM_OPERATORE_NOT_FOUND` (404) come un id
> inesistente. Senza, i comandi spegnerebbero la veste OPERATORE di una
> macchina — la sua veste e' `OPERATORE` con `tecnica`, e fermarla e' affare
> del pannello dei processi (A-6).
>
> La regola vale anche per `override-aree/`, `override-azioni/` e
> `override-oggetti/`, in GET e PUT (2026-10-20: prima un id non operatore
> riceveva una lista vuota, o gli override in scrittura).

---

## 1-bis. Area «Accessi» e azioni della credenziale

> Dal 2026-10-02 ([brief-db-be-fe-area-accessi](../../../dev/work-done/brief-db-be-fe-area-accessi.md)).
> La voce «Operatori» e' diventata l'area **«Accessi»**, tre schede che insieme
> censiscono TUTTE le credenziali, ognuna in una scheda sola: la partizione la
> decide il DB (`script.fn_categoria_accesso` → `OPERATORE` / `SISTEMA` /
> `ALTRO`) e nessuna lista la ricalcola. La prima scheda e' §1.1.

### 1-bis.1 GET /api/v1/amm-software/accessi/altri/ -- Altri accessi

Le credenziali di categoria `ALTRO`: clienti e fornitori del portale, clienti
dello shop, e le credenziali **senza alcuna veste** (`nessun_accesso = true`).
Legge `anagrafiche.vw_accessi_altri` (`v.*`: la vista e' il contratto), lista a
catalogo `anagrafiche.accessi_altri` (104). Envelope paginato standard
(`count`, `page`, `page_size`, `total_pages`, `results`).

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | string | Ricerca libera sulle colonne accese dal catalogo (nome, username, email, vesti, soggetti) |
| `ruolo_applicativo` | string | Una veste di quel tipo fra le vesti della credenziale (`CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`, …). `DISABILITATO` → 400 |
| `stato_accesso` | string | Il migliore fra le vesti: `ATTIVO`, `PENDING`, `NON_SPEDITO`, `DISATTIVO`, `NESSUNO`. Estraneo → 400 |
| `nessun_accesso` | bool | Nessuna veste |
| `secondo_fattore_stato` | string | `ASSENTE`, `DA_CONFERMARE`, `ATTIVO` |
| `secondo_fattore_obbligatorio` | bool | |
| `bloccata` | bool | Blocco dell'amministratore |
| `limit` / `offset` / `order_by` / `order_dir` | | Ordinabili: `nome_visualizzato` (default), `username`, `stato_accesso`, `nessun_accesso`, `secondo_fattore_stato`, `bloccata`, `ultimo_accesso` (senza verso: dal piu' recente) |

Riga: `auth_user_id`, `username`, `email`, `nome`, `cognome`,
`nome_visualizzato`, **`vesti`** (lista, una voce per veste anche spenta:
`identita_id`, `ruolo_applicativo`, `stato` di `script.fn_stato_veste`,
`attivo`, validita', `invito_inviato_at`, `token_scade_at`, `soggetto_id`,
`soggetto_ruolo_id`, `soggetto`, **`cliente_ids` (array)**, `fornitore_id`),
`vesti_elenco`, `soggetti_elenco`, `nessun_accesso`, `stato_accesso`,
`is_active`, `secondo_fattore_stato`, `secondo_fattore_obbligatorio`,
`bloccata`, `bloccata_dal`, `motivo_blocco`, `ultimo_accesso`, e la capability
dell'eliminazione **`can_delete`**, `delete_reason`, `delete_reason_key`,
`delete_dettaglio` (§1-bis.3: il kebab della riga la legge). ⚠️ La check gira
per riga filtrata; con una veste esce subito, quindi la ricerca della storia
tocca le sole credenziali senza vesti.

⚠️ `cliente_ids` e' un array perche' un soggetto_ruolo puo' avere piu' schede
cliente (una per istanza utility): il FE con una apre quella scheda, con piu'
d'una la scheda del soggetto. ⚠️ La vista attraversa `anagrafiche.clienti`
(RLS): la legge la richiesta, con le sue GUC.

### 1-bis.2 GET /api/v1/amm-software/accessi/sistema/ -- Accessi di sistema

Le credenziali di categoria `SISTEMA`: gli utenti tecnici dei processi
automatici (`tipo = PROCESSO`, con `processo_id`/`processo_codice` da aprire) e
i sistemi esterni (`tipo = API_CLIENT`, senza processo). **Sola lettura** (A-6):
il proprietario e' il pannello dei processi. Legge
`anagrafiche.vw_accessi_sistema`, lista `anagrafiche.accessi_sistema` (105,
`multi_emittente`: l'emittente per riga). Filtri `search`, `tipo`
(`PROCESSO`/`API_CLIENT`, estraneo → 400), `emittente_fiscale_id`,
`identita_attiva`, `bloccata`. Ordinabili: `username` (default), `tipo`,
`processo_codice`, `emittente_codice`, `emittente_ragione_sociale`,
`identita_attiva`, `bloccata`, `ultimo_accesso`.

⛔ I verbi dell'amministratore rifiutano una credenziale di questa categoria
con `E_CREDENZIALE_DI_SISTEMA` (409): il blocco (§1-bis.4) e l'**accensione**
dell'obbligo del secondo fattore (§1-bis.6). Restano aperte le uscite: lo
sblocco, lo spegnimento dell'obbligo, la rimozione di un device registrato per
errore. Il blocco d'emergenza di una credenziale di sistema compromessa si fa
dal server (sessione del migratore), non dall'app.

### 1-bis.3 GET /api/v1/amm-software/credenziali/{id}/ -- Stato della credenziale

```json
{ "data": {
  "auth_user_id": 7, "username": "cliente7", "email": null,
  "categoria": "ALTRO",
  "bloccata": true, "bloccata_dal": "2026-10-02T10:00:00+00:00",
  "bloccata_da": "tid", "motivo_blocco": "abuso",
  "can_block": true, "block_reason": null, "block_reason_key": null,
  "can_delete": false, "delete_reason": "CON_VESTI",
  "delete_reason_key": "amministrazione.accessi.elimina_reason.con_vesti",
  "delete_dettaglio": {"auth_user_id": 7}
} }
```

`can_block`, `block_reason`, `block_reason_key` sono il **primo motivo** di
`script.fn_check_credenziale_bloccabile`, la stessa check che il verbo del blocco
chiama prima di scrivere: pulsante spento e rifiuto dicono la stessa cosa.
Motivi e chiavi sono del DB; in ordine:

| `block_reason` | `block_reason_key` | Quando |
| --- | --- | --- |
| `CREDENZIALE_DI_SISTEMA` | `amministrazione.accessi.blocca_reason.credenziale_di_sistema` | credenziale di categoria `SISTEMA` |
| `ULTIMO_SUPER_ADMIN` | `amministrazione.accessi.blocca_reason.ultimo_super_admin` | ultimo SUPER_ADMIN raggiungibile |

`can_delete`, `delete_reason`, `delete_reason_key`, `delete_dettaglio` sono allo
stesso modo il primo motivo di `script.fn_check_credenziale_eliminabile`, la check
del verbo di §1-bis.5-bis (dal 2026-10-07). In ordine, e il primo vince:

| `delete_reason` | `delete_reason_key` | Quando |
| --- | --- | --- |
| `CON_VESTI` | `amministrazione.accessi.elimina_reason.con_vesti` | almeno una veste, anche spenta: con questo motivo la storia non si cerca |
| `STORIA_NON_VERIFICABILE` | `amministrazione.accessi.elimina_reason.storia_non_verificabile` | manca la FK di `identita_digitali` verso `django.auth_user` (installazione nuova, CI): fail-closed |
| `CON_STORIA` | `amministrazione.accessi.elimina_reason.con_storia` | una riga la tiene con una FK `RESTRICT`/`NO ACTION`; `delete_dettaglio.dove` e' l'**array** delle tabelle `schema.tabella` (il FE lo unisce in testo per la frase) |

Credenziale inesistente → 404
`E_CREDENZIALE_NON_TROVATA`. Il blocco si legge da `config.credenziali`
(leggibile dall'app; le scritture passano dai verbi).

### 1-bis.4 POST /api/v1/amm-software/credenziali/{id}/blocca/ -- Blocca

Corpo `{"motivo": "…"}`, **`Idempotency-Key` obbligatoria**. Chiama
`script.fn_blocca_credenziale` (SUPER_ADMIN alla prima riga, motivo obbligatorio
→ `E_CREDENZIALE_MOTIVO_OBBLIGATORIO`, poi il primo motivo della check di §1-bis.3:
credenziale di sistema → `E_CREDENZIALE_DI_SISTEMA`, anti-lockout →
`E_PROFILO_ULTIMO_SUPER_ADMIN`, entrambi 409)
e mette in blacklist **tutte** le sessioni della credenziale, nella stessa
transazione: un blocco con le sessioni vive non e' un blocco. Il blocco vale su
tutte le porte, non scade, il reset password non lo toglie. Risposta: lo stato
di §1-bis.3.

### 1-bis.5 POST /api/v1/amm-software/credenziali/{id}/sblocca/ -- Sblocca

Nessun corpo, `Idempotency-Key` obbligatoria. `script.fn_sblocca_credenziale`:
idempotente, non tocca i tentativi; le sessioni chiuse dal blocco non si
riaprono. Risposta: lo stato di §1-bis.3.

### 1-bis.5-bis DELETE /api/v1/amm-software/credenziali/{id}/ -- Elimina

Dal 2026-10-07 (brief-db-elimina-credenziale-senza-veste): il gesto che il
presidio `dbops.vw_credenziali_da_sanare` chiede per `NESSUNA_VESTE`. Nessun
corpo, **`Idempotency-Key` obbligatoria** (irreversibile: senza, il doppio invio
riceverebbe un 404 per un'operazione riuscita). Credenziale inesistente → 404
`E_CREDENZIALE_NON_TROVATA` prima del verbo. Chiama `script.fn_elimina_credenziale`:
SUPER_ADMIN alla prima riga, lock sulla riga di `auth_user`, primo motivo della
check di §1-bis.3, traccia in `config.credenziali_eliminate` (chi, quando, id,
username, email), poi il `DELETE` (le righe che le appartengono seguono in
`CASCADE`). Rifiuti, col codice del DB:

| Codice | Status | Quando |
| --- | --- | --- |
| `E_CREDENZIALE_CON_VESTI` | 409 | `CON_VESTI` (anche una veste nata durante il gesto: il lock la vede) |
| `E_CREDENZIALE_CON_STORIA` | 409 | `CON_STORIA`: il messaggio nomina le tabelle |
| `E_CREDENZIALE_STORIA_NON_VERIFICABILE` | 500 | `STORIA_NON_VERIFICABILE` (TECNICO: rimedia chi amministra il database) |

Risposta `{"status": "ok", "auth_user_id": 7}`. Nessuna sessione da chiudere: una
credenziale senza vesti non entra da nessuna porta. ⛔ L'app **non ha** il
`DELETE` su `django.auth_user`: questa e' l'unica strada.

### 1-bis.6 Secondo fattore della credenziale

`GET credenziali/{id}/secondo-fattore/`, `POST …/obbligo/` (`{valore}`),
`POST …/disattiva/` (`{motivo}`): stesso contratto di prima
([api_secondo_fattore](../../core/manual/api_secondo_fattore.md)), nuova sede.
⛔ Fino al 2026-10-02 stavano sotto `operatori/{id}/secondo-fattore/`: ritirate
nello stesso giro (il secondo fattore e' della credenziale, e un cliente del
portale non si raggiungeva da li').
Su una credenziale di sistema `POST …/obbligo/` con `valore = true` → 409
`E_CREDENZIALE_DI_SISTEMA` (una macchina non ha un telefono); `valore = false` e
`…/disattiva/` passano.

---

## 2. Permessi utente

### 2.1 GET /api/v1/amm-software/operatori/{id}/override-aree/ -- Lista override aree

Restituisce gli override del livello di accesso alle aree funzionali per un utente.
Gli override permettono di aumentare o ridurre il livello di accesso rispetto al
profilo del reparto di appartenenza.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "results": [
      {
        "id": 10,
        "area_id": 3,
        "area_codice": "VENDITE",
        "area_descrizione": "Gestione vendite",
        "livello": "TUTTO",
        "motivo": "Responsabile vendite",
        "valido_dal": "2026-01-01",
        "valido_al": null
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/override-aree/"
```

---

### 2.2 PUT /api/v1/amm-software/operatori/{id}/override-aree/ -- Salva override aree

Sostituisce completamente gli override aree di un utente (semantica replace: cancella
tutti gli esistenti e inserisce i nuovi). Invalida la cache permessi.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON:**

```json
{
  "items": [
    {
      "area_id": 3,
      "livello": "TUTTO",
      "motivo": "Responsabile vendite",
      "valido_dal": "2026-01-01",
      "valido_al": null
    }
  ]
}
```

| Campo item | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `area_id` | int | si | ID area funzionale |
| `livello` | string | si | Livello accesso (enum `config.livello_accesso`: `TUTTO`, `LETTURA`, `BLOCCATO`) |
| `motivo` | string | no | Motivazione dell'override |
| `valido_dal` | string | no | Data inizio validita' |
| `valido_al` | string | no | Data fine validita' |

`items` dev'essere una lista di oggetti; `area_id` (intero positivo) e
`livello` sono obbligatori. Altrimenti 400 `E_AMM_VALIDAZIONE` col campo
(2026-10-20: prima una voce malformata era un 500).

**Risposta:** lista aggiornata degli override aree (stesso formato del GET).

**Esempio curl:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"area_id": 3, "livello": "TUTTO", "motivo": "Promozione"}]}' \
  "https://host/api/v1/amm-software/operatori/1/override-aree/"
```

---

### 2.3 GET /api/v1/amm-software/operatori/{id}/override-azioni/ -- Lista override azioni

Restituisce gli override sulle singole azioni di processo per un utente.
Permette di abilitare o disabilitare specifiche azioni indipendentemente dal
profilo del reparto.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "results": [
      {
        "id": 5,
        "azione_id": 12,
        "permission_codename": "fattura.emetti",
        "azione_descrizione": "Emetti fattura",
        "area_codice": "VENDITE",
        "abilitata": true,
        "motivo": "Delega temporanea",
        "valido_dal": "2026-03-01",
        "valido_al": "2026-06-30"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/override-azioni/"
```

---

### 2.4 PUT /api/v1/amm-software/operatori/{id}/override-azioni/ -- Salva override azioni

Sostituisce completamente gli override azioni di un utente (semantica replace).
Invalida la cache permessi.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON:**

```json
{
  "items": [
    {
      "azione_id": 12,
      "abilitata": true,
      "motivo": "Delega temporanea",
      "valido_dal": "2026-03-01",
      "valido_al": "2026-06-30"
    }
  ]
}
```

| Campo item | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `azione_id` | int | si | ID azione processo |
| `abilitata` | bool | si | `true` per abilitare, `false` per disabilitare (solo booleano JSON) |
| `motivo` | string | no | Motivazione dell'override |
| `valido_dal` | string | no | Data inizio validita' |
| `valido_al` | string | no | Data fine validita' |

`items` dev'essere una lista di oggetti; `azione_id` (intero positivo) e
`abilitata` (booleano) sono obbligatori. Altrimenti 400 `E_AMM_VALIDAZIONE`
col campo (2026-10-20: prima una voce malformata era un 500).

**Risposta:** lista aggiornata degli override azioni (stesso formato del GET).

**Esempio curl:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"azione_id": 12, "abilitata": true, "motivo": "Delega"}]}' \
  "https://host/api/v1/amm-software/operatori/1/override-azioni/"
```

---

### 2.4-bis GET / PUT /api/v1/amm-software/operatori/{id}/override-oggetti/ -- Override oggetti

Gli override del livello di accesso su un singolo **oggetto** (model) del
catalogo `config.area_model_overrides`. Stessa regola delle altre rotte
`operatori/{id}/…` (404 `E_AMM_OPERATORE_NOT_FOUND` se l'id non e' un
operatore).

**GET** → `data.results`, una riga per override: `id`, `app_label`,
`model_name`, `livello`, `motivo`, `valido_dal`, `valido_al`, `area_id`,
`area_descrizione` (ordine: area, `app_label`, `model_name`).

**PUT** → sostituisce tutti gli override oggetto dell'operatore (semantica
replace, `config.fn_imposta_override_oggetti`) e invalida la cache permessi.
Risposta: la lista aggiornata (forma del GET).

```json
{ "items": [ { "app_label": "anagrafiche", "model_name": "conto_bancario",
               "livello": "LETTURA", "motivo": "Sola consultazione",
               "valido_dal": null, "valido_al": null } ] }
```

| Campo item | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `app_label` / `model_name` | string | si | Oggetto registrato nel catalogo (lookup §4.8) |
| `livello` | string | si | `TUTTO`, `LETTURA`, `BLOCCATO` |
| `motivo` | string | no | |
| `valido_dal` / `valido_al` | string \| null | no | `null` = senza inizio / senza fine |

**Errori** (tutti 400 `E_AMM_VALIDAZIONE`): `items` non lista o voce non
oggetto; `livello` mancante; oggetto non registrato nel catalogo; oggetto
riservato al kernel dei permessi (`can_override = false`). Lo stesso codice
traduce la FK `fk_user_override_oggetti_catalogo` se il catalogo cambia fra
lettura e scrittura.

---

### 2.5 GET /api/v1/amm-software/operatori/{id}/emittenti-scope/ -- Scope emittenti dichiarativo

**Contract Fase 2 multi-face**. Restituisce lo scope emittenti dichiarativo
dell'utente con capability data-driven. Sostituisce il vecchio shape "lista
grezza" che lasciava al FE l'interpretazione (vuoto = tutti, 1+ = whitelist).

Sorgente: `script.fn_get_user_emittenti_scope(p_auth_user_id)`. Single-row.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "scope_mode": "SINGLE",
    "emittenti_ids": [42],
    "emittente_descrizione": "Sede Roma",
    "allowed_scope_modes": ["GLOBAL", "SINGLE"],
    "can_change_scope": true,
    "change_scope_reason": null
  },
  "meta": { "request_id": "..." }
}
```

**Campi risposta:**

| Campo | Tipo | Descrizione |
|---|---|---|
| `scope_mode` | enum | `GLOBAL` (vede tutti gli emittenti) o `SINGLE` (vede solo `emittenti_ids[0]`). `MULTI` chiuso architetturalmente post Q2 (`UNIQUE(auth_user_id)` su `config.user_emittenti_fiscali`) |
| `emittenti_ids` | array[int] | `[]` se GLOBAL, `[id]` se SINGLE. Array per simmetria payload (preparazione futura) |
| `emittente_descrizione` | string \| null | Descrizione emittente quando SINGLE; NULL se GLOBAL |
| `allowed_scope_modes` | array[string] | Sempre `["GLOBAL", "SINGLE"]` post Q2. Il FE mostra solo i radio ammessi |
| `can_change_scope` | bool | False sse l'operatore e' SUPER_ADMIN e l'unico attivo (delega a `fn_check_ultimo_super_admin_attivo`). Preview UX, non garanzia |
| `change_scope_reason` | string \| null | Motivo it-IT free-form quando `can_change_scope=false` |

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/emittenti-scope/"
```

---

### 2.6 PUT /api/v1/amm-software/operatori/{id}/emittenti-scope/ -- Cambia scope

**Contract Fase 2 multi-face**. Cambio scope atomico via
`script.fn_change_user_emittenti_scope`. Sostituisce il vecchio payload
`{emittente_ids: [...]}` con shape dichiarativo `{scope_mode, emittenti_ids}`.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON:**

```json
{
  "scope_mode": "SINGLE",
  "emittenti_ids": [42]
}
```

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `scope_mode` | enum | si | `GLOBAL` o `SINGLE`. Altri valori (incluso `MULTI`) -> `E_AMM_SCOPE_NON_AMMESSO` (HTTP 400) |
| `emittenti_ids` | array[int] | dipende | Vuoto/omesso se GLOBAL. Esattamente 1 elemento int>0 se SINGLE. Lista con 0 o ≥2 elementi su SINGLE -> `E_AMM_SCOPE_NON_AMMESSO` |

**Regole:**

- `GLOBAL`: `emittenti_ids` viene ignorato e normalizzato a `[]` lato service.
- `SINGLE`: `emittenti_ids` deve contenere esattamente 1 int positivo.
- **Guard ultimo super admin**: integrato nella fn DB
  `fn_change_user_emittenti_scope`. Se l'operatore e' SUPER_ADMIN globale e
  l'unico attivo, il cambio scope -> SINGLE viene rifiutato con
  `E_PROFILO_ULTIMO_SUPER_ADMIN` (HTTP 409). Il preview `can_change_scope`
  lato detail e' fast-path UX, non garanzia (race tra sessioni).
- Invalida la cache permessi dell'utente.

**Risposta:** stesso shape del GET §2.5 con i valori post-change (rilettura
da `fn_get_user_emittenti_scope` per consistenza).

**Esempio curl — cambio a GLOBAL:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"scope_mode": "GLOBAL"}' \
  "https://host/api/v1/amm-software/operatori/1/emittenti-scope/"
```

**Esempio curl — cambio a SINGLE su emittente 42:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"scope_mode": "SINGLE", "emittenti_ids": [42]}' \
  "https://host/api/v1/amm-software/operatori/1/emittenti-scope/"
```

---

### 2.7 GET /api/v1/amm-software/operatori/{id}/permessi-ereditati/ -- Livelli ereditati dal profilo

Restituisce i livelli che l'operatore **eredita dal profilo**, cioe' cosa avrebbe
**senza nessun override individuale**. Sola lettura: non cambia niente e non
tocca la semantica dei permessi.

⭐ **A cosa serve.** Alimenta la colonna «ereditato» del pannello permessi. Un
override che **ripete** il valore del profilo non e' rumore innocuo: **congela
la riga**, perche' da quel momento quell'utente non segue piu' il reparto se il
reparto cambia livello. Vedere l'ereditato accanto all'override e' cio' che
evita di scriverlo.

⛔ **Non e' `GET /reparti/{uo_id}/profilo/`, e la differenza non e' cosmetica.**
Quello legge il **solo** binding `REPARTO` per `unita_organizzativa_id`. I
bindings sono **tre** e i resolver prendono il primo per priorita':

| Priorita' | Tipo | Legato a |
| --- | --- | --- |
| **1** | `AD_HOC` | l'identita' digitale dell'utente |
| 2 | `REPARTO` | l'unita' organizzativa |
| 3 | `PORTALE` | il ruolo applicativo dell'identita' |

Per un utente con un binding `AD_HOC` la lettura per reparto darebbe un valore
**plausibile e sbagliato**, su una schermata di sicurezza. Questo endpoint legge
invece da `script.fn_get_permessi_ereditati_aree` / `fn_get_permessi_ereditati_azioni`,
che leggono `script.fn_get_profili_accesso_applicabili` per la veste `OPERATORE`:
**la stessa catena** che usano `fn_resolve_livello_area` e `fn_check_azione_processo`.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "aree": [
      {
        "area_id": 2,
        "area_codice": "vendite",
        "area_descrizione": "Vendite",
        "livello": "LETTURA",
        "profilo_nome": "Profilo reparto Amministrazione",
        "profilo_tipo": "REPARTO"
      }
    ],
    "azioni": [
      {
        "azione_id": 3,
        "permission_codename": "genera_fatture_lotti",
        "azione_descrizione": "Genera fatture lotti",
        "area_codice": "vendite",
        "abilitata": true,
        "profilo_nome": "Profilo reparto Amministrazione",
        "profilo_tipo": "REPARTO"
      }
    ]
  }
}
```

⚠️ **Una voce ASSENTE e' un dato, non un buco**: significa che *nessun profilo*
copre quell'area o quell'azione, quindi vale il **default** — `BLOCCATO` per le
aree, azione **negata** per le azioni. Un utente senza profili applicabili
riceve due liste vuote, e va rappresentato come «default», non come «vuoto».

ℹ️ **Nessuna chiave `oggetti`**, ed e' voluto: `config.profili_accesso_oggetti`
non esiste. La catena di un model e' *override oggetto -> override area ->
profilo dell'**area** -> BLOCCATO*, quindi l'ereditato di un oggetto e' il
livello della sua **area**, che il chiamante ha gia' nella chiave `aree`.
Restituirlo anche qui sarebbe una seconda risposta alla stessa domanda, con due
posti in cui sbagliarla.

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/permessi-ereditati/"
```

---

### 2.8 GET /api/v1/amm-software/operatori/{id}/permessi-effettivi/ -- Permessi effettivi col tetto d'area

Restituisce, per ogni **azione di processo attiva** e per ogni **oggetto del
catalogo** `config.area_model_overrides`, il valore che l'operatore ha
**davvero**: la catena individuale (override, profilo) sotto il **tetto
dell'area** (guida di architettura dei permessi §3). Sola lettura.

⭐ **A cosa serve.** Un override piu' permissivo della sua area resta scritto
ma **dormiente**: non vale finche' l'area non si riapre. Il pannello permessi
lo mostra con l'etichetta «limitata dall'area»; senza questa lettura
mostrerebbe «abilitata» su un'azione che il sistema nega.

⛔ **Non e' `GET /api/v1/core/users/{id}/permessi-effettivi/`**, il riepilogo
per area senza azioni. Il calcolo sta a DB
(`script.fn_get_permessi_effettivi_azioni` / `..._oggetti`): sono la stessa
catena che usano i resolver del backend e le mappe di `/me/`, non una copia.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "azioni": [
      {
        "azione_id": 3,
        "permission_codename": "genera_fatture_lotti",
        "area_id": 2,
        "abilitata_specifica": true,
        "livello_area": "BLOCCATO",
        "livello_minimo_area": "TUTTO",
        "abilitata": false,
        "limitata_da_area": true
      }
    ],
    "oggetti": [
      {
        "app_label": "anagrafiche",
        "model_name": "conto_bancario",
        "area_schema_db": "anagrafiche",
        "livello_override": "TUTTO",
        "livello_area": "LETTURA",
        "livello_specifico": "TUTTO",
        "livello": "LETTURA",
        "limitato_da_area": true
      }
    ]
  }
}
```

| Campo | Significato |
| --- | --- |
| `abilitata_specifica` / `livello_specifico` | il valore **senza** tetto: override, poi profilo (azioni) o area (oggetti) |
| `livello_area` | il livello risolto dell'area della voce (per un oggetto: l'area **dell'oggetto**, `fn_area_di_oggetto`) |
| `livello_minimo_area` | il minimo che l'azione chiede alla sua area (`config.azioni_processo`) |
| `abilitata` / `livello` | il valore **applicato** |
| `limitata_da_area` / `limitato_da_area` | `true` quando il tetto ferma il valore specifico: la voce e' dormiente |
| `livello_override` | l'override individuale valido sull'oggetto, `null` se non c'e' |

ℹ️ **Nessuna chiave `aree`**: il livello effettivo di un'area e' il suo
override o l'ereditato (§2.7), che il pannello ha gia'. I valori riflettono lo
stato **salvato**: il pannello li ricarica dopo ogni salvataggio di un
override. Un id inesistente risponde con l'errore di operatore non trovato,
non con «tutto negato».

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/permessi-effettivi/"
```

---

### 2.9 GET /api/v1/amm-software/permessi-riepilogo/ -- Riepilogo permessi per area

Le chip della lista operatori: per gli operatori **della pagina** una riga per
(operatore, area attiva) con il livello effettivo, gli override scritti e le
voci fermate dal tetto d'area (`script.fn_get_permessi_riepilogo_aree`).

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `auth_user_ids` | string | si | Id separati da virgola (interi positivi, duplicati ignorati), al massimo 200 |

**Risposta:** `data.results`, ogni riga `{auth_user_id, area_id, area_codice,
area_descrizione, livello, override_count, voci_limitate}`, ordinate per
operatore e ordinamento dell'area. Gli id che non sono di categoria
`OPERATORE` non producono righe.

**Errori:** 400 `E_AMM_VALIDAZIONE` (`field: auth_user_ids`) se il parametro
manca o e' vuoto, se un pezzo non e' un intero positivo, o oltre 200 id.

---

## 3. Reparti

### 3.1 GET /api/v1/amm-software/reparti/ -- Lista reparti

Restituisce la lista paginata delle unita' organizzative attive con conteggi
di configurazione (lista a catalogo `amm.reparti`, contratto di lista standard).

**Parametri di query:**

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | string | Ricerca libera su `descrizione`/`codice` (colonne accese a catalogo, soglia 1 carattere) |
| `limit` / `offset` | integer | Paginazione (default 25, massimo 200) |
| `order_by` | string | `descrizione` (default), `codice`, `profilo_aree_count`, `operatori_count`; fuori whitelist → **400** `E_VALIDATION_INPUT` (dal 2026-10-20) |
| `order_dir` | string | `asc` / `desc` |

Solo i reparti attivi (`attivo = true`).

**Risposta:**

```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 2,
        "codice": "DEV",
        "descrizione": "Sviluppo",
        "attivo": true,
        "profilo_aree_count": 5,
        "profilo_azioni_count": 12,
        "operatori_count": 8
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/reparti/"
```

---

### 3.2 GET /api/v1/amm-software/reparti/{uo_id}/profilo/ -- Profilo reparto

Restituisce il profilo permessi completo di un reparto: aree funzionali con livello
di accesso e azioni processo con stato abilitazione.

**Parametri path:** `uo_id` (int) -- ID unita' organizzativa.

**Risposta:**

```json
{
  "data": {
    "aree": [
      {
        "id": 1,
        "area_id": 3,
        "area_codice": "VENDITE",
        "area_descrizione": "Gestione vendite",
        "livello": "TUTTO"
      }
    ],
    "azioni": [
      {
        "id": 1,
        "azione_id": 12,
        "permission_codename": "fattura.emetti",
        "azione_descrizione": "Emetti fattura",
        "area_codice": "VENDITE",
        "abilitata": true
      }
    ],
    "richiede_secondo_fattore": false
  },
  "meta": { "request_id": "..." }
}
```

`richiede_secondo_fattore`: chi riceve il profilo del reparto deve usare il
secondo fattore; `false` se il reparto non ha ancora un profilo.

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/reparti/2/profilo/"
```

---

### 3.3 PUT /api/v1/amm-software/reparti/{uo_id}/profilo/ -- Salva profilo reparto

Sostituisce completamente il profilo permessi di un reparto (aree + azioni, semantica
replace). Invalida la cache permessi di **tutti gli operatori** del reparto.

**Parametri path:** `uo_id` (int) -- ID unita' organizzativa.

**Payload JSON:**

```json
{
  "aree": [
    { "area_id": 3, "livello": "TUTTO" },
    { "area_id": 5, "livello": "LETTURA" }
  ],
  "azioni": [
    { "azione_id": 12, "abilitata": true },
    { "azione_id": 15, "abilitata": false }
  ],
  "richiede_secondo_fattore": true
}
```

| Campo aree | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `area_id` | int | si | ID area funzionale |
| `livello` | string | si | Livello accesso (tipo enum `config.livello_accesso`) |

| Campo azioni | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `azione_id` | int | si | ID azione processo |
| `abilitata` | bool | si | `true` per abilitare, `false` per disabilitare |

| Campo radice | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `richiede_secondo_fattore` | bool | no | Obbligo del secondo fattore per chi riceve il profilo. Assente = invariato (profilo nuovo: `false`); se presente dev'essere un booleano JSON, altrimenti 400 `E_AMM_VALIDAZIONE` |

**Regole:**

- `aree` e `azioni` sono **obbligatorie** (la lista vuota esplicita svuota quella
  parte del profilo); assenti, o con una voce che non è un oggetto o senza un suo
  campo → 400 `E_AMM_VALIDAZIONE` col campo, prima di scrivere (dal 2026-10-21:
  prima una lista assente diventava vuota e svuotava il profilo con un 200, e una
  chiave mancante era un 500).
- `uo_id` inesistente → 400 `E_AMM_VALIDAZIONE` («Reparto inesistente»).
- Il profilo (tipo `REPARTO`, codice `REPARTO_<codice_interno>`) si scrive con
  `config.fn_scrivi_profilo_accesso` e si lega al reparto con
  `config.fn_lega_profilo_reparto`; `attivo` del profilo segue il reparto.
- La modifica impatta tutti gli operatori che appartengono al reparto
- La cache permessi viene invalidata per l'intero reparto (`invalidate_department`)

**Risposta:** profilo reparto aggiornato (stesso formato del GET).

**Esempio curl:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "aree": [{"area_id": 3, "livello": "TUTTO"}],
    "azioni": [{"azione_id": 12, "abilitata": true}]
  }' \
  "https://host/api/v1/amm-software/reparti/2/profilo/"
```

---

## 4. Lookup

Endpoint di supporto per popolare dropdown e selettori nell'interfaccia di amministrazione.

### 4.1 GET /api/v1/amm-software/lookup/unita-organizzative/

Lista di tutte le unita' organizzative (anche inattive) per filtri e dropdown.

```json
{
  "data": {
    "results": [
      { "id": 2, "descrizione": "Sviluppo", "parent_id": 1 }
    ]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/unita-organizzative/"
```

---

### 4.2 GET /api/v1/amm-software/lookup/aree-funzionali/

Lista delle aree funzionali attive, ordinate per ordinamento e codice.

```json
{
  "data": {
    "results": [
      {
        "id": 3,
        "codice": "vendite",
        "codice_interno": "vendite",
        "schema_db": "vendite",
        "descrizione": "Gestione vendite",
        "ordinamento": 10
      }
    ]
  }
}
```

> **Tre chiavi distinte** (`config.aree_funzionali`): `codice` e' l'etichetta
> **mutabile** a video; `codice_interno` e' la chiave **immutabile**; `schema_db`
> e' la chiave tecnica (nome schema DB) su cui si risolvono i livelli di accesso
> via `script.fn_resolve_livello_area`. La **logica** (matrice permessi) usa
> `schema_db`, non `codice`.

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/aree-funzionali/"
```

---

### 4.3 GET /api/v1/amm-software/lookup/azioni-processo/

Lista delle azioni processo attive con area di appartenenza.

```json
{
  "data": {
    "results": [
      {
        "id": 12,
        "permission_codename": "fattura.emetti",
        "descrizione": "Emetti fattura",
        "pericolosa": false,
        "area_id": 3,
        "area_codice": "VENDITE"
      }
    ]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/azioni-processo/"
```

---

### 4.4 GET /api/v1/amm-software/lookup/emittenti-fiscali/

Lista degli emittenti fiscali attivi per la configurazione scope utente.
Ogni riga porta le **due** chiavi dell'emittente (`id` = PK di
`emittenti_fiscali`, `soggetto_ruolo_id` = il ruolo) e, dal 2026-09-21, il
**`soggetto_id`** (uuid di `anagrafiche.soggetti`): e' quello che il super
admin dentro un emittente usa per scegliere fra gli indirizzi dell'azienda
(`useEmittenteFiscaleField.soggettoIdSessione` → drawer del magazzino).
⚠️ Fino a quel giorno il FE lo leggeva da una colonna che la query non
proiettava: il pulsante «Scegli indirizzo» restava spento per l'admin, senza
nessun errore.

```json
{
  "data": {
    "results": [
      {
        "id": 10,
        "codice": "EMT001",
        "soggetto_ruolo_id": 77,
        "soggetto_id": "0190a1b2-0000-7000-8000-000000000001",
        "ragione_sociale": "Azienda SRL"
      }
    ]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/emittenti-fiscali/"
```

### 4.5 GET /api/v1/amm-software/lookup/rounding-modes/ -- (Fase 3)

Lookup statico dei modi di arrotondamento ammessi per `anagrafiche.emittenti_fiscali.rounding_policy`. Allineati al CHECK constraint `chk_emittenti_fiscali_rounding_policy`: 4 codici fissi (UP, DOWN, HALF_UP, HALF_DOWN). **Niente HALF_EVEN** (a differenza del lookup catalogo `/catalogo/lookup/rounding-modes/` che ne ha 5: UoM operativa ammette anche banker's rounding).

Single source of truth lato Python: `apps/amm_software/services/amm_software_service.py::_ROUNDING_MODE_VALIDI_EMITTENTE` + `_ROUNDING_MODE_DESCRIZIONI_EMITTENTE`. Nessuna tabella DB.

**Response shape**: `data` e' lista nuda (non envelope `{count, results}`).

```json
{
  "data": [
    { "codice": "HALF_UP",   "descrizione": "Arrotondamento meta' su (5 va su)",       "ordering": 1 },
    { "codice": "HALF_DOWN", "descrizione": "Arrotondamento meta' giu' (5 va giu')",  "ordering": 2 },
    { "codice": "UP",        "descrizione": "Arrotondamento sempre su (verso infinito)", "ordering": 3 },
    { "codice": "DOWN",      "descrizione": "Arrotondamento sempre giu' (verso zero)",  "ordering": 4 }
  ]
}
```

**Consumer FE**: `frontend/src/amministrazione/components/EmittenteRoundingModeSelect.vue` (wrapper riusabile cached con `useGlobalLookup('amm.emittenti_rounding_modes')`). Usato da `EmittenteFiscaleDrawer.vue` (campo `rounding_policy` testata) e `EmittenteFiscaleUtilitiesTab.vue` (campo `metodo_arrotondamento_importi` per riga utility).

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/rounding-modes/"
```

### 4.6 GET /api/v1/amm-software/lookup/audit-sources/ -- (Fase 5)

Lookup delle sorgenti audit ammesse per la timeline `audit-log`. Single source of truth lato DB: `script.vw_audit_sources`, gia' filtrata `attivo=true` e ordinata per `code`. Sostituisce il `buildAuditTabellaOptions` hardcoded del FE legacy. Cardinalita' bassa (8 righe attuali, +2 vs legacy: `user_override_oggetti` permessi v2 + `identita_digitali` multi-face). Niente paginazione.

**Response shape**: `data` e' lista nuda di `{code, label_key, area_funzionale}`.

- `code`: id semantico della sorgente (es. `user_override_aree`).
- `label_key`: chiave i18n FE (es. `amm.audit_tabella_override_aree`).
- `area_funzionale`: enum chiuso `PERMESSI` | `AUTH` | `ANAGRAFICHE` | `EMITTENTI` | `FATTURAZIONE`. Il FE puo' raggruppare il filtro per area se serve UI.

```json
{
  "data": [
    { "code": "identita_digitali",      "label_key": "amm.audit_tabella_identita",         "area_funzionale": "AUTH" },
    { "code": "profili_reparto_aree",   "label_key": "amm.audit_tabella_profilo_aree",     "area_funzionale": "PERMESSI" },
    { "code": "user_override_oggetti",  "label_key": "amm.audit_tabella_override_oggetti", "area_funzionale": "PERMESSI" }
  ]
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/audit-sources/"
```

### 4.7 ~~GET /api/v1/amm-software/lookup/email-log-stati/~~ -- RITIRATO il 2026-09-26

Il vocabolario degli stati del log email e' sceso in `core`
(`apps/core/services/email_constants.py::STATI_EMAIL_LOG_DESCRIZIONI`) e si
serve da `GET /api/v1/core/email/log/stati/`, aperto a chi apre la lista del
log — cioe' a ogni operatore, non piu' solo al super admin. Envelope
`{"data": {"results": [...]}}`. Dettaglio in
[api_email.md](../../core/manual/api_email.md) §«Endpoint Operatore — Log Email».
Il numero di sezione resta per non spostare i riferimenti.

### 4.8 GET /api/v1/amm-software/lookup/model-overrides/ -- (Fase 8)

Lookup catalogo dei `(app_label, model_name)` ammessi come target di
override v2 (livello model). Single source of truth: la tabella
`config.area_model_overrides`, che dichiara anche quali oggetti sono
**riservati** (colonna `riservato`, dal 2026-09-28).

**Capability**: ogni riga espone `can_override` (bool, `NOT riservato`) e
`reason` (chiave i18n o `null`). I model del kernel permessi
(`identita_digitali`, `profili_accesso` e le sue tre tabelle figlie,
`area_model_overrides`, `user_override_*`, `user_emittenti_fiscali`) hanno
`can_override=False` con reason `amm.model_override_reason_riservato`. Override
su questi model aprirebbero scenari di lockout ricorsivo.

**Il rifiuto è del DB.** La FK composita `fk_user_override_oggetti_catalogo`
lega ogni riga di `config.user_override_oggetti` a un oggetto a catalogo **e
non riservato**: il `PUT` degli override oggetti controlla prima per dare un
messaggio che nomina l'oggetto, e una violazione della FK (catalogo cambiato
nel frattempo, o scrittura fuori dal service) esce comunque come
`E_AMM_VALIDAZIONE`, non come 500. ⛔ Fino al 2026-09-28 l'elenco dei riservati
era una costante Python (`_MODEL_OVERRIDE_RISERVATI`), ritirata.

**Response shape**: lista in `data.results`. Ogni riga:

```json
{
  "id": 1,
  "app_label": "anagrafiche",
  "model_name": "conto_bancario",
  "area_schema": "anagrafiche",
  "area_descrizione": "Anagrafiche",
  "can_override": true,
  "reason": null
}
```

Esempio riga riservata (kernel permessi):

```json
{
  "id": 99,
  "app_label": "anagrafiche",
  "model_name": "auth_user",
  "area_schema": "anagrafiche",
  "area_descrizione": "Anagrafiche",
  "can_override": false,
  "reason": "amm.model_override_reason_riservato"
}
```

**Consumer FE**: `OperatorePermessiTab.vue` filtra il dropdown su
`can_override === true`. Per le righe pre-esistenti che puntano a un model
diventato riservato (drift dati storico), la cella `<Select>` e' disabled
con tooltip che mostra `t(reason)`.

**Defense-in-depth**: il service `put_override_oggetti` rifiuta scritture
su model con `can_override=False` con `E_AMM_VALIDAZIONE` — il filtro FE
non e' sufficiente per request crafted.

---

## 5. Form-defaults emittente fiscale (Fase 3)

### 5.1 GET /api/v1/amm-software/emittenti-fiscali/form-defaults/

Defaults pre-compilazione del form di creazione anagrafica emittente fiscale. Centralizza il consumo di `config.parameters` (`EMITTENTE_DEFAULT_BOLLO_AUTO`, `EMITTENTE_DEFAULT_BOLLO_SOGLIA`, `EMITTENTE_DEFAULT_ROUNDING_POLICY`) con cast tipi gia' applicato lato BE: il FE non duplica il cast generico di `/core/parameters/defaults/`. Pattern allineato a `ApiArticoliFormDefaults` (catalogo Fase 8 -- A5).

**Cascata**: user -> group -> emittente -> default via `script.fn_get_parameter_full`. In creazione `emittente_fiscale_id` e' `None` (cascata effettiva user->group->default).

**Cast applicati**:

| Campo response | Codice parameter | Cast | Convenzione |
|---|---|---|---|
| `defaults.bollo_auto` | `EMITTENTE_DEFAULT_BOLLO_AUTO` | `bool` | `'true'`/`'false'` case-insensitive; altro -> `false` (default-safe) |
| `defaults.bollo_soglia` | `EMITTENTE_DEFAULT_BOLLO_SOGLIA` | `Decimal` o `null` | Stringa vuota = nessuna soglia -> `null`; non parsabile -> `null` (best-effort) |
| `defaults.rounding_policy` | `EMITTENTE_DEFAULT_ROUNDING_POLICY` | `str` o `null` | Validato vs `_ROUNDING_MODE_VALIDI_EMITTENTE` (4 valori, no HALF_EVEN); fuori enum -> `null` |

**Note**:

- Il campo `attivo` **non** passa per `parameters`: la colonna `anagrafiche.emittenti_fiscali.attivo` ha gia' `DEFAULT true`. Il FE non lo include nei defaults.
- `non_editable_fields` ritornato statico oggi (`['codice', 'soggetto_id']`). In attesa che `dbops.vw_non_editable_fields` (Fase 5) includa anche le tabelle anagrafiche, il FE legge gia' la chiave per non avere breaking change quando la fonte diventera' DB-driven.
- Best-effort sui cast: parameters mancanti, malformati o fuori enum non sollevano errore. Il form mostra comunque, l'utente compila/seleziona manualmente.

**Response:**

```json
{
  "data": {
    "defaults": {
      "bollo_auto": false,
      "bollo_soglia": null,
      "rounding_policy": "HALF_UP"
    },
    "non_editable_fields": ["codice", "soggetto_id"]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/emittenti-fiscali/form-defaults/"
```

---

## 6. Processi automatici — i presidi e «Esegui ora»

⚠️ **Di questa famiglia qui ci sono i presidi (§6.1), «Esegui ora» (§6.2) con la
parte del dettaglio che lo alimenta (§6.3), l'accensione (§6.4) e la
riattivazione dell'utente tecnico (§6.5).** Le altre rotte (`GET processi/`,
`GET processi/{codice}/`, `GET processi/{codice}/run/`,
`POST processi/{codice}/identita/`) esistono e **non sono documentate**: e' un
debito dichiarato, non un'omissione da leggere come «non ci sono». Contratto
vivo: `/api/docs/`.

### 6.1 GET /api/v1/amm-software/processi/presidi/

Lo stato di **tutte** le viste-presidio del cantiere «nessun processo senza
operatore», in **un round-trip**: per ognuna il conteggio, le prime righe e la
descrizione.

⭐ **La natura di ogni presidio la dichiara il DATABASE, non il backend.** È il
`COMMENT` della vista a dire se *«deve restare VUOTA»* oppure se è *«un registro
di DEBITO che deve CALARE»*, e il backend lo consegna in `descrizione` leggendolo
con `obj_description`. ⛔ Un elenco di eccezioni scritto nel backend o nel
frontend sarebbe la seconda sede della stessa decisione, e la seconda diverge.

⛔ **Quante siano non è scritto da nessuna parte, ed è una scelta.** Dal
2026-09-10 l'elenco è il **catalogo** `dbops.presidi` (natura `ZERO`), letto da
`PresidiRepository.stato_presidi`; fino a quel giorno era la costante
`PRESIDI_PROCESSI` di `processi_repository.py`, oggi rimossa. Il nome della vista
esce qualificato collo schema (ci sono viste di `dbops` **e** di `maintenance`).
Un numero copiato
accanto a un elenco che cresce invecchia in silenzio: fino al 2026-09-07 il
docstring della view diceva «i SEI presidi» e alla stessa data l'elenco ne
contava dieci.

**Response shape**: `presidi` è una lista; `con_righe` è il numero che si guarda
per primo.

```json
{
  "data": {
    "presidi": [
      {
        "vista": "dbops.vw_processi_programmazione_da_guardare",
        "descrizione": "PRESIDIO: i processi automatici la cui sveglia e la cui ultima corsa non tornano. DEVE restare VUOTA. …",
        "significato": "Uno o più processi automatici non girano come dovrebbero.",
        "azione": "Per ogni processo segui il rimedio indicato accanto alla sua causa.",
        "chi_agisce": "SISTEMISTA",
        "conteggio": 1,
        "righe": [ { "processo_codice": "apply_storicizza_weekly", "stato": "GIRA_E_NON_REGISTRA", "causa": "GIRA_E_NON_REGISTRA", "…": "…" } ],
        "cause": [
          {
            "causa": "GIRA_E_NON_REGISTRA",
            "chi_agisce": "SVILUPPO",
            "significato": "Un lavoro programmato è partito, ma non ha lasciato traccia della sua corsa.",
            "azione": "Avvisa lo sviluppo: il lavoro si interrompe prima di riuscire a registrare l'esito.",
            "conteggio": 1,
            "righe": [ { "processo_codice": "apply_storicizza_weekly", "…": "…" } ]
          }
        ],
        "troncato": false,
        "elencabili": true,
        "errore": null,
        "da_guardare": true
      }
    ],
    "con_righe": 4,
    "non_letti": 0
  }
}
```

| Campo | Significato |
|---|---|
| `vista` | nome **qualificato collo schema**: due schemi possono avere viste omonime, e mezzo nome manderebbe a guardare quella sbagliata |
| `descrizione` | il `COMMENT` della vista — è lì che sta la differenza fra «deve essere zero» e «deve calare» |
| `significato`, `azione` | il testo **per chi agisce** (`dbops.presidi_testi`, la riga senza variante), nella lingua di chi legge con ripiego su `it`. `null` se il presidio non ha testo: il pannello ripiega sulla `descrizione` |
| `chi_agisce` | a chi tocca spegnere il presidio **nel suo insieme** (`AMMINISTRATORE`, `SISTEMISTA`, `SVILUPPO`) |
| `conteggio` | le righe che chiedono un intervento, da `dbops.fn_conta_presidio` (filtro `colonna_stato` compreso): dice quanto sta fuori dalle prime consegnate |
| `righe` | le prime N righe, con le colonne che la vista ha (forme diverse per vista) |
| `cause` | solo per i presidi che dichiarano `colonna_variante` (oggi il presidio dei processi): **tutte le cause accese**, da `dbops.fn_conta_presidio_per_variante` (ordine per valore, la causa `null` in coda), ognuna con il suo `conteggio`, il suo `chi_agisce`, `significato` e `azione` (`dbops.presidi_cause` + `presidi_testi`, ripiego per lingua dentro la causa) e le `righe` **del campione** che le appartengono — anche nessuna, se la causa sta oltre le prime righe o la vista non si elenca. Altrove `[]`. ⛔ Una causa senza testo ha i tre campi a `null`: non eredita mai il testo del presidio, che darebbe il rimedio di un altro guasto. ⚠️ Il `conteggio` di una causa non è mai minore delle sue `righe` (conteggio e campione sono due letture), e la somma dei conteggi può scostarsi dal `conteggio` del presidio per la stessa ragione |
| `troncato` | le righe mostrate non sono tutte — senza, venti su duecento si leggerebbero come «sono venti» |
| `elencabili` | `false` sulle viste con perimetro (`security_invoker`): il conteggio arriva da `fn_conta_presidio`, le righe **no**, per contratto — «non elencabile» e «niente da elencare» vanno distinti |
| `errore` | il presidio **non si è potuto leggere**: `conteggio` è `null` e qui c'è il perché. ⛔ Non è uno zero: il verde vuol dire «visto e vuoto» |
| `da_guardare` | `true` se ha righe **oppure** non è stato letto. È la stessa domanda che la testata conta (`con_righe` + `non_letti`), decisa **nella riga** dal repository: il pannello la legge e non la ricalcola (2026-09-15, tolta la copia in `PresidiProcessiPanel.vue`) |

⚠️ **Le colonne di `righe` non sono un contratto fisso**: ogni presidio ha la sua
forma e il client le rende leggendo le chiavi che trova
(`PresidiProcessiPanel.vue`). Un elenco di colonne per vista sarebbe un terzo
posto in cui quella forma è scritta, e si romperebbe alla prima colonna aggiunta.

⚠️ **`conteggio > 0` non è sempre un errore**, e per questo la `descrizione` va
resa insieme al numero: alcune viste sono registri di debito. ⭐ Al **2026-09-07**
`dbops.vw_processi_programmazione_da_guardare` nasce con **una** riga
(`apply_storicizza_weekly`, che dal febbraio 2026 gira senza lasciare traccia sul
giornale): il suo stesso `COMMENT` lo dichiara e dice quando va tolto. Brief:
`work-done/brief-db-sveglia-dei-processi.md` §8.1.

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/processi/presidi/"
```

⭐ **Dal 2026-09-18 la risposta porta anche `totale`** (quanti presidi `ZERO`
sono stati guardati): è la stessa testata di §6.1-bis, calcolata da **una**
funzione (`_testata_presidi` in `processi_service.py`) per i due lettori.

### 6.1-bis GET /api/v1/amm-software/processi/presidi/conteggi/ — la testata sola, per il pallino

**Scopo.** I tre numeri della testata — `totale`, `con_righe`, `non_letti` —
**senza** le prime righe. È la sorgente del **pallino dei presidi** in topbar
(decisione #8 di Tid, 2026-09-18; piano
`piano-be-fe-osservabilita-pallino-e-superfici.md` §2): un contatore ambientale
letto ogni cinque minuti da ogni scheda aperta, che non deve pagare le righe di
esempio.

**Contesto.** Stesso giro di §6.1 (`PresidiRepository.stato_presidi(con_righe=False)`:
stesse viste `ZERO` dal catalogo, stesso `fn_conta_presidio`, stesso isolamento
per presidio), stessa porta (`AdminAPIView`). ⛔ È un parametro del repository e
non un secondo metodo: una copia «senza righe» divergerebbe dalla prima al primo
campo nuovo, e il pallino direbbe una cosa e il pannello un'altra. Il pannello,
quando ricarica, **passa i suoi numeri al pallino** (`usePresidiPolling`
osserva lo store): le due letture non possono raccontare due stati.

**Input.** Nessuno.

**Output.**

```json
{ "data": { "totale": 20, "con_righe": 1, "non_letti": 0 } }
```

| Campo | Significato |
|---|---|
| `totale` | quanti presidi `ZERO` sono stati guardati (compresi i non letti) |
| `con_righe` | quanti hanno righe: il numero **rosso** del pallino |
| `non_letti` | quanti non si sono potuti leggere: il numero **giallo** — cecità, non guasto, e non si somma agli accesi |

**Regole.** Un presidio che non si legge **non è un errore di questa risposta**:
è `non_letti + 1`, per contratto. Chi non passa la porta riceve 403 e il pallino
**non compare** (il composable si spegne definitivamente su 403/401, come il
badge delle code per chi non ha l'area core). ⚠️ La rotta sta sotto
`processi/`, **prima** di `<str:codice>/` — stessa regola d'ordine di `presidi/`;
il test `test_processi_presidi_conteggi_api.py` pinna che risolva a questa view
e non al dettaglio di un processo chiamato «presidi».

**Dipendenze DB.** `dbops.presidi` (catalogo), `dbops.fn_conta_presidio`
(`SECURITY DEFINER`, attraversa la RLS).

### 6.2 POST /api/v1/amm-software/processi/{codice}/esegui-ora/ — «Esegui ora» su una sveglia

Accoda **un** lavoro `ESEGUI_PROCESSO` su `dbops.coda_lavori` per la sveglia di
deploy indicata, con lo scope di chi preme (`run_as = OPERATORE`); il drenatore
(`draina_coda_lavori`, ogni minuto) lancia `bin/run-command.sh <comando>` come
sottoprocesso — **la stessa riga del timer, meno l'orario** — e il comando
registra il suo run sotto il proprio processo con `origine = COMMAND` e
l'utente di chi ha premuto. **Il web non esegue niente.** Brief:
`work-done/brief-db-avvio-manuale-di-un-processo.md`; piano
`piano-be-fe-avvio-manuale-di-un-processo.md`.

⚠️ **Porta**: `AdminAPIView` (v1 solo `SUPER_ADMIN`, decisione di Tid del
14-09). L'azione `processo_avvia` e' a catalogo ma **non** e' dichiarata sulla
view — `AdminAPIView` non la leggerebbe, e un attributo che sembra un cancello
e non lo e' sarebbe peggio di nessun attributo.

**Header obbligatorio**: `Idempotency-Key` (400 senza). E' la chiave HTTP del
doppio submit; quella di **business** («una per unit sui lavori vivi»,
`esegui:<unit>`) la scrive il backend, ed e' quella che fa dire «gia' in coda».

**Request body**:

```json
{ "unit": "zeroerp-digest-presidi-giornaliero" }
```

⛔ Si manda la **unit**, mai un comando: l'argv si risolve dal dichiarato di
deploy (`backend/deploy/sveglie.json`), che e' la whitelist.

**Response** (200) — la forma del giro di fatturazione:

```json
{ "data": { "job_id": 4321, "stato": "PENDING", "unit": "zeroerp-digest-presidi-giornaliero" } }
```

**Rifiuti, nell'ordine in cui si valutano — tutti PRIMA di accodare:**

| Status | Codice | Quando |
| --- | --- | --- |
| 400 | `E_CODA_SCOPE_OPERATORE_INVALIDO` | il JWT non porta l'`identita_id`: lo stesso codice che il drenatore solleverebbe un minuto dopo, detto adesso a chi puo' fare qualcosa |
| 400 | `E_VALIDATION_INPUT` (`field: unit`) | `unit` assente, vuota o non stringa |
| 404 | `E_PROCESSO_NON_TROVATO` | il codice non e' nel registro (valutato **prima** del controllo della unit) |
| 400 | `E_VALIDATION_INPUT` (`field: unit`) | `unit` non fra le sveglie **di quel** processo |
| 422 | `E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO` | `forma = servizio`, o `avvio_manuale = false` nel dichiarato: non e' un candidato (natura, non stato) |
| 501 | `E_PROCESSO_SVEGLIA_NON_ABILITATA` | il processo e' **spento** su questa installazione (`dbops.fn_processo_acceso_dichiarato`): si riaccende con `POST processi/{codice}/accensione/` (§6.4), col motivo |
| 500 | `E_CONFIG_MANCANTE` | non si sa se il processo sia acceso: l'ambiente dell'installazione non e' dichiarato |
| 409 | `E_PROCESSO_AVVIO_GIA_IN_CODA` | esiste un lavoro `ESEGUI_PROCESSO` vivo (`PENDING`/`IN_CORSO`) con la stessa chiave; il `context` porta `job_id` |
| 501 | `E_JOB_TYPE_NON_ATTIVO` | il tipo di coda e' ancora `attivo = false` (regola del binding): e' il cancello voluto finche' l'handler non e' in release |

⚠️ I motivi 422/501/500/409 sono gli stessi — nello stesso ordine — della
capability `can_esegui_ora` del dettaglio (§6.3): li produce **lo stesso
predicato** (`avvio_manuale.motivi_esegui_ora`), quindi il tooltip del pulsante
spento e il rifiuto non possono dire due cose diverse.

**Gli esiti dell'esecuzione non passano da qui**: `E_PROCESSO_AVVIO_FALLITO`
(exit ≠ 0) ed `E_PROCESSO_AVVIO_TROPPO_LUNGO` (oltre il tetto di 300 s, figlio
ucciso) finiscono in `coda_lavori.ultimo_errore`, terminali, e si leggono in
*Strumenti → Code di lavoro*; la diagnosi del comando sta nel run del
processo eseguito (tab «Ultime corse» del suo drawer).

**Esempio curl:**

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: $(uuidgen)" -H "Content-Type: application/json" \
  -d '{"unit":"zeroerp-digest-presidi-giornaliero"}' \
  "https://host/api/v1/amm-software/processi/digest_presidi/esegui-ora/"
```

### 6.3 `sveglie[]` nel dettaglio — `GET processi/{codice}/`

Il dettaglio porta `sveglie`, una riga per unit dichiarata per quel processo
(zero, una o piu'): il **dichiarato** di deploy (cio' che il client mostra) e la
**capability** (cio' su cui decide), nella famiglia 1 dei nomi di `api.md`
§Capability di riga (motivo e chiave discendono dal flag).

```json
{
  "unit": "zeroerp-digest-presidi-settimanale", "forma": "timer",
  "comando": ["digest_presidi", "--cadenza", "settimanale"],
  "oncalendar": "*:00", "dovuto": {"ogni": "settimana", "giorno": 0, "dalle": "07:30"},
  "avvio_manuale": true,
  "nota": "…",
  "can_esegui_ora": false,
  "can_esegui_ora_reason": "E_PROCESSO_AVVIO_GIA_IN_CODA",
  "can_esegui_ora_reason_key": "amministrazione.processi.esegui_ora_blocco.gia_in_coda",
  "can_esegui_ora_dettaglio": {"job_id": 4321}
}
```

| Campo | Significato |
| --- | --- |
| `avvio_manuale` | la sveglia e' candidata a «Esegui ora» (dichiarato di deploy). ⛔ Il campo `abilita` e' ritirato (2026-10-16): se il processo sia acceso lo dice `accensione` del dettaglio (§6.4), non la sveglia |
| `oncalendar` | la **sveglia** del timer (`null` per un servizio). ⚠️ Su una sveglia calendariale e' `*:00`, ogni ora: la cadenza del lavoro e' `dovuto` |
| `dovuto` | dal 2026-10-09, solo sulle sveglie calendariali: `{ogni: giorno\|settimana\|mese, giorno, dalle}` — una volta per giorno/settimana/mese **aziendale**, dal `giorno` (0 = lunedi'; o del mese) alle `dalle` (`HH:MM`, fuso dell'azienda). La decide l'`ExecCondition` `e_dovuto` (brief un-solo-fuso-aziendale T-9). `null` = il timer lavora a ogni sveglia |
| `can_esegui_ora` | **derivato** dal motivo (`reason is None`), mai calcolato a parte |
| `can_esegui_ora_reason` | il codice macchina del **primo** motivo, o `null` |
| `can_esegui_ora_reason_key` | la chiave i18n del tooltip — una per motivo, fissata nei locales del client |
| `can_esegui_ora_dettaglio` | i parametri **con nome** della frase (`{job_id}`), o `null` |

⭐ Il client la legge con `bloccoAttivo(riga, 'can_esegui_ora',
'can_esegui_ora')` / `motivoBloccoRiga(...)` (`ProcessoDrawer.vue`, tab
«Sveglie»); il test `test_processi_esegui_ora` (17-18) pinna che i nomi emessi
siano quelli letti e che le tre chiavi esistano in `it.json` e `en.json`. I
lavori vivi si leggono con **una** query per tutte le unit del processo.

### 6.4 POST /api/v1/amm-software/processi/{codice}/accensione/ — Accendi, spegni, torna al default

La scelta a mano sull'**accensione** del processo su questa installazione
(`dbops.fn_imposta_accensione_processo`, guard di `dbops.processi_accensione`).
Porta `AdminAPIView`, come «Esegui ora».

**Header obbligatorio**: `Idempotency-Key` (400 senza).

**Request body**:

```json
{ "acceso": false, "motivo": "Manutenzione del server di posta" }
```

| Campo | Tipo | Obbligatorio | Descrizione |
| --- | --- | --- | --- |
| `acceso` | bool \| null | si | `true` accende, `false` spegne, `null` toglie la scelta e torna al default per ambiente del catalogo. Va **detto**: assente non vale «default» |
| `motivo` | string | si | Obbligatorio per tutti e tre i gesti |

**Response** (200): l'accensione rinfrescata, nella forma di `accensione` del
dettaglio: `acceso` (stato effettivo), `spegnibile`, `acceso_in_sviluppo`,
`acceso_in_produzione`, `ambiente`, `scelta_a_mano` (`{acceso, motivo, utente,
data, ammessa}` o `null`), `ha_sveglia`, `can_imposta_accensione` /
`_reason`, `can_accendere` / `_reason` / `_reason_key`.

**Rifiuti, nell'ordine — tutti prima di scrivere:**

| Status | Codice | Quando |
| --- | --- | --- |
| 400 | `E_VALIDATION_INPUT` (`field: acceso`) | `acceso` assente, o non booleano/null |
| 400 | `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO` (`field: motivo`) | motivo assente o vuoto |
| 404 | `E_PROCESSO_NON_TROVATO` | il codice non e' nel registro |
| 422 | `E_PROCESSO_NON_SPEGNIBILE` | il catalogo dichiara il processo non spegnibile |
| 422 | `E_PROCESSO_SENZA_SVEGLIA` | processo senza sveglia (canale `CODA` o ritirato) |
| 422 | `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE` | accensione a mano, in produzione, di un processo non accendibile in produzione |

I tre 422 li solleva il guard del DB; il drawer li anticipa con
`can_imposta_accensione` / `can_accendere`.

### 6.5 POST /api/v1/amm-software/processi/{codice}/identita/riattiva/ — Riattiva l'utente tecnico

Riaccende l'utente tecnico **spento** del processo per un emittente — tutta la
terna: utente Django, identita' digitale, legame nel registro
(`script.fn_riattiva_utente_tecnico`). Endpoint separato dalla creazione
(`POST processi/{codice}/identita/`): ci si arriva dal rifiuto
`E_UTENTE_TECNICO_DA_RIATTIVARE` di quella.

- **Header obbligatorio**: `Idempotency-Key`.
- **Corpo**: `{ "emittente_codice": "..." }` (obbligatorio, con il codice
  processo del path; mancante → 400 `E_CORE_VALIDATION`).
- **Risposta** (200): `{ "data": { "auth_user_id": 123 } }`.
- **Errori**: i guard della funzione DB, coi loro codici a catalogo; un errore
  DB non riconosciuto → 400 `E_CORE_VALIDATION`.
- **Permesso**: `AdminAPIView`.

---

## 7. Stato del setup

### 7.1 GET /api/v1/amm-software/setup-status/

I contatori del banner «operatori non assegnati», in un jsonb solo da
`script.fn_get_setup_status()`. Nessun parametro. Porta `AdminAPIView`.

```json
{ "data": { "emittenti_attivi": 2, "operatori_totali": 14, "operatori_assegnati": 11,
            "operatori_admin_globali": 2, "operatori_non_assegnati": 1 } }
```

Un operatore conta se la sua veste e' utilizzabile oggi
(`script.fn_veste_utilizzabile`); admin = `script.fn_is_super_admin`.

---

## Regole trasversali

- **Autenticazione**: tutti gli endpoint richiedono JWT Bearer token con binding `SUPER_ADMIN` (`AdminAPIView`)
- **Cache permessi**: ogni PUT su permessi (override aree, azioni, oggetti, emittenti scope, profilo reparto) invalida la cache permessi dell'utente o del reparto interessato
- **Semantica replace**: le PUT su permessi cancellano tutti i record esistenti e inseriscono i nuovi (non e' un merge/patch)
- **Ordinamento lista utenti**: whitelist di §1.1 (`last_name`, `soggetto_cognome`, `username`, `is_super_admin`, `ruolo_applicativo`, `is_active`, `unita_organizzativa_nome`, `override_count`, `valido_dal`, `valido_al`); una colonna fuori whitelist ripiega sull'ordine di default, un `order_dir` estraneo e' un 400
- **Throttling**: l'endpoint lista utenti ha throttling search attivo

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_AMM_VALIDAZIONE` | 400 | Campi obbligatori mancanti, `ruolo_sistema` legacy nel payload (Fase 1), validazioni domain |
| `E_AMM_OPERATORE_NOT_FOUND` | 404 | Operatore non trovato, o credenziale non di categoria `OPERATORE`, su tutte le rotte `operatori/{id}/…` (dettaglio, aggiorna, disabilita, override, scope, permessi ereditati/effettivi) |
| `E_AMM_SCOPE_NON_AMMESSO` | 400 | (Fase 2) `scope_mode` non in `['GLOBAL','SINGLE']`, oppure `SINGLE` con array vuoto/multi-elemento |
| `E_CREDENZIALE_DI_SISTEMA` | 409 | Blocco o accensione dell'obbligo del secondo fattore su una credenziale di categoria `SISTEMA` (§1-bis). Verbi `script.fn_blocca_credenziale` e `script.fn_imposta_totp_obbligatorio` |
| `E_CREDENZIALE_CON_VESTI` | 409 | Eliminazione di una credenziale che ha almeno una veste, anche spenta (§1-bis.5-bis). Verbo `script.fn_elimina_credenziale` |
| `E_CREDENZIALE_CON_STORIA` | 409 | Eliminazione di una credenziale senza vesti che compare gia' fra i dati: il messaggio nomina le tabelle (§1-bis.5-bis) |
| `E_CREDENZIALE_STORIA_NON_VERIFICABILE` | 500 | Eliminazione dove mancano le FK verso `django.auth_user` (installazione nuova, CI): fail-closed (§1-bis.5-bis) |
| `E_PROFILO_ULTIMO_SUPER_ADMIN` | 409 | (Fase 1) L'operazione (disabilita, demote, cambio scope) lascerebbe il sistema senza super admin attivi. Trigger DB `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` |
| `E_OPERATORE_SCOPE_PARAM_NON_VALIDO` | 400 | (Fase 5) `fn_change_user_emittenti_scope` rifiuta il payload (scope_mode invalido, array vuoto/multi-elemento). Codice stabile dal DB, sostituisce il `RAISE 22023` generico pre-Fase 5 |
| `E_AUDIT_SUMMARY_PARAM_NON_VALIDO` / `E_AUDIT_SOURCE_NON_TROVATO` / `E_AUDIT_SNAPSHOT_NON_TROVATO` | — | **Non esposti**: li solleva `AmmSoftwareService.get_audit_summary`, che nessuna rotta serve (non c'e' un endpoint audit-summary in `urls_v1.py`) |

## Dipendenze DB

| Funzione/Tabella | Schema | Ruolo |
|---|---|---|
| `fn_get_operatore_detail(INTEGER)` | `script` | **Fase 1**. Single source of truth per dettaglio operatore + capability (`can_invite/can_disable/can_demote_super_admin`). Idioma lookup-by-id (0 righe = id non valido) |
| `fn_check_operatore_invitabile(INTEGER)` | `script` | **Fase 1**. Calcola `can_invite/invite_reason` per il dettaglio |
| `fn_check_ultimo_super_admin_attivo(INTEGER)` | `script` | **Fase 1**. Check "e' l'unico SA attivo?" usato da `can_disable/can_demote` e da `can_change_scope` (Fase 2) |
| `fn_is_super_admin(INTEGER)` | `script` | Verifica binding profilo SUPER_ADMIN per l'utente. Gated su `app.ruolo_applicativo` GUC (post 2026-04-21): contesti non-OPERATORE ritornano false fail-closed |
| `fn_get_user_emittenti_scope(INTEGER)` | `script` | **Fase 2**. Single-row con `scope_mode/emittenti_ids/allowed_scope_modes/can_change_scope` |
| `fn_change_user_emittenti_scope(INTEGER, BIGINT[])` | `script` | **Fase 2**. Cambio scope atomico con guard `fn_check_ultimo_super_admin_attivo` integrato. Solleva `E_AMM_SCOPE_NON_AMMESSO` o `E_PROFILO_ULTIMO_SUPER_ADMIN` |
| `fn_get_parameter_full(...)` | `script` | **Fase 3**. Cascata risoluzione parameter user -> group -> emittente -> session -> default. Usata da `ParameterService.get_defaults` per il form-defaults emittente fiscale |
| Seed `config.parameters` `EMITTENTE_DEFAULT_*` | `config` | **Fase 3**. 3 chiavi: `BOLLO_AUTO=false`, `BOLLO_SOGLIA=''` (= NULL applicativo), `ROUNDING_POLICY=HALF_UP`. Tutti `text NOT NULL`, cast a Python a carico del BE (helpers `_cast_param_bool`/`_cast_param_decimal`) |
| `chk_emittenti_fiscali_rounding_policy` | `anagrafiche` | **Fase 3**. CHECK constraint sulla colonna `emittenti_fiscali.rounding_policy`: ammette **4 valori** (`UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`). Niente `HALF_EVEN` (a differenza di catalogo UoM operativa). E' il riferimento per `_ROUNDING_MODE_VALIDI_EMITTENTE` lato Python |
| `vw_audit_sources` | `script` | **Fase 5**. Vista `(code, label_key, area_funzionale)` filtrata `attivo=true` ordinata per `code`. 8 sorgenti audit (incluse `user_override_oggetti` permessi v2 + `identita_digitali` multi-face). Letta da `list_audit_sources` per il lookup e da `list_audit_log` per build dinamico delle UNION ALL |
| `fn_audit_summary(text, bigint)` | `script` | **Fase 5**. Calcola `{summary, diff}` per uno snapshot audit. Param: `(audit_source_code, storico_id)` dove `storico_id` e' la PK riga in `storico.<code>`. Esclude le 5 colonne audit standard (`data_*`, `user_*`, `tx_id`). Solleva `E_AUDIT_SNAPSHOT_NON_TROVATO` con marker stabile |
| `fn_crea_operatore_v2(...)` | `anagrafiche` | Orchestratore creazione operatore (credenziale + soggetto PF + risorsa umana + veste OPERATORE spenta) |
| `fn_sync_auth_user_is_active(INTEGER)` | `anagrafiche` | Sincronizza `auth_user.is_active` con stato identita digitale + risorsa umana |
| `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` | `config` | Trigger DB autorita' finale per anti-lockout: blocca DELETE/UPDATE binding SUPER_ADMIN se ultimo attivo. Solleva con marker `E_PROFILO_ULTIMO_SUPER_ADMIN` |
| `auth_user` | Django | Tabella autenticazione utenti |
| `identita_digitali` | `anagrafiche` | **Fase 1 multi-face**. Bridge `soggetti_ruoli ↔ auth_user` con `ruolo_applicativo`, `attivo`, `invito_inviato_at`, `deve_cambiare_password`. Sostituisce il ponte 1:1 `risorse_umane_auth_user`, che oggi e' una vista in ritiro non letta dal backend (analisi-software-per-dati-morti §2.1) |
| `profili_accesso_bindings` | `config` | Binding profili accesso (incluso SUPER_ADMIN id 9100) sull'identita digitale |
| `risorse_umane` | `anagrafiche` | Dati operatore (qualifica, UO, validita') |
| `unita_organizzative` | `config` | Reparti / unita' organizzative |
| `user_override_aree` | `config` | Override livello accesso aree per utente |
| `user_override_azioni` | `config` | Override azioni processo per utente |
| `user_override_oggetti` | `config` | Override permessi v2 per singolo model (`app_label.model_name`) |
| `user_emittenti_fiscali` | `config` | Scope emittenti fiscali per utente. Post-Q2: `UNIQUE(auth_user_id)` (max 1 riga) |
| `aree_funzionali` | `config` | Catalogo aree funzionali |
| `azioni_processo` | `config` | Catalogo azioni processo |
| `area_model_overrides` | `config` | Catalogo (app_label, model_name) ammessi per override v2 |
| `profili_accesso` / `profili_accesso_aree` / `profili_accesso_azioni` | `config` | Profili di accesso (anche quello di reparto, tipo `REPARTO`) con livelli per area e azioni; scritti da `config.fn_scrivi_profilo_accesso`, legati al reparto da `config.fn_lega_profilo_reparto` |
| `fn_get_permessi_ereditati_aree` / `_azioni` | `script` | Livelli ereditati dal profilo (§2.7) |
| `fn_get_permessi_riepilogo_aree` | `script` | Riepilogo per area (§2.9) |
| `fn_imposta_override_oggetti` | `config` | Scrittura replace degli override oggetto (§2.4-bis) |
| `fn_get_setup_status()` | `script` | Contatori di setup (§7.1) |
| `emittenti_fiscali` | `anagrafiche` | Catalogo emittenti fiscali |

## File backend

| File | Ruolo |
|---|---|
| `apps/amm_software/api/views.py` | View API (AdminAPIView): operatori, override, permessi, reparti, processi, audit/error log, lookup, setup status |
| `apps/amm_software/api/accessi_views.py` / `invito_views.py` / `email_views.py` | Area «Accessi» e credenziali, invito operatore, email |
| `apps/amm_software/api/urls_v1.py` | Routing sotto `/api/v1/amm-software/` |
| `apps/amm_software/services/amm_software_service.py` | Service layer -- validazione, orchestrazione, invalidazione cache. **Fase 3**: `_ROUNDING_MODE_VALIDI_EMITTENTE` + `_cast_param_bool` + `_cast_param_decimal` + `get_emittente_form_defaults` + `list_emittente_rounding_modes` |
| `apps/amm_software/db/amm_software_repository.py` | Repository -- accesso DB diretto (SQL raw) |
| `apps/amm_software/types.py` | TypedDict per righe utente |
| `apps/core/services/permissions_cache.py` | `invalidate_user()`, `invalidate_department()` |
| `apps/core/services/parameter_service.py` | `ParameterService.get_defaults` (cascata user->group->emittente->default via `fn_get_parameter_full`). Usato da Fase 3 form-defaults emittente |
| `apps/core/api/views_parameters.py` | `get_user_context(request, svc)` -- helper riusato dalle view form-defaults |
| `apps/amm_software/tests/api/test_operatori_views.py` | Test lista e dettaglio operatori |
| `apps/amm_software/tests/api/test_crea_operatore.py` | Test creazione operatore |
| `apps/amm_software/tests/api/test_override_permessi.py` | Test override aree/azioni/emittenti |
| `apps/amm_software/tests/api/test_profili_reparto.py` | Test profili reparto |
| `apps/amm_software/tests/api/test_emittenti_form_defaults_views.py` | **Fase 3**: smoke test API form-defaults + lookup rounding-modes |
| `apps/amm_software/tests/services/test_amm_software_service.py` | Test service layer (incluso Fase 3: cast helpers, form-defaults, rounding modes coverage) |
