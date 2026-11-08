## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_preventivi_da_pushare`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> * [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
>
> Approfondimento funzioni:
>
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)

---

### 🎯 Scopo Principale

`vendite.fn_list_preventivi_da_pushare(...)` seleziona le righe preventivo
pronte per il push verso `commesse_attivita`, restituendo un payload completo
per l’handler di acquisizione.

---

### Regole principali

* considera preventivi nello stato di accettazione (`ACCETTATO`, dal lettore
  [`script.fn_stato_accettazione_id`](/dbzero/script/funzioni/fn_stato_accettazione_id)).
  Se il vocabolario non ne marca uno la funzione solleva
  `E_CONFIG_MANCANTE`: non lista mai preventivi in uno stato qualunque. Nessun filtro sulla
  testata: `billing_account_id` e `utility_id` sono `NOT NULL`;
* **predicato di riga dalla vista unica**
  [vw_preventivi_righe_smistabili_commessa](/dbzero/vendite/views/vw_preventivi_righe_smistabili_commessa):
  righe attive con quantità e prezzo validi, natura NULL
  (pregresso → COMMESSA) o `destinazione_tipo='COMMESSA'`, non già EMESSE in
  commessa (idempotenza). La merce (`ORDINE`) è esclusa: va su
  `fn_push_preventivo_a_ordine`;
* costruisce `segment_key` deterministica con `script.fn_segment_key` (`PREVENTIVO:{uid}:R:{riga_id}`);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_preventivo_id` — vedi sezione dedicata
  * `p_righe_ids` — vedi sezione dedicata

---

### Push singolo preventivo (UI-driven)

Il parametro `p_preventivo_id` (tipo `vendite.preventivi.id%TYPE`, default `NULL`) consente
di restringere il risultato al singolo preventivo selezionato dall'utente nel drawer preventivo
(pulsante "Push commessa" di `PreventiviIntegrazione.vue`).

| Valore  | Comportamento                                                          |
|---------|------------------------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato                          |
| `> 0`   | Filtra al preventivo specificato; tutti gli altri filtri in AND        |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO`                           |

**Semantica AND dei filtri:** `p_preventivo_id` si aggiunge in AND agli altri filtri. Se si
passa anche `p_billing_account_id` di un BA diverso da quello del preventivo, si ottengono
0 righe (comportamento atteso: i filtri sono tutti coerenti o il push non avviene).

**Idempotenza:** se il preventivo ha righe già in `commesse_attivita` con `stato_emissione = 'EMESSA'`,
la funzione restituisce 0 righe — coerente con il NOT EXISTS del batch.

---

### Push per sottoinsieme righe (Pannello Smistamento)

Il parametro `p_righe_ids bigint[]` (default `NULL`) consente lo smistamento
**riga per riga** dal Pannello Smistamento, simmetrico al ramo ordine
(`fn_push_preventivo_a_ordine.p_righe_ids`).

| Valore | Comportamento |
|--------|---------------|
| `NULL` | Comportamento invariato (batch e push-tutto) |
| valorizzato | Filtro aggiuntivo `pr.id = ANY(p_righe_ids)`; **richiede `p_preventivo_id`** |
| valorizzato senza `p_preventivo_id` | Guard: solleva `E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO` |

Le righe del sottoinsieme **non eleggibili** (già in commessa, natura ORDINE,
non attive) sono **skippate in silenzio** — coerente con D5: il "tutte già
allocate → errore semantico" resta a carico del BE con il count eleggibili.

> ⚠️ Una sola firma: un overload a 4 parametri sarebbe ambiguo (tutti i parametri hanno
> DEFAULT). Il parametro è in coda con DEFAULT, e le chiamate posizionali restano valide.

---

### Competenza e periodo

I campi di competenza alimentano `commesse_attivita` (colonne **NOT NULL**) e
sono derivati così:

| Campo | Derivazione | Note |
| --- | --- | --- |
| `competenza_dal` | `COALESCE(validita_dal, competenza_mese, data)` | mai NULL |
| `competenza_al` | `GREATEST(competenza_dal, COALESCE(validita_al, validita_dal, competenza_mese, data))` | garantisce `dal ≤ al` |
| `competenza_mese` | `COALESCE(competenza_mese, date_trunc('month', COALESCE(validita_dal, data)))` | la **policy** `preventivi.competenza_mese` vince sul derivato |

* **`competenza_dal/al`** = periodo attività (validità del preventivo o, in sua
  mancanza, data documento). Un preventivo ACCETTATO **senza validità** è
  legittimo: i fallback evitano il crash NOT NULL sul push.
* **`competenza_mese`** = mese di fatturazione. Se la colonna di policy
  `preventivi.competenza_mese` è valorizzata (accettazione DIFFERITA, o handler
  pratica `vendita.push_preventivo`), è **autorevole**; altrimenti fallback al
  mese derivato da validità/data (pregresso).
* Periodo e mese di fatturazione sono **indipendenti**: una riga DIFFERITA può
  avere periodo a giugno e mese di fatturazione a settembre.
* Il filtro `p_competenza_mese` usa la **stessa espressione** di `competenza_mese`,
  così lista e filtro restano coerenti.

---

### 📦 Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`preventivo_id`, `preventivo_uid`, `riga_id`),
* dati commessa/competenza,
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* provenienza (`sorgente_tipo_id`, `sorgente_chiave`, `segment_key`): `sorgente_chiave` è l'uid
  del preventivo in testo, e la madre `fn_upsert_commessa_attivita` la traduce con
  `script.fn_sorgente_chiave` nella colonna del `key_selector` del tipo (`sorgente_uid`, perché
  il preventivo si riconosce dall'uid); `riga_id` arriva in commessa come la riga della provenienza (`sorgente_riga`),
* `meta` tecnico per il push.

---

### Note di migrazione

* 2026-05-10 — arriva `p_preventivo_id`.
* 2026-06-10 — competenza e periodo derivati con i ripieghi.
* 2026-06-12 — arriva `p_righe_ids`, e il predicato di riga passa alla vista unica; la firma a 4
  parametri si ritira (brief-db-smistamento-preventivi, C).
* 2026-10-10 — il filtro sullo stato di accettazione non cade più con `IS NULL OR`, e il filtro di
  «testata completa» si ritira (brief-db-istanza-nasce-col-ba-residui, D-2 e R-3).
* 2026-10-20 — la `segment_key` la compone `script.fn_segment_key` col codice del tipo, al posto
  del prefisso `PREV:` (brief-db-grammatica-unica-documenti).
* 2026-10-31 — lo stato di accettazione lo dà `script.fn_stato_accettazione_id`
  (`E_CONFIG_MANCANTE` al posto di `E_CODICE`).
* 2026-11-07 — `riga_id` arriva in commessa come `sorgente_riga` (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — la colonna d'uscita `sorgente_uid` diventa `sorgente_chiave`, la chiave del
  documento in testo che la madre traduce (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
