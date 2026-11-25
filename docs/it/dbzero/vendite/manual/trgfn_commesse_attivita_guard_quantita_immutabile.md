## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_attivita_guard_quantita_immutabile()`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la tabella che protegge
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — dove la quantità è già uscita
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_quantita_immutabile) — il gemello sulle attività fatturabili
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) — il re-push, che il guard non ferma
> * [vendite.fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta) — la porta del reset del lotto: la GUC e il proprietario
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

**Una riga di commessa già emessa è un fatto, e i fatti non si modificano.** Il guard
blocca l'`UPDATE` della quantità su una riga il cui `stato_emissione` è diverso da
`NON_EMESSA`.

La ragione è contabile, non tecnica: quella quantità è già uscita verso
`attivita_fatturabili` e, da lì, verso un documento. Cambiarla a posteriori farebbe
divergere il documento emesso dalla riga che dichiara di rappresentarlo, senza lasciare
traccia di quando e perché. La correzione si fa **aggiungendo righe** — una rettifica a
quantità negativa — non riscrivendo la storia.

---

### Aggancio

Trigger `trg_commesse_attivita_a10_guard_quantita_immutabile_upd` — fase `_a10_`,
`BEFORE UPDATE OF quantita` su `vendite.commesse_attivita`, `FOR EACH ROW`.

---

### Regole applicate

Blocca quando **entrambe**:

1. `OLD.stato_emissione <> 'NON_EMESSA'` — la riga è già uscita;
2. `NEW.quantita IS DISTINCT FROM OLD.quantita` — la quantità cambia davvero.

Il secondo punto non è formalità: una riscrittura dello **stesso** valore passa. È ciò che
permette all'`ON CONFLICT DO UPDATE` di `fn_upsert_commessa_attivita` di non rompersi quando
ripassa su righe già allineate.

**Il re-push normale non incontra il guard**: agisce su righe `NON_EMESSA`, che la prima
condizione lascia fuori. Non serve nessuna porta nella hot-path.

---

### La porta del reset del lotto

Il guard lascia passare la scrittura quando la **porta del reset del lotto** è aperta. La legge
[`vendite.fn_porta_reset_lotto_aperta`](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta), che
risponde sì solo se la GUC `zeroerp.maintenance_reset_lotto_draft` è accesa **e** chi scrive è il
proprietario della tabella.

La GUC la accende solo la pulizia del lotto,
[`vendite.fn_cleanup_fatture_by_ids`](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids), riservata
al proprietario, e la spegne prima di uscire: la porta è aperta solo mentre la pulizia lavora. ⛔ Per
l'applicazione la porta è sempre chiusa: accendere la GUC da sé e scrivere diretta non apre niente.

Serve al **reset di un lotto**, dove le righe già emesse tornano `NON_EMESSA` e la loro
quantità torna legittimamente modificabile. ⚠️ Mentre la porta è aperta il guard lascia passare
tutto, non solo le righe del lotto: il limite è che la apre solo la pulizia, e solo per la sua
durata.

---

### Il gemello sulle attività fatturabili

`trgfn_attivita_fatturabili_guard_quantita_immutabile` presidia lo **stesso valore un
livello più in basso**, con una logica diversa: là non conta lo stato, conta che la quantità
dell'attività fatturabile continui a **specchiare** quella della commessa madre.

I due si dividono il lavoro così:

* **qui**: la riga emessa non cambia quantità;
* **là**: l'attività fatturabile non si stacca dalla commessa che la genera.

Entrambi leggono la stessa porta del reset del lotto.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE` | `UPDATE` che cambia `quantita` su riga con `stato_emissione <> 'NON_EMESSA'` |

Sollevato via `script.fn_log_and_raise_error`; nel context finiscono `id`, `segment_key`,
`stato_emissione`, `quantita_old` e `quantita_new` — abbastanza per ricostruire il tentativo
senza risalire alla riga.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — con la GUC accesa dall'applicazione
  la porta resta chiusa.

---

### Note di migrazione

* 2026-07-21 — nasce (brief immutabilità quantità §0, §4a).
* 2026-11-25 — la porta del reset si legge da `vendite.fn_porta_reset_lotto_aperta` e chiede anche
  il proprietario; prima bastava la GUC, che l'applicazione poteva accendere da sé
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7).

---

{% include-markdown "signature-core.md" %}
