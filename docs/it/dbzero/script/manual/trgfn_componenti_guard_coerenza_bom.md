## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_componenti_guard_coerenza_bom()`

> 👀 **Vedi anche**
>
> [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM validata
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — check `is_composito` sul padre
> [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — prima tabella che la usa
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione BoM CASO A

Trigger function **BEFORE INSERT OR UPDATE** generica del modello BoM unificato. Esegue **4 guard di coerenza** per garantire che ogni riga inserita nelle tabelle `*_righe_componenti` sia associata a un componente legittimo e valido della BoM dell'articolo padre.

---

### 🎯 Scopo Principale

Garantisce l'integrità del modello BoM unificato a livello di trigger DB, indipendentemente dal layer BE che chiama l'INSERT. I 4 check bloccano stati inconsistenti che potrebbero nascere da refactoring BE, chiamate API dirette o seed dati. Il guard su `esposto_in_fattura` (guard 4 originale) è stato rimosso con il modello unificato: tutti i componenti attivi generano righe, indipendentemente dal flag di presentazione fattura.

---

### TG_ARGV layout

```
TG_ARGV[0]  schema padre        (es. 'vendite')
TG_ARGV[1]  tabella padre       (es. 'preventivi_righe')
TG_ARGV[2]  col FK figli->padre (es. 'riga_preventivo_id')
TG_ARGV[3]  tabella testata     (es. 'preventivi')
TG_ARGV[4]  col FK padre->testata (es. 'preventivo_id')
TG_ARGV[5]  col data su testata (es. 'data')
```

La funzione accede direttamente a `NEW.articolo_componente_id` e `NEW.componente_id` (nomi di colonna fissi per convenzione su tutte e 5 le tabelle `*_righe_componenti`).

---

### I 4 guard

| # | Check | Errore sollevato |
|---|---|---|
| **1** | Articolo della riga padre ha `is_composito = TRUE` | `E_DOC_RIGA_NON_COMPOSITO` (434) |
| **2** | `articolo_componente_id` appartiene alla BoM del padre (`prodotto_id = padre.articolo_id`) | `E_DOC_COMPONENTE_NON_BOM` (435) |
| **3** | `componente_id` coincide con `articoli_componenti.componente_id` per la riga BoM indicata | `E_DOC_COMPONENTE_ID_INCOERENTE` (438) |
| **4** | BoM valida alla data del documento (`validita @> data_rif`) | `E_DOC_COMPONENTE_BOM_NON_VALIDA` (437) |

I guard 2-4 vengono valutati in un'unica SELECT su `articoli_componenti`, dopo il guard 1. Il guard 3 (coerenza `componente_id`) è difensivo: evita che un INSERT possa specificare un `componente_id` diverso dall'articolo reale della BoM entry indicata. Il guard originale su `esposto_in_fattura = TRUE` (ex guard 4, codice `E_DOC_COMPONENTE_NON_ESPOSTO` 436) è stato rimosso con il modello unificato — vedi migration `20260513-08`.

---

### Ottimizzazione query

L'implementazione fonde in un'unica query dinamica i dati della riga padre e `is_composito` dell'articolo (via JOIN padre → `catalogo.articoli` → testata), riducendo da 3 a 2 round-trip rispetto a query separate.

---

### Applicazione

Primo trigger registrato su tutte le tabelle `*_righe_componenti` — 5 tabelle totali:

- `vendite.preventivi_righe_componenti`
- `vendite.ordini_righe_componenti`
- `vendite.ddt_righe_componenti`
- `vendite.contratti_righe_componenti`
- `vendite.listini_righe_componenti`

Parametri trigger:

- Timing: **BEFORE INSERT OR UPDATE**
- Fase: **`_a10_`** (guard/block)
- Scope: **FOR EACH ROW**
- **No `UPDATE OF`**: il guard deve intercettare qualsiasi UPDATE per validare le colonne BoM in caso di modifica.

---

### Quando NON scatta

- **DELETE**: scope BEFORE INSERT OR UPDATE.
- **Guard 4 skip**: se `v_data_rif IS NULL` (la testata non ha colonna data valorizzata), il controllo validità BoM viene saltato per tolleranza — gli altri 3 guard rimangono attivi.

---

### Note implementative

- SQL dinamico usato per leggere schema/tabelle parametrizzati; identificatori sempre quotati via `%I`.
- `NEW.articolo_componente_id` e `NEW.componente_id` sono acceduti direttamente (non dinamicamente): tutte e 5 le tabelle `*_righe_componenti` devono avere questi nomi esatti per convenzione.
- Prefisso `script.*` per riuso cross-dominio: stessa funzione usata da 5 tabelle sorgente differenti senza duplicazione logica.
- **Rev 2026-05-13**: rimosso guard `esposto_in_fattura` (modello unificato — tutti i componenti attivi generano righe nelle tabelle sorgente). Vedi migration `20260513-08`.
