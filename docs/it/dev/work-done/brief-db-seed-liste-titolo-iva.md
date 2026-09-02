# Brief team DB — seed lotto 3: le due liste dentro `TitoloIvaDrawer`

> **Stato**: ✅ **seed APPLICATO dal team DB** il 2026-09-02 (liste **64** e
> **65** in `lista_definizione.csv`, colonne 703-711). ⚠️ La nota precedente
> diceva che in questo tree non c'erano: era vera quando è stata scritta, e il
> merge `be811011a` l'ha superata. Resta scritta come fatto datato, non come
> stato.
>
> ⛔ **Ciò che NON è chiuso, ed è dichiarato qui perché non sembri fatto**: il
> drawer non è convertito — `grep titolo_iva_ambiti frontend/src` non trova
> niente, e le due `DataTable` grezze di `TitoloIvaDrawer` sono ancora lì. È il
> lavoro FE di Gruppo B, e il seed lo aspetta.
>
> ✅ **Il BE che il seed ha reso esigibile è invece fatto** (2026-09-02), perché
> tre presidi si sono accesi da soli nel momento in cui le righe sono arrivate:
>
> | Presidio acceso dal seed | Cosa ha chiesto | Fatto |
> | --- | --- | --- |
> | `test_lista_proiezione_campo_sorgente` §2 | una riga in `_ESERCIZI` per ogni lista senza vista | ✅ 64 e 65, esercitate su `list_ambiti` / `list_movimenti` |
> | idem §4 | una whitelist di ordinamento per ogni lista esercitata | ✅ `_ORDER_COLS_MOVIMENTI` (4 colonne, chiavate sui campi fisici) e `list_movimenti(order_by, order_dir)`. ⭐ Gli **ambiti** no, ed è corretto: a catalogo nessuna loro colonna è `ordinabile = t`, quindi vanno in `ORDINAMENTO_LOCALE` — non c'è nessun contratto da esigere |
> | `test_perimetro_emittente_copertura` | un `lista_codice` su una view per ogni lista a registro | ✅ dichiarato su `SoggettoTitoloIvaAmbitiView` e `SoggettoTitoloIvaMovimentiView` |
>
> ⚠️ **Un punto da rivedere insieme, e non l'ho toccato perché è vostro.** Il §4
> di questo brief dice *«`perimetro_emittente` non si accende»*, ma le due liste
> **non** hanno una riga in `lista_definizione_perimetro_emittente.csv` — e
> l'assenza di quella riga significa `TRUE` (è la decisione D-3 del lotto 2,
> presa in quella forma). Oggi non fa danno, perché il perimetro vale come sul
> padre `anagrafiche.soggetto_titoli_iva` e chi apre il drawer ci è arrivato da
> lì. Ma il brief e il catalogo dicono due cose diverse, e conviene farne dire
> una sola.
>
> **Chi scrive**: BE/FE. **Cosa serve**: 2 codici lista a catalogo, nient'altro.
> **Nessun DDL, nessun changeSet**: quattro append ai mirror `runOnChange` di
> `80_data/sql/ui/`, la stessa forma del [lotto 2](brief-db-seed-liste-lotto-2.md).

---

## 1. Perché ora

Rilievo di Tid in collaudo, 2026-09-02: *«il drawer del nuovo titolo IVA è
formattato male, stretto; e non usare le primitive DataTable»*.

La prima metà è **già corretta** e non riguarda il DB: il drawer scriveva
`DRAWER_WIDTH.LARGE`, chiave che **non esiste** in `constants.js` — `undefined`
in `width`, e il drawer restava al default di PrimeVue, **320px**. Nessun
errore, build verde, ESLint muto: le griglie a 2 e 3 colonne collassavano e la
maschera sembrava scritta male quando era solo strizzata. Corretto in
`DRAWER_WIDTH.WIDE` e presidiato da `frontend/scripts/check-drawer-width.mjs`.

⛔ **La seconda metà passa da qui.** Dentro quel drawer restano **due
`DataTable` grezze** — gli ambiti e il registro dei movimenti — e
`<ListaConfigurabile>` non è uno scambio di componente: è parametrizzato dalla
configurazione che il DB risolve (`ui.fn_resolve_lista_config`). Senza un
`codice` a catalogo non c'è niente da montare.

⚠️ Sono classificate **Gruppo B** nel
[piano](../work-in-progress/piano-migrazione-primevue-5.md) (§Classificazione del 02-09): sono le
righe *dell'entità che il drawer mostra*. Il Gruppo B si converte, come è già
successo con `LottoDrawer` (3 liste) e i 4 pannelli `ui`.

---

## 2. Le righe

### `lista_definizione.csv` (+2, id 64-65)

```
64,anagrafiche.titolo_iva_ambiti,Ambiti di un titolo IVA,anagrafiche,NULL,t,2026-09-02 00:00:00,mctit,f
65,anagrafiche.titolo_iva_movimenti,Registro movimenti di un titolo IVA,anagrafiche,NULL,t,2026-09-02 00:00:00,mctit,f
```

⚠️ `vista_sql = NULL` per entrambe: sono servite da endpoint, non da una view.
⛔ **Conseguenza da tenere presente** (già scritta nel lotto 2 §8): con
`vista_sql IS NULL` il trigger `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`
**esce senza validare**. Nessuno guarderà i `campo_sorgente` qui sotto: un refuso
non è un errore, è una **colonna vuota che non si lamenta**. Li ho confrontati a
mano con `_AMBITO_COLS` e `_MOVIMENTO_COLS` del repository.

`multi_emittente = f`: il titolo è già di un emittente, e queste liste sono le
sue righe.

### `lista_colonna.csv` (+9, id 703-711)

Lista 64 — **ambiti** (3 colonne):

```
703,64,livello,Livello,,livello,identificatore,string,,140,10,left,,10,f,f,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_livello,10
704,64,oggetto,Merce,,,informazione,string,,320,20,left,,10,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_oggetto,20
705,64,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
```

Lista 65 — **movimenti** (6 colonne):

```
706,65,data,Data,,data_movimento,identificatore,date,date_short,110,10,left,,10,f,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_data,10
707,65,movimento,Movimento,,tipo_movimento,informazione,string,,130,20,left,,10,f,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_movimento,20
708,65,imponibile,Imponibile,,imponibile,informazione,numeric,currency_eur,130,30,right,,10,f,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_imponibile,10
709,65,documento,Documento,,,informazione,string,,200,40,left,,10,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_documento,30
710,65,motivo,Motivo,,motivo,informazione,string,,240,50,left,,10,f,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_motivo,40
711,65,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
```

⚠️ **Le due colonne senza `campo_sorgente` sono calcolate** e hanno uno slot nel
frontend: `oggetto` compone articolo / gruppo voce / tipo voce a seconda del
`livello`, `documento` compone la fattura e la riga. Stessa forma di `validita`
e `stato` sulla lista 62. ⛔ Per questo sono `ordinabile = f`: non esiste una
colonna sola da ordinare, e una freccia sopra un valore composto o risponde 400
o ordina per un campo che non è quello che si legge.

⭐ **`ordinabile` diverge fra le due liste, ed è la differenza che conta**:

| | Lista 64 (ambiti) | Lista 65 (movimenti) |
| --- | --- | --- |
| Popolazione | limitata **per modello** — gli oggetti su cui un titolo si applica | **cresce**: è un registro append-only, e ogni fattura ne scrive |
| Montaggio FE | `:paginata="false"` | paginata |
| `ordinabile` | `f` su tutte | `t` sulle 4 con `campo_sorgente` |
| `pagina_dimensione` del preset | **vuota** | `25` |

⛔ È la stessa disciplina del lotto 2 §D-5: su una lista non paginata la
`pagina_dimensione` si lascia **vuota**, perché `COALESCE(..., 25)` renderebbe
indistinguibile «non l'ho scelta» da «l'ho scelta 25».

### `lista_preset.csv` (+2, id 64-65)

```
64,64,titolo_iva_ambiti_default,Vista standard ambiti del titolo,sistema,,,t,,,t,2026-09-02 00:00:00,mctit
65,65,titolo_iva_movimenti_default,Vista standard registro movimenti,sistema,,,t,25,,t,2026-09-02 00:00:00,mctit
```

### `lista_preset_colonna.csv` (+9)

```
64,703,10,t,f
64,704,20,t,f
64,705,999,t,f
65,706,10,t,f
65,707,20,t,f
65,708,30,t,f
65,709,40,t,f
65,710,50,t,f
65,711,999,t,f
```

⭐ **Preset == catalogo**, cioè banner DEF-2 **spento alla nascita**: una colonna
a catalogo fuori dal preset accenderebbe «ci sono colonne nuove» su una lista
che non ne ha.

⛔ **E la riga `azioni` nel preset non è facoltativa**: entrambe le liste hanno
un'azione per riga (il cestino sull'ambito, l'annullo sul movimento). Senza la
colonna `tipo_colonna = 'azione'` a catalogo il BB **non rende la colonna** e
quei due verbi spariscono **senza che niente fallisca** — è il difetto DB-1, poi
DB-2, e il presidio
`test_chi_fornisce_lo_slot_actions_ha_la_colonna_a_catalogo` lo pretende adesso.

---

## 3. Cosa fa il BE quando le righe atterrano — ✅ FATTO il 2026-09-02

Le righe sono atterrate lo stesso giorno e il lavoro è stato fatto subito dopo:
**BE-4 e BE-5 sono chiuse, e il drawer è convertito** (le due `DataTable` grezze
non ci sono più, contatore della regola zero 49 → **48**).

| # | Stato |
| --- | --- |
| **BE-4** | ✅ `list_movimenti(limit, offset, order_by, order_dir) -> (righe, totale)` con `COUNT(*) OVER()` e `fallback_count_sql`; whitelist `_ORDER_COLS_MOVIMENTI` sui campi fisici; endpoint paginato |
| **BE-5** | ✅ `list_ambiti(limit=None, offset)` ritorna `(righe, totale)` dalla **stessa** valutazione — non una seconda query. Envelope `{results, count}` |
| **FE** | ✅ due store su `createListaStore` + `useDrawerTabLista` + `<DrawerTabLista>`; gli ambiti `:paginata="false"`, il registro paginato |

⚠️ **`limit=None` = tutte le righe, e non è una comodità**: entrambi i metodi
hanno altri consumatori interni — `get_titolo` incorpora le due liste nel
dettaglio, e `annulla_movimento` indicizza il registro per verificare che il
movimento **appartenga a quel titolo**. Impaginare sotto quel controllo lo
avrebbe fatto guardare metà delle righe: è il modo in cui un guard smette di
guardare senza che niente lo dica.

<details>
<summary>La richiesta originale (per storia)</summary>

| # | Dove | Cosa | Perché |
| --- | --- | --- | --- |
| **BE-4** | `.../{titolo_id}/movimenti/` | `limit`/`offset` + `(righe, totale)` da **una** valutazione, e whitelist `MOVIMENTI_SORT_COLUMNS` chiavata sui `campo_sorgente` fisici (`data_movimento`, `tipo_movimento`, `imponibile`, `motivo`) | Le 4 colonne sono seminate `ordinabile = t`. Senza, la freccia o risponde 400 o non ordina — **e la seconda non lo dice** |
| **BE-5** | `.../{titolo_id}/ambiti/` | `count` accanto a `results`, da una query **sua** | La lista si monta `:paginata="false"`, dove `total` non è decorazione ma l'**asserzione** che le righe siano tutte. ⛔ Mai `len(results)`: sposterebbe la tautologia dal frontend al backend senza toglierla |

⭐ **E non è servito che qualcuno se ne ricordasse**: i presidi si sono accesi da
soli quando le righe sono arrivate — `test_lista_proiezione_campo_sorgente` ha
preteso un esercizio e una whitelist per ciascuna, `test_perimetro_emittente_copertura`
un `lista_codice` sulle view.

</details>

---

## 4. Cosa NON cambia

* **Nessun DDL, nessun changeSet**: quattro append, come il lotto 2.
* **Nessuna colonna `sensibile`**: non ci sono IBAN né dati riservati qui. Vale
  la nota del lotto 2 — `sensibile = t` è **allow-list** e senza una riga in
  `ui.lista_colonna_permesso` renderebbe la colonna invisibile a **tutti**.
* **Il perimetro emittente lo fa la RLS** sulle tre tabelle dei titoli, non
  queste liste: `perimetro_emittente` non si accende (il titolo è già dentro il
  perimetro di chi ha aperto il drawer).

---

## 5. Verifiche fatte prima di scrivere questo brief

* i `campo_sorgente` confrontati **uno per uno** con `_AMBITO_COLS` e
  `_MOVIMENTO_COLS` del repository: esistono tutti (`livello`, `data_movimento`,
  `tipo_movimento`, `imponibile`, `motivo`);
* id liberi verificati **sul database vero**, non solo nei CSV:
  `max(lista_definizione.id) = 63`, `max(lista_colonna.id) = 702`,
  `max(lista_preset.id) = 63`;
* **valori ENUM letti dal database, non inventati**: `tipo_colonna` ∈
  {`identificatore`, `informazione`, `azione`}, `tipo_dato` ∈ {`string`,
  `numeric`, `date`, `datetime`, `boolean`}, `formato` ∈ {`currency_eur`,
  `date_short`, `datetime_short`, `yesno`}. ⚠️ La prima stesura di queste righe
  aveva `valore` / `decimal` / `currency` — tre valori che *sembrano* giusti e
  non esistono;
* le 8 chiavi `etichetta_i18n_key` risolte nei locales: esistono tutte
  (`col_oggetto` vale **«Merce»**, e l'etichetta della riga è allineata a quella);
* parità CSV ↔ DB verificata prima di scrivere.
