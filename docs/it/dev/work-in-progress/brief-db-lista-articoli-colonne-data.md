# Brief DB — Lista articoli: le due colonne data nel catalogo colonne

> **Destinatari:** team DB (`dev/db-tid`). Ricaduta BE di una riga (§3), che
> si fa dopo il merge del seed.
>
> **Tipo:** allineamento di seed, piccolo. Decisione di Tid del 2026-09-26:
> *«aggiungere al catalogo»*.
>
> **Stato:** 📝 da fare.

---

## 1. Il disallineamento

La lista **`catalogo.articoli`** (`ui.lista_definizione` id 26) ha una
whitelist di ordinamento, `ARTICOLI_ORDER_COLUMNS` in
`backend/apps/catalogo/db/catalogo_repository.py`, che ammette `data_insert` e
`data_update`. Il repository le proietta già (`a.data_insert`, `a.data_update`)
e le usa anche per il filtro per data.

Il catalogo colonne (`ui.lista_colonna`, seed
`db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv`) **non ha queste
due righe** per la lista 26. Le conseguenze sono due:

- l'operatore non può né vederle né ordinarle da interfaccia, anche se il
  backend le supporta;
- il backend non può dichiarare il ripiego DESC delle colonne data (regola di
  Tid del 2026-09-02: una lista ordinata per data si apre dal più recente).
  Il presidio `test_liste_configurabili_seed` (test 10) confronta quell'insieme
  con il seed, e dichiararlo oggi lo farebbe diventare rosso.

Le liste UoM dello stesso catalogo (id 20 e 21) le hanno già.

## 2. Richiesta al team DB

Due righe in `ui.lista_colonna` per `lista_id = 26`, ricalcate sulle righe
279/280 (lista 20) e 287/288 (lista 21):

| codice | campo_sorgente | tipo_dato | formato | gruppo | filtrabile | ordinabile | esportabile | etichetta_i18n_key |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `data_insert` | `data_insert` | `datetime` | `datetime_short` | `Audit` | f | **t** | t | `common.data_insert` |
| `data_update` | `data_update` | `datetime` | `datetime_short` | `Audit` | f | **t** | t | `common.data_update` |

- **`ordine_default`**: dopo le colonne informative, prima di `azioni` (999),
  per esempio 90 e 95.
- **Visibilità di default e `priorita`**: come le liste UoM (10 e 5), a meno
  che il team DB non preferisca tenerle nascoste di default su una lista già
  larga.
- Le chiavi i18n `common.data_insert` / `common.data_update` esistono già in
  entrambi i locales: nessun intervento sul frontend.

## 3. Ricaduta BE (dopo il merge del seed)

In `catalogo_repository.py`:
- dichiarare `ARTICOLI_SORT_COLONNE_DATA = frozenset({"data_insert", "data_update"})`
  e passarlo a `sql_order_clause(colonne_desc=...)` in `list_articoli`;
- togliere il commento `⚠️ Nessun insieme per gli articoli`, che segnala
  proprio questo punto aperto.

Il test 10 diventa il presidio dell'allineamento: se una delle due righe
sparisse dal seed, il test diventerebbe rosso.
