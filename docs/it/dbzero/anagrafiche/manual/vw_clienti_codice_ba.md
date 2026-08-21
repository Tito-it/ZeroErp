## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_clienti_codice_ba`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
>
Approfondimento viste:
> • [anagrafiche.vw_clienti_lista](/dbzero/anagrafiche/views/vw_clienti_lista)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Espone il cliente con **il codice del suo billing account** come codice di ricerca, insieme
allo stato e alle date del ciclo di vita. È la superficie usata dalla **ricerca per codice
universale**: quella che, dato un codice digitato dall'operatore, deve dire a quale entità
appartiene senza sapere in anticipo di che tipo sia.

Da qui la colonna `entita_id`, che è `cl.id` ripetuto sotto un nome generico: serve a chi
consuma la ricerca in modo polimorfo e non vuole conoscere il nome della chiave di ciascun
dominio.

---

### ⚠️ È deliberatamente più permissiva della gemella

La vista è `WITH (security_invoker = on)` — eredita quindi la RLS di chi interroga, e
`anagrafiche.billing_account` ce l'ha attiva. Ma il legame è un **`LEFT JOIN`**:

```sql
LEFT JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
```

Conseguenza: se il billing account non è visibile, **il cliente resta in elenco** e `codice`
arriva `NULL`. In `vw_clienti_lista`, che usa un `JOIN` interno sullo stesso legame, lo stesso
cliente **sparirebbe del tutto**.

Non è un'incoerenza: è la differenza fra una **lista** (mostra ciò che l'operatore può
vedere per intero) e una **ricerca** (deve poter dire «esiste, ma non te lo posso
qualificare»). Chi sceglie fra le due sta scegliendo anche questo comportamento.

⚠️ Il rovescio pratico: un `codice` `NULL` in questa vista ha **due** cause indistinguibili —
il cliente non ha billing account, oppure ce l'ha ma è fuori perimetro. Per separarle serve
`billing_account_id`, che la vista espone apposta.

---

### Cosa **non** garantisce

* **Nessuna unicità del codice**: nulla impedisce che due clienti condividano lo stesso BA e
  quindi lo stesso codice. Una ricerca per codice può restituire più righe.
* **Nessun filtro di stato**: i clienti chiusi ci sono, con il loro `stato_codice_interno`.
* **Nessun dato anagrafico**: niente ragione sociale né codice fiscale. Per quelli si passa da
  `vw_clienti_lista`.

---

### Consumatori

Nessun consumo diretto dal backend: è letta da altre viste e funzioni del livello DB
(la ricerca per codice universale). ⚠️ Va quindi trattata come **superficie interna al
database**: cambiarne le colonne non rompe un endpoint, rompe le viste che la compongono, e
quelle non falliscono — restituiscono meno righe.

---

{% include-markdown "signature-core.md" %}
