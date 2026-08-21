## 📘 Documentazione Concettuale – Vista `config.vw_codici_errore`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.codici_errore](/dbzero/config/tabelle/codici_errore)
> • [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
> • [config.classi_errore](/dbzero/config/tabelle/classi_errore)
>
Approfondimento viste:
> • [config.vw_codici_errore_identita](/dbzero/config/views/vw_codici_errore_identita)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Superficie di revisione**: mette la classe accanto alla frase, per vedere a occhio nudo una
classe che contraddice il testo che l'operatore legge.

Serve a una domanda che nessuna delle due tabelle sa rispondere da sola: *questo errore è
classificato coerentemente con quello che dice?* Un messaggio che parla di «documento non
trovato» classificato `DATO_ERRATO` è un difetto che si vede solo affiancando le due colonne —
e si traduce, a valle, in uno stato HTTP sbagliato.

Espone identità (`codice`, `classe`, `obsoleto_dal`, `note`) e traduzione (`lingua`,
`messaggio`, `causa`, `soluzione`).

---

### ⚠️ Non è uno a uno: il join moltiplica per lingua

```sql
LEFT JOIN config.messaggi_errore m ON m.codice = c.codice
```

Nessun filtro su `lingua`. Un codice tradotto in due lingue compare quindi **due volte**.

Misurato il 2026-08-21: 726 codici in catalogo, **727 righe** nella vista — un solo codice ha
oggi due traduzioni (`it` e `en`). Lo scarto è minimo, ma **cresce con le traduzioni**: il
giorno in cui il catalogo fosse tradotto per intero, la vista raddoppierebbe.

⭐ Per questo esiste `vw_codici_errore_identita`, che garantisce una riga per codice. **Chi
conta i codici da qui sbaglia**, e sbaglia di poco — che è il modo peggiore, perché il numero
sembra giusto.

✅ **Il consumatore che conta lo sa già.** `genera_error_policies` — il comando che genera le
policy del backend — legge `vw_codici_errore_identita`, e porta in testa un divieto esplicito
di usare questa vista. La sua motivazione aggiunge un caso che da qui non si vedrebbe:
filtrare per `lingua = 'it'` **non** sarebbe un rimedio, perché il `LEFT JOIN` fa comparire un
codice privo di messaggio con `lingua IS NULL` — e il filtro lo scarterebbe **in silenzio**.
Non un errore: righe che spariscono.

Il rischio, quindi, non è aperto: è presidiato nel punto giusto. Resta scritto qui perché il
prossimo consumatore non ha modo di saperlo se non glielo si dice.

---

### Il `LEFT JOIN` è deliberato

Un codice **senza** traduzione compare comunque, con i campi del messaggio a `NULL`. È il
comportamento voluto: un codice senza frase è precisamente il difetto che questa vista deve
rendere visibile, e un `JOIN` interno lo nasconderebbe.

Misurato: oggi **zero** codici senza messaggio. La colonna `messaggio` a `NULL` è quindi un
segnale, non un caso normale.

---

### Scope

`WITH (security_invoker = true)` — formale, nessuna delle tabelle lette ha RLS. Va
**ri-specificata a ogni `CREATE OR REPLACE VIEW`**, altrimenti PostgreSQL azzera la reloption.

---

{% include-markdown "signature-core.md" %}
