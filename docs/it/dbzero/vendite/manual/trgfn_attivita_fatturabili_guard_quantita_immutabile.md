## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
>
Approfondimento funzioni:
> • [vendite.trgfn_commesse_attivita_guard_quantita_immutabile](/dbzero/vendite/funzioni/trgfn_commesse_attivita_guard_quantita_immutabile)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

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

1. **Bypass**: se la GUC `zeroerp.maintenance_reset_lotto_draft` vale `1`/`true`/`on`/`yes`,
   esce subito.
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

### Il bypass di manutenzione

Stessa GUC del gemello sulle commesse:

```sql
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'on';
```

Serve al reset di un lotto a DRAFT. Vale la stessa avvertenza: aperta la porta, lo specchio
non è più imposto per tutta la transazione. Sempre `SET LOCAL`, mai di sessione.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE` | `UPDATE` che porta `quantita` a un valore diverso da quello della commessa madre |

Sollevato via `script.fn_log_and_raise_error`; context con `id`, `commessa_attivita_id`,
`quantita_new`, `quantita_commessa`.

---

### Riferimenti

Brief *immutabilità quantità* §4a — mirror-enforcement (2026-07-21).

---

{% include-markdown "signature-core.md" %}
