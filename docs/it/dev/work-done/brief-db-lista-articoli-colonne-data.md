# Brief DB — Lista articoli: le due colonne data nel catalogo colonne

> **Destinatari:** team DB (`dev/db-tid`). Ricaduta BE di una riga (§3), che
> ⛔ entra **nello stesso merge** del seed, non dopo (§3).
>
> **Tipo:** allineamento di seed, piccolo. Decisione di Tid del 2026-09-26:
> *«aggiungere al catalogo»*.
>
> **Stato:** ✅ chiuso il 2026-09-26. Lato DB righe 939/940 applicate da Tid
> (pgTAP verdi); ricaduta BE (§3) fatta su `dev/backend-tid` lo stesso giorno,
> test 10 e 10-bis verdi.

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

### ✅ Fatto (2026-09-26)

Righe **939** e **940** in coda a `80_data/sql/ui/lista_colonna.csv`:

| id | codice | larghezza | ordine_default | allineamento | gruppo / ordine | priorita |
| --- | --- | --- | --- | --- | --- | --- |
| 939 | `data_insert` | 150 | 90 | center | `Audit` / 1 | 10 |
| 940 | `data_update` | 150 | 95 | center | `Audit` / 1 | 5 |

Gli altri campi sono quelli della tabella qui sopra. `gruppo_ordine` vale 1
perché sulla lista 26 nessun'altra colonna ha un gruppo: `Audit` è il primo.

- **Nessun changeSet nuovo.** Il CSV lo applica il mirror
  `20260806-15-riancora-mirror-ui-lista-colonna` (`runOnChange` +
  `validCheckSums: ANY`), che ri-gira al cambio del file. La sequenza
  dell'`id` la riallinea `90_end/20260602-17-resync-ui-seed-identity-sequences`.
- Nessun pgTAP conta le colonne della lista 26: censito con un grep in
  `db/pgtap` per `catalogo.articoli` e `lista_id = 26`.
- Applicato da Tid il 2026-09-26: pgTAP verdi, nessuna regressione.

## 3. Ricaduta BE (⛔ nello stesso merge del seed)

⛔ **Correzione del 2026-09-26: non «dopo il merge».** Il presidio
`test_liste_configurabili_seed` legge il **CSV del repository**, non il DB.
Col seed nuovo, `catalogo.articoli` ha colonne data ordinabili senza
`colonne_desc` e non è nel registro `_DEBITO_RIPIEGO_DATA_ASC`, quindi il
**test 10-bis** (`test_il_debito_del_ripiego_asc_non_cresce`) diventa rosso
finché non entra la riga BE qui sotto. Il test 10 è il gemello: dichiarare
l'insieme senza il seed lo fa rosso. Quindi seed e riga BE vanno in `Tito-dev`
**nello stesso merge**. Aggiungere la lista al registro di debito per
passare non è un rimedio: il registro può solo calare.

In `catalogo_repository.py`:

- dichiarare `ARTICOLI_SORT_COLONNE_DATA = frozenset({"data_insert", "data_update"})`
  e passarlo a `sql_order_clause(colonne_desc=...)` in `list_articoli`;
- togliere il commento `⚠️ Nessun insieme per gli articoli`, che segnala
  proprio questo punto aperto.

Il test 10 diventa il presidio dell'allineamento: se una delle due righe
sparisse dal seed, il test diventerebbe rosso.
