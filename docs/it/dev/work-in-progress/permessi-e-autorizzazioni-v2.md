# Permessi e Autorizzazioni v2 — Livello Oggetto e Granularita' Fine

> Documento di pianificazione per l'estensione del sistema permessi.
> Data creazione: 2026-04-02
> Ultimo aggiornamento: 2026-04-10
> Stato: **FASI 1-5 COMPLETATE (sessione 2026-04-10)** — Fase 6 (attivazione incrementale) da fare per dominio
> Prerequisito: v1 completata (in work-done/permessi-e-autorizzazioni.md)
> Guida architetturale: `docs/it/guide/architettura-permessi-e-autorizzazioni.md`

---

## Contesto

Il sistema permessi v1 e' completo e operativo con **due livelli di granularita'**:

| Livello | Cosa controlla | Esempio | Stato |
|---------|---------------|---------|-------|
| **Area** (schema DB) | Accesso all'intero dominio | "Vendite: LETTURA" → l'operatore vede ma non modifica | **Attivo** |
| **Azione processo** | Permesso su operazione specifica | "genera_fatture_lotti: abilitata" → puo' lanciare pipeline | **Attivo** |

Manca il **terzo livello**, gia' strutturato nel DB ma non ancora integrato:

| Livello | Cosa controlla | Esempio | Stato |
|---------|---------------|---------|-------|
| **Oggetto** (model) | Accesso a singola entita' dentro un dominio | "Puo' vedere estratto conto ma non dettaglio fatture" | **DB pronto, API/frontend da fare** |

### Infrastruttura DB gia' disponibile

- Tabella `config.user_override_oggetti` — override per `app_label` + `model_name` + livello
- Tabella `config.area_model_overrides` — mapping model → area di appartenenza
- Funzione `script.fn_resolve_livello_oggetto(p_auth_user_id, p_app_label, p_model_name, p_area_schema_db)` — risolve livello con fallback a livello area
- Model ORM `UserOverrideOggetto` e `AreaModelOverride` (managed=False)

### Perche' non e' stato attivato nella v1

I domini applicativi (vendite, pagamenti, catalogo) hanno poche API esposte.
Il livello oggetto diventa utile quando ci sono **piu' entita' dentro lo stesso dominio**
con esigenze di accesso differenziate. Ad esempio:

- Dominio **vendite**: fatture (riservate), preventivi (visibili a tutti), DDT (solo magazzino)
- Dominio **pagamenti**: scadenze (tutti), riconciliazioni (solo amministrazione), estratto conto (lettura)
- Dominio **anagrafiche**: soggetti (tutti), indirizzi (tutti), conti bancari (riservati)

Finche' i domini non hanno le API complete, il livello area e' sufficiente.

---

## Obiettivo v2

Permettere all'admin di configurare permessi **per singola entita'** dentro un dominio.
L'operatore potrebbe avere accesso TUTTO su "vendite" ma LETTURA su "fatture" e BLOCCATO su "riconciliazioni pagamenti".

---

## Stato infrastruttura verificato (2026-04-10)

Analisi sessione 2026-04-10 ha verificato lo stato reale:

| Layer | Componente | Stato |
|-------|-----------|-------|
| DB | `config.user_override_oggetti` | Esiste, 0 righe |
| DB | `config.area_model_overrides` | Esiste, 0 righe (nessun seed) |
| DB | `script.fn_resolve_livello_oggetto` | Esiste, firma `(int, varchar, varchar, varchar) → livello_accesso` |
| Backend | `PermissionResolver.get_livello_oggetto()` | **Esiste** (riga 81-101 permissions_resolver.py) |
| Backend | `ZeroERPPermission` righe 192-196 | **Gia' chiama** `get_livello_oggetto` ma solo se la view ha un queryset ORM (`_get_model_meta`) |
| Backend | `_get_model_meta` | Legge solo da `view.queryset.model._meta` — tutte le 139 DomainAPIView usano raw SQL senza queryset |

**Conclusione:** il backend ha la logica ma non si attiva mai perche' nessuna view ha queryset. Serve l'attributo `model_permission` come fallback per le view raw SQL.

---

## 1. Backend — Integrazione livello oggetto nelle API

### 1.1 Estendere `ZeroERPPermission`

`ZeroERPPermission.has_permission()` (righe 191-200 di `permissions.py`) gia' chiama
`get_livello_oggetto` quando `_get_model_meta` ritorna `(app_label, model_name)`.
Ma `_get_model_meta` legge dal queryset ORM che non esiste nelle DomainAPIView.

Fix minimale: leggere anche da attributo `model_permission` dichiarato sulla view:

```python
class ApiFatturaDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "fattura")  # (app_label, model_name) — opzionale
```

Modifica in `_get_model_meta` o nel caller diretto (righe 191-196):
```python
app_label, model_name = self._get_model_meta(view)
if not app_label:
    mp = getattr(view, "model_permission", None)
    if mp:
        app_label, model_name = mp
```

Se `model_permission` e' dichiarato, la catena `fn_resolve_livello_oggetto` scatta
e fa fallback automatico al livello area se non c'e' override → zero regressioni.

- [x] 1.1 — Estendere `ZeroERPPermission.has_permission()` per leggere `model_permission` ✅ (2026-04-10)
- [x] ~~1.2 — Estendere `ZeroERPPermission` per usare `fn_resolve_livello_oggetto`~~ (gia' fatto)
- [x] ~~1.3 — Aggiornare `PermissionResolver` con `get_livello_oggetto()`~~ (gia' fatto)

### 1.2 API admin per override oggetti

Attualmente l'admin gestisce override aree e azioni. Servono endpoint per gli override oggetti:

- [x] 1.4 — `GET /api/v1/amm-software/operatori/{id}/override-oggetti/` ✅ (2026-04-10)
- [x] 1.5 — `PUT /api/v1/amm-software/operatori/{id}/override-oggetti/` ✅ (2026-04-10, con validazione catalogo)
- [x] 1.6 — Repository: `get_override_oggetti()`, `put_override_oggetti()`, `list_model_overrides()` ✅
- [x] 1.7 — Lookup: `GET /api/v1/amm-software/lookup/model-overrides/` ✅

### 1.3 Popolare `config.area_model_overrides`

La tabella di mapping model → area deve contenere le entita' configurabili.
Ogni riga dice "il model `fattura` dell'app `vendite` appartiene all'area `vendite`".

- [x] 1.8 — Seed dati: 11 model inseriti (5 anagrafiche, 3 vendite, 1 pratiche, 2 catalogo) ✅ (DB Tid 2026-04-10)
- [ ] 1.9 — API admin per gestire la tabella (CRUD) — seed-only per ora, editing UI differito

---

## 2. Frontend — Gestione override oggetti

### 2.1 Tab Permessi operatore

Aggiungere una **terza sezione** nel tab Permessi del drawer operatore
(dopo "Override Aree" e "Override Azioni"):

- [x] 2.1 — Sezione "Override Oggetti" con DataTable (Model + Livello + Elimina, Aggiungi/Salva) ✅ (2026-04-10)
- [x] 2.2 — Aggiornato `OperatorePermessiTab.vue` con terza sezione ✅

### 2.2 Matrice permessi riepilogativa

Estendere la pagina Permessi (`PermessiRiepilogoView`) per mostrare
anche il livello oggetto quando configurato:

- [ ] 2.3 — Opzionale: colonne espandibili per area → sotto-colonne per model con override

### 2.3 Enforcement frontend

Le view che corrispondono a un model con override devono rispettare il livello:

- [x] 2.4 — Esteso `useReadonlyMode(schemaDb, modelName)` con param opzionale ✅ (2026-04-10)
- [ ] 2.5 — Se il profilo utente include override oggetto, `visibleDomains` potrebbe nascondere sotto-voci (differito)

---

## 3. Diagnostica

- [ ] 3.1 — Estendere endpoint `permessi-effettivi` con livello oggetto per ogni model registrato
- [ ] 3.2 — Estendere endpoint `permessi-audit` con storico override oggetti

---

## 4. Test

- [x] 4.1 — Test Django: `fn_resolve_livello_oggetto` con override presente → usa override ✅ (`test_model_permission_uses_livello_oggetto`)
- [x] 4.2 — Test Django: `fn_resolve_livello_oggetto` senza override → fallback a livello area ✅ (`test_model_permission_fallback_area`)
- [x] 4.3 — Test Django: `ZeroERPPermission` con `model_permission` dichiarato ✅ (`test_no_model_permission_uses_area`)
- [ ] 4.4 — Test Django: API CRUD override oggetti (da aggiungere)
- [ ] 4.5 — Test pgTAP: `fn_resolve_livello_oggetto` (da aggiungere)

---

## Quando attivare

Il livello oggetto va attivato **per dominio** man mano che le API dei domini vengono completate:

| Dominio | API attive | Override oggetto utile quando |
|---------|-----------|-------------------------------|
| vendite | 11 endpoint | Fatture vs preventivi vs DDT hanno permessi diversi |
| pratiche | 20+ endpoint | Tipi pratica con visibilita' differenziata |
| pagamenti | 0 endpoint | Quando scadenze, riconciliazioni, estratti conto avranno API |
| anagrafiche | 30+ endpoint | Quando conti bancari o contatti sensibili richiedono restrizione |
| catalogo | 0 endpoint | Bassa priorita' — solitamente visibile a tutti |

**Non serve attivare tutto insieme.** Si aggiunge `model_permission` alle singole view
quando il business lo richiede, e il sistema fa fallback trasparente al livello area
per le view che non lo dichiarano.

---

## 5. Lavoro DB (branch `dev/db-tid`) ✅ Completato 2026-04-10

Le tabelle e la funzione `fn_resolve_livello_oggetto` esistevano gia'.
Tid ha applicato: seed dati + nuova funzione SQL + aggiornamento profilo utente.

### 5.1 Seed `config.area_model_overrides`

Popolare il catalogo dei model configurabili. Ogni riga registra un model
Django con la sua area di appartenenza. L'admin usera' questa lista come
dropdown quando configura override oggetto per un operatore.

**Struttura tabella (gia' esistente):**

```
config.area_model_overrides
  id           integer PK
  app_label    varchar NOT NULL   -- es. 'anagrafiche'
  model_name   varchar NOT NULL   -- es. 'conto_bancario'
  area_id      integer NOT NULL   -- FK config.aree_funzionali
  data_insert, user_insert, data_update, user_update (audit)
```

**Dati da inserire (migration `80_data`):**

```sql
INSERT INTO config.area_model_overrides (app_label, model_name, area_id)
VALUES
  -- anagrafiche (area_id = 1)
  ('anagrafiche', 'soggetto',         1),
  ('anagrafiche', 'cliente',          1),
  ('anagrafiche', 'fornitore',        1),
  ('anagrafiche', 'billing_account',  1),
  ('anagrafiche', 'conto_bancario',   1),
  -- vendite (area_id = 2)
  ('vendite', 'fattura',              2),
  ('vendite', 'preventivo',           2),
  ('vendite', 'listino',             2),
  -- pratiche (area_id = 12)
  ('pratiche', 'pratica',            12),
  -- catalogo (area_id = 4)
  ('catalogo', 'articolo',           4),
  ('catalogo', 'unita_misura',       4)
ON CONFLICT DO NOTHING;
```

> Nota: `app_label` + `model_name` corrispondono ai valori che le view backend
> dichiarano in `model_permission = ("app_label", "model_name")`. Non sono nomi
> tabella DB ma identificatori logici Django.

### 5.2 Funzione `script.fn_get_user_object_permissions_map`

Nuova funzione che ritorna la mappa degli override oggetto attivi per un utente.
Viene chiamata da `fn_get_user_profile` per arricchire il profilo con `permessi_oggetto`.

**Firma:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_object_permissions_map(
  p_auth_user_id integer
)
RETURNS jsonb
LANGUAGE plpgsql STABLE
```

**Semantica:**

- Legge da `config.user_override_oggetti` filtrando per `auth_user_id`
- Filtra override attivi: `valido_dal <= CURRENT_DATE` (o NULL) e `valido_al >= CURRENT_DATE` (o NULL)
- Ritorna JSONB con chiave `"app_label.model_name"` e valore il livello:

```json
{
  "anagrafiche.conto_bancario": "BLOCCATO",
  "vendite.fattura": "LETTURA"
}
```

- Se nessun override → ritorna `'{}'::jsonb`
- Pattern identico a `fn_get_user_permissions_map` (mappa area) e `fn_get_user_actions_map` (mappa azioni)

**Logica:**

```sql
SELECT COALESCE(
  jsonb_object_agg(
    uo.app_label || '.' || uo.model_name,
    uo.livello::text
  ),
  '{}'::jsonb
)
FROM config.user_override_oggetti uo
WHERE uo.auth_user_id = p_auth_user_id
  AND (uo.valido_dal IS NULL OR uo.valido_dal <= CURRENT_DATE)
  AND (uo.valido_al  IS NULL OR uo.valido_al  >= CURRENT_DATE);
```

### 5.3 Aggiornare `script.fn_get_user_profile`

Aggiungere la chiave `permessi_oggetto` al JSONB ritornato dal profilo utente:

```sql
-- Nella sezione dove si costruisce il risultato JSONB, aggiungere:
'permessi_oggetto', script.fn_get_user_object_permissions_map(p_auth_user_id),
```

Posizione: subito dopo la riga `'azioni_abilitate', script.fn_get_user_actions_map(...)`.

### 5.4 Test pgTAP suggeriti

```
-- fn_get_user_object_permissions_map: nessun override → '{}'
-- fn_get_user_object_permissions_map: con override attivo → chiave presente
-- fn_get_user_object_permissions_map: override scaduto (valido_al < today) → escluso
-- fn_get_user_object_permissions_map: override futuro (valido_dal > today) → escluso
-- fn_get_user_profile: profilo include chiave permessi_oggetto
```

### 5.5 Riepilogo migration DB

| # | Tipo | Percorso | Descrizione |
|---|------|----------|-------------|
| 1 | Seed | `80_data/config/` | Popola `area_model_overrides` con 11 model |
| 2 | Code | `20_code/script/` | Crea `fn_get_user_object_permissions_map` |
| 3 | Code | `20_code/script/` | Aggiorna `fn_get_user_profile` con `permessi_oggetto` |

---

## Dipendenze

- ~~Nessuna modifica DB necessaria~~ → 3 migration (seed + 2 funzioni) ✅ applicate 2026-04-10
- Nessuna nuova dipendenza Python
- Fasi 1-5 completate 2026-04-10 (sessione singola)
- Fase 6 (attivazione `model_permission` nelle view dominio) — incrementale, da fare per dominio
- Code review completata: fix HIGH (BA lookup sr_ids) + MEDIUM (validazione catalogo model) applicati
