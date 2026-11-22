## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
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
> * [anagrafiche.fn_search_indirizzi_dettaglio](/dbzero/anagrafiche/funzioni/fn_search_indirizzi_dettaglio) — la ricerca dei civici, che restituisce righe di questa vista
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

Escono anche i civici spenti: chi vuole solo quelli in uso filtra su `attivo`, come fa la ricerca.

---

### Chi la legge

La lettura risolta degli indirizzi (`anagrafiche.vw_indirizzi_resolved_base`) per gli indirizzi col dettaglio,
le viste dei punti di fornitura e delle istanze, la ricerca dei civici, il controllo del doppione. La vista si
legge soltanto: i civici si scrivono sulla tabella, attraverso il «trova o crea».

---

### ⚠️ Che cosa oggi non copre

* **I civici di una via che non si risolve spariscono**: la vista unisce la via risolta con un join interno, e
  quando la catena via → comune → provincia → CAP si interrompe (un comune che perde la provincia, per esempio)
  il civico non esce più, né qui né nelle letture che passano da qui. Negli indirizzi risolti quel civico resta,
  ma senza testo, comune e CAP.

---

{% include-markdown "signature-core.md" %}
