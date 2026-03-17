## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_guard_fatturato`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
>
**Approfondimento funzioni:**
>
• [vendite.trgfn_attivita_fatturabili_normalize](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_normalize)  
> • [vendite.trgfn_attivita_fatturabili_guard_fonte](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_fonte)  
>
🎯 Scopo Principale

(latest review 26-01-2026)
La funzione **`vendite.trgfn_attivita_fatturabili_guard_fatturato()`** blocca
modifiche o cancellazioni di righe di `vendite.attivita_fatturabili` che
risultano gia` agganciate a una riga di fattura.

> Nota: il blocco puo` essere **bypassato** solo in contesti di manutenzione
> tramite GUC `zeroerp.maintenance_reset_lotto_draft = on` (reset tecnico lotto DRAFT).

---

### Regola applicata

* Trigger **BEFORE UPDATE/DELETE** su `vendite.attivita_fatturabili`.
* Se `fattura_riga_id` e` valorizzato, l’operazione e` bloccata con
  `script.fn_log_and_raise_error('E_RIGA_GIA_FATTURATA')`.
* In caso di `DELETE`, la funzione ritorna **OLD** (evita errori su RETURN NEW).

---

### Ruolo nel processo

Questa guard tutela l’integrita` del processo di fatturazione:

* evita modifiche dopo l’aggancio a una riga di fattura;
* preserva la coerenza tra attivita` fatturabili e fatture.

---

{% include-markdown "signature-core.md" %}
