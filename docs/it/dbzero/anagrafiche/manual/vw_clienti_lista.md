## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_clienti_lista`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> • [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
>
Approfondimento viste:
> • [anagrafiche.vw_clienti_codice_ba](/dbzero/anagrafiche/views/vw_clienti_codice_ba)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Vista **flat** dei clienti per la lista UI `anagrafiche.clienti`. Denormalizza in una riga
sola ciò che nel modello sta su cinque tabelle: anagrafica del soggetto (compreso
`id_fiscale_univoco_cf_piva`), codice del billing account, utility, stato del cliente e le
quattro date del ciclo di vita (attivazione, sospensione, riattivazione, chiusura).

Esiste per una ragione precisa: una lista configurabile deve poter **ordinare e filtrare su
qualunque colonna mostrata** senza che il backend ricostruisca i join a ogni richiesta.

---

### ⚠️ Lo scope non lo applica lei: lo eredita

La vista è dichiarata `WITH (security_invoker = on)`. Le policy RLS delle tabelle sottostanti
si applicano quindi **a chi interroga**, non al proprietario della vista. Non c'è nessun
filtro di perimetro scritto nel corpo, e non deve esserci: sarebbe una seconda sorgente di
verità accanto alle policy.

Fra le tabelle lette, **`anagrafiche.billing_account` ha la RLS attiva** (quattro policy).

---

### ⚠️ Un cliente fuori perimetro non compare «senza codice»: **sparisce**

È la conseguenza che conta, e non si vede leggendo l'elenco delle colonne. Il billing account
è agganciato con un **`JOIN` interno**:

```sql
JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
```

`JOIN` interno + RLS significa che, se il BA non è visibile a chi interroga, **l'intera riga
del cliente non esiste** per quella query. Lo stesso vale per istanza utility, soggetto,
utility e stato, tutti agganciati con `JOIN` interno — ma quelle tabelle oggi non hanno RLS.

Quindi: **un conteggio più basso del previsto su questa vista può essere il perimetro, non i
dati.** Prima di inseguire un cliente «sparito», si controlla se il suo billing account è
dentro il perimetro emittente di chi sta guardando.

⭐ Il comportamento è deliberatamente **opposto** a quello della vista gemella
`vw_clienti_codice_ba`, che sullo stesso legame usa un `LEFT JOIN`: là il cliente resta e il
codice arriva `NULL`. Due viste sullo stesso dominio, due risposte diverse alla stessa
domanda — sapere quale si sta usando è la differenza fra un elenco completo e uno filtrato.

---

### Cosa **non** garantisce

* **Nessuna deduplicazione**: la granularità è la riga di `anagrafiche.clienti`, cioè
  soggetto × utility. Lo stesso soggetto compare più volte se è cliente su più utility.
* **Nessun ordinamento**: non c'è `ORDER BY`. Lo decide chi interroga.
* **Nessuna nozione di "attivo"**: non filtra per stato. Un cliente chiuso c'è, con il suo
  `stato_codice_interno`. Il filtro è della lista, non della vista.

---

### Consumatori

Lista configurabile `anagrafiche.clienti` (`ui.lista_colonna`) e il repository del dominio
anagrafiche. ⚠️ Aggiungere una colonna alla lista significa aggiungerla **qui** e poi
registrarla in `ui.lista_colonna`: la lista non può mostrare ciò che la vista non espone.

---

{% include-markdown "signature-core.md" %}
