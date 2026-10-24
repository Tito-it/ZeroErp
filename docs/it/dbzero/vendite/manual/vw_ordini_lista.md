## 📘 Documentazione Concettuale – Vista `vendite.vw_ordini_lista`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento)
> [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento)
> [config.valute](/dbzero/config/tabelle/valute)
>
> Guida correlata:
> [Configurazione, personalizzazione e responsività delle liste](/guide/configurazione-liste)

---

### 🎯 Scopo Principale

(rev 2026-06-03 — rev1)

`vendite.vw_ordini_lista` è la vista **canonica e self-contained** che alimenta la
**lista ordini di vendita configurabile** (`ui.lista_definizione` codice
`vendite.ordini`, lista_id=7, sistema liste DEF-8). È pura **denormalizzazione**:
nessuno scope/filtro/paginazione (restano nel repository backend consumer). Gemella
di `vw_contratti_lista`, `vw_preventivi_lista`, `vw_offerte_commerciali_lista`, ma
creata **da zero** (per gli ordini non esisteva una vista lista precedente).

È `WITH (security_invoker = on)`: la vista gira col contesto del chiamante, così le
**policy RLS** della tabella base `vendite.ordini` (tre facce: operatore/portale/shop)
si applicano e non è «RLS cosmetica».

#### Specificità ordine vs preventivi/offerte

* **Niente revisioni**: nessuna colonna `rev`/`is_attiva`/`has_next_revisione`
  (gli ordini non hanno storico revisioni). Più semplice.
* **Niente listino in testata**: l'ordine fissa i prezzi sulle righe alla conferma,
  non eredita una versione listino. Nessuna colonna `listino_*`.
* **Cliente via `soggetto_ruolo` diretto**: `o.soggetto_ruolo_id` (NOT NULL) →
  `soggetti_ruoli` → `soggetti`, senza passare da `istanza_utility` (che su ordini
  non esiste). Risolve il cliente anche per i **prospect** senza billing account.
* **Assi OdV-specifici**: espone `fatturazione_trigger` (quando scatta il push a
  commessa) e `canale_origine` (ADMIN/PORTALE/SHOP).
* **Estensioni 2026-06-03**: `agente_denominazione` (agente/venditore) e
  `documento_origine_tipo`/`documento_origine_codice` (provenienza upstream).

---

### Colonna derivata — `documento_origine_codice` (risoluzione polimorfa)

```sql
CASE o.documento_origine_tipo
    WHEN 'PREVENTIVO' THEN pv.numero
    WHEN 'OFFERTA'    THEN oc.codice
END AS documento_origine_codice
```

Il link al documento commerciale di origine è **tipizzato**: `documento_origine_tipo`
(`PREVENTIVO`/`OFFERTA`) + `documento_origine_id` (riferimento **polimorfo**, niente FK
fisica unica). La vista risolve il codice leggibile con due `LEFT JOIN` condizionati
per tipo — solo il ramo del tipo corrente matcha. Entrambe le colonne sono NULL per gli
**ordini diretti** (non nati da un upstream). Nessuna `UNIQUE` sul link: un
preventivo/offerta può generare **più ordini** (vedi tabella `vendite.ordini`).

---

### Nomi canonici (lezione DEF-8)

Ogni `campo_sorgente` del catalogo combacia con una colonna della vista (validato dal
trigger anti-typo `trg_ui_lista_colonna_a10_valida_campo_sorgente`):

| Significato | Colonna vista |
| --- | --- |
| Ragione sociale del cliente | **`ragione_sociale_completa`** |
| Identificativo fiscale (CF/P.IVA) | **`id_fiscale_univoco_cf_piva`** |
| Codice billing account (alias legittimo) | **`ba_codice`** |
| Codice interno stato (severity Tag FE) | **`stato_codice_interno`** |

`numero` è esposto **nudo** (sempre valorizzato dal trigger `trgfn_ordini_gen_numero`
all'INSERT, anche in BOZZA → nessun fallback).

---

### JOIN principali

| Tabella | Dati esposti | Note |
| --- | --- | --- |
| `config.stati_doc_ordini` | `stato_codice_interno`, `stato_descrizione` | INNER JOIN |
| `anagrafiche.soggetti_ruoli` → `anagrafiche.soggetti` | `soggetto_id`, `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva` | INNER (cliente `soggetto_ruolo_id` NOT NULL); anche prospect |
| `anagrafiche.billing_account` | `ba_codice` | LEFT (BA nullable sugli ordini) |
| `anagrafiche.emittenti_fiscali` | `emittente_fiscale_codice` | LEFT |
| `config.utilities` | `utility_codice`, `utility_descrizione` | LEFT |
| `config.modalita_pagamento` | `modalita_pagamento_codice` | LEFT |
| `config.termini_pagamento` | `termine_pagamento_codice` | LEFT |
| `config.valute` | `valuta_codice` | LEFT |
| `anagrafiche.soggetti_ruoli` → `anagrafiche.soggetti` (agente) | `agente_denominazione` | LEFT (`agente_soggetto_ruolo_id` nullable) |
| `vendite.preventivi` / `vendite.offerte_commerciali` | `documento_origine_codice` | LEFT condizionati per tipo (polimorfo) |

---

### 📑 Campi chiave esposti

* **Identificazione**: `id`, `uid`, `numero`, `serie`, `anno`, `data`
* **Stato**: `stato_doc_ordine_id`, **`stato_codice_interno`** (severity Tag FE), `stato_descrizione`
* **Cliente (via soggetto_ruolo)**: `soggetto_ruolo_id`, `soggetto_id`, **`ragione_sociale_completa`**, **`id_fiscale_univoco_cf_piva`**, `billing_account_id`, **`ba_codice`**
* **Permessi / emittente**: `emittente_fiscale_id` (scope RLS), **`emittente_fiscale_codice`**
* **Utility**: `utility_id`, **`utility_codice`**, `utility_descrizione`
* **Importi**: `imponibile_tot`, `sconto_tot`, `iva_tot`, **`totale_doc`**
* **Pagamento / valuta**: `modalita_pagamento_codice`, `termine_pagamento_codice`, `valuta_codice`, `tasso_cambio`
* **Assi OdV**: **`fatturazione_trigger`**, `canale_origine`
* **Commerciale (E)**: `agente_soggetto_ruolo_id`, **`agente_denominazione`**
* **Origine (A1)**: `documento_origine_tipo`, `documento_origine_id`, **`documento_origine_codice`**
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`

---

### Mappatura catalogo lista (`vendite.ordini`, lista_id=7)

Le **10 colonne visibili** di default nel preset `ordini_default` (`pagina_dimensione=25`,
ordinamento `data desc`): `numero`, `data`, cliente (`ragione_sociale_completa`),
`ba_codice`, `id_fiscale`, `utility_codice`, `totale_doc`, `fatturazione_trigger`,
`stato`, `azioni`. La colonna tecnica nascosta `stato_codice_interno` (`visibile=false`)
alimenta il render del Tag severity FE. Il resto (utility_descrizione, canale_origine,
imponibile/iva, modalità/termine pagamento, valuta, emittente, anno, serie,
**documento_origine**, **agente**, data_insert) sono **extra opt-in**.

L'attributo **`priorita`** governa il ritiro dinamico responsive: resistono `numero`
(100), cliente (95), `stato` (90), `totale_doc` (80); si ritirano per prime
`ba_codice` (40) e `fatturazione_trigger` (30); `numero` e `azioni` non si ritirano mai.

---

### Esempio d'uso

```sql
-- Ordini di un emittente nello scope, con cliente, totale e provenienza
SELECT id, numero, data,
       stato_codice_interno, ragione_sociale_completa, id_fiscale_univoco_cf_piva,
       ba_codice, utility_codice, totale_doc,
       fatturazione_trigger, agente_denominazione,
       documento_origine_tipo, documento_origine_codice
  FROM vendite.vw_ordini_lista
 WHERE emittente_fiscale_id = 1
 ORDER BY data DESC, id;
```

```sql
-- Ordini nati da un preventivo (provenienza upstream)
SELECT numero, data, ragione_sociale_completa, documento_origine_codice
  FROM vendite.vw_ordini_lista
 WHERE documento_origine_tipo = 'PREVENTIVO'
 ORDER BY data DESC;
```

---

### Note operative

* **`numero` sempre valorizzato**: generato all'INSERT dal trigger gen codice (anche in
  BOZZA), quindi esposto nudo senza fallback.
* **Cliente sempre risolto**: `soggetto_ruolo_id` è NOT NULL → la vista lo risolve anche
  per i prospect senza billing account (`ba_codice` resta NULL).
* **Origine NULL = ordine diretto**: `documento_origine_*` è valorizzato solo dal service
  di conversione preventivo/offerta→ordine; lo scheletro CRUD non lo popola.
* **`security_invoker=on`**: le tre policy RLS di `vendite.ordini` (operatore/portale/
  shop) restano efficaci attraverso la vista.
* **Performance**: tutti i lookup su PK/indici; i due LEFT JOIN polimorfi per l'origine
  matchano al più una riga grazie alla condizione sul tipo.

---

---

### 🔄 rev 2026-10-11 — la lista non calcola più il grafo

Changeset `20261011-97`. La vista non legge più la sintesi della lineage di tutti
i documenti. Le colonne della frontiera e del transito (`frontiera_*`,
`n_discendenti_attivi`, `is_transitato`) le chiede il backend a
[`fn_documento_lineage_sintesi`](fn_documento_lineage_sintesi.md) per i soli
documenti della pagina. La pratica (`pratica_id`, `pratica_numero`,
`n_pratiche`) resta qui, filtrabile e ordinabile, e la legge
`pratiche.fn_pratica_del_documento`. Una pagina da 25 righe costava ~320-390 ms,
ora ~8-70 ms più la sintesi delle 25 chiavi (~58 ms) — dbdev, 2026-10-11.

{% include-markdown "signature-core.md" %}

---

### 🔄 rev 2026-09-13 — la consegna richiesta, in testata

Colonna nuova in coda: **`data_consegna_richiesta_cliente_min`**, la prima data
di consegna che il cliente ha chiesto sulle righe **attive** dell'ordine
(`20260913-17`).

* **È un calcolo, non una colonna dell'ordine.** La data di consegna vive
  sulla riga — una riga può essere pronta e un'altra no — e la testata la
  espone come minimo delle righe. Una colonna in `vendite.ordini` sarebbe una
  seconda verità, fuori sincrono al primo cambio di riga.
* **Vuota = nessuna riga attiva la dichiara.** Le righe spente non contano.
* **Il nome dice di chi è la data.** Il suffisso `_cliente` segue la regola dei
  documenti: non marcato = nostro, marcato = della controparte. Sull'ordine
  d'acquisto la richiesta è nostra e la conferma è del fornitore.
* È la colonna `746` della lista ordini, disponibile in «Personalizza colonne»;
  non ordina finché il backend non la mette in whitelist.

Brief: `brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezione 5.2.
