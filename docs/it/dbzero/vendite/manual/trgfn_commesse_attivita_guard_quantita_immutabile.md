## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_attivita_guard_quantita_immutabile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
>
Approfondimento funzioni:
> • [vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_quantita_immutabile)
> • [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

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
condizione lascia fuori. Non serve nessun bypass nella hot-path.

---

### Il bypass di manutenzione

```sql
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'on';
```

Con questa GUC valorizzata (`1`, `true`, `on`, `yes`) il guard esce in testa e lascia
passare tutto. Serve al **reset di un lotto a DRAFT**, dove le righe già emesse vanno
riportate indietro e la loro quantità torna legittimamente modificabile.

⚠️ È una porta di servizio reale: aperta la GUC, l'immutabilità **non esiste più** per
l'intera transazione, su ogni riga toccata — non solo su quelle del lotto che si sta
resettando. Va usata con `SET LOCAL` (mai `SET` di sessione) e sul perimetro più stretto
possibile.

---

### Il gemello sulle attività fatturabili

`trgfn_attivita_fatturabili_guard_quantita_immutabile` presidia lo **stesso valore un
livello più in basso**, con una logica diversa: là non conta lo stato, conta che la quantità
dell'attività fatturabile continui a **specchiare** quella della commessa madre.

I due si dividono il lavoro così:

* **qui**: la riga emessa non cambia quantità;
* **là**: l'attività fatturabile non si stacca dalla commessa che la genera.

Entrambi riconoscono la stessa GUC di bypass.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE` | `UPDATE` che cambia `quantita` su riga con `stato_emissione <> 'NON_EMESSA'` |

Sollevato via `script.fn_log_and_raise_error`; nel context finiscono `id`, `segment_key`,
`stato_emissione`, `quantita_old` e `quantita_new` — abbastanza per ricostruire il tentativo
senza risalire alla riga.

---

### Riferimenti

Brief *immutabilità quantità* §0 / §4a (2026-07-21).

---

{% include-markdown "signature-core.md" %}
