## 📘 Documentazione Concettuale – Tabella `vendite.preventivi_indirizzi`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)  
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)  
> • [config.tipi_indirizzi_allowed](/dbzero/config/tabelle/tipi_indirizzi_allowed)  
> • [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)  

---

### 🎯 Scopo Principale

`vendite.preventivi_indirizzi` memorizza lo **snapshot indirizzi** associato
al preventivo (fatturazione/spedizione/altri tipi ammessi), mantenendo
storico coerente anche se l’anagrafica origine cambia nel tempo.

---

### ✅ Regole principali

1. relazione 1:N con preventivo, ma **un solo record per tipo indirizzo**
   (`uq_preventivi_indirizzi_uno_per_tipo_` su `preventivo_id, tipo_indirizzo_id`);
2. `snapshot` (`jsonb`) obbligatorio;
3. trigger `trgfn_tipi_indirizzi_only_allowed('PREVENTIVI')` per accettare
   solo tipi indirizzo autorizzati all’ambito preventivi.

---

### 📌 Tracciabilita` origine

Campi opzionali:
* `origine_indirizzo_id`
* `origine_soggetto_ruolo_id`

Permettono di risalire al record anagrafico sorgente usato per lo snapshot.

---

### 🔗 Ruolo nel flusso

Gli indirizzi snapshot:

* fissano il contesto documento al momento della proposta commerciale;
* riducono divergenze successive in stampa/documenti derivati;
* supportano coerenza nelle successive fasi di attività fatturabili/fatturazione.

---

### 🧷 Audit

Audit standard su insert/update:
* `data_insert`, `user_insert`
* `data_update`, `user_update`

---

### 👓 Ruolo nel sistema

`vendite.preventivi_indirizzi` separa la componente anagrafica variabile dalla
vista documento “congelata”, garantendo riproducibilita` del preventivo lungo il ciclo.

