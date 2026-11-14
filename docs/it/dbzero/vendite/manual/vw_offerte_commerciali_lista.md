## 📘 Documentazione Concettuale – Vista `vendite.vw_offerte_commerciali_lista`

> **Ultimo aggiornamento**: 14 novembre 2026
>
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
vendite.fn_offerta_scaduta(sdo.esito, o.validita_al, (SELECT script.fn_data_operativa())) AS is_scaduta
```

`TRUE` quando l'offerta è **scaduta per l'operatore**: la validità è passata (rispetto alla data
operativa dell'azienda) **e** il cliente non ha ancora risposto, cioè lo stato non ha un esito nel
vocabolario (`config.stati_doc_offerte.esito`, oggi vuoto su bozza ed emessa). Un'offerta accettata,
rifiutata, superata o annullata con la validità passata non è scaduta: il cliente ha già risposto, o
l'offerta non è più viva.

⭐ **La regola sta in [`vendite.fn_offerta_scaduta`](/dbzero/vendite/manual/fn_offerta_scaduta)**, che
la vista compone e che il dettaglio dell'offerta chiama sulla sua riga: lista e dettaglio dicono la stessa
cosa senza che il dettaglio legga la vista. Chi mostra il badge «Scaduta» legge il flag e non filtra gli
stati per conto suo; la colonna configurabile «Scaduta» della lista dice la stessa
cosa del badge. Lo stato si legge per significato (l'esito), non per codice: uno stato nuovo di
attesa, senza esito, entra da sé.

---

### ⭐ Colonne derivate — le DUE domande, separate (rev 2026-08-28)

```sql
sdo.is_superato AS is_superata          -- «rimpiazzata da una revisione successiva?»
sdo.is_abortito                          -- «annullata?»
(NOT sdo.is_superato AND NOT sdo.is_abortito)  AS is_attiva
EXISTS (SELECT 1 FROM vendite.offerte_commerciali f
         WHERE f.revisione_padre_id = o.id)    AS has_next_revisione
```

Fino al 2026-08-28 `is_attiva` era scritta cosi':

```sql
sdo.codice_interno NOT IN ('SUPERATA', 'ANNULLATA')   -- ⛔ due domande, un flag
```

⛔ **Il difetto non era il valore, era che le due domande non erano piu'
separabili.** La lista offerte filtra `is_attiva IS TRUE` di default
(`offerte_repository`, parametro `solo_attiva`): un'offerta ANNULLATA non era
raggiungibile da **nessun** filtro di stato, e riappariva solo col toggle «storico
revisioni» — che promette di nascondere le revisioni *rimpiazzate*, non gli
annullamenti. Stesso difetto, e stessa correzione, dei preventivi
(`vw_preventivi`, changeSet `20260828-08`).

| Cosa si vuole chiedere | Predicato |
| --- | --- |
| «solo l'ultima revisione» (toggle storico OFF) | `is_superata IS FALSE` |
| «l'offerta e' viva e corrente» | `is_attiva IS TRUE` |
| «le annullate» (filtro di stato) | `stato_codice_interno = 'ANNULLATA'`, che ora **trova** qualcosa |

⚠️ **Nessun valore e' cambiato.** `is_superato` e' `true` sul solo `SUPERATA`,
`is_abortito` sul solo `ANNULLATA`: la nuova espressione seleziona esattamente le
stesse righe del letterale precedente. Il guadagno e' che la vista **non nomina
piu' nessuno stato** — il significato di `SUPERATA` sta ora dove stanno gia'
`fase`, `esito` e `terminale`, cioe' in
[config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte).

* **`is_superata`** — semantica garantita dal trigger
  `trgfn_offerte_commerciali_revisione` (`_z90_ AFTER INSERT`), che porta il padre
  in `SUPERATA` quando nasce la revisione successiva. Costo O(1).
  > ✅ *Il limite noto e' stato chiuso il 2026-08-28* (changeSet `20260828-12` e
  > `20260828-13`, su segnalazione del backend). Fino a quel giorno, se l'ultima
  > revisione di un lineage veniva annullata **senza successore**, il padre
  > restava `SUPERATA` e **nessuna** offerta del lineage risultava attiva: lo
  > stato sapeva andare e non sapeva tornare. Ora un trigger `_z90_` riporta il
  > padre a `EMESSA` quando la revisione che lo superava viene annullata e non
  > ne resta nessun'altra viva — l'inverso esatto di
  > `trgfn_offerte_commerciali_revisione`, e la stessa regola che i preventivi
  > hanno per costruzione: *una revisione abortita non rimpiazza nessuno*.
  > ⚠️ La transizione `SUPERATA -> EMESSA` e' ora ammessa, quindi non e' piu'
  > vero che `SUPERATA` sia senza uscite. La porta e' chiusa da una **regola**,
  > non da un privilegio: si esce dal superamento solo se non esiste piu' una
  > revisione figlia viva, altrimenti
  > `E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA` — vale per chiunque scriva, non solo
  > per il trigger.
* **`has_next_revisione`** — `TRUE` se esiste almeno un figlio (qualunque stato).
  Diverso da `is_superata`: dice «qualcuno ha **provato** a revisionarla», non
  «qualcuno l'ha **rimpiazzata**». Efficiente grazie all'indice parziale
  `ix_offerte_commerciali_revisione_padre`.

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
* **Flag revisione**: **`is_attiva`**, **`is_superata`**, **`is_abortito`**, **`has_next_revisione`**
* **Stato**: `stato_doc_offerta_id`, **`stato_codice_interno`** (severity Tag FE), `stato_descrizione`
* **Scadenza**: **`is_scaduta`** (badge FE: validità passata e nessun esito, la regola intera)
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
       is_attiva, is_superata, is_abortito, is_scaduta,
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
-- Toggle «Mostra storico revisioni» OFF = solo l'ultima revisione del lineage.
-- ⚠️ is_superata, NON is_attiva: quest'ultima nasconderebbe anche le annullate,
--    e il filtro di stato «Annullata» tornerebbe vuoto per costruzione.
SELECT id, codice, revisione_numero, stato_codice_interno, ragione_sociale_completa
  FROM vendite.vw_offerte_commerciali_lista
 WHERE is_superata IS FALSE
 ORDER BY validita_dal DESC, id;
```

```sql
-- Offerte scadute: validità passata e nessuna risposta del cliente
SELECT id, codice, stato_codice_interno, validita_al
  FROM vendite.vw_offerte_commerciali_lista
 WHERE is_scaduta = TRUE
 ORDER BY validita_al;
```

---

### Note operative

* **`is_scaduta` è la regola intera**: la validità passata **e** nessun esito
  dello stato. Il frontend mostra il badge dal flag, senza combinarlo con lo
  stato.
* **Listino opzionale**: `listino_codice`/`listino_versione_codice` sono NULL per
  offerte senza listino — la cella FE mostra il solo codice o nulla.
* **`security_invoker=on`**: vista pronta per un'eventuale RLS sulla tabella base.
* **Performance**: tutti i lookup su PK/indici, `EXISTS` su indice parziale per
  `has_next_revisione`, zero scansioni full.

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
