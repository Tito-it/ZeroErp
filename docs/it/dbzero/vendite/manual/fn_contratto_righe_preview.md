# fn_contratto_righe_preview

### Scopo

Preview completa delle righe per il drawer `ContrattoRigheDrawer`: ritorna tutti gli articoli visibili nel contesto del contratto — articoli dal listino con overlay eccezioni, e articoli AGGIUNTA fuori-listino. Sostituisce lo SQL inline di `contratti_repository.list_righe_preview`. Il BE diventa thin wrapper.


> ⭐ **Dal 2026-10-04 è un ingresso di una riga** (`20261004-72`): il corpo vive in
> [vendite.fn_documento_righe_preview](/dbzero/vendite/funzioni/fn_documento_righe_preview),
> comune con l'offerta ([vendite.fn_offerta_righe_preview](/dbzero/vendite/funzioni/fn_offerta_righe_preview)).
> Firma e colonne invariate. Le regole qui sotto valgono per i due documenti;
> la versione del listino la dice [vendite.fn_documento_listino_operativo](/dbzero/vendite/funzioni/fn_documento_listino_operativo)
> e «Escludi» lo spegne [script.fn_check_esclusione_articolo_documento](/dbzero/script/funzioni/fn_check_esclusione_articolo_documento).
> Brief: brief-db-righe-esclusione-solo-non-si-vende (R4).

**Nota architetturale (DB-ORD, 2026-06-04)**: la Parte 1 (espansione listino standalone + bundle, variazione globale, aggregazione BoM) è stata estratta nel core condiviso [vendite.fn_espandi_listino_versione](/dbzero/vendite/manual/fn_espandi_listino_versione), riusato anche da [vendite.fn_offerta_righe_espanse](/dbzero/vendite/manual/fn_offerta_righe_espanse) (regola del 2: una sola implementazione della logica listino+BoM). L'output di questa funzione **non cambia** (stesse 19 colonne, stessa semantica drawer); cambia solo l'organizzazione interna: Parte 1 = core + overlay OVERRIDE/ESCLUSIONE, Parte 2 (AGGIUNTA) invariata.

> **Vedi anche**
>
> - [vendite.contratti](/dbzero/vendite/tabelle/contratti) — testata contratto, `listino_versione_id`
> - [vendite.listini_righe_componenti](/dbzero/vendite/tabelle/listini_righe_componenti) — bundle dal listino
> - [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti) — figli AGGIUNTA bundle
> - [vendite.fn_contratto_riga_componenti_preview](/dbzero/vendite/manual/fn_contratto_riga_componenti_preview) — preview singolo bundle per form atomic (scopo diverso, non sostituisce questa fn)
> - [vendite.fn_contratto_riga_componenti_init](/dbzero/vendite/manual/fn_contratto_riga_componenti_init) — inizializzazione figli bundle all'INSERT AGGIUNTA

## Schema

`vendite`

## Firma

```sql
vendite.fn_contratto_righe_preview(
    p_contratto_id   vendite.contratti.id%TYPE
)
RETURNS TABLE (
    articolo_id           catalogo.articoli.id%TYPE,
    articolo_codice       catalogo.articoli.codice%TYPE,
    articolo_descrizione  catalogo.articoli.descrizione%TYPE,
    is_composito          catalogo.articoli.is_composito%TYPE,
    uom_id                vendite.listini_righe.uom_id%TYPE,
    uom_codice            catalogo.unita_misura.codice%TYPE,
    prezzo_listino        vendite.listini_righe.prezzo%TYPE,
    tipo_variazione       vendite.contratti.tipo_variazione_globale%TYPE,
    valore_variazione     vendite.contratti.valore_variazione_globale%TYPE,
    override_riga_id      vendite.contratti_righe.id%TYPE,
    override_prezzo       vendite.contratti_righe.prezzo_unitario%TYPE,
    tipo_eccezione        vendite.contratti_righe.tipo_eccezione%TYPE,
    origine               varchar,
    prezzo_finale         vendite.listini_righe.prezzo%TYPE,
    componenti            jsonb,
    quantita              vendite.contratti_righe.quantita%TYPE,
    qta_operativa         vendite.contratti_righe.qta_operativa%TYPE,
    tipo_erogazione       vendite.contratti_righe.tipo_erogazione%TYPE,
    fonte_quantita_attesa vendite.contratti_righe.fonte_quantita_attesa%TYPE,
    riga_key              text,
    azioni                text[],
    escludi_blocco_codice text,
    ordine                vendite.contratti_righe.ordine%TYPE,
    uom_operativa_id      vendite.contratti_righe.uom_operativa_id%TYPE
)
LANGUAGE plpgsql STABLE SECURITY INVOKER
```

## Logica — 4 parti

La funzione emette righe da 4 blocchi `RETURN QUERY` concatenati. L'ordine corrisponde alla priorità visiva nel drawer.

### Determinazione versione listino

Prima di emettere righe, risolve la versione operativa:

- **Contratto ATTIVO** (`c.listino_versione_id IS NOT NULL`): usa direttamente lo snapshot fissato all'attivazione.
- **Contratto DRAFT** (`c.listino_versione_id IS NULL`): lookup su `listini_versioni` con `stato IN ('ATTIVA','CHIUSA') AND validita @> CURRENT_DATE ORDER BY (stato='ATTIVA') DESC`. BOZZA esclusa (regola stati operativi — fix Bug A 2026-05-16, vedi [listini_versioni](/dbzero/vendite/manual/listini_versioni)).
- Se `listino_id IS NULL` (contratto senza listino): salta le Parti 1a/1b, ritorna solo Parte 2.

### Parte 1a — Standalone dal listino (`is_composito = FALSE`)

JOIN `listini_righe → articoli → unita_misura` + LEFT JOIN `contratti_righe` (solo OVERRIDE/ESCLUSIONE).

| Condizione eccezione | `origine` | `prezzo_finale` |
|---|---|---|
| Nessuna riga in `contratti_righe` | `DA_LISTINO` | `prezzo_listino` × variazione globale |
| `tipo_eccezione = OVERRIDE` | `OVERRIDE` | `override_prezzo` |
| `tipo_eccezione = ESCLUSIONE` | `ESCLUSIONE` | NULL |

`componenti = NULL`.

### Parte 1b — Bundle dal listino (`is_composito = TRUE`)

Cerca padri compositi distinti in `listini_righe_componenti` per la versione. Il padre compare come riga virtuale (non è in `listini_righe`, che contiene solo non-compositi).

| Condizione eccezione | `origine` | `prezzo_finale` |
|---|---|---|
| Nessuna riga in `contratti_righe` | `DA_LISTINO` | `SUM(lrc.prezzo × ac.coeff_qta)` aggregato in DB |
| `tipo_eccezione = OVERRIDE` | `OVERRIDE` | `override_prezzo` |
| `tipo_eccezione = ESCLUSIONE` | `ESCLUSIONE` | NULL |

`componenti = jsonb_agg` dei figli da `listini_righe_componenti` (anche in caso di OVERRIDE sul padre — la composizione resta quella del listino).

### Parte 2a — AGGIUNTA standalone

Righe `contratti_righe` con `tipo_eccezione = AGGIUNTA` e `articoli.is_composito = FALSE`.

`prezzo_finale = override_prezzo`, `origine = 'AGGIUNTA'`, `componenti = NULL`.

### Parte 2b — AGGIUNTA bundle composito

Righe `contratti_righe` con `tipo_eccezione = AGGIUNTA` e `articoli.is_composito = TRUE`.

`prezzo_finale = override_prezzo` (aggiornato da `trgfn_componenti_ricalcola_padre` dopo ogni modifica ai figli).  
`componenti = jsonb_agg` dei figli da `contratti_righe_componenti`.

## Shape JSONB `componenti`

Uniforme tra Parte 1b (sorgente listino) e Parte 2b (sorgente contratto_righe_componenti):

```json
{
  "articolo_componente_id": "uuid",
  "componente_id":          "uuid",
  "componente_codice":      "varchar",
  "componente_descrizione": "varchar",
  "uom_id":                 "bigint",
  "uom_codice":             "varchar",
  "coeff_qta":              "numeric",
  "prezzo":                 "numeric",
  "obbligatorio":           "boolean",
  "esposizione_in_fattura": "varchar"
}
```

`esposizione_in_fattura`: il codice interno del modo in cui il componente si vede in fattura sotto il suo kit (`NASCOSTO` | `DESCRITTIVO` | `VALORIZZATO`), letto da `catalogo.articoli_componenti`. Fino al 2026-10-01 la chiave era `esposto_in_fattura` (boolean: `false` → `NASCOSTO`, `true` → `DESCRITTIVO`), rev `20261001-53`.

`coeff_qta`: in Parte 1b viene da `catalogo.articoli_componenti.coeff_qta`; in Parte 2b da `contratti_righe_componenti.coeff_qta_snapshot`.  
`prezzo`: in Parte 1b è `listini_righe_componenti.prezzo`; in Parte 2b è `contratti_righe_componenti.prezzo_unitario`.  
`uom_id` / `uom_codice`: in Parte 1b l'UoM base del componente; in Parte 2b `contratti_righe_componenti.uom_operativa_id`, l'UoM in cui è quotato il suo prezzo (dal 2026-10-04, `20261004-01`).

## Output — colonne principali

| Colonna | Semantica |
|---|---|
| `articolo_id` / `articolo_codice` / `articolo_descrizione` | Articolo padre |
| `is_composito` | `TRUE` = bundle (ha `componenti`), `FALSE` = standalone |
| `uom_id` / `uom_codice` | UoM: da `listini_righe.uom_id` per 1a, da `articoli.uom_id` per 1b; per 2a/2b l'UoM **della riga** (`contratti_righe.uom_operativa_id`), e se è NULL la base dell'articolo |
| `prezzo_listino` | Prezzo raw dal listino (NULL per bundle e AGGIUNTA) |
| `tipo_variazione` / `valore_variazione` | Variazione globale del contratto (NULL per Parte 2) |
| `override_riga_id` / `override_prezzo` | `contratti_righe.id` e `prezzo_unitario` se eccezione presente |
| `tipo_eccezione` | `OVERRIDE` / `ESCLUSIONE` / `AGGIUNTA` o NULL |
| `origine` | `DA_LISTINO` / `OVERRIDE` / `ESCLUSIONE` / `AGGIUNTA` |
| `prezzo_finale` | Prezzo effettivo da mostrare in UI (aggregato in DB, non delegato al FE) |
| `componenti` | JSONB array figli (bundle); NULL per standalone |
| `quantita` | Snapshot quantita della riga persistita; valorizzata solo per righe con eccezione (OVERRIDE/ESCLUSIONE/AGGIUNTA), NULL per DA_LISTINO puro |
| `qta_operativa` | Quantita in UoM operativa; valorizzata solo per righe con eccezione, NULL per DA_LISTINO puro |
| `tipo_erogazione` | `CANONE` / `UNA_TANTUM` / `ORARIO` / `CONSUMO`; valorizzato solo per righe con eccezione, NULL per DA_LISTINO puro |
| `fonte_quantita_attesa` | `FISSA` / `MANUALE` / `TIMESHEET` / `LETTURE` (`DERIVATA_COMPONENTI` ritirata il 2026-10-21); valorizzata solo per righe con eccezione, NULL per DA_LISTINO puro |
| `riga_key` / `azioni` / `escludi_blocco_codice` | Chiave di riga, verbi ammessi e motivo per cui «Escludi» è spento: vedi rev 2026-09-28 |
| `ordine` | `contratti_righe.ordine` della riga persistita; NULL per DA_LISTINO puro |
| `uom_operativa_id` | `contratti_righe.uom_operativa_id` così com'è scritto (NULL per DA_LISTINO puro, e per una riga senza quantità); è il dato che il form di modifica rimanda al `PATCH` |

## Note operative

- **Colonne qta/tipo/fonte NULL per DA_LISTINO**: nelle parti 1a/1b, `quantita`, `qta_operativa`, `tipo_erogazione` e `fonte_quantita_attesa` vengono da `cr.*` via LEFT JOIN. Quando non c'è eccezione (DA_LISTINO puro) il JOIN non trova righe e i campi sono NULL. Per OVERRIDE/ESCLUSIONE il JOIN trova la riga eccezione e i campi sono valorizzati. Per AGGIUNTA (parti 2a/2b) il JOIN è diretto e i campi sono sempre valorizzati. Il consumer FE deve gestire NULL come "usa il default listino".
- **`STABLE`**: nessun side effect, ottimizzabile dal planner per chiamate multiple nella stessa transazione.
- **Duplicazioni**: mutualmente esclusivi per costruzione. 1a usa `is_composito=FALSE` da listino, 1b usa padri compositi da `listini_righe_componenti`, 2a/2b filtrano su `tipo_eccezione=AGGIUNTA` con rispettivo `is_composito`. Non ci sono doppioni tra le parti.
- **AGGIUNTA su articolo già in listino**, e OVERRIDE o ESCLUSIONE fuori listino: li previene in fase di INSERT la check di riga `script.fn_check_articolo_riga` (guard `script.trgfn_righe_guard_articolo_ammesso`, dal 2026-10-13). La fn non duplica questo check.
- **Contratto inesistente**: se `p_contratto_id` non corrisponde a nessun contratto, la fn ritorna zero righe (non raise).


---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

**Diventa la sorgente della lista `vendite.contratto_righe`** per le due forme del contratto (`20260928-32`, D-8.4). Tre colonne in coda: `riga_key` (`L:<articolo>:<uom>` per le righe del listino, `A:<id>` per le aggiunte: la chiave che il frontend inventava), `azioni` (i verbi che l'origine ammette: dal listino sovrascrivi prezzo / escludi; prezzo forzato modifica / ripristina il listino; esclusione modifica / ripristina l'articolo; aggiunta modifica / rimuovi) ed `escludi_blocco_codice` (il motivo per cui «Escludi» è spento, da `script.fn_check_esclusione_articolo_contratto` — dal 2026-10-04 [script.fn_check_esclusione_articolo_documento](/dbzero/script/funzioni/fn_check_esclusione_articolo_documento), comune con l'offerta —, lo stesso predicato del guard). Il blocco «fuori bozza» resta di documento. La versione del listino in vigore per il contratto in bozza non è più scelta qui: la dice [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore) (`20260928-39`). Per ogni data la versione in vigore è **al più una**, per costruzione (nessuna sovrapposizione fra versioni ATTIVE e CHIUSE, date di una CHIUSA bloccate), quindi «la prima» e «tutte le valide» sono la stessa cosa. Stesso esito, provato sui dati di dev.

<!-- rev-2026-10-04-uom-della-riga -->
### 🔄 rev 2026-10-04 — l'UoM della riga, e ordine (brief-db-liste-righe-documento §9.11)

**Le AGGIUNTA escono nell'UoM in cui la riga è quotata** (`20261004-01`). Prima uscivano nell'UoM base dell'articolo: quantità e prezzo comparivano accanto a un'UoM che non era la loro, a video, nell'export e in stampa. Inoltre il form di modifica, che non trovava l'UoM della riga, al primo salvataggio la riscriveva con quella dell'articolo. Una riga senza UoM operativa (succede solo quando non ha una quantità, cioè con fonte diversa da `FISSA`) ricade sulla base dell'articolo, come fa già [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) quando la riga viene scritta. Vale anche per i componenti di un bundle AGGIUNTA: ognuno esce nella sua UoM operativa.

**Due colonne in coda**: `ordine` e `uom_operativa_id` della riga di `contratti_righe`, vuote sulle righe che vengono solo dal listino. Servono al form di modifica, che le rimanda al `PATCH`: senza, ogni modifica azzerava l'ordine della riga e l'UoM di un'eccezione andava indovinata. In tutto 24 colonne.

<!-- rev-2026-10-04-esclusione-senza-modifica -->
### 🔄 rev 2026-10-04 — un'esclusione non si modifica (brief-db-contratto-esclusione-non-modificabile)

**La riga ESCLUSIONE ha un solo verbo: ripristina l'articolo** (`20261004-14`). Prima aveva anche «modifica», e il drawer, che rende i verbi del database, apriva il form di modifica su un articolo che il contratto non vende: il form ripiegava su erogazione a canone e fonte fissa, e al primo salvataggio scriveva sull'esclusione valori che nessuno aveva scelto. Un'esclusione si crea (Escludi) e si cancella (Ripristina articolo), e basta. Il database rifiuta anche la modifica diretta: lo fa il guard [vendite.trgfn_contratti_righe_guard_esclusione_immutabile](/dbzero/script/funzioni/trgfn_righe_guard_esclusione_immutabile). Le altre origini non cambiano.

| Origine | Verbi |
| --- | --- |
| `DA_LISTINO` | `SOVRASCRIVI_PREZZO`, `ESCLUDI` |
| `OVERRIDE` | `MODIFICA`, `RIPRISTINA_LISTINO` |
| `ESCLUSIONE` | `RIPRISTINA_ARTICOLO` |
| `AGGIUNTA` | `MODIFICA`, `RIMUOVI` |

