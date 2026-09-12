## 📘 Documentazione Concettuale – Funzione `vendite.fn_lotto_da_emit_batch`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
>
Approfondimenti funzioni:
>
[vendite.fn_classe_emittibilita_per_giro](/dbzero/vendite/manual/fn_classe_emittibilita_per_giro) ·
[vendite.fn_list_commesse_emittibili](/dbzero/vendite/manual/fn_list_commesse_emittibili) ·
[vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/manual/fn_emit_attivita_fatturabili_da_commessa)

---
### 🎯 Scopo Principale
(latest review 12-09-2026)

Dal **marchio del giro** al **lotto** che sta girando. Il pull riceve l'identità
del giro come `p_emit_batch_id` — il marchio che scrive su ogni riga che
consegna — e il lotto corrente si risolve da
`vendite.fatturazione_lotti.lock_batch_id`, che ha un `UNIQUE`: al più una riga.

È una riga sola di SQL, ed esiste come funzione per una ragione sola: la
leggono **due** funzioni (la discovery e l'emit), e fino al 12-09-2026 stava
inline in una e **mancava** nell'altra. Una risoluzione che deve essere identica
in due posti vive meglio in uno.

---

### Che cosa risponde

| Ingresso | Uscita | Che cosa significa per chi chiama |
| --- | --- | --- |
| il `lock_batch_id` di un lotto | l'`id` del lotto | il giro ha un'identità: l'auto-esclusione del proprio lotto si applica |
| `NULL` | `NULL` | chiamante fuori pipeline (backfill, riconciliazione): **nessuna** auto-esclusione |
| un marchio che non corrisponde a nessun lotto | `NULL` | lotto sparito: stessa risposta prudente |
| il marchio di un lotto **fuori dal perimetro RLS** di chi esegue | `NULL` | la funzione è `SECURITY INVOKER`: chi non vede il lotto non ne ottiene l'identità — fail-closed |

---

### Esempio d'uso

```sql
SELECT vendite.fn_lotto_da_emit_batch('01a094ed-9aff-74f1-9cca-69a7a9a9f556');  -- → 13338
```

Origine: `docs/it/dev/work-in-progress/brief-db-rilancio-step-non-rivede-le-proprie-commesse.md` (D1);
changeSet `20260912-13`.

---

{% include-markdown "signature-core.md" %}
