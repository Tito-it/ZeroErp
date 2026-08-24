## 📘 Documentazione Concettuale – Funzione `script.fn_get_vie_discendenti`

> 👀 **Vedi anche**
>
> • [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario)
> • [storico.stradario_trasformazioni](/dbzero/storico/tabelle/stradario_trasformazioni)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Data una via, restituisce **tutte quelle che ne sono derivate** per trasformazione
amministrativa, con il livello di profondità.

È una `WITH RECURSIVE` su `storico.stradario_trasformazioni`: risale la catena
`via_id_orig → via_id_nuovo` fino a esaurirla.

⭐ Serve perché le trasformazioni si **incatenano**: una via fusa in un'altra che a sua volta
viene rinominata. Cercare un solo passo restituirebbe una risposta parziale — e parziale in
modo silenzioso.

⚠️ Legge da `storico.stradario_trasformazioni`, che è uno dei quattro storici **la cui tabella
viva non esiste più** ed è **vuoto**. Oggi questa funzione restituisce sempre zero righe: non è
rotta, è senza dati.

---

{% include-markdown "signature-core.md" %}
