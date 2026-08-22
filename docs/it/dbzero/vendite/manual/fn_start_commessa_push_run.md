## 📘 Documentazione Concettuale – Funzione `vendite.fn_start_commessa_push_run`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_push_log](/dbzero/vendite/tabelle/commesse_push_log)  
>
**La funzione che chiude ciò che questa apre:**
>
• [vendite.fn_close_commessa_push_run](/dbzero/vendite/funzioni/fn_close_commessa_push_run)  
>
### 🎯 Scopo Principale
`vendite.fn_start_commessa_push_run` **apre** un giro dell'orchestratore push:
scrive la riga in `commesse_push_log` all'inizio della corsa, in stato
`IN_ESECUZIONE`, e ne restituisce l'identificativo. Quell'identificativo è ciò
che il chiamante conserva per chiudere il giro quando ha finito.

---

### Perché la riga nasce all'inizio

Fino al 2026-08-22 il giro veniva registrato **alla fine**. Sembra la scelta
naturale — si scrive ciò che è successo — e costava due cose:

* l'evento d'avvio non aveva niente da citare, e scriveva un identificativo che
  non esisteva ancora;
* ⭐ **un giro interrotto spariva**: moriva a metà e non lasciava nessuna riga.

Aprendo in testa, la riga rimasta `IN_ESECUZIONE` diventa l'unica prova che
qualcosa è partito e non è tornato.

---

### Regole principali

* Scrive `stato = 'IN_ESECUZIONE'`, `run_at = now()`, `risultato = {}`.
* Tutti i parametri sono facoltativi: `dry_run` (default falso), `source_types`
  (gli handler previsti) e `correlation_id` (l'identità del giro).
* ⛔ **Nessun controllo che possa rifiutare l'apertura.** Un diario che si apre
  non ha niente da verificare, e un rifiuto qui impedirebbe a un giro di partire
  per un difetto dell'appunto che lo registra.
* ⚠️ `correlation_id` resta vuoto se il chiamante non lo passa, e **non viene
  inventato**: un identificativo coniato qui non lo conoscerebbe nessun altro
  registro, quindi non ricucirebbe niente. Un buco dichiarato si conta; un filo
  che non lega sembra un filo.

---

### Esempio d'uso

```sql
-- 1) si apre il giro e si tiene l'identificativo
SELECT vendite.fn_start_commessa_push_run(
  p_dry_run        => false,
  p_source_types   => ARRAY['HandlerPreventivi', 'HandlerOrdini'],
  p_correlation_id => '0198f2c1-2f9c-7a41-9c33-1f0a5b7c9e10'::uuid
);

-- 2) …la corsa fa il suo lavoro…

-- 3) e alla fine si chiude, citando quell'identificativo
SELECT vendite.fn_close_commessa_push_run(
  p_id        => 1234,
  p_stato     => 'COMPLETATO',
  p_risultato => '{"HandlerPreventivi": {"created": 12}}'::jsonb,
  p_durata_ms => 842
);
```

---

{% include-markdown "signature-core.md" %}
