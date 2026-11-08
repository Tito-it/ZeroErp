## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_smistamento_righe`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) · [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) — il documento e le sue righe
> * [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) — il ramo merce
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) · [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — il ramo commessa
>
> Approfondimento viste:
>
> * [vendite.vw_preventivi_smistamento](/dbzero/vendite/views/vw_preventivi_smistamento) — l'aggregata
> * [vendite.vw_preventivi_righe_smistabili_commessa](/dbzero/vendite/views/vw_preventivi_righe_smistabili_commessa) · [vendite.vw_preventivi_righe_smistabili_ordine](/dbzero/vendite/views/vw_preventivi_righe_smistabili_ordine) — che cosa resta da smistare
>
> Approfondimento funzioni:
>
> * [script.fn_segment_key](/dbzero/script/funzioni/fn_segment_key) — la chiave del push della riga
> * [script.fn_get_stato_push_segment](/dbzero/script/funzioni/fn_get_stato_push_segment) — il classificatore del segmento

---

### 🎯 Scopo Principale

La fonte dati del **Pannello Smistamento**: una riga per ogni riga **attiva** del preventivo, con la natura, la destinazione e lo **stato di smistamento** autorevole per l'interfaccia. `stato_smistamento` è l'unica verità: non ci sono flag booleani accanto.

---

### Colonne chiave

| Campo | Significato |
| --- | --- |
| `natura_vendita_id`, `natura_vendita_codice` | La natura della riga (fotografia di riga) |
| `destinazione_tipo` | La destinazione **effettiva**: quella della natura, `COMMESSA` se la natura non la dice — la stessa convenzione di `fn_list_preventivi_da_pushare` |
| `ordine_riga_id`, `ordine_id`, `ordine_numero` | Il ramo merce: la riga d'ordine generata (via `ordini_righe.preventivo_riga_id`, unico → nessuna moltiplicazione) |
| `stato_smistamento` | Lo stato autorevole: `RESIDUA` / `A_ORDINE` / `IN_COMMESSA` / `EMESSA_AF` / `FATTURATA` |

---

### Come si decide `stato_smistamento`

Il ramo commessa si riconosce dal **segmento** della riga: la chiave del push che
`script.fn_segment_key` costruisce per il tipo `PREVENTIVO`, l'uid del preventivo e l'id della riga.
Valutazione in cascata (vince il primo vero):

1. `FATTURATA` — una riga di commessa del segmento, non annullata, ha un'attività fatturabile con la
   riga di fattura;
2. `EMESSA_AF` — una riga di commessa del segmento, non annullata, ha un'attività fatturabile;
3. `IN_COMMESSA` — il segmento non è `LIBERA` per `script.fn_get_stato_push_segment`: la riga è già
   mandata in commessa, anche se non ancora emessa. Una riga di commessa `ANNULLATA` (commessa
   annullata) non conta, e la riga di preventivo torna `RESIDUA`;
4. `A_ORDINE` — la riga ha generato una riga d'ordine;
5. `RESIDUA` — non smistata su alcun ramo.

L'attività fatturabile si trova **dalla riga di commessa**, con la sua FK `commessa_attivita_id`: la
provenienza dell'attività è quella della riga di commessa, e l'attività non ne ha una sua.

Gli stati 1–3 sono progressivi sul ramo commessa; `A_ORDINE` è lo stato finale del ramo merce (la
fatturazione della merce segue il ciclo ordine → bolla).

---

### Note operative

* `security_invoker = on`: la vista applica le policy di chi la interroga.
* I rami commessa e attività fatturabile sono valutati con `EXISTS`: niente moltiplicazioni da
  segmenti o righe ripetute.
* Solo righe `attivo IS TRUE`.
* Test: `db/pgtap/vendite/test-vw-preventivi-smistamento-v1.sql`.

---

### Note di migrazione

* 2026-06-12 — prende il posto di `vw_preventivi_stato_fatturazione_righe`, con la natura; i flag
  `in_commessa`, `emessa_af`, `fatturata` si ritirano (brief-db-smistamento-preventivi).
* 2026-10-12 — `IN_COMMESSA` lo dice il classificatore del segmento: prima contava solo la riga
  emessa, e una riga mandata e non emessa risultava `RESIDUA` (brief-db-annullo-a-valle-riapre-a-monte, D-5).
* 2026-10-20 — la chiave del segmento la costruisce `script.fn_segment_key`, col codice del tipo
  `PREVENTIVO` (brief-db-grammatica-unica-documenti).
* 2026-11-07 — `FATTURATA` ed `EMESSA_AF` cercano l'attività fatturabile dalla riga di commessa del
  segmento; prima dalla provenienza dell'attività, che si ritira (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
