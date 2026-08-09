# Brief DB — DEF-8 fornitori: seed catalogo + preset + estensione vista CF/PIVA

> **Tipo**: seed CSV (lista_definizione/colonna/preset/preset_colonna) +
> piccolo update vista SQL (`vw_fornitori_dettaglio` con
> `id_fiscale_univoco_cf_piva`).
> **Branch**: `dev/db-tid`.
> **Autore brief**: backend agent (Tid, sessione 2026-05-23).
> **Origine**: roadmap `sviluppo-personalizzazioni-liste_def.md` -> DEF-8
> incrementale (passo 3 di 13, dopo clienti + soggetti).
> **Decisioni operative chiuse da Tid 2026-05-23**:
>
> 1. Scope: personalizzazione (DEF-8) + export CSV/Excel (DEF-1) insieme.
> 2. Preset default: identico all'attuale lista fornitori
>    (6 colonne visibili + azioni).
> 3. Lezioni applicate da DEF-8 soggetti: `sensibile=false` su CF/PIVA,
>    `campo_sorgente='id_fiscale_univoco_cf_piva'` (campo GENERATED).

## Contratto col repo BE (per allineamento)

Il repository `apps.anagrafiche.db.fornitori_repository.FornitoriRepository.list_fornitori`
([backend/apps/anagrafiche/db/fornitori_repository.py:95](../../../../backend/apps/anagrafiche/db/fornitori_repository.py))
legge dalla vista `anagrafiche.vw_fornitori_dettaglio`. La vista oggi
espone questi campi (verifica `information_schema.columns`):

- `id`, `soggetto_ruolo_id`, `codice`, `attivo`
- `stato_codice`, `stato_descrizione`, `blocca_ordini`
- `soggetto_id`, `ragione_sociale_completa`
- `codice_fiscale`, `partita_iva` (separati)
- `valuta_iso`, `modalita_pagamento_codice`, `modalita_pagamento_desc`
- `termine_pagamento_codice`, `giorni_pagamento`, `fine_mese`
- `split_payment`, `ritenuta_acconto`, `regime_fiscale`
- `rating`, `qualifica_scadenza`, `canale_fe`, `pec_email`
- `data_insert`, `data_update`

**Differenza vs soggetti**: il fornitore legge da vista (`vista_sql`
valorizzata), non da repo Python con alias. Il trigger DB
`trgfn_ui_lista_colonna_a10_valida_campo_sorgente` valida `campo_sorgente`
contro le colonne reali della vista.

## Modifiche DB richieste

### Step 1. Estendere `vw_fornitori_dettaglio` con `id_fiscale_univoco_cf_piva`

La colonna `id_fiscale_univoco_cf_piva` esiste come `GENERATED ALWAYS` su
`anagrafiche.soggetti` (COALESCE CF/PIVA, identico al pattern clienti).
La vista oggi non la propaga, quindi va aggiunta nel SELECT della vista
(JOIN su `soggetti` via `soggetto_id`):

```sql
-- nuova migration: 20_code/anagrafiche/2026MMDD-NN-update-vw-fornitori-dettaglio-add-id-fiscale-univoco-mctit.yaml
CREATE OR REPLACE VIEW anagrafiche.vw_fornitori_dettaglio AS
SELECT v.*,
       s.id_fiscale_univoco_cf_piva
  FROM <SELECT esistente AS v>
  JOIN anagrafiche.soggetti s ON s.id = v.soggetto_id;

-- (oppure aggiungere `s.id_fiscale_univoco_cf_piva` al SELECT della
--  view se l'attuale gia' JOINa soggetti)
```

Senza questo step, il seed `lista_colonna` con
`campo_sorgente='id_fiscale_univoco_cf_piva'` farebbe scattare il trigger
B2 di validazione (`E_UI_CAMPO_SORGENTE_NON_TROVATO`).

### Step 2. Seed `ui.lista_definizione`

Nuova riga nel CSV `80_data/sql/ui/lista_definizione.csv`:

```csv
codice,descrizione,schema_dati,vista_sql,attivo
anagrafiche.fornitori,Fornitori,anagrafiche,vw_fornitori_dettaglio,t
```

A differenza di clienti/soggetti (`vista_sql=NULL`), qui valorizziamo
la vista — il trigger B1 verifica che la vista esista nel pg_catalog (OK
dopo Step 1).

### Step 3. Seed `ui.lista_colonna`

15 colonne nel CSV `80_data/sql/ui/lista_colonna.csv` (per
`lista_id` di `anagrafiche.fornitori`). Tabella:

| codice | etichetta | etichetta_i18n_key | campo_sorgente | tipo_colonna | tipo_dato | formato | larghezza_default | ordine_default | gruppo | gruppo_ordine | filtrabile | ordinabile | esportabile | ricercabile_full | sensibile | attivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `codice` | Codice | `fornitori.col_codice` | `codice` | `identificatore` | `text` |  | 130 | 10 | dati | 10 | t | t | t | t | f | t |
| `ragione_sociale_completa` | Ragione Sociale | `fornitori.col_ragione_sociale` | `ragione_sociale_completa` | `informazione` | `text` |  | 200 | 20 | dati | 10 | t | t | t | t | f | t |
| `id_fiscale` | Id. Fiscale | `fornitori.col_id_fiscale` | `id_fiscale_univoco_cf_piva` | `informazione` | `text` |  | 160 | 30 | dati | 10 | t | t | t | t | f | t |
| `modalita_pagamento_desc` | Mod. pagamento | `fornitori.col_modalita_pagamento` | `modalita_pagamento_desc` | `informazione` | `text` |  | 150 | 40 | dati | 10 | t | t | t | f | f | t |
| `stato` | Stato | `fornitori.col_stato` | `stato_descrizione` | `informazione` | `text` |  | 110 | 50 | dati | 10 | t | t | t | f | f | t |
| `data_insert` | Creazione | `fornitori.col_data_insert` | `data_insert` | `informazione` | `date` | `date_short` | 110 | 60 | dati | 10 | t | t | t | f | f | t |
| `azioni` | Azioni | `common.col_azioni` |  | `azione` |  |  |  | 99 |  |  | f | f | f | f | f | t |
| `codice_fiscale` | Codice fiscale | `common.codice_fiscale` | `codice_fiscale` | `informazione` | `text` |  | 140 | 70 | extra | 20 | t | t | t | t | f | t |
| `partita_iva` | Partita IVA | `common.partita_iva` | `partita_iva` | `informazione` | `text` |  | 140 | 80 | extra | 20 | t | t | t | t | f | t |
| `pec_email` | PEC | `fornitori.col_pec_email` | `pec_email` | `informazione` | `text` |  | 220 | 90 | extra | 20 | f | t | t | f | f | t |
| `canale_fe` | Canale FE | `fornitori.col_canale_fe` | `canale_fe` | `informazione` | `text` |  | 100 | 100 | extra | 20 | t | t | t | f | f | t |
| `split_payment` | Split payment | `fornitori.col_split_payment` | `split_payment` | `informazione` | `bool` | `yesno` | 110 | 110 | extra | 20 | t | t | t | f | f | t |
| `ritenuta_acconto` | Ritenuta | `fornitori.col_ritenuta_acconto` | `ritenuta_acconto` | `informazione` | `bool` | `yesno` | 110 | 120 | extra | 20 | t | t | t | f | f | t |
| `regime_fiscale` | Regime fiscale | `fornitori.col_regime_fiscale` | `regime_fiscale` | `informazione` | `text` |  | 130 | 130 | extra | 20 | f | t | t | f | f | t |
| `data_update` | Aggiornamento | `fornitori.col_data_update` | `data_update` | `informazione` | `date` | `date_short` | 110 | 140 | extra | 20 | t | t | t | f | f | t |

Note:

- **`sensibile=false` su tutto, anche CF/PIVA e PEC**: lezione DEF-8
  soggetti (un `sensibile=true` senza grant esplicito in
  `lista_colonna_permesso` farebbe sparire la colonna dal payload anche
  per SUPER_ADMIN). Se serve restrizione per profili specifici (es.
  portale shop), aggiungere record `lista_colonna_permesso` opt-out.
- **Colonna unificata `id_fiscale`** (visibile nel preset di default):
  `campo_sorgente='id_fiscale_univoco_cf_piva'`, etichetta "Id. Fiscale"
  identica a clienti+soggetti. Step 1 della vista e' prerequisito (il
  trigger B2 valida `campo_sorgente` contro `pg_attribute` della vista).
- **`codice='id_fiscale'`** scelto distinto da `codice_fiscale` per
  permettere di tenere entrambi nel catalogo: l'utente che preferisce
  vedere CF e P.IVA separatamente puo' attivarli da Personalizza Colonne.
  Divergenza voluta vs clienti+soggetti (che hanno `codice='codice_fiscale'`
  per la colonna unificata). Allineamento clienti+soggetti a `id_fiscale`
  resta possibile in un brief separato di rename (richiede migrazione
  delle preferenze utente JSONB esistenti su clienti).
- **Gruppo `extra`** (gruppo_ordine 20) per le 8 colonne opt-in: si vedono
  nel drawer "Personalizza colonne" sotto un raggruppamento dedicato, e
  l'utente le attiva al bisogno.
- **`tipo_dato='bool'`+`formato='yesno'`** per split_payment/ritenuta_acconto:
  il default formatter di `<ListaConfigurabile>` rende automaticamente
  "Si/No" (vedi `useI18n` localizzata).

### Step 4. Seed `ui.lista_preset` (1 preset di sistema)

Nuova riga in `80_data/sql/ui/lista_preset.csv`:

```csv
codice,descrizione,lista_codice,ambito,profilo_accesso_id,emittente_fiscale_id,pagina_dimensione,ordinamento_default,filtri_default,is_default,attivo
fornitori_default,Vista standard fornitori,anagrafiche.fornitori,sistema,,,50,"[{""col"":""ragione_sociale_completa"",""dir"":""asc""}]",{},t,t
```

`pagina_dimensione=50` allineato al default `useSearchTable`.
`ordinamento_default` matcha `defaultSortField: 'ragione_sociale_completa'`
del FE attuale.

### Step 5. Seed `ui.lista_preset_colonna`

7 righe in `80_data/sql/ui/lista_preset_colonna.csv` — solo le colonne
visibili di default (il resto `attivo=true` nel catalogo ma non incluso
nel preset = appare come "nascosta" finché l'utente non la attiva):

| preset_codice | colonna_codice | ordine | larghezza | visibile | fissata |
|---|---|---|---|---|---|
| `fornitori_default` | `codice` | 10 | 130 | t | t |
| `fornitori_default` | `ragione_sociale_completa` | 20 | 200 | t | f |
| `fornitori_default` | `id_fiscale` | 30 | 160 | t | f |
| `fornitori_default` | `modalita_pagamento_desc` | 40 | 150 | t | f |
| `fornitori_default` | `stato` | 50 | 110 | t | f |
| `fornitori_default` | `data_insert` | 60 | 110 | t | f |
| `fornitori_default` | `azioni` | 99 |  | t | f |

`codice` ha `fissata=true` (identificatore, pattern clienti+soggetti).
**Importante**: la colonna visibile nel preset deve essere `id_fiscale`
(la versione unificata che mostra CF o P.IVA via campo GENERATED), NON
`codice_fiscale` (CF puro, vuoto per quasi tutti i fornitori azienda).
Le 8 colonne extra del catalogo (`codice_fiscale`, `partita_iva`,
`pec_email`, `canale_fe`, `split_payment`, `ritenuta_acconto`,
`regime_fiscale`, `data_update`) NON sono nel preset → in
`fn_resolve_lista_config` lo Step 3 "merge colonne nuove" le aggiunge
automaticamente in coda con `visibile=false`, e il `colonne_nuove` count
le segnala col badge "N nuove disponibili" all'utente.

## Smoke post-seed

```bash
# Vista estesa
psql -c "SELECT 'id_fiscale_univoco_cf_piva' = ANY(ARRAY(
  SELECT column_name FROM information_schema.columns
   WHERE table_schema='anagrafiche' AND table_name='vw_fornitori_dettaglio'
)) AS view_ok;"
-- atteso: true

# Lista registrata
psql -c "SELECT codice FROM ui.lista_definizione WHERE codice='anagrafiche.fornitori';"
-- atteso: 1 riga

# Conta colonne risolte per utente con preferenza vuota
psql -c "SELECT jsonb_array_length(
  ui.fn_resolve_lista_config('anagrafiche.fornitori', <user_id>, NULL) -> 'colonne'
) AS n_colonne;"
-- atteso: 14 (tutte presenti, 7 visibili + 7 nascoste-merge)
```

Lato FE/BE post-seed: niente cambio richiesto immediatamente
(`<ListaConfigurabile codice="anagrafiche.fornitori">` funziona).
Refactor di `FornitoriSearchTable.vue` + endpoint export arrivano nei
commit successivi del backend agent.

## Riferimenti

- Brief gemello (soggetti, atterrato 2026-05-11):
  `brief-db-def8-soggetti-catalogo.md` (⚠️ documento non presente nel repo)
  + `brief-db-def8-soggetti-fix-id-fiscale.md` (⚠️ documento non presente nel repo).
- Lezioni cross-DEF-8 (sensibile=false + campo GENERATED) documentate in
  [sviluppo-personalizzazioni-liste_def.md](../work-in-progress/sviluppo-personalizzazioni-liste_def.md)
  sezione DEF-8 "Lezioni dallo smoke soggetti".
- Repository: [backend/apps/anagrafiche/db/fornitori_repository.py](../../../../backend/apps/anagrafiche/db/fornitori_repository.py).
- FE attuale: [frontend/src/anagrafiche/components/FornitoriSearchTable.vue](../../../../frontend/src/anagrafiche/components/FornitoriSearchTable.vue).
