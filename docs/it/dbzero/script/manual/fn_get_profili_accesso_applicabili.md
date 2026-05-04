## Documentazione Concettuale – Funzione `script.fn_get_profili_accesso_applicabili`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
**Tabelle correlate:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
> [config.profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree)
> [config.profili_accesso_azioni](/dbzero/config/tabelle/profili_accesso_azioni)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
>
**Funzioni correlate:**
>
[script.fn_has_identita_attiva](/dbzero/script/funzioni/fn_has_identita_attiva)
> [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin)
> [script.fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area)
> [script.fn_check_azione_processo](/dbzero/script/funzioni/fn_check_azione_processo)

---
### 🎯 Scopo Principale
(latest review 04-05-2026 — modello legacy `profili_reparto_*` dismesso)

La funzione **`script.fn_get_profili_accesso_applicabili`** risolve la lista
di **profili di accesso applicabili** a un utente, basandosi sul modello
generalizzato `profili_accesso` + `profili_accesso_bindings` (§4.3 WIP
multi-face-auth). E' l'unica fonte di verita' per il calcolo dei profili
applicabili — non esistono piu' altri lookup paralleli.

Copre **tutti** i ruoli applicativi (operatore, cliente portale, fornitore
portale, shop customer) con un modello uniforme. La logica precedente,
ad-hoc su `profili_reparto_aree/_azioni` tramite JOIN a
`risorse_umane_auth_user` + `risorse_umane.unita_organizzativa_id`, e'
stata rimossa il 2026-05-04 (changeSet `20260505-02-drop-profili-reparto`).

Usata da (§4.8):

* [`fn_resolve_livello_area`](/dbzero/script/funzioni/fn_resolve_livello_area)
* [`fn_resolve_livello_oggetto`](/dbzero/script/funzioni/fn_resolve_livello_oggetto)
  (indirettamente, tramite fallback sull'area)
* [`fn_check_azione_processo`](/dbzero/script/funzioni/fn_check_azione_processo)

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | ID utente Django. Fail-closed su `NULL`. |
| `p_ruolo_applicativo` | `config.ruolo_applicativo` | **Opzionale** (DEFAULT `NULL`). Se `NULL` → comportamento legacy (tutti i profili di tutte le vesti dell'user). Se valorizzato → filtra solo le identita con quella specifica veste. Post 20-04-2026 per modello SSO multi-veste. |

---

### Output

`TABLE (profilo_accesso_id integer, priorita smallint)` — set di profili
applicabili, uno per riga, con indicazione di priorità.

| Colonna | Semantica |
|---------|-----------|
| `profilo_accesso_id` | FK a `config.profili_accesso.id` |
| `priorita` | `1` = AD_HOC (override personale); `2` = REPARTO / PORTALE (default di gruppo) |

---

### Tipi di binding risolti

La funzione è un `UNION ALL` di tre sorgenti, una per tipo di profilo:

#### 1. `AD_HOC` (priorità 1)

Binding diretto sull'identità digitale dell'utente. Rappresenta un **override
personale** che vince su qualsiasi default di gruppo.

Filtri:
- `identita_digitali.attivo = true`
- Identità nella finestra temporale (`valido_dal <= oggi <= valido_al`)
- `ruolo_applicativo <> 'DISABILITATO'`
- `profili_accesso_bindings.attivo = true`
- `profili_accesso.attivo = true` e `tipo = 'AD_HOC'`

#### 2. `PORTALE` (priorità 2)

Binding per `ruolo_applicativo` dell'identità dell'utente. Rappresenta il
**default** per un tipo di portale (`CLIENTE_PORTALE_STANDARD`,
`FORNITORE_PORTALE_STANDARD`, `SHOP_CUSTOMER_STANDARD`).

Filtri uguali al ramo AD_HOC, con `tipo = 'PORTALE'` e `JOIN` su
`pab.ruolo_applicativo = id.ruolo_applicativo`.

#### 3. `REPARTO` (priorità 2)

Binding per `unita_organizzativa_id` dell'operatore interno, risolta via
`risorse_umane.soggetto_ruolo_id = identita_digitali.soggetto_ruolo_id` →
`ru.unita_organizzativa_id`. Rappresenta il default del reparto.

Filtri aggiuntivi:
- `ruolo_applicativo = 'OPERATORE'` (solo operatori)
- `risorse_umane.attivo = true`

---

### Parametro `p_ruolo_applicativo` (post 20-04-2026)

Nel modello SSO multi-veste un `auth_user` puo' avere N identita attive
(una per `ruolo_applicativo`). Senza filtro, la fn restituirebbe tutti i
profili applicabili a tutte le vesti dell'user, mischiando capability
operatore e portale. Il parametro opzionale discrimina:

* `NULL` (default, backward compatible) — comportamento legacy: tutti i
  profili di tutte le vesti attive dell'user.
* `'OPERATORE'` — solo profili applicabili all'identita OPERATORE.
* `'CLIENTE_PORTALE'` — solo profili preset portale del cliente.
* `'SHOP_CUSTOMER'` — solo profili preset shop.
* ecc. per le altre vesti.

**Uso tipico nei resolver (follow-up post PR-B):** il resolver dovrebbe
leggere la veste corrente dal GUC `app.ruolo_applicativo` (popolato dal
middleware `JwtAuditAuthentication`) e passarla alla fn:

```sql
SELECT script.fn_get_profili_accesso_applicabili(
    p_auth_user_id,
    NULLIF(current_setting('app.ruolo_applicativo', true), '')::config.ruolo_applicativo
);
```

**Stato corrente (04-05-2026):** i 4 resolver chiamanti
(`fn_resolve_livello_area`, `fn_check_azione_processo`,
`fn_get_user_permissions_map`, `fn_get_user_actions_map`) **NON** passano
ancora il parametro — continuano a funzionare in modalita' default
(tutte le vesti). Il pass-through del GUC `app.ruolo_applicativo` e'
rinviato al primo momento in cui il BE tocca i chiamanti, per evitare
cambio comportamento globale senza coordinamento. Fino a quel momento
l'isolamento veste e' garantito da (a) permission class per namespace,
(b) `fn_is_super_admin` filtrato OPERATORE.

---

### Regola di selezione nelle funzioni resolver

Le funzioni che usano questo helper applicano il pattern:

```sql
SELECT <livello|abilitata>
  FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id) h
  JOIN config.profili_accesso_aree paa  -- o profili_accesso_azioni
    ON paa.profilo_accesso_id = h.profilo_accesso_id
 WHERE paa.area_id = <area_target>
 ORDER BY h.priorita
 LIMIT 1;
```

`ORDER BY h.priorita LIMIT 1` garantisce che:

* Se esiste un profilo AD_HOC che definisce l'area/azione → vince (priorità 1).
* Altrimenti si pesca dal profilo REPARTO/PORTALE (priorità 2).

Se non esiste neppure quello, il resolver ritorna `BLOCCATO` / `false`.

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: funzione pura, inlineable dal planner quando
  usata come sub-query, niente side effect.
* Ritorno `TABLE` (set-returning): consente JOIN diretto con
  `profili_accesso_aree` / `profili_accesso_azioni` per singolo lookup.
* `DISTINCT` su ciascun ramo UNION per robustezza (se il modello
  dovesse, per qualche ragione, produrre duplicati).
* Il filtro `ruolo_applicativo <> 'DISABILITATO'` è esplicito in
  AD_HOC e PORTALE; implicito in REPARTO tramite `= 'OPERATORE'`.

---

---

### Esempi d'uso

**In una funzione resolver** (pattern §4.8):

```sql
-- Trova il livello per l'area 'vendite'
SELECT paa.livello
  FROM script.fn_get_profili_accesso_applicabili(42) h
  JOIN config.profili_accesso_aree paa
    ON paa.profilo_accesso_id = h.profilo_accesso_id
  JOIN config.aree_funzionali af
    ON af.id = paa.area_id
 WHERE af.schema_db = 'vendite'
 ORDER BY h.priorita
 LIMIT 1;
```

**Diagnostica — elenco profili di un utente**:

```sql
SELECT h.priorita,
       pa.tipo,
       pa.codice,
       pa.descrizione
  FROM script.fn_get_profili_accesso_applicabili(42) h
  JOIN config.profili_accesso pa
    ON pa.id = h.profilo_accesso_id
 ORDER BY h.priorita, pa.tipo;
```

**Calcolo del livello "best" per ogni area** (map set-based):

```sql
WITH livelli AS (
    SELECT paa.area_id, paa.livello, h.priorita
      FROM script.fn_get_profili_accesso_applicabili(42) h
      JOIN config.profili_accesso_aree paa
        ON paa.profilo_accesso_id = h.profilo_accesso_id
),
best AS (
    SELECT DISTINCT ON (area_id) area_id, livello
      FROM livelli
     ORDER BY area_id, priorita
)
SELECT af.schema_db, COALESCE(b.livello, 'BLOCCATO') AS livello
  FROM config.aree_funzionali af
  LEFT JOIN best b ON b.area_id = af.id
 WHERE af.attivo = true;
```

---

### Evoluzione attesa

* **§4.8.4** — test pgTAP regression che verificano `fn_resolve_livello_area`
  per operatori noti (`db/pgtap/script/test-fn-resolve-regression-operatore.sql`).
* **§4.9** — le prime policy RLS useranno `fn_get_profili_accesso_applicabili`
  (indirettamente, tramite `fn_resolve_livello_*`) per filtrare le righe
  in base al livello di accesso.
* **Pass-through veste** — i resolver dovranno propagare il GUC
  `app.ruolo_applicativo` come secondo argomento, per isolare le capability
  per veste nel modello SSO multi-veste.

---

{% include-markdown "signature-core.md" %}
