## 📘 Documentazione Concettuale – Vista `vendite.vw_offerte_commerciali_list`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [vendite.listini](/dbzero/vendite/tabelle/listini)
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
>
> Trigger correlati:
> [vendite.trgfn_offerte_commerciali_revisione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_revisione)

---

### 🎯 Scopo Principale

(rev 2026-05-27 — rev1)

`vendite.vw_offerte_commerciali_list` e' la vista denormalizzata principale per la **lista
offerte commerciali**. Espone tutti i dati necessari al frontend (tabella lista,
toggle storico revisioni) e al backend (filtro permessi per scope emittente).

Strutturalmente speculare a `vendite.vw_preventivi_list` (rev3): usa lo stesso pattern
di lookup soggetto via `istanza_utilities` e lo stesso criterio di derivazione `is_attiva`.

---

### JOIN principali

| Tabella | Dati esposti | Note |
| --- | --- | --- |
| `config.stati_doc_offerte` | `stato_codice`, `stato_codice_interno`, `stato_descrizione` | INNER JOIN |
| `anagrafiche.istanze_utilities` → `anagrafiche.soggetti` | `soggetto_id`, `cliente_denominazione`, `id_fiscale` | LEFT (in pratica sempre match: `istanza_utility_id` NOT NULL su offerte) |
| `anagrafiche.billing_account` | `billing_account_codice` | LEFT (in pratica sempre match: `billing_account_id` NOT NULL su offerte) |
| `config.utilities` | `utility_codice`, `utility_descrizione` | LEFT (in pratica sempre match: `utility_id` NOT NULL) |

---

### 📑 Campi chiave esposti

* **Identificatori**: `id`, `uid`, `codice`, `revisione_numero`, `revisione_padre_id`
* **Flag revisione**: **`is_attiva`**, **`has_next_revisione`**
* **Stato**: `stato_doc_offerta_id`, `stato_codice`, **`stato_codice_interno`**, `stato_descrizione`
* **Billing account**: `billing_account_id`, **`billing_account_codice`**
* **Soggetto (via istanza)**: `soggetto_id`, `cliente_denominazione`, **`id_fiscale`**
* **Permessi**: `emittente_fiscale_id` (colonna persistita, popolata dal trigger)
* **Utility e istanza**: `utility_id`, **`utility_codice`**, **`utility_descrizione`**, `istanza_utility_id`, **`istanza_utility_codice`**
* **Listino**: `listino_id`, `listino_versione_id`
* **Variazione globale**: `valore_variazione_globale`, `tipo_variazione_globale`
* **Validita'**: `validita_dal`, `validita_al`
* **Ciclo vita**: `data_emissione`, `data_accettazione`, `data_rifiuto`, `data_annullamento`
* **Audit**: `data_insert`, `user_insert`

**Ordinamento default**: `data_insert DESC, id DESC` (tiebreaker per stabilita').

---

### Colonne derivate — `is_attiva` e `has_next_revisione`

#### `is_attiva`

```sql
sdo.codice_interno NOT IN ('SUPERATA', 'ANNULLATA') AS is_attiva
```

`TRUE` se l'offerta non e' stata superata da una revisione successiva ne' annullata.
La semantica "non esiste revisione successiva non-abortita" e' garantita dal trigger
`trgfn_offerte_commerciali_revisione` (`_z90_`, `AFTER INSERT`): all'inserimento di
rev.N+1, il trigger porta automaticamente rev.N in stato SUPERATA.

**Costo**: O(1) — derivata dal join su `stati_doc_offerte` gia' presente, zero subquery.

> **Edge case noto**: se l'ultima revisione di un lineage viene annullata senza creare
> un successore, la revisione padre rimane SUPERATA e nessuna offerta del lineage risulta
> `is_attiva = true`. Limite del modello trigger attuale (retroportare il padre
> richiederebbe un secondo trigger); fuori scope in v1.

#### `has_next_revisione`

```sql
EXISTS (
    SELECT 1 FROM vendite.offerte_commerciali figlio
     WHERE figlio.revisione_padre_id = o.id
) AS has_next_revisione
```

`TRUE` se esiste almeno un figlio (qualunque stato). Usato dalla UI per il
**toggle "mostra storico revisioni"**: una riga con `has_next_revisione = FALSE`
non ha predecessori da espandere.

**Costo**: efficiente grazie all'indice parziale `ix_offerte_commerciali_revisione_padre`
(`WHERE revisione_padre_id IS NOT NULL`), che indicizza solo le righe figlio — minoranza
della tabella.

---

### Nota sul lookup soggetto (via istanza)

Il soggetto e' raggiunto tramite `istanza_utility_id → istanze_utilities → soggetti`,
in un unico join invece dei 3 join via billing account del vecchio pattern.

**Perche' funziona**: `offerte_commerciali.istanza_utility_id` e' NOT NULL;
`istanze_utilities.soggetto_id` e' NOT NULL con FK diretta a `soggetti`. Il soggetto
via istanza coincide con quello via BA (garantito dalla coerenza del modello anagrafico).

**Nota BA**: `billing_account_id` e' NOT NULL sulle offerte (a differenza dei preventivi
prospect), quindi `billing_account_codice` e' sempre valorizzato.

---

### Esempio d'uso

```sql
-- Lista offerte attive per un emittente, con dati cliente
SELECT id, codice, revisione_numero,
       is_attiva, has_next_revisione,
       stato_codice_interno, cliente_denominazione, id_fiscale,
       billing_account_codice,
       utility_codice, istanza_utility_codice,
       validita_al
  FROM vendite.vw_offerte_commerciali_list
 WHERE emittente_fiscale_id = 1
   AND is_attiva = TRUE
 ORDER BY data_insert DESC;
```

```sql
-- Storico revisioni di un lineage (tutte le revisioni di una offerta)
SELECT id, codice, revisione_numero,
       stato_codice_interno, is_attiva,
       data_emissione, data_accettazione
  FROM vendite.vw_offerte_commerciali_list
 WHERE id = :id_radice
    OR revisione_padre_id = :id_radice
 ORDER BY revisione_numero;
```

```sql
-- Offerte con revisioni successive (toggle storico)
SELECT id, codice, revisione_numero, has_next_revisione
  FROM vendite.vw_offerte_commerciali_list
 WHERE has_next_revisione = TRUE
 ORDER BY data_insert DESC
 LIMIT 20;
```

---

### Note operative

* **`is_attiva` e stato terminale**: gli stati SUPERATA e ANNULLATA sono terminali immutabili;
  la derivazione `NOT IN ('SUPERATA','ANNULLATA')` e' stabile e non richiede ricalcolo.
* **`has_next_revisione` e indice parziale**: l'indice `ix_offerte_commerciali_revisione_padre`
  copre solo le righe con `revisione_padre_id IS NOT NULL`, cioe' esclusivamente le revisioni
  figlio. E' piccolo rispetto alla tabella completa → `EXISTS` efficiente.
* **Nessun importo aggregato**: a differenza di `vw_preventivi_list`, la vista non espone
  totali (imponibile, IVA, totale): le offerte commerciali non hanno un calcolo importo
  testata nativo — gli importi emergono dalle eccezioni e dal listino versione.
* **Performance JOIN**: tutti i lookup sono su PK indicizzata, zero scansioni full.

---

{% include-markdown "signature-core.md" %}
