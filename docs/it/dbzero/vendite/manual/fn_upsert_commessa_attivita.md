## 📘 Documentazione Concettuale – Funzione `vendite.fn_upsert_commessa_attivita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> • [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> • [vendite.promo_articoli](/dbzero/vendite/tabelle/promo_articoli)
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti)
> • [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
>
**Approfondimento funzioni:**
>
• [vendite.fn_batch_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_batch_upsert_commessa_attivita)
> • [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
> • [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale
(latest review 15-04-2026)

Upsert idempotente di una riga `vendite.commesse_attivita` sulla chiave `(commessa_id, segment_key)`, con **snapshot pricing v5** obbligatorio in firma. Restituisce `(attivita_id, is_new)` per distinguere INSERT da UPDATE (via `xmax = 0` nel RETURNING).

Tre gruppi di validazione applicativa (`E_PARAMETRO_INVALIDO`) + tre guard di coerenza con lo stato commessa:

| Gruppo | Fail-fast |
| --- | --- |
| Parametri core | Null/≤0 su ID, segment_key vuota o > 128 char, quantità = 0, prezzo_snapshot NULL |
| Dominio enum snapshot v5 | `origine_prezzo` ∈ {PROMO, CONTRATTO_OVERRIDE, CONTRATTO_LISTINO, CATEGORIA, MANUALE}; `tipo_variazione_applicata` ∈ {PERCENTUALE, VALORE_FISSO, PREZZO_FISSO, NESSUNA} |
| Classificazione operativa | `tipo_movimento` ∈ {NORMALE, RETTIFICA, ONERE} |

---

### Parametri

#### Core (obbligatori, posizionali)

| Parametro              | Tipo     | Note                                                             |
| ---------------------- | -------- | ---------------------------------------------------------------- |
| `p_commessa_id`        | bigint   | >0; lookup su `vendite.commesse`                                 |
| `p_segment_key`        | varchar  | Trimmed, non vuoto, ≤ 128 char                                   |
| `p_articolo_id`        | uuid     | FK `catalogo.articoli`                                           |
| `p_istanza_utility_id` | bigint   | >0; FK `anagrafiche.istanze_utilities`                           |
| `p_data_attivita`      | date     | Data dell'attività erogata                                       |
| `p_uom_id`             | bigint   | >0; FK `catalogo.unita_misura`                                   |
| `p_quantita`           | numeric  | ≠ 0 (negativi ammessi per rettifiche/utility)                    |
| `p_competenza_mese`    | date     | Normalizzato al primo giorno del mese via `date_trunc('month')`  |
| `p_competenza_dal`     | date     | Inizio competenza                                                |
| `p_competenza_al`      | date     | Fine competenza                                                  |
| `p_prezzo_snapshot`    | numeric  | Obbligatorio; negativi ammessi (storni)                          |

#### Snapshot pricing v5 (obbligatori, posizionali dopo `p_prezzo_snapshot`)

Tutti obbligatori in firma. Passare `NULL` esplicito quando la dimensione non si applica (es. `p_classe_utenza_id_snapshot` per utility commercio, `p_promo_id` se origine ≠ PROMO).

| Parametro | Tipo | Valore tipico |
| --- | --- | --- |
| `p_prezzo_base_snapshot` | numeric(22,10) | Prezzo base pre-variazione (ritornato da `fn_resolve_prezzo_listino_v2.prezzo_base_snapshot`) |
| `p_origine_prezzo` | varchar(32) | Enum: `PROMO` \| `CONTRATTO_OVERRIDE` \| `CONTRATTO_LISTINO` \| `CATEGORIA` \| `MANUALE` |
| `p_tipo_variazione_applicata` | varchar(16) | Enum: `PERCENTUALE` \| `VALORE_FISSO` \| `PREZZO_FISSO` \| `NESSUNA` |
| `p_valore_variazione_applicata` | numeric(10,4) | Valore effettivo della variazione applicata |
| `p_promo_id` | bigint | FK `vendite.promo_articoli`; NOT NULL solo se origine = PROMO |
| `p_contratto_id` | bigint | FK `vendite.contratti`; NOT NULL se origine CONTRATTO_* |
| `p_categoria_cliente_id_snapshot` | smallint | FK `anagrafiche.categorie_clienti`; congela la categoria |
| `p_classe_utenza_id_snapshot` | integer | FK `config.classi_utenze`; NULL per utility senza dimensione |

#### Opzionali (con DEFAULT, dopo lo snapshot)

`p_qta_operativa`, `p_uom_operativa_id`, `p_factor_to_base` (default 1), `p_posticipa_al`, `p_tipo_doc_fiscale_id`, `p_valuta_id`, `p_area_geografica_id`, `p_listino_versione_id`, `p_prezzo_bloccato` (default false), `p_pricing_mode` (default `FIXED`), `p_prezzo_da_riallineare` (default false), `p_stato_approvazione` (default `BOZZA`), `p_stato_emissione` (default `NON_EMESSA`), `p_sorgente_tipo_id`, `p_sorgente_uid`, `p_tipo_movimento` (default `NORMALE`), `p_meta` (default `'{}'::jsonb`).

> La firma usa `%TYPE` su ogni parametro che riflette una colonna di `commesse_attivita`.

---

### Normalize `tipo_doc_fiscale_id` (rev 2026-06-19)

Il `tipo_doc_fiscale` **non si deriva da una regola di business** (semantica aperta, configurabile per azienda — vedi `brief-db-guard-tipo-doc-attivita`). La funzione applica solo un **default opzionale**:

* se `p_tipo_doc_fiscale_id` è valorizzato → ha **priorità** (usato così com'è);
* se è `NULL` e `p_sorgente_tipo_id` è valorizzato → risolve il default da `config.sorgenti.tipo_doc_fiscale_id` (single source of truth, **dentro** la funzione);
* se anche la sorgente non ha default → resta `NULL`. La valorizzazione **non è imposta qui**: l'obbligo scatta solo sullo stato emittibile, via il guard `trg_commesse_attivita_a10_guard_tipo_doc_emittibile` (codice `E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO`, 497).

---

### Output

```sql
RETURNS TABLE (
    attivita_id bigint,
    is_new      boolean
)
```

| Campo | Semantica |
| --- | --- |
| `attivita_id` | `id` della riga `commesse_attivita` inserita o aggiornata |
| `is_new` | `true` se INSERT, `false` se UPDATE (determinato da `xmax = 0` nel RETURNING) |

---

### Regole UPDATE (ON CONFLICT)

* Tutte le colonne **sovrascritte** da EXCLUDED tranne `meta` e `tipo_doc_fiscale_id`:
  * `meta` esistente **mergeato** con l'input (`COALESCE(meta, '{}') || COALESCE(EXCLUDED.meta, '{}')`). Una chiave `tipo_consumo` scritta prima del 2026-10-13 resta nel meta della riga esistente; quella in arrivo si toglie prima (vedi la rev 2026-10-13).
  * `tipo_doc_fiscale_id` **no-regressione** (rev 2026-06-19): `COALESCE(EXCLUDED.tipo_doc_fiscale_id, commesse_attivita.tipo_doc_fiscale_id)`. Un re-push con valore in arrivo `NULL` **non azzera** un tipo_doc già risolto; un cambio a un valore non-NULL resta consentito.
* Snapshot pricing v5: **sovrascrive sempre** (rappresenta lo snapshot del calcolo corrente; se il resolver è stato rieseguito, il nuovo risultato vince).
* Guard: se la riga esistente ha `stato_emissione ≠ NON_EMESSA`, update bloccato con `E_COMMESSA_ATTIVITA_GIA_EMESSA`.

---

### Errori sollevati

Via `script.fn_log_and_raise_error` (`SQLSTATE 'P0001'`).

| Codice | Quando |
| --- | --- |
| `E_PARAMETRO_INVALIDO` | ID NULL/≤0, segment_key invalida, quantità = 0, prezzo_snapshot NULL, enum fuori dominio, tipo_movimento/consumo invalidi |
| `E_COMMESSA_NON_TROVATA` | `commessa_id` non esiste in `vendite.commesse` |
| `E_COMMESSA_NON_MODIFICABILE` | `stati_commessa.modificabile = false` per lo stato corrente |
| `E_COMMESSA_ATTIVITA_GIA_EMESSA` | Riga esistente con `stato_emissione ≠ NON_EMESSA` |

---

### Dipendenze DB

* Tabelle: `vendite.commesse_attivita`, `vendite.commesse`, `vendite.stati_commessa`, `config.sorgenti` (lookup default `tipo_doc_fiscale_id`).
* Funzioni: `script.fn_log_and_raise_error`, `vendite.fn_link_commessa_sorgente` (dal 2026-10-12: il link documento → commessa).
* Trigger/CHECK DB: `chk_commesse_attivita_origine_prezzo`, `chk_commesse_attivita_tipo_variazione_applicata` garantiscono i domini enum anche se il guard applicativo è bypassato; `trg_commesse_attivita_a10_guard_tipo_doc_emittibile` + `chk_commesse_attivita_tipo_doc_emittibile` impongono `tipo_doc_fiscale_id NOT NULL` sullo stato emittibile (APPROVATA+NON_EMESSA).

---

### Esempio d'uso (con snapshot pricing v5)

```sql
SELECT *
  FROM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => 12345,
    p_segment_key                   => 'ORD-1001-RIGA-1',
    p_articolo_id                   => '8c5ce3a9-8f52-4d07-ae36-884c5f8d4a1f',
    p_istanza_utility_id            => 10,
    p_data_attivita                 => DATE '2026-06-01',
    p_uom_id                        => 1,
    p_quantita                      => 1,
    p_competenza_mese               => DATE '2026-06-01',
    p_competenza_dal                => DATE '2026-06-01',
    p_competenza_al                 => DATE '2026-06-30',
    p_prezzo_snapshot               => 90,
    -- Snapshot pricing v5 (risultato di fn_resolve_prezzo_listino_v2)
    p_prezzo_base_snapshot          => 100,
    p_origine_prezzo                => 'CATEGORIA',
    p_tipo_variazione_applicata     => 'PERCENTUALE',
    p_valore_variazione_applicata   => -10,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => 3,       -- es. SILVER
    p_classe_utenza_id_snapshot     => NULL     -- utility commercio
  );
```

Output:

```text
 attivita_id | is_new
-------------+--------
    7890123  | t
```

---

### Nota — porta oneri (`p_causale_onere_id`)

Dal 21-07-2026 la firma include `p_causale_onere_id` (default `NULL`): la causale di un onere,
scritta sulla colonna `commesse_attivita.causale_onere_id`. Guard di coerenza: ammessa **se e
solo se** `tipo_movimento = 'ONERE'` (rispecchia il CHECK biconditional della tabella). I
chiamanti storici (push/lister) non la passano → righe `NORMALE` con causale `NULL`. Il writer
di norma è la madre
[`fn_aggiungi_onere_commessa`](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa), non un
chiamante diretto.

---


---

### 🔄 rev 2026-08-18 — due parametri nuovi, e un `DROP` obbligatorio

Brief: `brief-design-note-credito-resi` (slice **N1b** e **N5**).

| Parametro | Tipo | Default | Cosa porta |
|---|---|---|---|
| `p_natura_doc_id` | `commesse_attivita.natura_doc_id%TYPE` | `NULL` | la **natura fiscale** del documento che l'attività produrrà (`FATTURA` / `NOTA_CREDITO` / …) |
| `p_fattura_riga_rettificata_id` | `commesse_attivita.fattura_riga_rettificata_id%TYPE` | `NULL` | per una **rettifica**, la riga di fattura che sta correggendo |

#### ⚠️ Perché `DROP` + `CREATE` e non `CREATE OR REPLACE`

Con 40 parametri di cui 21 con `DEFAULT`, aggiungerne uno con
`CREATE OR REPLACE` **non sostituisce la funzione**: PostgreSQL la identifica
dalla firma, quindi ne nascerebbe una **seconda** — un overload — e con i default
su entrambe ogni chiamata esistente diventerebbe ambigua (*function is not
unique*).

⛔ E il `DROP` è **senza `CASCADE`**, mai con: i chiamanti la risolvono per nome a
runtime, non c'è dipendenza strutturale da propagare.

✅ **Censimento fatto prima di scrivere**: tutti i chiamanti — i quattro DB,
`commesse_repository.upsert_attivita` e i sei smoke-test Python — usano
**argomenti nominali**. Due parametri in coda con `DEFAULT NULL` sono quindi
trasparenti: nessuno è stato toccato.

#### ⭐ `p_natura_doc_id` ha `DEFAULT NULL`, non `DEFAULT «FATTURA»`

Il default vero è `FATTURA`, ma si risolve **dentro** la funzione con un
`COALESCE` sulla chiave naturale
([`config.fn_get_natura_doc_fiscale_id`](/dbzero/config/funzioni/fn_get_natura_doc_fiscale_id)).
Un id cablato nella firma sarebbe una **fotografia del catalogo di oggi**: resta
valido — cioè sbagliato in silenzio — dopo un reseed.

#### I due guard nuovi

* natura non risolta → `E_CONFIG_MANCANTE`. Meglio un errore parlante qui che un
  *not-null violation* tre livelli più in basso;
* `fattura_riga_rettificata_id` valorizzata **solo** su una `RETTIFICA`. È
  un'**implicazione**, non un'equivalenza: il vocabolario ammette rettifiche che
  non nascono da una riga di fattura (i conguagli). Il `CHECK` di tabella è la
  rete finale; qui il messaggio dice **quale** parametro è incoerente.

⚠️ **Nessun guard sul segno della quantità**: una rettifica di accredito è
negativa (D-NC-2), ma una futura nota di **debito** sarebbe positiva. Il
predicato resta `= 0`, non `<= 0` — ed è la porta da cui la nota di credito entra
senza una seconda pipeline.

⚠️ Nell'`ON CONFLICT` natura e riga rettificata seguono il chiamante
(`EXCLUDED`), come già `tipo_movimento`. Non serve il `COALESCE` difensivo che
protegge `tipo_doc_fiscale_id`: i `segment_key` non si incrociano — un push
(`ORD:`/`DDT:`) non può atterrare sul segmento di una rettifica (`…#RET:<n>`).

---

### 🔄 rev 2026-10-12 — il link documento → commessa nasce con la riga

(brief-db-annullo-a-valle-riapre-a-monte, D-13 di Tid, `20261012-46`)

Una riga che viene da un **documento spinto in commessa** — sorgente con
`config.sorgenti.scope = 'PUSH_COMMESSA'`: preventivo, ordine, contratto, bolla,
consumi — chiama, prima di scriversi,
[vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente):

* stesso documento, stessa commessa → il link c'è già, niente si riscrive;
* il documento sta in un'**altra commessa aperta** →
  `E_COMMESSA_SORGENTE_ALTRA_COMMESSA`, e la riga non si scrive;
* la sua commessa di prima è **chiusa o annullata** → link nuovo; quello vecchio
  resta come storia.

Fuori dal blocco: le righe senza sorgente (`ONERE`, `RETTIFICA`) e la sorgente
`COMMESSA` (`PIPELINE_MARKER`), che fixture e smoke usano per le righe «della
commessa».

⭐ **Perché qui e non nel backend.** Prima il link lo scriveva il backend, a parte,
prima di questa funzione. La regola «un documento in una sola commessa aperta»
valeva solo se chi scriveva la riga si ricordava del link, e i pgTAP che mandano in
commessa da questa madre non la attraversavano mai: è così che il difetto del
secondo invio dopo l'annullo della commessa è arrivato al collaudo con i test
verdi. D-10: andata e ritorno di uno stesso arco in un posto solo, il DB.

---

{% include-markdown "signature-core.md" %}

### 🔄 rev 2026-10-13 — `tipo_consumo` ritirato

ChangeSet `20261013-16` (con `-17` … `-23` per batch, builder pgTAP e i cinque
lister). Decisione A di Tid, dalla segnalazione BE sugli smoke del 2026-10-13.

* **Perché.** `tipo_consumo` non era una colonna: la funzione lo scriveva solo
  in `meta`, e nessuno lo leggeva. Il vocabolario che pretendeva (`ACCONTO`,
  `CONGUAGLIO`, `STORNO`) non lo produceva nessuna sorgente con un significato:
  preventivi, ordini e DDT mandavano la costante `CONGUAGLIO`, i contratti
  l'erogazione della riga e i consumi `CONSUMO`, che qui erano rifiutati
  (`E_PARAMETRO_INVALIDO`). Il push dei contratti non arrivava in commessa.
  L'erogazione ha già il suo posto: `meta.tipo_erogazione`, scritta dal lister
  dei contratti.
* **Cosa cambia.** Via il parametro `p_tipo_consumo` (era in mezzo alla firma:
  `DROP` + `CREATE`, come nel 2026-08-18), il suo controllo e la chiave in
  `meta`. La chiave si **toglie anche dal meta in ingresso**: il reso
  (`fn_accredita_riga_reso`) ricopia il meta della riga d'origine, e senza la
  sottrazione la chiave rinascerebbe sulle rettifiche.
* **Cosa non cambia.** Le righe già scritte tengono la chiave: sono la
  fotografia di quell'invio, e una bonifica di massa su `commesse_attivita`
  farebbe scattare i trigger «padre attivo», lo storico e l'audit.
* **Chiamanti.** Chi passava `p_tipo_consumo` per nome va ritoccato: il batch,
  il builder `dbops.fn_pgtap_crea_commessa_attivita`, i pgTAP e il backend
  (`CommesseRepository.upsert_attivita`). Il pgTAP che manda un contratto dalla
  madre è `vendite/test-push-contratto-dalla-madre-v1`.

