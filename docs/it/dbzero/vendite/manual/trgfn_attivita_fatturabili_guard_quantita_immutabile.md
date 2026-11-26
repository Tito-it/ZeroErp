## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile()`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — la tabella che protegge
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la commessa madre, di cui la quantità è lo specchio
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_commesse_attivita_guard_quantita_immutabile](/dbzero/vendite/funzioni/trgfn_commesse_attivita_guard_quantita_immutabile) — il gemello sulla commessa
> * [vendite.fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta) — la porta del reset del lotto: la GUC e il proprietario
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

**La quantità di un'attività fatturabile deve specchiare quella della commessa madre.**
Il guard blocca l'`UPDATE` che la porterebbe a un valore *diverso* da quello della riga
`commesse_attivita` collegata.

Non è immutabilità: è **mirror-enforcement**. La differenza conta. Un guard di immutabilità
direbbe «questo valore non si tocca» e romperebbe l'emissione, che la quantità la riscrive a
ogni passata. Qui la regola è più precisa: si può riscrivere quanto si vuole, purché il
valore continui a coincidere con la commessa. L'emit — un upsert che copia
`ca.quantita` — passa **per costruzione**; un `UPDATE` manuale a un valore inventato no.

---

### Aggancio

Trigger `trg_attivita_fatturabili_a10_guard_quantita_immutabile_upd` — fase `_a10_`,
`BEFORE UPDATE OF quantita` su `vendite.attivita_fatturabili`, `FOR EACH ROW`.

---

### Regole applicate

1. **La porta del reset del lotto**: se è aperta, esce subito (sezione qui sotto).
2. Se `commessa_attivita_id IS NULL` → **passa**: senza madre non c'è specchio da imporre.
3. Se la quantità non cambia (`IS NOT DISTINCT FROM OLD`) → passa.
4. Altrimenti legge `quantita` dalla commessa madre e blocca se
   `NEW.quantita IS DISTINCT FROM` quel valore.

---

### ⚠️ L'attività senza commessa madre non è presidiata

Il ramo `commessa_attivita_id IS NULL` è una scelta esplicita, non una dimenticanza: le
attività fatturabili che non nascono da una commessa (import diretti, alimentazioni di altra
origine) non hanno un valore con cui confrontarsi.

Va però saputo, perché disegna il perimetro reale del presidio: **su quelle righe la
quantità resta liberamente modificabile.** Se un giorno una sorgente cominciasse a creare
attività senza `commessa_attivita_id`, quel flusso nascerebbe fuori dal guard — e nessun
errore lo segnalerebbe.

---

### ⚠️ Se la madre sparisce, il confronto diventa `NULL`

Il valore della commessa è letto con `SELECT ... INTO`. Se la riga madre non c'è più — o non
è visibile — la variabile resta `NULL`, e `NEW.quantita IS DISTINCT FROM NULL` è **vero**
per qualunque quantità non nulla: l'`UPDATE` viene bloccato.

È il verso giusto in cui sbagliare (fail-closed), ma il messaggio riporta
`quantita_commessa = null`, che si legge come «la commessa vale zero» e non come «la commessa
non è stata trovata». Nel diagnosticare, quel `null` va interpretato.

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

La stessa porta la legge il gemello sulle commesse. Serve al reset di un lotto, che riporta
indietro le attività.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE` | `UPDATE` che porta `quantita` a un valore diverso da quello della commessa madre |

Sollevato via `script.fn_log_and_raise_error`; context con `id`, `commessa_attivita_id`,
`quantita_new`, `quantita_commessa`.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — con la GUC accesa dall'applicazione
  la porta resta chiusa.

---

### Note di migrazione

* 2026-07-21 — nasce, col mirror-enforcement (brief immutabilità quantità §4a).
* 2026-11-25 — la porta del reset si legge da `vendite.fn_porta_reset_lotto_aperta` e chiede anche
  il proprietario; prima bastava la GUC, che l'applicazione poteva accendere da sé
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7).

---

{% include-markdown "signature-core.md" %}
