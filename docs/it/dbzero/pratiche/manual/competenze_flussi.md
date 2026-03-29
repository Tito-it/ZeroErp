## 📘 Documentazione Tabella – `pratiche.competenze_flussi`

> 👀 **Vedi anche**
>
> [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
>
> Funzioni collegate:
>
> [pratiche.fn_coda_lavoro_operatore](/dbzero/pratiche/manual/fn_coda_lavoro_operatore)
> [pratiche.fn_prendi_in_carico_flusso](/dbzero/pratiche/manual/fn_prendi_in_carico_flusso)

---
### 🎯 Scopo Principale

Matrice delle competenze: definisce per ogni tipo di flusso (template) e reparto (unita' organizzativa), quali operatori (risorse umane) sono abilitati a eseguire quel tipo di flusso.

E' configurazione statica, gestita dall'amministratore. Non contiene dati operativi runtime.

---

### Modello semantico

La riga dice: *"l'operatore X, nel reparto Y, e' abilitato a eseguire flussi del tipo Z"*.

```
competenze_flussi
  └── template_flusso_id  → quale tipo di flusso
  └── unita_organizzativa_id  → in quale reparto
  └── risorsa_umana_id  → quale operatore
  └── attivo  → competenza attiva o sospesa
```

Il vincolo UNIQUE su `(template_flusso_id, unita_organizzativa_id, risorsa_umana_id)` garantisce che un operatore non possa avere la stessa competenza duplicata.

---

### Utilizzo nel sistema

1. **Coda di lavoro** (`fn_coda_lavoro_operatore`): la tabella determina il livello COMPETENZA (flussi non assegnati che l'operatore puo' prendere) e il livello REPARTO (flussi del reparto dell'operatore).
2. **Presa in carico** (`fn_prendi_in_carico_flusso`): verifica che l'operatore abbia competenza attiva prima di assegnare il flusso.

---

### Note operative

* Il flag `attivo` permette di sospendere una competenza senza rimuovere la configurazione (es. operatore in ferie).
* La tabella ha trigger standard: audit (`trgfn_audit_data_user_generic`), tx_id (`trgfn_tx_id_managed`), storico (`trgfn_storico_generic`).

---

{% include-markdown "signature-core.md" %}
