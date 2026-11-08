# fn_resolve_dashboard_config

> **Ultimo aggiornamento**: 8 novembre 2026

### 🎯 Scopo Principale

Punto centrale di risoluzione della configurazione di una **dashboard** per un utente. Applica la cascata di preset, il merge automatico dei widget nuovi e il filtro autorizzativo dei widget. Restituisce un JSONB pronto per il frontend, senza logica di business lato applicazione. È il gemello di [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config), semplificato: nessun livello per-elemento, nessuna normalizzazione `esportabile`/`identificatore`.

## Schema

`ui`

## Firma

```sql
ui.fn_resolve_dashboard_config(
  p_dashboard_codice     VARCHAR,
  p_auth_user_id         INTEGER,
  p_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE
) RETURNS JSONB
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_dashboard_codice` | `VARCHAR` | Sì | Codice dashboard (es. `home`) |
| `p_auth_user_id` | `INTEGER` | Sì | ID utente Django (`django.auth_user.id`) |
| `p_emittente_fiscale_id` | `BIGINT` | No | ID emittente fiscale del contesto. NULL se non rilevante. |

## Algoritmo (6 passi)

**0. Risoluzione dashboard_id** — lookup `ui.dashboard_definizione` per codice. Errore `E_UI_DASHBOARD_NON_TROVATA` se non trovata o non attiva.

**1. Profili applicabili + mappe permessi** — chiama `script.fn_get_profili_accesso_applicabili(p_auth_user_id, <veste>)` — la veste la dà [`ui.fn_veste_corrente`](/dbzero/ui/funzioni/fn_veste_corrente) (`NULL` = tutte) — per l'array profili della cascata ruolo, e risolve **una sola volta** le due mappe aggregate del filtro permessi:
  - `script.fn_get_user_permissions_map(p_auth_user_id)` → `{ schema_db: livello }`
  - `script.fn_get_user_actions_map(p_auth_user_id)` → `{ permission_codename: bool }`

  Entrambe sono GUC-aware: con veste corrente ≠ `OPERATORE` producono `BLOCCATO`/`false` (fail-closed).

**2. Cascata per chiave** (dal 1-11-2026, gemella delle liste) — `widget` e `dimensione_max` si risolvono **ognuna per conto suo**, dal primo livello che la contiene:
  1. Preferenza personale utente (`ui.dashboard_preferenza_utente`): una chiave presente è una scelta; assente (o `null`) vuol dire «come lo standard». `dimensione_max` vale se è un intero positivo. Si legge anche `preset_base_id`, `preset_base_contenuto_aggiornato_il`, `preset_aggiornato_ignored_at` per lo step 2.5
  2. Il **preset di base**: il primo, in quest'ordine, con almeno un widget attivo — di ruolo (`ambito='ruolo'`, join su `fn_get_profili_accesso_applicabili` con `ORDER BY priorita ASC`), di emittente fiscale, di sistema; sempre `is_default=TRUE`. Si cerca **sempre**, anche con una preferenza
  3. **Catalogo grezzo** (fallback "mai vuota"): per i widget, tutti quelli attivi del pool della dashboard (`ui.dashboard_widget ⋈ ui.widget`), ordinati per `ordine_default`, `visibile=TRUE`; per `dimensione_max`, 8

  Lo **standard** di `dimensione_max` è quella del preset di base, o 8. ⚠️ Fino al 31-10-2026 la cascata sceglieva un livello solo, il primo con i widget: una preferenza di soli widget rispondeva 8 invece della dimensione del preset, e il frontend congelava nella preferenza la dimensione del preset di quel momento (ripulite dal changeSet `20261101-29`).

**2.5 DEF-2: calcolo flag `preset_aggiornato`** — identico alla funzione liste. Se la preferenza ha `preset_base_id` e `preset_base_contenuto_aggiornato_il` valorizzati, legge `dashboard_preset.contenuto_aggiornato_il` corrente e calcola:

```text
preset_aggiornato = TRUE sse:
  (a) preset_base_contenuto_aggiornato_il IS NOT NULL
  (b) dashboard_preset.contenuto_aggiornato_il IS NOT NULL
  (c) dashboard_preset.contenuto_aggiornato_il > preset_base_contenuto_aggiornato_il   ← il preset è più recente dello snapshot
  (d) preset_aggiornato_ignored_at IS NULL                     ← mai ignorato
      OPPURE preset_aggiornato_ignored_at < dashboard_preset.contenuto_aggiornato_il  ← preset cambiato dopo l'ultimo ignore
```

**3. Merge widget nuovi** — widget nel pool della dashboard (`ui.dashboard_widget`) ma assenti dalla configurazione candidata vengono aggiunti in coda con `visibile=FALSE` e `ordine = ordine_default + 10000`. Il contatore `widget_nuovi` indica quanti sono stati aggiunti. Garantisce che un widget aggiunto a catalogo dopo il salvataggio dell'utente compaia (non visibile) senza riscrivere la preferenza.

**4. Assemblaggio finale, filtro permessi e arricchimento** — per ogni widget del candidato:
  - **membership**: tenuto solo se appartiene al pool della dashboard (`ui.dashboard_widget`) ed è attivo (`ui.widget.attivo`) — un widget staccato o disattivato sparisce da tutti, preferenza inclusa
  - **filtro permessi** (nessuna tabella permessi dedicata):
    - `area_id IS NULL` **oppure** `livello(schema_db) <> 'BLOCCATO'` — decodifica `area_id → config.aree_funzionali.schema_db` e legge la mappa aree
    - **E** `azione_id IS NULL` **oppure** `abilitata(permission_codename)` — decodifica `azione_id → config.azioni_processo.permission_codename` e legge la mappa azioni
    - un widget che fallisce uno dei due gate viene rimosso
  - **arricchimento**: `tipo_widget`, `etichetta`, `etichetta_i18n_key`, `deep_link`, `contatore_key`, `soglia` letti **freschi** da `ui.widget` (il candidato/preferenza porta solo il `codice`, §3d del brief)

**5. Output JSONB** — restituisce la struttura pronta per il frontend.

## Caratteristiche

- **STABLE**: non modifica dati.
- Errori sollevati via `script.fn_log_and_raise_error` con codice `E_UI_DASHBOARD_NON_TROVATA`.
- **Campi opachi**: `deep_link`, `contatore_key`, `soglia` non sono interpretati né valutati dal DB — solo conservati e restituiti (grammatica FE / calcolo BE).

## Risultato

JSONB con le chiavi:

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `widget` | `jsonb[]` | Array di widget con `codice`, `ordine`, `visibile`, `tipo_widget`, `etichetta`, `etichetta_i18n_key`, `deep_link`, `contatore_key`, `soglia` |
| `dimensione_max` | `integer` | Numero massimo di card mostrabili (mirror di `pagina_dimensione` delle liste) |
| `dimensione_max_standard` | `integer` | La dimensione **senza** la preferenza: quella del preset di base, o 8 (dal 1-11-2026) |
| `origine` | `jsonb` | Per `widget` e `dimensione_max`, il livello da cui viene: `preferenza`, `ruolo`, `emittente_fiscale`, `sistema` o `catalogo`. Il frontend rimanda al salvataggio solo le chiavi `preferenza`, più quella toccata (dal 1-11-2026) |
| `widget_nuovi` | `integer` | Numero di widget aggiunti dal merge automatico (>0 = badge "aggiornato" nel frontend) |
| `preset_aggiornato` | `boolean` | DEF-2: `TRUE` se il preset di base è cambiato dopo lo snapshot della preferenza utente E l'utente non ha ancora ignorato. `FALSE` in tutti gli altri casi. |

> **Vincolo "mai vuota"** (brief §1/§3.bis): la cascata degrada fino al catalogo grezzo, mai a lista vuota — *prima* del filtro permessi. Il filtro però è ortogonale e può legittimamente svuotare la home a un utente senza permessi su nessuna area dei widget. La garanzia è realmente onorata solo se il **seed** del catalogo include almeno un widget **non-gated** (`area_id`/`azione_id` entrambi NULL): è una condizione di seed, non di struttura.

## Dipendenze

- `ui.dashboard_definizione` — lookup dashboard per codice
- `ui.widget` — catalogo globale widget (attributi freschi + gating `area_id`/`azione_id`)
- `ui.dashboard_widget` — pool candidato + sorgente catalogo grezzo/merge
- `ui.dashboard_preset` + `ui.dashboard_preset_widget` — configurazioni predefinite
- `ui.dashboard_preferenza_utente` — preferenza personale
- `script.fn_get_profili_accesso_applicabili` — risoluzione profili (cascata ruolo)
- `script.fn_get_user_permissions_map` / `script.fn_get_user_actions_map` — filtro permessi (resolve once)
- `config.aree_funzionali` / `config.azioni_processo` — decodifica `area_id`/`azione_id` per il lookup nelle mappe

## Esempio

```sql
-- Home per l'utente 42, emittente fiscale 1
SELECT ui.fn_resolve_dashboard_config('home', 42, 1);

-- Variante senza contesto emittente
SELECT ui.fn_resolve_dashboard_config('home', 42, NULL);
```

---

### Note di migrazione

* 2026-11-08 — il flag `preset_aggiornato` legge `dashboard_preset.contenuto_aggiornato_il` e lo snapshot rinominato (`brief-db-revisione-dbops`, giro 7-bis blocco c). Il JSON in uscita non cambia.
