## 📘 Documentazione Concettuale – Funzione `script.fn_disdetta_cliente()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)
> • [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Cessazione di un cliente senza subentro** — la disdetta. Imposta `data_chiusura` e porta lo
stato a `CH` (chiuso).

Fa **solo** questo. Tutto il resto succede per effetto dei trigger a cascata, ed è il motivo
per cui la funzione è così breve:

| Trigger | Effetto |
|---|---|
| `trgfn_clienti_set_periodo` | aggiorna il periodo di validità |
| `trgfn_clienti_sync_stato_pdp` | il punto di prelievo torna **DISPONIBILE** |
| `trgfn_storico_generic` | storicizzazione della riga |
| `trgfn_audit_data_user_generic` | audit |

⭐ La conseguenza che conta è la seconda: **disdire un cliente libera il PdP**, che torna
disponibile per un nuovo contratto. Non è la funzione a farlo, ed è giusto — chiunque chiuda
un cliente per un'altra strada ottiene lo stesso effetto.

---

### ⚠️ Il billing account **non** viene toccato

È una policy esplicita, non una dimenticanza: il BA resta attivo dopo la disdetta, perché
servono ancora **fatture finali, conguagli e riconciliazioni**. Chiudere il conto mentre ci
sono partite aperte renderebbe impossibile incassarle.

La chiusura del BA è un'operazione **separata**, e va fatta quando il ciclo economico è
concluso — non quando finisce il rapporto di fornitura. Le due cose finiscono in momenti
diversi, e il modello lo riflette.

---

### La differenza dal subentro

Questa è la cessazione **senza** subentro. Nel subentro il PdP non torna disponibile: passa
direttamente al cliente nuovo, e la continuità della fornitura va preservata. Sono due verbi
distinti proprio perché l'effetto sul PdP è opposto.

---

### Guard sui parametri

* `p_cliente_id` — `NOT NULL` e `> 0`;
* `p_data_cessazione` — `NOT NULL` e **`>= data_attivazione`**: un cliente non può cessare
  prima di essere iniziato.

Gli stati sono risolti per `codice_interno` (`AT` → `CH`), non per id: la matrice resta dato
di configurazione.

---

{% include-markdown "signature-core.md" %}
