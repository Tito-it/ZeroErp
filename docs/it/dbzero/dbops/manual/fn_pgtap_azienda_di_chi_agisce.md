## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_azienda_di_chi_agisce`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo, che la usa quando il contesto è già aperto
>
> • [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente dei builder, che la usa col billing account del test
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-modello-documento-vendita` (§4-octies)

---
### 🎯 Scopo Principale

(rev 2026-10-24)

**L'azienda su cui una fixture scrive quando il contesto è già aperto**: quella di chi
agisce. Torna l'emittente (id, codice, soggetto) e l'operatore (utente e identità).

```sql
SELECT * FROM dbops.fn_pgtap_azienda_di_chi_agisce('il mio builder');
```

---
### 🧭 Perché esiste

Era un pezzo del mondo dei pgTAP: con un contesto aperto il mondo non costruisce una nuova
azienda, usa quella di chi agisce. Serviva anche ai builder che ricevono il cliente di
un'altra fixture, e ricopiarlo cinque volte avrebbe dato cinque versioni della stessa regola:
ora ha una sede, e il mondo la usa.

---
### 🔗 Cosa decide

* **L'azienda** la risolve la stessa regola della produzione
  (`script.fn_resolve_emittente_for_user`): l'emittente scelto in alto, se l'utente lo può
  usare, altrimenti la sua azienda di configurazione. È la stessa domanda che si fa il
  database quando lega un cliente all'azienda.
* **Solleva**, nominando chi la chiama, in tre casi: nessun contesto aperto; un utente senza
  un'azienda su cui scrivere; un utente senza identità di operatore attiva.

Non scrive niente.
