## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_ddt_da_pushare`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> * [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> * [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
>
> Approfondimento funzioni:
>
> * [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
> * [vendite.fn_ddt_push_diagnosi](/dbzero/vendite/funzioni/fn_ddt_push_diagnosi) — **la fonte unica dell'eleggibilità**: questo lister ne deriva
> * [vendite.fn_partite_merce](/dbzero/vendite/funzioni/fn_partite_merce) — la partita, per documento

---

### 🎯 Scopo Principale

`vendite.fn_list_ddt_da_pushare(...)` seleziona le righe DDT pronte per
il push verso `commesse_attivita`, restituendo un payload completo per
l'handler di acquisizione.

⭐ **Non decide chi è eleggibile.** L'eleggibilità sta scritta in **un** posto,
[`fn_ddt_push_diagnosi`](/dbzero/vendite/funzioni/fn_ddt_push_diagnosi): questo
lister ne **deriva** — `FROM fn_ddt_push_diagnosi(p_ddt_id) WHERE motivo IS
NULL` — e aggiunge solo ciò che è suo: i filtri di chiamata (competenza, BA,
limit) e la proiezione dei campi per la pipeline. Il BA, la riga d'ordine
sorgente e la **dose** (`quantita_push`) li riceve dalla diagnosi, non li
ricalcola. Le regole qui sotto descrivono *cosa* rende una riga eleggibile;
*dove* sono scritte è la diagnosi, rank per rank.

⛔ Un predicato di eleggibilità nuovo si aggiunge alla diagnosi come rank, non
qui: qui non c'è più un posto dove metterlo.

Supporta **due modalita`**:
- **DDT da ordine**: fatturazione delegata dall'ordine via `fatturazione_trigger`
- **DDT autonomo**: DDT con billing_account proprio, senza ordine sorgente

---

### Regole principali

**Caso A — DDT da ordine (fulfillment esiste):**

* l'ordine sorgente ha `fatturazione_trigger IN ('SPEDITO','CONSEGNATO')`;
* lo stato DDT deve corrispondere al trigger dell'ordine;
* prezzo: `COALESCE(ddt_righe.prezzo_unitario, ordini_righe.prezzo_unitario)`;
* billing_account: `COALESCE(ddt.billing_account_id, ordini.billing_account_id)`.

**Caso B — DDT autonomo (nessun fulfillment):**

* `ddt.billing_account_id IS NOT NULL` (obbligatorio);
* stato DDT IN (`SPEDITO`, `CONSEGNATO`);
* prezzo da `ddt_righe.prezzo_unitario` (puo` essere NULL; handler risolve).

**Regole comuni:**

* riga attiva (`attivo = TRUE`);
* esclude segmenti gia` instradati in `commesse_attivita` (`segment` diverso da
  `LIBERA`: idempotenza batch);
* la `quantita` proiettata e` la **dose** della diagnosi — `GREATEST(0,
  LEAST(quantita della riga, differenza della partita))` — e una riga con dose
  zero non esce (`DDT_CONTATORE`); `qta_operativa` scala in proporzione;
* costruisce `segment_key` deterministica con `script.fn_segment_key` (`DDT_VENDITA:{uid}:R:{riga_id}`);
* `prezzo_bloccato = TRUE` se prezzo_snapshot presente;
* sorgente tipo: `DDT_VENDITA`, letto da `config.sorgenti` per `codice_interno`;
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_ddt_id` — vedi sezione dedicata

---

### Push singolo DDT (estensione coordinata)

Il parametro `p_ddt_id` (tipo `vendite.ddt.id%TYPE`, default `NULL`) consente
di restringere il risultato a un singolo DDT.

| Valore  | Comportamento                                            |
|---------|----------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato            |
| `> 0`   | Filtra al DDT specificato; tutti gli altri filtri in AND |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO`             |

Estensione coordinata con le altre 4 `fn_list_*_da_pushare` per uniformare
la signature al client Python `CommesseRepository.fetch_pushable_rows` (4 args posizionali).

---

### Relazione con fn_list_ordini_da_pushare

Le due funzioni sono **mutuamente esclusive** per design:

| fatturazione_trigger | Chi pusha | Funzione |
|---------------------|-----------|----------|
| `CONFERMATO` | Ordine | `fn_list_ordini_da_pushare` |
| `SPEDITO` | DDT alla spedizione | `fn_list_ddt_da_pushare` |
| `CONSEGNATO` | DDT alla consegna | `fn_list_ddt_da_pushare` |

Il campo `fatturazione_trigger` su `vendite.ordini` (default da
`anagrafiche.billing_account.fatturazione_ordini`) determina quale
funzione gestisce il push a commessa.

---

### Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`ddt_id`, `ddt_uid`, `riga_id`),
* dati commessa/competenza (risolti da DDT o ordine sorgente),
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* provenienza (`sorgente_tipo_id`, `sorgente_chiave`, `segment_key`): `sorgente_chiave` è l'uid
  della bolla in testo, e la madre `fn_upsert_commessa_attivita` la traduce con
  `script.fn_sorgente_chiave` nella colonna del `key_selector` del tipo (`sorgente_id`, perché la
  bolla si riconosce dall'id); `riga_id` arriva in commessa come la riga della provenienza
  (`sorgente_riga`). La provenienza è sempre la bolla, anche quando la riga nasce da un ordine:
  l'ordine resta in `meta`,
* `meta` tecnico con riferimento ordine sorgente (se presente).

---

### `fatturazione_immediata`: dalla costante alla colonna

Fino al 2026-07-27 questa funzione proiettava la **costante `FALSE`** nello slot
`fatturazione_immediata`: il contratto della `RETURNS TABLE` era simmetrico a
quello dei preventivi, ma il **dato** no. Conseguenza pratica: un DDT non
poteva mai finire sulla corsia immediata.

Dal changeset `20260727-06` il valore è letto dalla **colonna reale**
`vendite.ddt.fatturazione_immediata` (aggiunta da `20260727-03`). Il valore proiettato qui viaggia fino a
`fn_get_or_create_commessa`, dove è **parte della chiave di dedup**: è così che
il flag separa fisicamente le due corsie (commesse distinte → lotti distinti →
`GIORNALIERO` che numera da solo *vs* `MASSIVO` che si ferma a `EMESSA`).

⚠️ **`prezzo_bloccato` NON è stato toccato** e non va toccato: qui vale
`(COALESCE(dr.prezzo, src.prezzo) IS NOT NULL)`, indipendente dal flag. L'accoppiamento
`prezzo_bloccato = COALESCE(fatturazione_immediata, false)` esiste **solo** in
`fn_list_preventivi_da_pushare`. Copiare qui quella riga cambierebbe in silenzio
il comportamento di pricing.

Presidio a valle: dopo il push il flag non è più modificabile sul documento
([`trgfn_guard_fatturazione_immediata_immutabile`](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile)).

Brief: `brief-db-emissione-fattura-per-documento-sorgente` PARTE B (step B3).

---

### 🔄 rev 2026-09-21 — la partita si legge per documento (D14, quarta leva)

ChangeSet `20260921-23`. Il lister leggeva `vw_partite_merce` in `JOIN`, e la
vista calcola le partite di **tutti** i DDT anche quando `p_ddt_id` ne chiede
uno — cioè a ogni apertura del drawer, dalla capability. Ora legge
[`fn_partite_merce`](/dbzero/vendite/funzioni/fn_partite_merce) con il DDT
chiesto come seme (`ARRAY[p_ddt_id]`): la **chiusura** del documento. Con
`p_ddt_id NULL` (la lista del push, il cockpit) il seme è `NULL` = tutte,
com'era. Stessi predicati, stesso contratto verso la pipeline, stessi numeri: la
vista è la proiezione della stessa funzione.

⚠️ Il seme è un `CASE` senza colonne: in piano custom si piega a un letterale,
in piano generico (dalla sesta esecuzione plpgsql) la funzione lo riceve come
parametro e i suoi rami in `UNION ALL` lo trattano da *One-Time Filter* — mai
una scansione intera (brief `brief-db-partita-merce-per-documento` §2-bis.2).

---

### 🔄 rev 2026-09-21 — il lister deriva dalla diagnosi (D14, seconda leva, forma B2)

ChangeSet `20260921-33` (con `20260921-32`, la diagnosi, e `20260921-34`, la
capability). Fino a qui lister e diagnosi erano **due copie** della stessa
regola, tenute uguali da un pgTAP che confrontava le righe vive — verde per
sottrazione su un database da zero. Ora la `cand` del lister non ripete più
nessun predicato: parte dalla diagnosi (`motivo IS NULL`), rimette in `JOIN`
`ddt` / `ddt_righe` / `articoli` / `billing_account` / `ordini_righe` /
`ordini` **per la proiezione** (per chiave, dai fatti che la diagnosi espone),
e applica i soli filtri di chiamata. Contratto verso la pipeline invariato
(firma, 31 campi, `ORDER BY`, `LIMIT`, il guard su `p_ddt_id <= 0`); stesse
righe e stesse quantità per costruzione.

Il presidio non è più un'equivalenza da tenere:
`test-fn-available-actions-ddt-reason-catch-all-v1` costruisce l'eleggibile e
lo legge a tre voci (diagnosi, lister, capability), e pinna la **forma** — il
corpo del lister nomina la diagnosi e non `fn_partite_merce` né
`fn_get_stato_push_segment`.

### ⛔ Si pianifica una volta (`plan_cache_mode`, changeSet 20261010-84)

La funzione porta `SET plan_cache_mode = force_generic_plan`: chiama con un
parametro la diagnosi del push, una funzione SQL che si incorpora in una query
grande, e in modo `auto` la plancache la ripianificava a ogni chiamata.
⚠️ È una proprietà **invisibile nel corpo**: un `CREATE OR REPLACE` che non la
ripete la perde, senza errore e con gli stessi risultati. Presidio:
`db/pgtap/script/test-plan-cache-mode-piano-generico-v1.sql`.

### La riga-onere va in commessa come ONERE

Dal `20261103-40` (brief-db-addebito-trasporto-ordine §8.1, K-1) la riga-onere della bolla
(`script.fn_natura_e_merce` falso sulla natura congelata) esce con `tipo_movimento = 'ONERE'` e con la
causale dell'articolo nella colonna **nuova** `causale_onere_id`, in coda (NULL sulla merce); la
sorgente è la bolla. Chi è eleggibile e la dose li dice ancora la diagnosi, che ha il ramo dell'onere
(niente partita merce, dose = quantità della riga): qui la natura è solo proiezione. RETURNS TABLE
cambiato: DROP + CREATE, `plan_cache_mode` ridichiarato.

⚠️ Il backend deve passare `causale_onere_id` alla madre (`p_causale_onere_id`), o la riga ONERE si
rifiuta (`E_PARAMETRO_INVALIDO`).

---

### Note di migrazione

* 2026-10-20 — la `segment_key` la compone `script.fn_segment_key` col codice del tipo, al posto
  del prefisso `DDT:` (brief-db-grammatica-unica-documenti).
* 2026-11-07 — `riga_id` arriva in commessa come `sorgente_riga` (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — la colonna d'uscita `sorgente_uid` diventa `sorgente_chiave`, la chiave del
  documento in testo che la madre traduce (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
