## 📘 Documentazione Concettuale – Procedura `maintenance.proc_bump_toponomastica(p_toponomastica_id, p_descrizione)`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[config.toponomastica](/dbzero/config/tabelle/toponomastica)   
> [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)   
>
**Approfondimento funzioni:**   
>
[config.trgfn_toponomastica_bump_normalize](/dbzero/config/funzioni/trgfn_toponomastica_bump_normalize)   
> [config.trgfn_toponomastica_protect_update](/dbzero/config/funzioni/trgfn_toponomastica_protect_update)   
>
🎯 Scopo Principale

(latest review 02-01-26)
Consentire la correzione controllata di un toponimo **in uso**, forzando la rinormalizzazione di `config.stradario_generale` tramite i trigger esistenti.

---

### Come Funziona

1. Attiva un flag di manutenzione di sessione (`zeroerp.maintenance_toponomastica = 'on'`).
2. Aggiorna la descrizione del toponimo (`config.toponomastica.descrizione`).
3. L'UPDATE innesca `trgfn_toponomastica_bump_normalize`, che riallinea `indirizzo_normalizzato` su `stradario_generale`.

---

### Parametri

| Parametro            | Tipo    | Descrizione                     |
| -------------------- | ------- | ------------------------------- |
| `p_toponomastica_id` | integer | ID del toponimo da correggere.  |
| `p_descrizione`      | text    | Nuova descrizione del toponimo. |

---

### Output

* Nessun valore di ritorno (procedura).

---

### Note Operative

* La procedura va usata solo in manutenzione controllata.
* Fuori manutenzione, il guard blocca le modifiche ai toponimi in uso.

---

> **"Correzione controllata dei toponimi, con riallineamento automatico dello stradario generale."**

