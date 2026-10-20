## 📘 Documentazione Concettuale – Funzione `vendite.fn_parametri_importo_riga()`

> 👀 **Vedi anche**
>
> [vendite.articolo_regole_fatturazione](/dbzero/vendite/tabelle/articolo_regole_fatturazione)
> [anagrafiche.fn_parametri_importo_utility](/dbzero/anagrafiche/funzioni/fn_parametri_importo_utility)
> [vendite.trgfn_fatture_righe_importo](/dbzero/vendite/funzioni/trgfn_fatture_righe_importo)

### 🎯 Scopo

(21-10-2026 — brief `brief-db-modelli-documento-standard`, §10.7 R-3)

Dice con quanti decimali e con quale metodo si arrotonda l'**importo di una riga** di fattura. È il
punto unico: lo legge il trigger delle righe, e lo legge il backend quando raggruppa le attività
fatturabili.

### Da dove vengono i parametri

1. la **regola dell'articolo** (`articolo_regole_fatturazione`), se l'articolo ne ha una;
2. altrimenti i **parametri effettivi dell'azienda per l'utility della fattura**
   (`anagrafiche.fn_parametri_importo_utility`): la sua riga per l'utility, poi per il metodo la
   sua policy generale, poi il valore di sistema dell'utility.

La riga e il totale della fattura seguono così la stessa catena.

### Righe

Sempre una. I due valori sono `NULL` solo se l'articolo non ha regole **e** l'utility manca: chi
la legge decide. Il trigger delle righe solleva `E_CONFIG_MANCANTE`, come il ricalcolo dei totali
per una fattura senza utility.

### Note di migrazione

Prima il default era il letterale `2 / HALF_UP`, scritto nel trigger delle righe e di nuovo nel
backend (`_GROUP_ATTIVITA_SELECT` di `pipeline_repository`).
