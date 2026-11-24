## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_dettaglio`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — i civici
> * [config.stradario](/dbzero/config/tabelle/stradario) — la via, da cui viene il comune
>
> Approfondimento viste:
>
> * [script.vw_indirizzo_completo](/dbzero/script/views/vw_indirizzo_completo) — la via risolta, da cui vengono nome del comune, CAP e provincia
> * [anagrafiche.vw_indirizzi_resolved_base](/dbzero/anagrafiche/views/vw_indirizzi_resolved_base) — la lettura risolta degli indirizzi, che la usa per quelli col dettaglio
> * [anagrafiche.vw_pdp](/dbzero/anagrafiche/views/vw_pdp) — i punti di fornitura, che la usano per il loro civico
> * [anagrafiche.vw_istanze_utilities_dettaglio](/dbzero/anagrafiche/views/vw_istanze_utilities_dettaglio) — le istanze, che la usano per il loro civico
>
> Approfondimento funzioni:
>
> * [script.fn_check_indirizzo_duplicato](/dbzero/script/funzioni/fn_check_indirizzo_duplicato) — il controllo del doppione
> * [script.fn_get_search_detail](/dbzero/script/funzioni/fn_get_search_detail) — il dettaglio di una ricerca

---

### 🎯 Scopo Principale

`anagrafiche.vw_indirizzi_dettaglio` è il civico pronto da leggere: le colonne di `anagrafiche.indirizzi_dettaglio`
con accanto il comune, il nome del comune, il CAP e la sigla della provincia della sua via.

---

### Che cosa aggiunge al civico

* **Il comune** (`comune_id`) dalla via di `config.stradario`.
* **Nome del comune, CAP e provincia** (`descrizione_comune`, `cap`, `provincia`) dalla via risolta di
  `script.vw_indirizzo_completo`. Il CAP è quello della via: nello stradario una via sta in un CAP solo.
* L'id del civico esce come `indirizzo_dettaglio_id`, il nome con cui lo cercano tutte le altre letture.

`indirizzo_normalizzato`, `via_norm` e il dettaglio sono quelli della tabella, cioè i valori scritti dal
trigger di normalizzazione. La vista non calcola niente: legge.

Escono anche i civici spenti: chi vuole solo quelli in uso filtra su `attivo`, come fa la ricerca dei civici.

---

### Chi la legge

La lettura risolta degli indirizzi (`anagrafiche.vw_indirizzi_resolved_base`) per gli indirizzi col dettaglio,
le viste dei punti di fornitura e delle istanze, il controllo del doppione. La ricerca dei civici la fa il
backend leggendo questa vista: nel database non c'è una funzione di ricerca dei civici. La vista si
legge soltanto: i civici si scrivono sulla tabella, attraverso il «trova o crea».

---

### Una via che non si risolve non ha civici

La vista unisce la via risolta con un join interno: un civico la cui catena via → comune → provincia → CAP fosse
interrotta non uscirebbe, né qui né nelle letture che passano da qui. Il modello però non lo produce. Un civico non
nasce su una via che non si risolve (`E_INDIRIZZO_VIA_NON_RISOLTA`, dal guard della chiave, su ogni strada), e la
provincia di un comune che lo stradario usa non si toglie (`E_COLONNA_NON_MODIFICABILE`). Il caso si raggiunge solo
con una scrittura che salta i trigger.

---

### Note di migrazione

* 2026-11-24 — si ritira `anagrafiche.fn_search_indirizzi_dettaglio`, la ricerca dei civici del database che
  restituiva righe di questa vista: non la chiamava nessuno, e la ricerca del backend legge la vista.

---

{% include-markdown "signature-core.md" %}
