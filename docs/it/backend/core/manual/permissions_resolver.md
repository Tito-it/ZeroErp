# PermissionResolver (Core Django)

## Scopo

Risolutore centrale dei permessi ZeroErp: una classe statica che **delega ogni
decisione alle funzioni SQL `script.fn_*`** e tiene una cache per-request per
non ripetere lo stesso round-trip due volte nella stessa richiesta HTTP.

> ⛔ **Riscritto il 2026-09-12** (analisi-software-per-dati-morti §4). Fino a
> quel giorno questa pagina descriveva una catena risolta **in Python** —
> «`ruolo_sistema → override utente → profilo reparto → BLOCCATO`», con
> `get_ruolo_sistema()`, `ProfiloRepartoArea/Azione` e il ponte
> `risorse_umane_auth_user` — che **non esiste più da mesi**: il tipo
> `ruolo_sistema` è caduto in Fase 7 (29-04-2026), i profili reparto sono stati
> dismessi col cutover multi-face, il ponte è `identita_digitali`. Un manuale
> che racconta il modello vecchio è il canale con cui il morto rientra: chi lo
> legge in buona fede riscrive il codice che descrive.

## Contesto

Classe in `apps/core/services/permissions_resolver.py`. La usano
`ZeroERPPermission` (DRF), `EmittenteFiscaleScopeMixin`, `JwtAuditMiddleware`,
gli endpoint `/api/v1/core/me/` e `/users/{id}/permessi-effettivi/`, i service
che applicano lo **scope emittente** (documenti, vendite, coda lavori, AI).

**Il modello che risolve** (guida `risorse-umane-e-accessi.md`,
`architettura-multi-face-auth.md`): un `auth_user` ha N **identità digitali**
(`anagrafiche.identita_digitali`, una per veste attiva); l'operatore interno è
l'identità `OPERATORE`, legata alla risorsa umana per `soggetto_ruolo_id`.
I permessi vengono dai **profili di accesso** (`config.profili_accesso*`, tipo
`REPARTO` / `PORTALE` / `AD_HOC` / `SUPER_ADMIN`) legati all'identità con
binding a tre vie (reparto, identità singola, ruolo applicativo), più gli
**override individuali** (`config.user_override_*`). La catena — priorità,
finestre di validità, default `BLOCCATO` — vive **nelle funzioni SQL**; qui non
ne esiste una copia.

Tutti i metodi accettano un dict `cache` opzionale (`request._zeroerp_perms_cache`
quando disponibile): chiave stabile per metodo + argomenti, `None` non
memorizzato.

## Costanti

```python
LIVELLO_MAP = {
    "TUTTO":    frozenset({"view", "add", "change", "delete"}),
    "LETTURA":  frozenset({"view"}),
    "BLOCCATO": frozenset(),
}
```

## Metodi pubblici

| Metodo | Delega a | Ritorna | Cache key |
| --- | --- | --- | --- |
| `is_super_admin(user, cache=None)` | `script.fn_is_super_admin` | `bool` — binding `SUPER_ADMIN` attivo **sulla veste OPERATORE** (una identità portale/shop con lo stesso binding non attiva il bypass); fail-closed su identità inattiva o fuori finestra | `is_super_admin` |
| `get_ruolo_applicativo(user, cache=None)` | GUC `app.ruolo_applicativo` (propagata da `JwtAuditAuthentication`), fallback `identita_digitali` attiva | `str \| None` — `OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`, `API_CLIENT`, `DISABILITATO` | `ruolo_applicativo` |
| `get_livello_area(user, area_schema_db, *, cache=None)` | `script.fn_resolve_livello_area` | `"TUTTO" \| "LETTURA" \| "BLOCCATO"` (default `BLOCCATO`) | `area:{schema_db}` |
| `get_livello_oggetto(user, app_label, model_name, area_schema_db, *, cache=None)` | `script.fn_resolve_livello_oggetto` | livello del singolo model, con ripiego sull'area | `oggetto:{app_label}.{model_name}` |
| `check_azione(user, permission_codename, *, cache=None)` | `script.fn_check_azione_processo` | `bool` | `azione:{codename}` |
| `get_emittenti_sr_ids(user, *, cache=None)` | `script.fn_get_emittenti_scope_sr_ids` | `list[int] \| None` di **`soggetto_ruolo_id`** — per le query che filtrano su `*_soggetto_ruolo_id` (BA scope, ricerca universale, liste vendite) | `emittenti_sr_ids` |
| `get_emittenti_pk_ids(user, *, cache=None)` | `script.fn_get_emittenti_scope_pk_ids` | `list[int] \| None` di **PK `emittenti_fiscali.id`** — per le query che filtrano su `emittente_fiscale_id` | `emittenti_pk_ids` |
| `get_emittente_for_user(user, *, cache=None)` | `script.fn_resolve_emittente_for_user` | `int \| None` — l'**unico** emittente 1-a-1 dell'operatore (PK); `None` per admin globale o istanza «0 emittenti» | `emittente_for_user` |
| `get_unita_organizzativa_id(user, cache=None)` | `script.fn_get_uo_id_for_user` | `int \| None` — l'UO della risorsa umana dell'identità OPERATORE | `uo_id` |
| `has_profilo_applicabile_per_area(user, area_schema_db, *, cache=None)` | `script.fn_get_profili_accesso_applicabili` ⋈ `profili_accesso_aree` | `bool` — distingue «BLOCCATO intenzionale» da «nessun profilo configurato» nei messaggi di diniego | `has_profilo:{schema_db}` |
| `get_area_schema_db(app_label, model_name)` | `config.area_model_overrides` | lo `schema_db` dell'area di un model (default `app_label`) | — |
| `list_model_overrides_grouped()` | `config.area_model_overrides` | `{schema_db: [{app_label, model_name}]}` per `permessi-effettivi` | — |

### Scope emittente: SR contro PK, e sono due nomi soltanto

`get_emittenti_sr_ids` e `get_emittenti_pk_ids` rispondono alla stessa domanda
(«quali emittenti vede questo operatore») in due **convenzioni di colonna**
diverse; si sceglie in base a ciò su cui la query filtra (guida
`soggetti-e-ruoli-anagrafici §5b`, memoria `feedback_emittente_pk_vs_soggetto_ruolo`).
Semantica comune: `None` = nessuna restrizione, `[]` = **nessun accesso**
(fail-closed: identità OPERATORE non attiva), super admin → `None`.

⛔ L'alias `get_emittenti_ids` — deprecato dal 2026-05-02 e arrivato a **nove**
chiamanti — è stato **tolto il 2026-09-12** (analisi-software-per-dati-morti
§2.7). Il presidio è il grep a zero.

## Regole

- **Nessuna logica di permesso in Python.** Il wrapper esegue una `SELECT` e
  traduce il risultato; un `if` che «anticipa» la funzione SQL sarebbe una
  seconda sede della regola, e le due si sfilano in silenzio.
- **Fail-closed per costruzione**: riga assente → `BLOCCATO` / `False` /
  `[]`, mai un permesso concesso per mancanza di un dato.
- **La cache è per richiesta, non per processo**: vive in
  `request._zeroerp_perms_cache` e muore con la richiesta. La cache **Redis**
  dei permessi è un altro oggetto (`permissions_cache.md`), invalidata dai
  writer (profili, override, reparto).
- **I mock non provano il contratto DB.** Un test con `connection` finta prova
  la traduzione del risultato, non che la funzione esista o che la firma leghi:
  il contratto cross-veste di `fn_is_super_admin` è provato dai pgTAP in
  `db/pgtap/script/`.

## Dipendenze DB

| Oggetto | Uso |
| --- | --- |
| `script.fn_is_super_admin` | bypass totale, filtrato sulla veste OPERATORE |
| `script.fn_resolve_livello_area` · `fn_resolve_livello_oggetto` | catena area / oggetto |
| `script.fn_check_azione_processo` | azioni di processo |
| `script.fn_get_emittenti_scope_sr_ids` · `fn_get_emittenti_scope_pk_ids` | scope emittente, due convenzioni |
| `script.fn_resolve_emittente_for_user` | emittente 1-a-1 |
| `script.fn_get_uo_id_for_user` | unità organizzativa (`identita_digitali` → `soggetti_ruoli` → `risorse_umane`) |
| `script.fn_get_profili_accesso_applicabili` | profili applicabili all'identità |
| `anagrafiche.identita_digitali` | fallback di `get_ruolo_applicativo` senza GUC |
| `config.area_model_overrides` · `config.aree_funzionali` · `config.profili_accesso_aree` | catalogo aree/model |

## Note di migrazione

- **Fase 7 (29-04-2026)**: `ruolo_sistema` (ADMIN / OPERATIVO / DISABILITATO)
  è caduto; al suo posto `is_super_admin` + `ruolo_applicativo`.
- **Cutover multi-face (19/20-04-2026)**: il ponte `risorse_umane_auth_user`
  è diventato una vista di compatibilità su `identita_digitali` e i profili
  reparto sono stati sostituiti dai profili di accesso generalizzati.
  ⚠️ La vista è in ritiro (analisi-software-per-dati-morti §2.1): nessun
  metodo qui la legge.
- **2026-05-02**: `get_emittenti_pk_ids` diventa la canonica PK con i guard;
  **2026-08-18** la legacy `script.fn_get_emittenti_scope` senza guard è
  droppata (`20260818-66`); **2026-09-12** l'alias `get_emittenti_ids` è tolto.

## Test

`apps/core/tests/services/test_permissions_resolver.py` — unitari con
`connection` mockata (traduzione del risultato, chiavi di cache, binding del
nome della funzione SQL chiamata).
