# API Permessi Effettivi (Core Django)

## Scopo

Esporre un endpoint diagnostico che restituisce i permessi effettivi risolti per un utente,
iterando tutte le aree funzionali attive e mostrando il livello di accesso, le azioni
consentite e lo stato del profilo reparto.

## Contesto

View `ApiPermessiEffettivi` in `apps/core/api/views.py` (`DomainAPIView`,
`skip_area_check = True`).

La risoluzione e' tutta delegata al DB tramite `PermissionResolver`:
`script.fn_resolve_livello_area` per l'area (catena: veste OPERATORE attiva →
super admin = `TUTTO` → override utente → profili applicabili → `BLOCCATO`) e
`script.fn_resolve_livello_oggetto` per ogni model configurabile dell'area. Si
iterano le aree attive di `config.aree_funzionali`. Serve a rendere trasparente la
risoluzione permessi per diagnostica e onboarding.

## Endpoint

```http
GET /api/v1/core/users/{user_id}/permessi-effettivi/
```

Richiede autenticazione JWT (`JwtAuditAuthentication`).

## Input

Path parameter:

| Parametro | Tipo | Obbligatorio | Note                                     |
|-----------|------|:------------:|------------------------------------------|
| `user_id` | int  | Sì           | ID `auth_user` dell'utente da consultare |

## Output

```json
{
  "data": {
    "user_id": 1,
    "username": "mario.rossi",
    "is_super_admin": false,
    "ruolo_applicativo": "OPERATORE",
    "is_active": true,
    "unita_organizzativa_id": 10,
    "aree": [
      {
        "codice": "VENDITE",
        "schema_db": "vendite",
        "descrizione": "Vendite",
        "livello": "TUTTO",
        "azioni_consentite": ["add", "change", "delete", "view"],
        "has_profilo_reparto": true,
        "modelli": [
          {"app_label": "vendite", "model_name": "contratto", "livello": "LETTURA"}
        ]
      },
      {
        "codice": "ACQUISTI",
        "schema_db": "acquisti",
        "descrizione": "Acquisti",
        "livello": "BLOCCATO",
        "azioni_consentite": [],
        "has_profilo_reparto": false,
        "modelli": []
      }
    ],
    "emittenti_ids": [1, 3, 5]
  },
  "meta": {"request_id": "..."}
}
```

Campi risposta:

| Campo                          | Tipo          | Note                                                      |
|--------------------------------|---------------|-----------------------------------------------------------|
| `user_id`                      | int           | ID utente consultato                                      |
| `username`                     | string        | Username Django                                           |
| `is_super_admin`               | bool          | Binding SUPER_ADMIN attivo sulla veste OPERATORE (`script.fn_is_super_admin`) |
| `ruolo_applicativo`            | string\|null  | Veste letta dal contesto della richiesta (vedi Regole)    |
| `is_active`                    | bool          | `auth_user.is_active`: puo' fare login o no               |
| `unita_organizzativa_id`       | int\|null     | Reparto (`script.fn_get_uo_id_for_user`); null per non operatori o senza risorsa umana attiva |
| `aree`                         | array         | Livello effettivo per ogni area funzionale attiva         |
| `aree[].codice`                | string        | Codice area (es. `VENDITE`)                               |
| `aree[].schema_db`             | string        | Schema DB corrispondente                                  |
| `aree[].descrizione`           | string        | Descrizione area                                          |
| `aree[].livello`               | string        | `TUTTO`, `LETTURA` o `BLOCCATO`                           |
| `aree[].azioni_consentite`     | array         | Azioni CRUD consentite dal livello, ordinate              |
| `aree[].has_profilo_reparto`   | bool          | `true` se almeno un profilo applicabile (AD_HOC, REPARTO, PORTALE) configura l'area |
| `aree[].modelli`               | array         | Un elemento per ogni model configurabile dell'area (`config.area_model_overrides`) |
| `aree[].modelli[].app_label`   | string        | App Django del model                                      |
| `aree[].modelli[].model_name`  | string        | Nome del model                                            |
| `aree[].modelli[].livello`     | string        | Livello oggetto risolto (`TUTTO`, `LETTURA`, `BLOCCATO`)  |
| `emittenti_ids`                | array\|null   | PK `emittenti_fiscali.id` autorizzate; `null` = nessuna restrizione (super admin); `[]` = nessun accesso (nessuna veste OPERATORE attiva) |

## Regole

- Solo superuser Django o utenti con binding SUPER_ADMIN possono consultare i permessi
  di **altri** utenti; tutti gli altri possono consultare solo i propri.
- Se l'utente non ha il permesso di consultare altri, restituisce `E_PERMESSO_NEGATO` (403).
- Se `user_id` non esiste, restituisce `E_CORE_VALIDATION` (400).
  > ⚠️ Difetto noto (E-4): un «non trovato» che esce 400 — vedi
  > [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).
- Utente senza veste OPERATORE attiva: tutte le aree risultano `BLOCCATO`.
- Super admin: tutte le aree risultano `TUTTO`.
- `has_profilo_reparto = false` con `livello = BLOCCATO` indica che nessun profilo
  applicabile configura l'area (diverso da un profilo che imposta esplicitamente
  BLOCCATO). Il nome del campo resta per compatibilita' col frontend.
- `ruolo_applicativo` viene letto prima dalla GUC `app.ruolo_applicativo` della
  richiesta, cioe' la veste di **chi chiama**; solo in assenza di GUC si legge
  un'identita attiva dell'utente consultato. Per una consultazione di un altro
  utente via HTTP il campo riporta quindi la veste del chiamante.
  ⚠️ Difetto noto (S-6): [analisi-be-difetti-emersi-verifica-doc-api-core.md](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).
- `emittenti_ids = null` significa nessuna restrizione ambito emittente (l'utente vede tutto).

## Dipendenze DB

- `config.aree_funzionali` — iterazione aree attive
- `anagrafiche.identita_digitali` — identita' e `ruolo_applicativo`
- `anagrafiche.risorse_umane` — unita_organizzativa_id (via `script.fn_get_uo_id_for_user`)
- `config.user_override_aree` / `config.user_override_oggetti` — override individuali area e oggetto
- `config.profili_accesso`, `config.profili_accesso_aree`, `config.profili_accesso_bindings` — profili applicabili
- `config.area_model_overrides` — model configurabili per area (`modelli[]`)
- `config.user_emittenti_fiscali` — ambito emittente fiscale

## Codici errore

| Codice              | HTTP | Causa                                        |
|---------------------|------|----------------------------------------------|
| `E_PERMESSO_NEGATO` | 403  | Utente non autorizzato a consultare altri     |
| `E_CORE_VALIDATION` | 400  | `user_id` non trovato (difetto E-4)          |
| `E_GENERICO`        | 500  | Errore imprevisto                            |
