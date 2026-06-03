## 📘 Documentazione Concettuale – Vista `vendite.vw_offerte_commerciali_lista`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [vendite.listini](/dbzero/vendite/tabelle/listini)
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> [config.valute](/dbzero/config/tabelle/valute)
>
> Trigger / guida correlati:
> [vendite.trgfn_offerte_commerciali_revisione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_revisione)
> [Configurazione, personalizzazione e responsività delle liste](/guide/configurazione-liste)

---

### 🎯 Scopo Principale

(rev 2026-06-03 — rev1)

`vendite.vw_offerte_commerciali_lista` è la vista **canonica e self-contained**
che alimenta la **lista offerte commerciali configurabile**
(`ui.lista_definizione` codice `vendite.offerte`, sistema liste DEF-8). È pura
**denormalizzazione**: nessuno scope/filtro/paginazione (restano nel repository
backend consumer). Gemella di `vw_contratti_lista` e `vw_preventivi_lista`.

#### Differenza chiave vs `vw_offerte_commerciali_list` (deprecata)

Due salti rispetto alla vista list precedente:

1. **Nomi canonici** (lezione DEF-8, ogni `campo_sorgente` del catalogo combacia
   con una colonna della vista — trigger B2):

   | `vw_offerte_commerciali_list` | `vw_offerte_commerciali_lista` |
   | --- | --- |
   | `cliente_denominazione` | **`ragione_sociale_completa`** |
   | `id_fiscale` | **`id_fiscale_univoco_cf_piva`** |
   | `billing_account_codice` | **`ba_codice`** |

2. **Self-contained**: assorbe campi che prima erano derivati a valle nel
   repository (LEFT JOIN), eliminando quei JOIN dal backend:
   * **`listino_codice`** (JOIN `vendite.listini`)
   * **`listino_versione_codice`** (JOIN `vendite.listini_versioni.codice_versione`)
   * **`valuta_codice`** (JOIN `config.valute` via `o.valuta_id`)
   * **`emittente_fiscale_codice`** (JOIN `anagrafiche.emittenti_fiscali`)
   * **`is_scaduta`** — booleano materializzato (vedi sotto)

In più è `WITH (security_invoker = on)` (RLS-ready).

> La vista precedente `vw_offerte_commerciali_list` è stata **rimossa** (DROP
> changeset `20260603-10`) dopo la commutazione del backend (`list_offerte`)
> sulla vista canonica.

---

### Colonna materializzata — `is_scaduta`

```sql
(o.validita_al IS NOT NULL AND o.validita_al < CURRENT_DATE) AS is_scaduta
```

`TRUE` quando la finestra di validità dell'offerta è già scaduta. **Prima
viveva solo lato frontend** (nessuna colonna backend); spostandola in vista
diventa un dato di dominio unico e testabile.

> **Gating per stato lato FE**: il badge «scaduta» nell'interfaccia non si basa
> sul solo `is_scaduta`, ma sull'AND con l'appartenenza dello stato all'insieme
> `STATI_OFFERTA_SEGNALA_SCADENZA` (es. non si segnala una scadenza su un'offerta
> già ACCETTATA o ANNULLATA). La vista espone il dato grezzo `is_scaduta`; il
> filtro per stato resta una scelta di presentazione del frontend.

---

### Colonne derivate — `is_attiva` e `has_next_revisione` (invariate)

```sql
sdo.codice_interno NOT IN ('SUPERATA', 'ANNULLATA')                       AS is_attiva
EXISTS (SELECT 1 FROM vendite.offerte_commerciali f
         WHERE f.revisione_padre_id = o.id)                               AS has_next_revisione
```

* **`is_attiva`** — `TRUE` se l'offerta non è superata da una revisione
  successiva né annullata (semantica garantita dal trigger
  `trgfn_offerte_commerciali_revisione`, `_z90_ AFTER INSERT`). Costo O(1).
  > *Edge case noto*: se l'ultima revisione di un lineage viene annullata senza
  > successore, il padre resta SUPERATA e nessuna offerta del lineage risulta
  > `is_attiva` — limite del modello trigger attuale, fuori scope.
* **`has_next_revisione`** — `TRUE` se esiste almeno un figlio (qualunque stato):
  alimenta il toggle UI «mostra storico revisioni». Efficiente grazie all'indice
  parziale `ix_offerte_commerciali_revisione_padre`.

---

### JOIN principali

| Tabella | Dati esposti | Note |
| --- | --- | --- |
| `config.stati_doc_offerte` | `stato_codice_interno`, `stato_descrizione` | INNER JOIN |
| `anagrafiche.istanze_utilities` → `anagrafiche.soggetti` | `soggetto_id`, `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva` | LEFT (sempre match: `istanza_utility_id` NOT NULL) |
| `anagrafiche.billing_account` | `ba_codice` | LEFT (sempre match: `billing_account_id` NOT NULL su offerte) |
| `anagrafiche.emittenti_fiscali` | `emittente_fiscale_codice` | LEFT |
| `config.utilities` | `utility_codice`, `utility_descrizione` | LEFT |
| `vendite.listini` | `listino_codice` | LEFT (NULL = senza listino) |
| `vendite.listini_versioni` | `listino_versione_codice` | LEFT |
| `config.valute` | `valuta_codice` | LEFT |

---

### 📑 Campi chiave esposti

* **Identificatori**: `id`, `uid`, `codice`, `revisione_numero`, `revisione_padre_id`
* **Flag revisione**: **`is_attiva`**, **`has_next_revisione`**
* **Stato**: `stato_doc_offerta_id`, **`stato_codice_interno`** (severity Tag FE), `stato_descrizione`
* **Scadenza**: **`is_scaduta`** (badge FE, gating per stato lato frontend)
* **Cliente (via istanza)**: `billing_account_id`, **`ba_codice`**, `soggetto_id`, **`ragione_sociale_completa`**, **`id_fiscale_univoco_cf_piva`**
* **Permessi / emittente**: `emittente_fiscale_id` (scope), **`emittente_fiscale_codice`**
* **Utility e istanza**: `utility_id`, **`utility_codice`**, `utility_descrizione`, `istanza_utility_id`, `istanza_utility_codice`
* **Listino**: `listino_id`, **`listino_codice`**, `listino_versione_id`, **`listino_versione_codice`**
* **Variazione globale**: `tipo_variazione_globale`, `valore_variazione_globale`
* **Valuta**: `valuta_id`, `valuta_codice`
* **Validità / ciclo vita**: **`validita_dal`**, `validita_al`, **`data_emissione`**, `data_accettazione`, `data_rifiuto`, `data_annullamento`
* **Audit**: `data_insert`, `user_insert`

---

### Mappatura catalogo lista (`vendite.offerte`, lista_id=6)

Le 12 colonne visibili di default nel preset `offerte_default` riproducono 1:1
la lista attuale (codice, rev, cliente, cd. account, id. fiscale, utility,
listino, valido dal, valido al, emessa, stato, azioni). Le colonne tecniche
nascoste nel preset (`visibile=false`) servono ai render compositi FE:
`stato_codice_interno` (Tag severity), `is_scaduta` (badge «scaduta»),
`listino_versione_codice` (suffisso `· v{versione}` sulla cella Listino). Il resto
(`utility_descrizione`, `istanza_utility_codice`, variazioni, `valuta`,
`emittente_fiscale_codice`, date ciclo vita, `data_insert`) sono **extra opt-in**.

L'attributo **`priorita`** governa il ritiro dinamico: resistono `cliente` (95),
`stato` (90), `codice`/`rev`; si ritirano per prime `istanza` (35) e `ba_codice`
(40); `codice` e `azioni` non si ritirano mai.

---

### Esempio d'uso

```sql
-- Lista offerte attive per un emittente, con listino e flag scadenza
SELECT id, codice, revisione_numero,
       is_attiva, is_scaduta,
       stato_codice_interno, ragione_sociale_completa, id_fiscale_univoco_cf_piva,
       ba_codice, utility_codice,
       listino_codice, listino_versione_codice,
       validita_dal, validita_al, data_emissione
  FROM vendite.vw_offerte_commerciali_lista
 WHERE emittente_fiscale_id = 1
   AND is_attiva = TRUE
 ORDER BY validita_dal DESC, id;
```

```sql
-- Offerte scadute ma ancora in uno stato che segnala scadenza (gating in app)
SELECT id, codice, stato_codice_interno, validita_al
  FROM vendite.vw_offerte_commerciali_lista
 WHERE is_scaduta = TRUE
 ORDER BY validita_al;
```

---

### Note operative

* **`is_scaduta` è grezzo**: rappresenta solo l'avvenuto superamento di
  `validita_al`. La decisione se mostrarlo all'utente (badge) appartiene al
  frontend, che lo combina con lo stato.
* **Listino opzionale**: `listino_codice`/`listino_versione_codice` sono NULL per
  offerte senza listino — la cella FE mostra il solo codice o nulla.
* **`security_invoker=on`**: vista pronta per un'eventuale RLS sulla tabella base.
* **Performance**: tutti i lookup su PK/indici, `EXISTS` su indice parziale per
  `has_next_revisione`, zero scansioni full.

---

{% include-markdown "signature-core.md" %}
