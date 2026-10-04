# Linee guida Trigger (PostgreSQL + Liquibase)

## Scopo

Definire **convenzioni univoche** per:

* naming dei trigger e delle funzioni trigger,
* quando usare `UPDATE OF ...`,
* ordine di esecuzione (priorità),
* pattern degli eventi (`_ins/_upd/_dlt`).

---

## Convenzioni di naming

### Prefisso

* Tutti i trigger iniziano con **`trg_`**.

### Nome_tabella

* seguono con  **`_schema_`** opzionale nel caso di tabelle con nome identico su schema diverso, 
* **`_nome_tabella_`** .


### Fasi / priorità

Usiamo suffissi alfabetici per imporre l’**ordine di esecuzione** (i trigger sono eseguiti in ordine lessicografico):

* **`_a10_`** → **trigger di verifica/blocco** (validazioni, guard-rails). Se falliscono, chiamano la nostra funzione di errore/log e **impediscono** l’operazione.
* **`_a05_`** → **il rifiuto che deve parlare per primo**. Fra più guard `BEFORE ROW` sulla stessa tabella a parlare è quello col nome alfabeticamente minore, e la frase che l'operatore legge è quella. Quando un guard dice *«questa cosa non si tocca»* (immutabilità: documento fuori bozza, forma di un codice) deve venire **prima** dei guard che giudicano il valore nuovo o i legami (*«c'è un fulfillment»*, *«ci sono figli»*): altrimenti l'operatore riceve un rimedio che non è il rimedio. Precedenti: `trg_emittenti_fiscali_a05_guard_codice_forma_*`, `trg_*_a05_doc_righe_lock_fuori_bozza_*` (il building block «le righe di un documento si toccano solo in bozza», 2026-09-22). ⚠️ Non è una fascia «più importante»: è una precedenza fra rifiuti, da usare solo quando l'ordine è dominio.
* **`_z90_`** → **trigger finali** (effetti collaterali “terminali”), es. duplicazione su schema storico, audit finali.

Se servono step intermedi (facoltativo in futuro): riserviamo `_mXX_` (es. `_m50_`).

* **`_z90_`**  Usare per trigger defferrable.

### Eventi (segmento finale)

* `_ins` = `INSERT`
* `_upd` = `UPDATE` (vedi sotto quando usare `OF colonna`)
* `_dlt` = `DELETE`
* Combinali se serve: `_ins_upd`, `_upd_dlt`, `_ins_upd_dlt`.

### Pattern completo consigliato

```
trg_<schema_opzionale>_<tabella>_<fase>_<descrizione_breve>_<eventi>
```

* **fase**: `a10` o `z90` (`a05` solo per un rifiuto che deve precedere gli altri guard, vedi sopra)
* **descrizione_breve**: snake_case, verbo + oggetto, es. `only_allowed_tipi`
* **eventi**: `_ins`, `_upd`, `_dlt`, o combinati

---

## Scelta tra `UPDATE` vs `UPDATE OF colonna`

### Cosa fa davvero `UPDATE OF`

`UPDATE OF colonna` **non** vuol dire «quando la colonna cambia». Vuol dire
«quando la colonna è **scritta nel `SET`** dell'istruzione». Da qui due
conseguenze, ed entrambe mordono:

| Caso | `UPDATE OF colonna` |
| --- | --- |
| `SET colonna = <stesso valore>` | **scatta**, anche se non cambia niente |
| la colonna la cambia **un altro trigger `BEFORE`** (un ricalcolo, una normalizzazione, un default) | **non scatta**, anche se il valore è cambiato |
| la colonna la cambia una FK `ON UPDATE CASCADE` | scatta (la cascata scrive un `UPDATE … SET`) |

⛔ **Il secondo caso è quello pericoloso.** Un guard o una propagazione
agganciati con `UPDATE OF` su una colonna **derivata** — scritta da un altro
trigger `BEFORE` della stessa tabella — si aggirano cambiando la colonna da cui
deriva. Caso reale, chiuso il 2026-10-04: sulle righe dei documenti `quantita`
la calcola `trgfn_qta_from_operativa` da `qta_operativa`, e la propagazione ai
componenti del kit era `AFTER UPDATE OF quantita`. Un `UPDATE` del solo
`qta_operativa` (quello che fa il backend sui preventivi) cambiava la quantità
del padre e lasciava i componenti con quella vecchia.

### La regola

* **Se il trigger reagisce a un CAMBIO di valore**, si scrive `UPDATE` senza `OF`
  e il confronto si mette nel `WHEN`:
  `WHEN (OLD.colonna IS DISTINCT FROM NEW.colonna)`.
  Il `WHEN` vede la riga **dopo** i trigger `BEFORE` che vengono prima in ordine
  alfabetico; in un trigger `AFTER` vede la riga **finale**. È la forma da usare
  per le propagazioni e per i guard su colonne che altri trigger possono
  scrivere.
* **`UPDATE OF` resta giusto** quando la domanda è proprio «qualcuno ha
  **chiesto** di scrivere questa colonna?», e la colonna non ha scrittori
  automatici sulla stessa tabella. Esempi: il lock di colonna
  (`trgfn_lock_columns`), un guard su una colonna che solo l'operatore compila.
  Il guard confronta comunque `OLD` e `NEW` nel corpo, perché `UPDATE OF` scatta
  anche a valore uguale.
* Prima di agganciare un trigger con `UPDATE OF colonna`, si guarda se un altro
  trigger `BEFORE` della tabella scrive `NEW.colonna`. Se sì, `OF` è la forma
  sbagliata.
* Se la logica dipende dal **record intero** (storico, audit), si usa `UPDATE`
  senza `OF` e senza `WHEN`.

---

## Best practice riassunte

* **`_a10`**: prima linea di difesa (check & block).
* **`_z90`**: azioni finali “a valle” (es. storico).
* **`WHEN (OLD.x IS DISTINCT FROM NEW.x)`** per reagire a un cambio di valore; **`OF colonna`** solo per «la colonna è stata chiesta nel `SET`» (vedi sopra).
* Nomi **brevi e descrittivi**.
* Usare la funzione progetto per errori: `script.fn_log_and_raise_error(...)`.

---

## Checklist rapida (da usare nei PR)

* [ ] Nome con prefisso `trg_`, `_schema(opzionale)_tabella_` e fase corretta (`_a10_` / `_z90_`).
* [ ] Eventi coerenti (`_ins/_upd/_dlt`). Con `UPDATE OF colonna`, verificato che nessun altro trigger `BEFORE` della tabella scriva quella colonna; per reagire a un cambio di valore si usa `WHEN (OLD.x IS DISTINCT FROM NEW.x)`.
* [ ] In `_a10_` usata `script.fn_log_and_raise_error(...)`.
* [ ] Ordine lessicografico rispettato (niente prefissi “casuali”).
* [ ] Commenti/descrizioni chiari in SQL o Liquibase.



**Documento rettificato il 18/11/2025**
