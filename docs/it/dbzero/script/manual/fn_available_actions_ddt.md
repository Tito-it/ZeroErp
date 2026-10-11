## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_ddt`

> 👀 **Vedi anche**
>
> Tabelle:
> [config.transizioni_stati_ddt](/dbzero/config/tabelle/transizioni_stati_ddt)
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
>
> Funzioni:
> [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine) (mirror)
> [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione)
> [vendite.fn_ddt_push_diagnosi](/dbzero/vendite/funzioni/fn_ddt_push_diagnosi) — la fonte unica del push: letta **una** volta
> [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) — deriva dalla diagnosi: il push legge ciò che qui si dichiara

---

### 🎯 Scopo Principale

(rev 2026-07-09)

**`script.fn_available_actions_ddt(p_ddt_id) → jsonb`**: capabilities del DDT per il detail API
(drawer). Mirror di `fn_available_actions_ordine`, `STABLE`. È il **lato lettura** simmetrico al
guard `vendite.trgfn_ddt_guard_transizione` (stessa matrice `config.transizioni_stati_ddt`).

### Output (jsonb)

| Chiave | Contenuto |
|---|---|
| `available_actions` | transizioni manuali disponibili per lo stato corrente (da `meta.ui`: `key`/`label_key`/`requires_confirm`/`outlined`) → il FE non hardcoda i pulsanti; icona e colore li sceglie dal `key` |
| `can_change_state` | esiste almeno una transizione disponibile |
| `can_edit_testata` / `can_edit_righe` | `true` solo in `DRAFT` |
| `can_push_commessa` (+ `_reason`/`_reason_key`) | **una** lettura di `fn_ddt_push_diagnosi(p_ddt_id)`, aggregata: il flag è «esiste una riga con `motivo NULL`» — vero per **costruzione**, perché il lister che alimenta il push è quella stessa query; se `false`, prima la precedenza sul `segment` (`ALLOCATA` → `DDT_GIA_INVIATO`, `EMESSA` → `DDT_GIA_FATTURATO`), poi il motivo a rank minimo mappato per stringa (rami propri: `DDT_FATTURA_DA_ORDINE`, `DDT_SOLO_TRASPORTO`, `DDT_MERCE_IN_VIAGGIO`; il resto in `DDT_NON_PUSHABILE`). Nessuna logica di eleggibilità qui, e nessuna seconda lettura |
| `non_editable_fields` | campi bloccati (in DRAFT: sorgente/billing/numero; fuori DRAFT: tutta la testata) |
| `stato_codice` | `codice_interno` dello stato corrente |

Fallback sicuro: `NULL` se il DDT non esiste (o non è visibile a chi legge: la
funzione è `INVOKER` e la RLS resta di chi chiede).

### Il push, in una lettura

Fino al 2026-09-21 il blocco del push costava **quattro** letture — `EXISTS`
sul lister, due `EXISTS` su `fn_get_stato_push_segment` riga per riga, la
diagnosi per il motivo — e due di esse calcolavano la partita del documento.
Con la forma B2 (decisione D4 di `brief-db-partita-merce-per-documento`) la
diagnosi è la **fonte unica** e il lister ne deriva: una `SELECT` aggregata dà
flag, precedenza sul segmento e motivo. La precedenza è quella di sempre — un
DDT annullato con una riga instradata dice «già inviato», non il generico —
letta dalla colonna `segment` che la diagnosi ora espone.

⚠️ Perimetro dichiarato: la diagnosi guarda le righe **attive**; i due `EXISTS`
di prima scandivano `ddt_righe` senza guardare `attivo`. La differenza si
raggiunge solo disattivando una riga già instradata su un DDT emesso — stato
che oggi il modello ammette (decisione D7 del brief).

Presidio: `db/pgtap/script/test-fn-available-actions-ddt-reason-catch-all-v1.sql`
(16, casi costruiti: eleggibile a tre voci, `ALLOCATA`, `EMESSA`, precedenza
sull'annullato, le cause del catch-all, pin di forma, scope).

## Rev 2026-10-10 — la testata letta dal montaggio

`non_editable_fields` e `can_edit_testata` non sono più scritti nella funzione: li legge dal
montaggio del lock di testata
[`script.fn_doc_testata_in_stato`](/dbzero/script/funzioni/fn_doc_testata_in_stato). Restano
nella capability solo le colonne «sempre» (valide anche in bozza); dopo vengono quelle che il
lock blocca nello stato. Fuori bozza `can_edit_testata` è vero negli stati in cui una colonna
resta aperta (le note di un documento vivo, i dati di trasporto della bolla), falso a documento
chiuso. Brief `brief-db-testata-dopo-emissione`, fase 2.

## Rev 2026-10-11 — il cliente e gli indirizzi (brief-db-testata-dopo-emissione §11)

* **Il cliente (R-DB-1).** `billing_account_id` non è più fermo su ogni bolla. Lo è, anche in
  bozza, solo se un vincolo lo tiene: la bolla nasce da un ordine o da un reso, o evade già
  righe d'ordine. Il vincolo lo dice `vendite.fn_ddt_vincoli_cliente`, la stessa funzione del
  guard. La bolla senza sorgente riceve il cliente in bozza.
* **Gli indirizzi (R-DB-3).** `can_edit_indirizzi`: vero se gli indirizzi si possono scrivere
  nello stato della bolla, letto dal lock montato su `vendite.ddt_indirizzi` (in bozza sì,
  fuori no).

### ⛔ Si pianifica una volta (`plan_cache_mode`, changeSet 20261010-83)

La funzione porta `SET plan_cache_mode = force_generic_plan`: chiama con un
parametro la diagnosi del push, una funzione SQL che si incorpora in una query
grande, e in modo `auto` la plancache la ripianificava a ogni chiamata.
⚠️ È una proprietà **invisibile nel corpo**: un `CREATE OR REPLACE` che non la
ripete la perde, senza errore e con gli stessi risultati. Presidio:
`db/pgtap/script/test-plan-cache-mode-piano-generico-v1.sql`.

