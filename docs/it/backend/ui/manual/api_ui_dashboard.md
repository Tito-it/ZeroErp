# API — dashboard configurabile

## Scopo

Servire al frontend **la dashboard di un utente**: quali widget vede, in che
ordine, e con che numeri sopra. Quattro rotte (cinque metodi) sotto
`/api/v1/ui/dashboard/{codice}/`, dove `codice` identifica la dashboard (non
l'utente: quello arriva dal token).

## Contesto

La configurazione **non e' un record da leggere**: e' una **cascata risolta a
ogni richiesta**, e la risolve una funzione di database.

```
preferenza utente  →  preset (ruolo → emittente → sistema)  →  catalogo grezzo
```

⭐ **Per chiave** (dal 2026-11-01): `widget` e `dimensione_max` vengono ognuna dal
primo livello che la contiene, e la risposta lo dice in `origine`
(`preferenza`, `ruolo`, `emittente_fiscale`, `sistema`, `catalogo`), con
`dimensione_max_standard` (la misura senza la preferenza). Il FE rimanda al
salvataggio solo le chiavi `preferenza`, più quella toccata.

Sopra la cascata il DB fa altre due cose: **innesta i widget nuovi** comparsi a
catalogo dopo l'ultima scelta dell'utente, e **filtra per permessi**. Un widget
che l'utente non ha diritto di vedere non arriva al client — non arriva
*disabilitato*, non arriva proprio.

⭐ Tutte e quattro le view dichiarano `skip_area_check = True`, ed e' coerente:
la dashboard e' cross-area per definizione. Il perimetro non lo fa la view, lo
fa la funzione DB quando filtra i widget.

## 1. `GET /api/v1/ui/dashboard/{codice}/config/`

La configurazione **effettiva** per l'utente autenticato: l'esito della cascata,
gia' filtrato. E' l'unico endpoint che il FE deve chiamare per sapere cosa
disegnare. La risposta e' il jsonb di `ui.fn_resolve_dashboard_config`, cosi'
com'e':

```json
{
  "data": {
    "widget": [
      {
        "codice": "situazione_aperta",
        "ordine": 10,
        "visibile": true,
        "tipo_widget": "kpi",
        "etichetta": "Situazione aperta",
        "etichetta_i18n_key": "dashboard.home.situazione_aperta",
        "deep_link": "/vendite/dashboard-aperto",
        "contatore_key": "situazione_aperta",
        "soglia": null
      }
    ],
    "dimensione_max": 8,
    "dimensione_max_standard": 8,
    "origine": {"widget": "sistema", "dimensione_max": "catalogo"},
    "widget_nuovi": 0,
    "preset_base": {
      "id": 3,
      "ambito": "sistema",
      "contenuto_aggiornato_il": {"widget": "2026-11-20T09:12:00+00:00"}
    },
    "preset_base_cambiato": false,
    "preset_aggiornato": false,
    "preset_aggiornato_chiavi": []
  },
  "meta": {"request_id": "..."}
}
```

- `widget` — le card che l'utente puo' vedere, in ordine; `deep_link`,
  `contatore_key`, `soglia`, le etichette e `tipo_widget` sono freschi dal
  catalogo del pool, non dalla preferenza
- `dimensione_max` / `dimensione_max_standard` — quante card al massimo, con e
  senza la preferenza (da 1 a 100)
- `origine` — per chiave (`widget`, `dimensione_max`) il livello da cui viene
- `widget_nuovi` — le card nuove del pool che l'utente puo' vedere, contate
  dopo il filtro dei permessi
- `preset_base`, `preset_base_cambiato`, `preset_aggiornato`,
  `preset_aggiornato_chiavi` — gli stessi campi, con lo stesso significato, di
  [api_ui_liste §1](api_ui_liste.md#1-risolvi-configurazione-lista)

Il filtro dei permessi e' per **area e azione** (`script.fn_get_user_permissions_map`,
`script.fn_get_user_actions_map`), fail-closed fuori dalla veste `OPERATORE`.
I valori dell'esempio sono illustrativi.

⚠️ `DashboardService.get_catalogo` (il pool per una modale di scelta delle
card) esiste nel service ma **non ha una rotta**: oggi nessun endpoint lo
espone.

## 2. `GET /api/v1/ui/dashboard/{codice}/contatori/`

I contatori KPI dei widget **visibili**, calcolati in un giro solo.

⛔ **Non accetta chiavi dal client, ed e' una scelta di sicurezza esplicita.** Le
`contatore_key` sono quelle che la funzione DB ha gia' concesso a *questo*
utente: farsele passare da fuori aprirebbe una lettura cross-area — conteggi di
vendite a chi quell'area non ce l'ha. Il fatto che il client sappia gia' quali
widget vede non cambia la sostanza: la lista dei permessi non e' un parametro.

⭐ **Envelope per chiave**: la risposta è
`{"contatori": {"<contatore_key>": {"valore": <n>, "ok": true}, …}}`. Un
contatore che fallisce degrada **la sua** card (`{"valore": null, "ok": false}`)
senza oscurare le altre. Una dashboard mezza
piena e' informazione; una dashboard bianca perche' una query e' andata storta e'
un guasto.

Internamente risolve la config **una volta sola** e la passa al service dei
contatori: la funzione DB non viene chiamata due volte per la stessa richiesta.

## 3. `PUT` e `DELETE` `/api/v1/ui/dashboard/{codice}/preferenza/`

| metodo | fa |
|---|---|
| `PUT` | upsert della preferenza utente, **`Idempotency-Key` obbligatoria** — body: `widget` (lista di oggetti con le sole chiavi `codice` obbligatorio, una card del pool della dashboard, `ordine` intero positivo, `visibile` booleano; codici duplicati rifiutati) e `dimensione_max` (intero da 1 a 100), entrambi opzionali: la chiave **assente** vale «come lo standard». ⭐ La forma la giudica il DB (`ui.trgfn_preferenza_guard_forma`, BE8 e BE11 di brief-db-revisione-ui, 2026-11-22): altre chiavi, nel corpo o nel widget, una chiave a `null`, un tipo errato o il tetto superato sono un `400 E_UI_CONFIGURAZIONE_FORMA`, col messaggio che nomina la chiave e il motivo. ⛔ Il `PUT` senza nessuna chiave, o con un corpo che non è un oggetto, è un `400 E_UI_PREFERENZA_VALIDAZIONE`: per tornare allo standard si usa la `DELETE`. Risposta `{"id", "preset_base_id"}` |
| `DELETE` | cancella la preferenza: la dashboard **torna al preset**, non si svuota. Idempotente: `{"deleted": true\|false}` |

La `DELETE` e' il «ripristina predefiniti» della UI: senza preferenza la cascata
riparte dal preset di ruolo/emittente/sistema.

## 4. `POST /api/v1/ui/dashboard/{codice}/preferenza/ignore-preset-update/`

«Ignora» del banner **«il preset e' stato aggiornato»**: riscrive
`preset_base_id` della preferenza col valore che ha già, e il trigger
`ui.trgfn_preferenza_preset_base_snapshot` riallinea lo snapshot al contenuto
di oggi, chiave per chiave (`widget`, `dimensione_max`). ⛔ Dal giro 1b di
brief-db-revisione-ui (2026-11-20) l'ignorato `preset_aggiornato_ignored_at`
non esiste più. La risoluzione dice anche quali parti sono cambiate
(`preset_aggiornato_chiavi`). Body vuoto
ammesso, **`Idempotency-Key` obbligatoria**. Risposta `{"ignored": true}`; senza
preferenza: `404 E_UI_PREFERENZA_NON_TROVATA`.

⚠️ Serve perche' i due fatti convivono: l'utente ha personalizzato la sua
dashboard **e** l'amministratore ha cambiato il preset da cui era partita. Il
banner glielo dice; questo endpoint registra che ha scelto di tenersi la sua —
altrimenti l'avviso tornerebbe a ogni caricamento, che e' il modo piu' rapido di
insegnare a ignorare gli avvisi.

## Codici errore

| codice | HTTP | quando |
|---|---|---|
| `E_UI_DASHBOARD_NON_TROVATA` | 404 | `codice` dashboard inesistente (tutte e quattro le rotte) |
| `E_UI_PREFERENZA_VALIDAZIONE` | 400 | corpo del `PUT` che non è un oggetto, o senza nessuna chiave |
| `E_UI_CONFIGURAZIONE_FORMA` | 400 | forma del `PUT` non ammessa (dal guard a DB): il messaggio nomina la chiave e il motivo |
| `E_UI_PREFERENZA_NON_TROVATA` | 404 | `ignore-preset-update` senza una preferenza salvata |
| `E_IDEMPOTENCY_KEY_REQUIRED` | 400 | `PUT` preferenza o `POST` ignore-preset-update senza chiave |
| `E_UI_GENERIC_FAILED` | 400 | `config` e `contatori`: `DatabaseError` non riconosciuto durante la risoluzione |

## Dove guardare nel codice

| cosa | dove |
|---|---|
| le quattro view | `apps/ui/api/views_dashboard.py` |
| cascata e risoluzione | `apps/ui/services/dashboard_service.py` (`get_dashboard_config`), wrapper di `ui.fn_resolve_dashboard_config` |
| contatori | `apps/ui/services/dashboard_contatori_service.py` |
| preferenza e tombstone | `apps/ui/services/dashboard_preferenza_service.py` |

Correlate: [api_ui_liste](api_ui_liste.md) (le liste configurabili, stessa
filosofia di cascata) e [api_ui_admin_personalizzazioni](api_ui_admin_personalizzazioni.md)
(il lato amministrativo di preset e permessi).
