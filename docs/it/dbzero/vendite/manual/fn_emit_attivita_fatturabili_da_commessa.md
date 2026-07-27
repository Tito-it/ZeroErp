## 📘 Documentazione Concettuale – Funzione `vendite.fn_emit_attivita_fatturabili_da_commessa`
### 🎯 Scopo Principale
(latest review 16-06-2026)
Esegue il pull da `commesse_attivita` verso `attivita_fatturabili` (step 0 pipeline attività fatturabili).

---

### Regole applicate

* La ROOT source della commessa e` obbligatoria (`commesse_sorgenti`).
* La sorgente delle righe AF e` sempre `COMMESSA`.
* `segment_key` viene mappata deterministicamente in UUID per `attivita_fatturabili.sorgente_uid`.
* `attivita_fatturabili.sorgente_riga` viene valorizzato con `commesse_attivita.id`
  (coerenza con trigger polimorfo `key_selector='id'`).
* Idempotenza gestita tramite chiave sorgente (`COMMESSA + segment_key-hash`).
* Se trova una riga AF gia` fatturata, blocca l'aggiornamento con errore.
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

---

### Output

Ritorna contatori:

* `total_candidate`
* `inserted_rows`
* `updated_rows`
* `skipped_rows`

---

---

### Emissione mirata: `p_gruppi` (rev 2026-07-27)

Parametro `text[]`, default `NULL`. Restringe l'emissione ai soli **gruppi
fatturabili** richiesti — la chiave arriva da
[`fn_build_gruppo_fatturabile_key`](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key),
mai ricostruita a mano.

| Valore | Comportamento |
|---|---|
| `NULL` *(default)* | nessuna restrizione: **identico** al comportamento storico |
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

> **Firma cambiata**: la versione a 3 argomenti è stata droppata nello stesso
> changeSet. Un parametro con default su `RETURNS TABLE` crea un overload
> ambiguo, e ogni chiamata che omette `p_gruppi` fallirebbe con *function is not
> unique*.

{% include-markdown "signature-core.md" %}
