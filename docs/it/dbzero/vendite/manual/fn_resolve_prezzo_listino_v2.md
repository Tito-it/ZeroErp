## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_prezzo_listino_v2`

> 👀 **Vedi anche**
>
**Guide generali:**
>
• [Gestione listini](/guide/gestione-listini)
>
**Approfondimento tabelle:**
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> • [vendite.listini](/dbzero/vendite/tabelle/listini)
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
> • [vendite.promo_articoli](/dbzero/vendite/tabelle/promo_articoli)
> • [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti)
> • [anagrafiche.categorie_clienti_listini](/dbzero/anagrafiche/tabelle/categorie_clienti_listini)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>
**Approfondimento funzioni:**
>
• [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale
(latest review 14-04-2026)

`vendite.fn_resolve_prezzo_listino_v2` e' il **resolver prezzi pricing v5**. Riceve le dimensioni di calcolo (articolo, uom, data, BA, utility, emittente, classe utenza opzionale) e restituisce **una sola riga** con il prezzo risolto, il prezzo base pre-variazione e tutti i metadati necessari per lo snapshot in `commesse_attivita` / `attivita_fatturabili`.

La risoluzione avviene in **3 stadi deterministici** (nessun tie-break): la prima regola che matcha vince. Gli EXCLUDE no-overlap su `contratti`, `categorie_clienti_listini` e `promo_articoli` garantiscono l'unicita' del match senza bisogno di `ORDER BY`.

---

### Ordine di valutazione (3 stadi)

| Stadio | Fonte prezzo                                     | Origine output             |
| ------ | ------------------------------------------------ | -------------------------- |
| **0**  | `vendite.promo_articoli` (overlay)               | `PROMO`                    |
| **1a** | `vendite.contratti_righe.prezzo_unitario`        | `CONTRATTO_OVERRIDE`       |
| **1b** | `vendite.contratti.listino_id` + var. globale    | `CONTRATTO_LISTINO`        |
| **2**  | Matrice `categorie_clienti_listini` + variazione | `CATEGORIA`                |

Implementazione: il codice calcola **prima** STADIO 1/2 (prezzo base), poi la PROMO **sovrascrive** come overlay se la categoria del BA ha `partecipa_promo = TRUE`. Risultato identico all'ordine logico del doc v5 con una sola passata.

---

### Firma

```sql
vendite.fn_resolve_prezzo_listino_v2(
    p_articolo_id                 uuid,
    p_uom_id                      bigint,
    p_data_riferimento            date,
    p_ba_id                       bigint,
    p_utility_id                  integer,
    p_emittente_soggetto_ruolo_id bigint,
    p_classe_utenza_id            integer DEFAULT NULL
)
RETURNS TABLE (
    prezzo_finale                  numeric,
    prezzo_base_snapshot           numeric,
    tipo_variazione_applicata      varchar,
    valore_variazione_applicata    numeric,
    origine                        varchar,
    listino_id                     bigint,
    listino_versione_id            bigint,
    listino_riga_id                bigint,
    contratto_id                   bigint,
    promo_id                       bigint,
    categoria_cliente_listino_id   bigint
)
```

---

### Input

| Parametro                       | Tipo    | Obbligatorio | Note                                                              |
| ------------------------------- | ------- | ------------ | ----------------------------------------------------------------- |
| `p_articolo_id`                 | uuid    | si           | Articolo da prezzare                                              |
| `p_uom_id`                      | bigint  | si (>0)      | Unita' di misura di riferimento del prezzo                        |
| `p_data_riferimento`            | date    | si           | Data a cui risolvere validita' contratto/listino/promo            |
| `p_ba_id`                       | bigint  | si (>0)      | Billing account destinatario                                      |
| `p_utility_id`                  | integer | si (>0)      | Utility (1 operatore gestisce piu' utility)                       |
| `p_emittente_soggetto_ruolo_id` | bigint  | si (>0)      | Emittente fiscale (derivato dal JWT operatore lato BE)            |
| `p_classe_utenza_id`            | integer | no           | Classe utenza derivata da contratto_utilities o precontrattuali   |

---

### Output

| Campo                         | Tipo          | Semantica                                                                     |
| ----------------------------- | ------------- | ----------------------------------------------------------------------------- |
| `prezzo_finale`               | numeric       | Prezzo effettivo dopo applicazione variazione                                 |
| `prezzo_base_snapshot`        | numeric       | Prezzo base pre-variazione (utile per ricostruire l'aritmetica)               |
| `tipo_variazione_applicata`   | varchar       | `PERCENTUALE` \| `VALORE_FISSO` \| `PREZZO_FISSO` \| `NESSUNA`                |
| `valore_variazione_applicata` | numeric       | Valore della variazione (NULL se `NESSUNA`)                                   |
| `origine`                     | varchar       | `PROMO` \| `CONTRATTO_OVERRIDE` \| `CONTRATTO_LISTINO` \| `CATEGORIA`         |
| `listino_id`                  | bigint        | Listino risolto (NULL se `CONTRATTO_OVERRIDE` modalita' C)                    |
| `listino_versione_id`         | bigint        | Versione attiva del listino usata                                             |
| `listino_riga_id`             | bigint        | Riga listino usata (NULL se override)                                         |
| `contratto_id`                | bigint        | Contratto coinvolto se origine `CONTRATTO_*`                                  |
| `promo_id`                    | bigint        | Promo applicata se origine `PROMO`                                            |
| `categoria_cliente_listino_id`| bigint        | Riga matrice usata se origine `CATEGORIA`                                     |

---

### Formula variazione

Convenzione algebrica (il segno del valore rappresenta la direzione):

```
PERCENTUALE:  prezzo_base * (1 + valore / 100)    -- valore < 0 = sconto
VALORE_FISSO: prezzo_base + valore                -- valore < 0 = sconto
PREZZO_FISSO: valore                              -- prezzo assoluto (solo PROMO)
```

> ⚠️ **Convenzione da confermare con il business**: `vendite.promo_articoli` ha `CHECK (valore_variazione > 0 OR tipo_variazione = 'PREZZO_FISSO')`. Con la formula algebrica sopra un valore positivo rappresenta una maggiorazione, non uno sconto. Se la convenzione business e' "promo = sempre sconto, valore positivo", il CHECK va rilassato e la formula adattata (es. `base * (1 - v/100)`). La scelta definitiva va presa prima di aprire la UI operatore.

---

### Errori sollevati

Tutti via `script.fn_log_and_raise_error` (`SQLSTATE 'P0001'`).

| Codice                                     | Quando                                                                                      |
| ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `E_PARAMETRO_INVALIDO`                     | ID NULL o <= 0, data NULL, BA non trovato                                                   |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`  | Contratto ATTIVO in modalita' C ma nessuna riga con prezzo per l'articolo                   |
| `E_PREZZO_LISTINO_RIGA_NON_TROVATA`        | Listino risolto, ma manca riga attiva per (articolo, uom, versione valida alla data)        |
| `E_PREZZO_LISTINO_NON_TROVATO`             | BA senza categoria_cliente_id (difensivo: post-backfill e' NOT NULL)                        |
| `E_CATEGORIA_LISTINO_NON_MAPPATA`          | Nessuna riga in `categorie_clienti_listini` per la quadrupla richiesta                      |

Il resolver non restituisce mai `NULL`: o risolve un prezzo o solleva errore esplicito.

---

### Determinismo

Il match e' unico per costruzione DB:

* `ex_contratti_no_overlap` -> un solo contratto ATTIVO per `(ba, istanza_utility, utility, ambito)` sul periodo
* `ex_categ_cli_listini_no_overlap` -> un solo match in matrice per `(cat, utility, emittente, classe/NULL)` sul periodo
* `ex_promo_articoli_no_overlap` -> una sola promo per `(articolo, uom)` sul periodo
* `uq_listini_righe_key_attiva` -> una sola riga listino attiva per `(versione, articolo, uom)`

I `LIMIT 1` presenti nel codice sono **difensivi**, non discriminanti: se ne togli uno il risultato non cambia.

---

### Dipendenze DB

* Tabelle: `vendite.contratti`, `vendite.contratti_righe`, `vendite.listini`, `vendite.listini_versioni`, `vendite.listini_righe`, `vendite.promo_articoli`, `anagrafiche.billing_account`, `anagrafiche.categorie_clienti`, `anagrafiche.categorie_clienti_listini`, `config.stati_doc_contratti`
* Funzioni: `script.fn_log_and_raise_error`
* Estensioni: nessuna diretta (gli EXCLUDE a monte usano `btree_gist`)

---

### Esempio

```sql
-- Risoluzione prezzo per un BA gas con classe DOM-BTA
SELECT *
  FROM vendite.fn_resolve_prezzo_listino_v2(
      p_articolo_id                 := 'a1f2...'::uuid,
      p_uom_id                      := 7,
      p_data_riferimento            := '2026-06-15',
      p_ba_id                       := 12345,
      p_utility_id                  := 1,
      p_emittente_soggetto_ruolo_id := 100,
      p_classe_utenza_id            := 42
  );
```

Il record risultante va scritto in `vendite.commesse_attivita` (campi snapshot) al momento dell'emissione dell'attivita' in commessa.

---

{% include-markdown "signature-core.md" %}
