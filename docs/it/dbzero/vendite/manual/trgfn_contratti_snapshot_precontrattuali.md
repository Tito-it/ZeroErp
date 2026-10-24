## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_snapshot_precontrattuali()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)    
> • [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)    
> • [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)    
>
**Approfondimento funzioni:**    
>
• [vendite.fn_doc_fornitura_da_anagrafica](/dbzero/vendite/funzioni/fn_doc_fornitura_da_anagrafica)    
> • [vendite.fn_get_fornitura_da_anagrafica](/dbzero/vendite/funzioni/fn_get_fornitura_da_anagrafica)    
> • [vendite.trgfn_doc_fornitura_segue_cliente](/dbzero/vendite/funzioni/trgfn_doc_fornitura_segue_cliente)    
> • [vendite.fn_create_contratto](/dbzero/vendite/funzioni/fn_create_contratto)    
>
### 🎯 Scopo Principale
(latest review 12/10/26)

Quando nasce un contratto, la funzione gli dà la sua **scheda di fornitura**
(`vendite.contratti_utilities`): classe d'utenza, tipo d'uso, parametri tecnici,
presi dai dati precontrattuali del contatore (la coppia istanza/utility del
contratto).

La regola non è scritta qui: la funzione chiama il building block
`vendite.fn_doc_fornitura_da_anagrafica`, lo stesso che rifà la scheda quando il
contatore del contratto cambia in bozza.

La funzione è eseguita da un trigger **AFTER INSERT** su `vendite.contratti`.

---

### La vita della scheda di fornitura

| Momento | Che cosa succede |
| --- | --- |
| **Nascita** | La scheda arriva dai dati precontrattuali del contatore. Se il contatore non ne ha, il contratto nasce senza scheda |
| **Nascita con la scheda dell'operatore** | Se chi crea il contratto ha compilato la scheda, le sue voci **correggono** quella dell'anagrafica (vince l'operatore); le voci che non ha compilato restano quelle dell'anagrafica. Il drawer gliela mostra prima di creare (`vendite.fn_get_fornitura_da_anagrafica`) |
| **Bozza, cambio di contatore** | La scheda si **rifà da capo** dai dati del contatore nuovo: descriveva l'altro contatore, e le correzioni fatte a mano valevano per quello |
| **Fuori bozza** | La scheda non si tocca più (il blocco dei dati collegati del contratto): è la fonte stabile per prezzo, IVA e fatturazione |

La coppia istanza/utility della scheda è sempre quella del contratto: lo
garantisce il guard `vendite.trgfn_doc_fornitura_guard_coppia`.

---

### Contesto operativo

**Tabella di origine:** `anagrafiche.istanze_dati_precontrattuali` (un record per contatore)  
**Tabella di destinazione:** `vendite.contratti_utilities`  
**Trigger:** `AFTER INSERT` su `vendite.contratti`

---

### Ruolo nel processo

La scheda è quello che il prezzo e l'IVA leggono del contatore: la classe
d'utenza per il listino, il tipo d'uso (domestico, altri usi…) per l'aliquota.
Per questo deve descrivere **il contatore del contratto**, e lo segue finché il
contratto è in bozza; dopo, resta ferma.

---

{% include-markdown "signature-core.md" %}

---
