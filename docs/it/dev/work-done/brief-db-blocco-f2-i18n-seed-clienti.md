# Brief Team DB — Blocco F.2: i18n etichette + fix seed `anagrafiche.clienti`

**Data:** 2026-05-08
**Riferimento:** [`sviluppo-personalizzazioni-liste.md`](sviluppo-personalizzazioni-liste.md), §10/§11 Blocco E + Blocco F.
**Branch:** `dev/db-tid`
**Priorità:** alta — la lista clienti operativa (`anagrafiche.clienti`) ha colonne sbagliate / mancanti / non multilingua; gli utenti EN vedono header italiani statici.

> ⚠️ **Aggiornamento 2026-05-08** dopo prima passata DB: la riga
> `partita_iva` del catalogo va **rimossa** (non solo nascosta). Il
> design corretto e' una sola colonna "Id. Fiscale" con
> `campo_sorgente=id_fiscale_univoco_cf_piva` (CF or PIVA fallback gia'
> nel backend). La chiave i18n `clienti.col_partita_iva` non e' piu'
> necessaria e non e' stata aggiunta ai locales. Vedi sezione
> "Correzione 2026-05-08" in fondo a questo brief.

---

## Riepilogo

3 modifiche ortogonali da raggruppare in una micro-tranche:

1. **Modello `ui.lista_colonna`**: aggiungere colonna nullable `etichetta_i18n_key VARCHAR(120)` per supportare etichette multilingua FE-resolved.
2. **Funzione `ui.fn_resolve_lista_config`**: includere `etichetta_i18n_key` nel JSONB di output (oggetto colonna).
3. **Seed `anagrafiche.clienti`**: correggere `campo_sorgente` di `codice_fiscale`, aggiungere colonna composta `sosp_riatt`, popolare `etichetta_i18n_key` per tutte le colonne, aggiornare preset di sistema per nascondere di default le colonne in eccesso.

---

## Sintomo riportato

Lista clienti `/anagrafiche/clienti` (Blocco E5 atterrato 2026-05-07):

- Header colonne in inglese: l'utente vede "Ragione Sociale" anche con language=EN — `ui.lista_colonna.etichetta` e' una stringa letterale italiana.
- Colonna "Codice Fiscale" mostra il solo CF, senza fallback a P.IVA per persone giuridiche → utenti privi di CF appaiono vuoti.
- 13 colonne attive di default (con `partita_iva`, `stato_codice`, `data_sospensione`, `data_riattivazione`, `soggetto_codice` separate) → il template originale ne mostrava 9 con la coppia data_sospensione/data_riattivazione fusa in una colonna composta `sosp_riatt`.

Causa root: il seed Blocco E (atterrato 2026-05-07 dal team DB) ha mappato 1:1 i campi della query backend senza un preset di sistema che nasconda i tecnici, e senza colonna composta + senza chiavi i18n.

---

## 1. DDL: nuova colonna `etichetta_i18n_key`

File suggerito: `db/changelog/migrations_v2/00_schema/ui/20260508-01-alter-ui-lista-colonna-etichetta-i18n-key-mctit.yaml`.

```sql
ALTER TABLE ui.lista_colonna
  ADD COLUMN etichetta_i18n_key VARCHAR(120);

COMMENT ON COLUMN ui.lista_colonna.etichetta_i18n_key IS
  'Chiave i18n FE risolta via vue-i18n t(). Fallback a etichetta letterale '
  'se la chiave non esiste nei locales. NULL = usa solo etichetta.';
```

Niente vincoli (no UNIQUE, no NOT NULL): la chiave puo' essere riusata fra liste, e il fallback a `etichetta` letterale resta sempre possibile.

Niente impatto su `lista_preset_colonna` / `lista_preferenza_utente` (preferenza utente memorizza solo `codice` colonna stabile, non l'etichetta).

## 2. Funzione `ui.fn_resolve_lista_config`

Aggiungere `etichetta_i18n_key` agli oggetti colonna ritornati nel JSONB.

Punto di intervento: la subquery che costruisce gli oggetti colonna a partire da `ui.lista_colonna` deve esporre il nuovo campo. Pattern attuale (semplificato):

```sql
jsonb_build_object(
  'codice', lc.codice,
  'ordine', ...,
  'visibile', ...,
  'fissata', ...,
  'larghezza', ...,
  -- aggiungere:
  'etichetta_i18n_key', lc.etichetta_i18n_key
)
```

Estendere anche il SELECT del catalogo modale (se la funzione `ui.fn_resolve_lista_config` lo ritorna) o in alternativa la view backend di `apps.ui.db.ui_repository.list_colonne_by_codice` (che gia' fa SELECT esplicito sui campi di `ui.lista_colonna`): in quel caso il backend agent aggiungera' `lc.etichetta_i18n_key` al SELECT post DDL.

## 3. Seed CSV `anagrafiche.clienti`

File CSV del seed `ui.lista_colonna` per la lista `anagrafiche.clienti`.

### 3.1 Correzioni colonne esistenti

| codice | campo_sorgente DOPO | etichetta DOPO | etichetta_i18n_key | tipo_colonna | Note |
| --- | --- | --- | --- | --- | --- |
| `ragione_sociale` | `ragione_sociale_completa` | "Ragione Sociale" | `clienti.col_ragione_sociale` | identificatore | invariato |
| `ba_codice` | `ba_codice` | "Cd. Account" | `clienti.col_ba_codice` | informazione | etichetta da rivedere |
| `soggetto_codice` | `soggetto_codice` | "Cd. Soggetto" | `clienti.col_cd_soggetto` | informazione | invariato |
| `codice_fiscale` ⚠️ | `id_fiscale_univoco_cf_piva` ✏️ | "Id. Fiscale" ✏️ | `clienti.col_id_fiscale` | informazione | **rinominata logicamente** — il `codice` colonna resta `codice_fiscale` per compat preferenze utente; cambia solo `campo_sorgente` (BE espone gia' il campo dopo fix repo `clienti_repository.py`) ed etichetta |
| `partita_iva` | `partita_iva` | "Partita IVA" | `clienti.col_partita_iva` (da aggiungere ai locale) | informazione | invariato |
| `utility` | `utility_descrizione` | "Utility" | `clienti.col_utility` | informazione | invariato |
| `stato` | `stato_descrizione` | "Stato" | `clienti.col_stato` | informazione | invariato |
| `stato_codice` | `stato_codice` | "Cod. Stato" | (vuota — colonna tecnica) | informazione | invariato |
| `data_attivazione` | `data_attivazione` | "Attivazione" | `clienti.col_data_attivazione` | informazione | `formato='date_short'` |
| `data_sospensione` | `data_sospensione` | "Sospeso il" | `clienti.col_sospeso_il` | informazione | `formato='date_short'` |
| `data_riattivazione` | `data_riattivazione` | "Riattivato il" | `clienti.col_riattivato_il` | informazione | `formato='date_short'` |
| `data_chiusura` | `data_chiusura` | "Chiusura" | `clienti.col_data_chiusura` | informazione | `formato='date_short'` |
| `azioni` | (vuoto) | "Azioni" | `common.col_azioni` | azione | invariato |

### 3.2 Colonna nuova: `sosp_riatt` (composta calcolata FE)

Aggiungere riga con `campo_sorgente=NULL` (la colonna e' calcolata interamente lato FE — slot `cell-sosp_riatt` gia' presente in [`ClientiSearchTable.vue`](../../../../frontend/src/anagrafiche/components/ClientiSearchTable.vue#L235-L240)):

| codice | campo_sorgente | etichetta | etichetta_i18n_key | tipo_colonna | tipo_dato | ordine_default | larghezza_default | ordinabile | esportabile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sosp_riatt` | `NULL` | "Sosp./Riatt." | `clienti.col_sosp_riatt` | informazione | string | 105 | 130 | false | false |

**Verifica trigger guard**: `trgfn_ui_lista_colonna_a10_valida_campo_sorgente` deve ammettere `campo_sorgente IS NULL` per colonne calcolate FE. Se oggi blocca, aggiungere short-circuit `IF NEW.campo_sorgente IS NULL THEN RETURN NEW`. Decisione architetturale: si accetta colonna senza campo sorgente DB perche' in alcuni casi il dato e' derivato lato presentazione.

### 3.3 Preset di sistema (`ui.lista_preset` + `ui.lista_preset_colonna`)

Il preset di sistema `default` per `anagrafiche.clienti` deve mostrare di default solo le colonne effettivamente utili all'operatore. Configurazione richiesta:

| codice | visibile (preset sistema) | ordine |
| --- | --- | --- |
| `ragione_sociale` | true | 30 |
| `ba_codice` | true | 20 |
| `soggetto_codice` | true | 10 |
| `codice_fiscale` | true | 40 |
| `partita_iva` | **false** | 50 |
| `utility` | true | 60 |
| `stato` | true | 110 |
| `stato_codice` | **false** | 120 |
| `data_attivazione` | true | 70 |
| `data_sospensione` | **false** | 80 |
| `data_riattivazione` | **false** | 90 |
| `data_chiusura` | true | 100 |
| `sosp_riatt` | true | 105 |
| `azioni` | true | 999 |

`partita_iva` resta nel catalogo (un super-admin potrebbe volerla vedere separata) ma di default e' nascosta perche' coperta da `id_fiscale_univoco_cf_piva` (CF or PIVA fallback). `stato_codice` e le 2 date raw analoghe sono tecniche / sostituite da `sosp_riatt`.

---

## Esecuzione

1. Apply DDL nuova colonna (`20260508-01-alter-ui-lista-colonna-etichetta-i18n-key-mctit.yaml`).
2. Apply update `ui.fn_resolve_lista_config` (`runOnChange:true` allineata al pattern Blocco B).
3. Update CSV seed `ui.lista_colonna` con le 12+1 (correzioni + `sosp_riatt`) + popolare `etichetta_i18n_key`.
4. Update CSV seed `ui.lista_preset_colonna` con `visibile=false` sulle 4 colonne tecniche.
5. Lanciare Liquibase (changeset esistenti `runOnChange`).
6. Verificare:

```sql
SELECT lc.codice, lc.etichetta, lc.etichetta_i18n_key, lc.campo_sorgente, lc.tipo_colonna::text
  FROM ui.lista_colonna lc
  JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
 WHERE ld.codice = 'anagrafiche.clienti'
 ORDER BY lc.ordine_default;
```

Atteso: 14 righe (era 13), `codice_fiscale.campo_sorgente='id_fiscale_univoco_cf_piva'`, tutte hanno `etichetta_i18n_key` valorizzato, presenza di riga `sosp_riatt`.

```sql
SELECT lc.codice, lpc.visibile, lpc.ordine
  FROM ui.lista_preset_colonna lpc
  JOIN ui.lista_preset lp ON lp.id = lpc.preset_id
  JOIN ui.lista_colonna lc ON lc.id = lpc.colonna_id
 WHERE lp.lista_id = (SELECT id FROM ui.lista_definizione WHERE codice='anagrafiche.clienti')
   AND lp.ambito = 'sistema' AND lp.is_default = true
 ORDER BY lpc.ordine;
```

Atteso: 14 righe con visibile coerente alla tabella §3.3.

## Cosa fa il backend Python (gia' aggiornato)

`backend/apps/anagrafiche/db/clienti_repository.py` aggiunge `s.id_fiscale_univoco_cf_piva` al SELECT della lista clienti — pronto a fornire il campo non appena il seed lo richiede.

## Cosa fa il frontend (gia' aggiornato)

- `useListaConfig.load()` ora carica `config + catalogo` in parallelo (non piu' lazy on modal): le etichette + `campo_sorgente` sono disponibili al primo render, non si vede piu' il fallback "ragione_sociale" come header.
- `ListaConfigurabile.vue` risolve l'header della Column con `t(etichetta_i18n_key) || etichetta || codice` (fallback safe). Se la chiave i18n non esiste nei locales (`te()` false) o non e' valorizzata, fallback all'etichetta letterale.

## Correzione 2026-05-08 — `partita_iva` come riga separata: rimuovere

Dopo la prima passata DB e l'integrazione FE, e' emerso che il design
corretto e' una **sola colonna** "Id. Fiscale" che contiene
indistintamente CF (persone fisiche) o PIVA (persone giuridiche).
Il backend gia' espone `id_fiscale_univoco_cf_piva` con il fallback
applicato lato vista SQL — il FE legge solo quel campo.

Quindi la riga `partita_iva` nel catalogo e' ridondante e crea rumore
nella modale di personalizzazione (l'utente vedrebbe due colonne
fiscali: "Id. Fiscale" e "Partita IVA" separate).

### Modifica richiesta

CSV seed `ui.lista_colonna` per `anagrafiche.clienti`:

- **Rimuovere** la riga con `codice='partita_iva'`. In alternativa
  marcarla `attivo=false` se preferite preservare lo storico, ma
  rimuoverla e' piu' pulito (la lista catalogo si comporta come "nuovo
  default" — non ci sono ancora preferenze utente che la referenzino
  in produzione).

CSV seed `ui.lista_preset_colonna` per il preset di sistema della
stessa lista:

- **Rimuovere** la riga corrispondente al preset_id+colonna_id di
  `partita_iva`. (Se la riga `partita_iva` e' DELETE in `ui.lista_colonna`,
  la FK CASCADE gia' rimuove anche la riga in `lista_preset_colonna`.)

Niente da modificare nel resto del catalogo / preset (le altre 13 righe
gia' allineate alla §3.1 / §3.3 originali restano valide).

### Cosa non serve piu'

- La chiave i18n `clienti.col_partita_iva` non e' stata aggiunta ai
  locales it.json/en.json (il frontend non la usa piu' in nessun punto
  della lista clienti). La nota "FE pendente" del DB puo' considerarsi
  chiusa.

## Risposta attesa dal team DB

Conferma del completamento di:

1. DDL nuova colonna (idempotente, ON CONFLICT/preCondition).
2. Update fn_resolve_lista_config.
3. Seed CSV aggiornato.
4. Verifica SQL OK.

A quel punto il backend agent puo' riavviare il server (cache permessi non impattata, ma fn DB cached da PG va re-loaded automaticamente) e l'utente vede la lista clienti con etichette tradotte, fallback CF/PIVA, e default colonne pulito.
