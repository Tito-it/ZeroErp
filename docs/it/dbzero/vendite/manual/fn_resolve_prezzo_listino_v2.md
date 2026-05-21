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
(rev 2026-05-20 — 9° param p_listino_versione_id_preferito: fast path diretto)

`vendite.fn_resolve_prezzo_listino_v2` e' il **resolver prezzi pricing v5**. Riceve le dimensioni di calcolo (articolo, uom, data, BA, utility, emittente, classe utenza opzionale) e restituisce **una sola riga** con il prezzo risolto, il prezzo base pre-variazione e tutti i metadati necessari per lo snapshot in `commesse_attivita` / `attivita_fatturabili`.

La risoluzione avviene in **stadi deterministici** (nessun tie-break): la prima regola che matcha vince. Con `p_articolo_padre_contesto` viene attivato anche lo STADIO BUNDLE (`LISTINO_BUNDLE`). Gli EXCLUDE no-overlap su `contratti`, `categorie_clienti_listini` e `promo_articoli` garantiscono l'unicita' del match senza bisogno di `ORDER BY`.

---

### Ordine di valutazione (3 stadi + BUNDLE + FAST PATH)

| Stadio | Attivo quando | Fonte prezzo | Origine output |
| ------ | ------------- | ------------ | -------------- |
| **FAST PATH** | `p_listino_versione_id_preferito IS NOT NULL` | Versione fornita direttamente — bundle poi standalone | `LISTINO_BUNDLE` / `CONTRATTO_LISTINO`; se articolo non trovato → fallback a STADIO 2 |
| **0** | sempre (overlay) | `vendite.promo_articoli` (non in contesto bundle) | `PROMO` |
| **1a** | `p_listino_versione_id_preferito IS NULL` | `vendite.contratti_righe.tipo_eccezione` — OVERRIDE o AGGIUNTA | `CONTRATTO_OVERRIDE` / `CONTRATTO_AGGIUNTA` |
| **1a-ESC** | `p_listino_versione_id_preferito IS NULL` | `vendite.contratti_righe.tipo_eccezione` = ESCLUSIONE | raise `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` |
| **1b** | `p_listino_versione_id_preferito IS NULL` | Versione listino contratto + variazione globale (standalone) | `CONTRATTO_LISTINO` |
| **BUNDLE** | `p_articolo_padre_contesto IS NOT NULL` | `vendite.listini_righe_componenti` | `LISTINO_BUNDLE` |
| **2** | `v_origine IS NULL` (nessun prezzo trovato) | Matrice `categorie_clienti_listini` + variazione | `CATEGORIA` |

**FAST PATH — versione diretta (dal 2026-05-20)**: se `p_listino_versione_id_preferito IS NOT NULL`, il lookup contratto-via-BA (STADIO 1) viene saltato interamente. Il resolver usa la versione fornita direttamente per cercare bundle (`listini_righe_componenti`) e poi standalone (`listini_righe`). Se l'articolo **non e' presente** in quella versione, non alza errore: resetta e cade nel STADIO 2 (CATEGORIA). `contratto_id`, `tipo_eccezione` restano `NULL` nell'output. Pensato per contesti di anteprima (form atomic drawer) dove il caller gia' conosce la versione listino da usare.

**STADIO 1a — tipo_eccezione (dal 2026-05-15)**: cerca riga in `contratti_righe` per `(contratto_id, articolo_id)` e legge `tipo_eccezione`. Tre esiti:

* `OVERRIDE` → usa `prezzo_unitario` come prezzo finale, origine `CONTRATTO_OVERRIDE`. Bypassa sempre BUNDLE e listino.
* `ESCLUSIONE` → raise `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` (453). L'articolo non è fatturabile con questo contratto.
* `AGGIUNTA` → usa `prezzo_unitario` come prezzo finale, origine `CONTRATTO_AGGIUNTA`. È un articolo fuori listino aggiunto al contratto.
* Nessuna riga → procede a STADIO 1b.

**STADIO 1b — versione listino fissata (dal 2026-05-15)**: se il contratto ha `listino_versione_id IS NOT NULL` (snapshot fissato all'attivazione, vedi `trgfn_contratti_freeze_listino_versione`), usa quella versione direttamente. Altrimenti fallback sulla versione attiva a `p_data_riferimento` (§4.4).

**STADIO BUNDLE**: si attiva solo se `p_articolo_padre_contesto IS NOT NULL`. Viene valutato dopo aver determinato `listino_versione_id` (da STADIO 1b o STADIO 2) e PRIMA di applicare la variazione contratto/categoria. Cerca una riga in `vendite.listini_righe_componenti` per la quadrupla (listino_versione_id, padre, figlio, data). Se trovata, usa quel prezzo come `prezzo_base` e ritorna `origine = 'LISTINO_BUNDLE'`. `CONTRATTO_OVERRIDE` e `CONTRATTO_AGGIUNTA` (STADIO 1a) bypassano sempre il BUNDLE.

La promo overlay (STADIO 0) non viene applicata se `v_bundle_used = TRUE` — il prezzo bundle è già il prezzo specifico negoziato per il componente in quel contesto.

Implementazione: il codice calcola **prima** STADIO 1/2 (prezzo base), poi la PROMO **sovrascrive** come overlay se la categoria del BA ha `partecipa_promo = TRUE` e il bundle non è attivo. Risultato identico all'ordine logico del doc v5 con una sola passata.

Il lookup matrice in STADIO 2 (classe specifica + fallback NULL) e' eseguito in **1 sola query** con `ORDER BY classe_utenza_id IS NULL LIMIT 1`: il match specifico (FALSE) precede il fallback (TRUE) nel sort. L'EXCLUDE no-overlap garantisce al piu' 1 riga per ciascun scenario.

---

### Firma

```sql
vendite.fn_resolve_prezzo_listino_v2(
    p_articolo_id                 catalogo.articoli.id%TYPE,
    p_uom_id                      catalogo.unita_misura.id%TYPE,
    p_data_riferimento            date,
    p_ba_id                       anagrafiche.billing_account.id%TYPE,
    p_utility_id                  config.utilities.id%TYPE,
    p_emittente_soggetto_ruolo_id anagrafiche.soggetti_ruoli.id%TYPE,
    p_classe_utenza_id              config.classi_utenze.id%TYPE DEFAULT NULL,
    p_articolo_padre_contesto       uuid DEFAULT NULL,
    p_listino_versione_id_preferito vendite.listini_versioni.id%TYPE DEFAULT NULL
)
RETURNS TABLE (
    prezzo_finale                  vendite.listini_righe.prezzo%TYPE,
    prezzo_base_snapshot           vendite.listini_righe.prezzo%TYPE,
    tipo_variazione_applicata      anagrafiche.categorie_clienti_listini.tipo_variazione%TYPE,
    valore_variazione_applicata    anagrafiche.categorie_clienti_listini.valore_variazione%TYPE,
    origine                        varchar,
    listino_id                     vendite.listini.id%TYPE,
    listino_versione_id            vendite.listini_versioni.id%TYPE,
    listino_riga_id                vendite.listini_righe.id%TYPE,
    contratto_id                   vendite.contratti.id%TYPE,
    promo_id                       vendite.promo_articoli.id%TYPE,
    categoria_cliente_listino_id   anagrafiche.categorie_clienti_listini.id%TYPE,
    categoria_cliente_id_snapshot  anagrafiche.billing_account.categoria_cliente_id%TYPE,
    classe_utenza_id_snapshot      config.classi_utenze.id%TYPE,
    tipo_eccezione                 vendite.tipo_eccezione_contratto   -- Step 2.4: NULL se non STADIO 1a
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
| `p_articolo_padre_contesto`     | uuid    | no           | UUID articolo padre composito. Se fornito, attiva STADIO BUNDLE: cerca prezzo in `listini_righe_componenti` per (versione, padre, figlio, data). `NULL` = risoluzione standalone (default). |
| `p_listino_versione_id_preferito` | bigint | no (>0 se fornito) | **Fast path**: se non NULL, salta il lookup contratto-via-BA e usa questa versione listino direttamente. Se l'articolo non e' in quella versione, fallback silenzioso a STADIO 2. `NULL` (default) = comportamento standard. |

---

### Output

| Campo | Tipo | Semantica |
| --- | --- | --- |
| `prezzo_finale` | numeric | Prezzo effettivo dopo applicazione variazione |
| `prezzo_base_snapshot` | numeric | Prezzo base pre-variazione (utile per ricostruire l'aritmetica) |
| `tipo_variazione_applicata` | varchar | `PERCENTUALE` \| `VALORE_FISSO` \| `PREZZO_FISSO` \| `NESSUNA` |
| `valore_variazione_applicata` | numeric | Valore della variazione (NULL se `NESSUNA`) |
| `origine` | varchar | `PROMO` \| `CONTRATTO_OVERRIDE` \| `CONTRATTO_AGGIUNTA` \| `CONTRATTO_LISTINO` \| `LISTINO_BUNDLE` \| `CATEGORIA` |
| `listino_id` | — | Listino risolto (NULL se `CONTRATTO_AGGIUNTA` su contratto senza listino) |
| `listino_versione_id` | — | Versione usata. STADIO 1b: snapshot fissato all'attivazione o versione corrente §4.4. STADIO 2: versione corrente alla data. |
| `listino_riga_id` | — | Riga listino standalone usata (NULL se eccezione o bundle) |
| `contratto_id` | — | Contratto coinvolto se origine `CONTRATTO_*` |
| `promo_id` | — | Promo applicata se origine `PROMO` |
| `categoria_cliente_listino_id` | — | Riga matrice usata se origine `CATEGORIA` |
| `categoria_cliente_id_snapshot` | — | Categoria cliente al momento del calcolo: dal contratto (STADIO 1, congelata alla creazione) oppure dal BA (STADIO 2). |
| `classe_utenza_id_snapshot` | — | STADIO 1: da `contratti_utilities` (fallback `p_classe_utenza_id`). STADIO 2: `p_classe_utenza_id` input. |
| `tipo_eccezione` | `vendite.tipo_eccezione_contratto` | Non-NULL solo per `CONTRATTO_OVERRIDE` e `CONTRATTO_AGGIUNTA`. NULL per tutti gli altri path. Utile per badge/banner UI e audit. |

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

| Codice | HTTP (BE) | Quando |
| --- | --- | --- |
| `E_PARAMETRO_INVALIDO` | 400 | ID NULL o <= 0, data NULL, BA non trovato |
| `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` (453) | 422 | Articolo ha `tipo_eccezione = ESCLUSIONE` nel contratto attivo (Step 2.4) |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | 422 | Contratto senza listino (`listino_id NULL`) e nessuna eccezione per l'articolo |
| `E_LISTINO_VERSIONE_NON_ATTIVA` (448) | 422 | Listino determinato ma nessuna versione attiva alla data di riferimento |
| `E_PREZZO_LISTINO_RIGA_NON_TROVATA` | 422 | Versione trovata, ma manca riga attiva per (articolo, uom) — né bundle né standalone |
| `E_PREZZO_LISTINO_NON_TROVATO` | 422 | BA senza `categoria_cliente_id` e senza contratto attivo (difensivo) |
| `E_CATEGORIA_LISTINO_NON_MAPPATA` | 422 | Nessuna riga in `categorie_clienti_listini` per la quadrupla richiesta |

Il resolver non restituisce mai `NULL`: o risolve un prezzo o solleva errore esplicito.

---

### Determinismo

Il match e' unico per costruzione DB:

* `ex_contratti_no_overlap` -> un solo contratto ATTIVO per `(ba, istanza_utility, utility, ambito)` sul periodo. L'EXCLUDE include `istanza_utility_id` e `ambito`, quindi più contratti ATTIVI possono coesistere per la stessa `(ba, utility, data)` se differiscono in queste dimensioni. Il resolver non riceve `istanza_utility_id` come parametro: in caso di contratti sovrapposti usa `ORDER BY c.id DESC LIMIT 1` (contratto con ID maggiore). Nella maggioranza dei casi operativi un solo contratto ATTIVO esiste per BA+utility+data.
* `ex_categ_cli_listini_no_overlap` -> un solo match in matrice per `(cat, utility, emittente, classe/NULL)` sul periodo
* `ex_promo_articoli_no_overlap` -> una sola promo per `(articolo, uom)` sul periodo
* `uq_listini_righe_key_attiva` -> una sola riga listino attiva per `(versione, articolo, uom)`

I `LIMIT 1` presenti nel codice sono **difensivi** per STADIO 2 e BUNDLE, non discriminanti: se ne togli uno il risultato non cambia. Per STADIO 1 (contratti) il `ORDER BY c.id DESC LIMIT 1` è discriminante in caso di più contratti sovrapposti per dimensioni diverse (vedi sopra).

---

### Dipendenze DB

* Tabelle: `vendite.contratti`, `vendite.contratti_righe`, `vendite.listini`, `vendite.listini_versioni`, `vendite.listini_righe`, `vendite.listini_righe_componenti`, `vendite.promo_articoli`, `anagrafiche.billing_account`, `anagrafiche.categorie_clienti`, `anagrafiche.categorie_clienti_listini`, `config.stati_doc_contratti`
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
