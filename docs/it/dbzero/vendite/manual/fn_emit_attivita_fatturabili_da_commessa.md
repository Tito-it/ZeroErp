## 📘 Documentazione Concettuale – Funzione `vendite.fn_emit_attivita_fatturabili_da_commessa`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le righe da emettere
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — le attività fatturabili prodotte
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti) — la sorgente ROOT, obbligatoria
>
> Approfondimento viste:
>
> * [vendite.vw_commesse_attivita_emittibilita](/dbzero/vendite/views/vw_commesse_attivita_emittibilita) — la classe d'emittibilità di ogni riga
>
> Approfondimento funzioni:
>
> * [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key) — la chiave dei gruppi di `p_gruppi`
> * [vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili) — il filtro sulle attività già esistenti

---

### 🎯 Scopo Principale

Esegue il pull da `commesse_attivita` verso `attivita_fatturabili` (step 0 della pipeline delle
attività fatturabili), e restituisce i contatori delle righe candidate, inserite, aggiornate e
saltate.

---

### Regole applicate

* La ROOT source della commessa è obbligatoria (`commesse_sorgenti`): senza,
  `E_VALORE_MANCANTE`.
* **Una attività fatturabile per riga di commessa**: l'attività punta la riga con la FK
  `commessa_attivita_id` (NOT NULL e unica), e la sua provenienza è quella della riga di
  commessa. L'attività non ha colonne `sorgente_*` proprie.
* **Idempotenza sulla FK**: la riga già emessa si ritrova per `commessa_attivita_id`, non per la
  `segment_key` (che può cambiare forma sotto una riga già emessa); un secondo giro aggiorna
  l'attività invece di crearne un'altra.
* Se trova un'attività già fatturata, blocca l'aggiornamento con `E_RIGA_GIA_FATTURATA`.
* Propaga `commessa_id`, `commessa_attivita_id` e `prezzo_bloccato`.
* Propaga lo **snapshot audit pricing v5** (8 colonne) 1:1 da `commesse_attivita`:
  `prezzo_base_snapshot`, `origine_prezzo`, `tipo_variazione_applicata`,
  `valore_variazione_applicata`, `promo_id`, `contratto_id`,
  `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`.
  CHECK ed FK sono speculari tra le due tabelle, quindi il trasporto è diretto
  (la promo non è disattivabile finché referenziata dalla commessa, vedi guard
  `trgfn_prevent_deactivate_if_children`). Così l'audit di derivazione del prezzo
  raggiunge il livello di emissione, non solo `commesse_attivita`.
* Nel ramo UPDATE (resume di una riga AF non ancora fatturata) le 8 colonne audit
  vengono **rinfrescate** dalla riga commessa, coerentemente con `prezzo_unitario`/
  `prezzo_snapshot` (lo snapshot di emissione resta allineato finché non è fatturato).
* Aggiorna `commesse_attivita.stato_emissione = 'EMESSA'` per le righe emesse.
* **Quali righe**: si legge la **classe** da
  [vw_commesse_attivita_emittibilita](/dbzero/vendite/views/vw_commesse_attivita_emittibilita),
  **vista dal giro** con [fn_classe_emittibilita_per_giro](/dbzero/vendite/funzioni/fn_classe_emittibilita_per_giro):
  `PRONTA` entra; `TRATTENUTA` soltanto dal lotto corrente
  ([fn_lotto_da_emit_batch](/dbzero/vendite/funzioni/fn_lotto_da_emit_batch)`(p_emit_batch_id)`)
  è `PRONTA` e entra — è il proprio documento di un tentativo fallito, da
  riprendere al rilancio; trattenuta da un **altro** lotto in gioco resta fuori;
  `NON_APPROVATA`/`RIFIUTATA` solo con `p_only_approved = false`.
  ⭐ L'auto-esclusione del proprio lotto **non è scritta qui**: vive nell'helper, la stessa
  riga che legge la discovery
  ([fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili)).
  Presidio: `test-pull-non-prende-trattenuti-v1.sql` (P-5, P-5-bis, P-5-ter).

---

### Emissione mirata: `p_gruppi`

Parametro `text[]`, default `NULL`. Restringe l'emissione ai soli **gruppi
fatturabili** richiesti — la chiave arriva da
[`fn_build_gruppo_fatturabile_key`](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key),
mai ricostruita a mano.

| Valore | Comportamento |
|---|---|
| `NULL` *(default)* | nessuna restrizione |
| `'{}'` | richiesta vuota → zero righe |
| `{...}` | solo le righe di quei gruppi; chiave inesistente → zero righe, **nessun errore** |

**Il problema che chiude.** Questa funzione cicla *tutte* le righe `NON_EMESSA`
della commessa e mette `stato_emissione='EMESSA'` su ognuna. La commessa è
multi-sorgente: chiedere «fattura solo il preventivo» e far girare il pull non
filtrato porterebbe fuori da «Da emettere» anche le righe del contratto,
trasformandole in attività fatturabili orfane.

⚠️ **Filtrare qui NON basta.** Le attività fatturabili **già esistenti** — residui
di un giro interrotto, di un reset a bozza o del giro schedulato — le filtra
[`fn_select_attivita_fatturabili`](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili).
I due filtri lavorano su assi diversi e servono entrambi.

---

### Propaga anche natura e riga rettificata

Due colonne della propagazione 1:1 da `commesse_attivita` ad
`attivita_fatturabili`, sullo stesso modello di `tipo_movimento`:

* `natura_doc_id`
* `fattura_riga_rettificata_id`

⭐ **La natura deve arrivare fino alla TESTATA** — è lì che il builder XML della
FatturaPA chiederà se sta trasmettendo un TD01 o un TD04. Fermarla qui avrebbe
lasciato la chiave documento senza nulla da separare, e **fatture e note di
credito finirebbero sulla stessa testata**.

---

### Note di migrazione

* 2026-07-27 — arriva `p_gruppi`; la versione a 3 argomenti si ritira nello stesso changeSet, perché
  un parametro con default su `RETURNS TABLE` avrebbe creato un overload ambiguo
  (brief-db-emissione-fattura-per-documento-sorgente).
* 2026-08-18 — propaga `natura_doc_id` e `fattura_riga_rettificata_id`
  (brief-design-note-credito-resi, N1b e N5).
* 2026-09-12 — l'auto-esclusione del proprio lotto passa all'helper condiviso con la discovery:
  le due copie si erano sfilate, e al rilancio di un pull fallito la discovery scartava i propri
  documenti (brief-db-rilancio-step-non-rivede-le-proprie-commesse).
* 2026-11-07 — l'attività fatturabile non ha più una provenienza propria: prima la funzione
  scriveva `sorgente_tipo_id = COMMESSA`, un uuid ricavato dalla `segment_key` in `sorgente_uid` e
  l'id della riga in `sorgente_riga`, e ritrovava la riga emessa da quella chiave. Ora la ritrova
  per `commessa_attivita_id` (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
