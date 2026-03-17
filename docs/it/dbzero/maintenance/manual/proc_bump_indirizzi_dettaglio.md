## 📘 Documentazione Concettuale – Procedura `maintenance.proc_bump_indirizzi_dettaglio(p_stradario_id)`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)   
> [config.stradario](/dbzero/config/tabelle/stradario)   
>
**Approfondimento funzioni:**   
>
[anagrafiche.trgfn_indirizzi_dettaglio_protect_update](/dbzero/anagrafiche/manual/trgfn_indirizzi_dettaglio_protect_update)   
>
🎯 Scopo Principale

(latest review 02-01-26)
Riallineare la normalizzazione degli indirizzi di dettaglio quando cambia la via (stradario) in modo controllato e tracciato.

---

### Come Funziona

1. Attiva un flag di manutenzione di sessione (`zeroerp.maintenance_indirizzi_dettaglio = 'on'`).
2. Esegue un UPDATE "neutro" sulle righe con `stradario_id = p_stradario_id`.
3. L'UPDATE forza l'esecuzione dei trigger di normalizzazione e storicizzazione.

---

### Parametri

| Parametro        | Tipo    | Descrizione                                                       |
| ---------------- | ------- | ----------------------------------------------------------------- |
| `p_stradario_id` | integer | ID della via da riallineare in `anagrafiche.indirizzi_dettaglio`. |

---

### Output

* Nessun valore di ritorno (procedura).

---

### Note Operative

* La procedura e' l'unico modo previsto per riallineare gli indirizzi dopo una riclassificazione.
* Opera a livello di `indirizzi_dettaglio`, quindi impatta tutte le entita' che vi puntano (ruoli, soggetti, istanze).

---

> **"Riallineamento controllato: attiva manutenzione, aggiorna, storicizza."**
