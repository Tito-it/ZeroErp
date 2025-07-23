## 📘 Documentazione Concettuale – View `script.vw_indirizzo_completo`

> 👀 **Vedi anche**   
>
> Approfondimento tabelle:     
> - [config.stradario](/dbzero/config/tabelle/stradario)   
> - [config.comuni](/dbzero/config/tabelle/comuni)   
>
> Approfondimento view:     
> - [script.vw_stradario_esteso](/dbzero/script/view/vw_stradario_esteso)   

La view **`script.vw_indirizzo_completo`** estende la tabella `config.stradario` con dati anagrafici del comune, provincia, codice postale e dettaglio della via, fornendo un record unico per ogni via con tutte le informazioni utili.

---

### 🎯 Scopo Principale

* **Denormalizzazione per letture rapide**: aggregare in un’unica view i dati di stradario, comune, provincia, codice postale e via, semplificando le query di selezione degli indirizzi.
* **Pulizia e consistenza**: fornire campi già formattati e pronti per essere utilizzati nelle normalizzazioni e nelle funzionalità GIS.
* **Riutilizzabilità**: rendere disponibile un’unica sorgente per join di indirizzi completi, evitando duplicazione di codice SQL.

---

### 🔄 Definizione della View

```sql
CREATE OR REPLACE VIEW script.vw_indirizzo_completo AS
SELECT
  s.id                AS id_stradario,
  c.id                AS id_comune,
  c.descrizione       AS comune,
  p.sigla             AS provincia,
  cp.codice_postale   AS codice_postale,
  ve.indirizzo_generale       AS indirizzo_generale,
  s.geoloc,
  s.extra_info,
  ve.id_via           AS id_via,
  ve.tipo_toponimo,
  ve.nome_strada
FROM config.stradario s
JOIN config.comuni c
  ON s.comune_id = c.id
JOIN config.province p
  ON c.provincia_id = p.id
JOIN config.codici_postali cp
  ON s.codice_postale_id = cp.id
JOIN script.vw_stradario_esteso ve
  ON s.stradario_generale_id = ve.id_via;
```

---

### 💡 Vantaggi Operativi

* **Performance**: riduce il numero di join necessari nelle query di indirizzo, migliorando i tempi di risposta.
* **Manutenibilità**: ogni modifica strutturale (es. nuovi campi) può essere gestita centralmente nella view.
* **Coesione**: fornisce un modello concettuale “indirizzo completo” facilmente comprensibile e utilizzabile.

---

### 🔖 Commento sulla View

```sql
COMMENT ON VIEW script.vw_indirizzo_completo
  IS 'View che estende config.stradario con dati di comune, provincia,
     codice postale e dettaglio via dalla view script.vw_stradario_esteso';
```

---

> 🧠 **“`vw_indirizzo_completo` è il punto di riferimento per tutte le operazioni che richiedono i dati anagrafici e di localizzazione di una via, con un singolo accesso SQL.”**
