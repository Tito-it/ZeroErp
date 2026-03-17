## 📘 Documentazione Concettuale – Tabella `vendite.ordini_indirizzi`

> 👀 **Vedi anche**
>
**Approfondimenti tabelle:** 
>
•[vendite.ordini](/dbzero/vendite/tabelle/ordini)  
> •[config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)     
> •[anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)      
> •[anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)      
> **Analoghi**:
> •[vendite.fatture_indirizzi](/dbzero/vendite/tabelle/fatture_indirizzi)   
> •[vendite.ddt_indirizzi](/dbzero/vendite/tabelle/ddt_indirizzi)   

---

### 🎯 Scopo Principale

`vendite.ordini_indirizzi` memorizza gli **indirizzi associati alla testata ordine** come **snapshot JSON** al momento dell’inserimento/conferma. Per ciascun ordine è ammesso **al massimo un indirizzo per tipo** (es. *spedizione*, *fornitura*, *residenza*), garantito da `UNIQUE(ordine_id, tipo_indirizzo_id)`.

Lo snapshot consente di **cristallizzare** i dati (via/numero, CAP, comune, provincia, stato ISO, contatti, e‑mail, note) senza dipendere da modifiche successive in anagrafica.

---

### 🧾 Linee guida snapshot `jsonb`

Formato minimo suggerito (estensibile):

```json
{
  "intestazione": "string",
  "via": "string",
  "cap": "string",
  "citta": "string",
  "prov": "string",
  "stato": "IT|...",
  "email": "string",
  "telefono": "string",
  "note": "string"
}
```

> Per estero aggiungere `line2`, `line3`, `county/state`, `iso3`, ecc.

---

### Verifiche / Migliorie

1. **Refuso descrizione tabella**: *"alla ordine"* e *"ordinezione"* → correggere in *"all'ordine"* e *"spedizione/fornitura/residenza"*.
2. **Indice opzionale su tipo**: aggiungere `ix_ordini_indirizzi_tipo (tipo_indirizzo_id)` se i filtri per tipo sono frequenti.
3. **Snapshot mail**: la nota *"Includere nello snapshot la mail"* è già in linea: assicurare che le pipeline di generazione popolino sempre `email` se disponibile.
4. **Allineamento con analoghi**: mantenere naming coerente con `fatture_indirizzi`/`ddt_indirizzi` (FK/IDX prefix e commenti).

---

### Esempi

**Inserimento indirizzo di spedizione**

```sql
INSERT INTO vendite.ordini_indirizzi (
  ordine_id, tipo_indirizzo_id, snapshot,
  origine_indirizzo_id, origine_soggetto_ruolo_id
) VALUES (
  :ordine_id, :tipo_spedizione_id,
  jsonb_build_object(
    'intestazione','ACME S.p.A.',
    'via','Via Roma, 10','cap','00100','citta','Roma','prov','RM','stato','IT',
    'email','ordini@acme.it','telefono','06-123456','note','Consegna su appuntamento'
  ),
  :indirizzo_id, :soggetto_ruolo_id
);
```

**Aggiornamento tipo (controllo whitelist)**

```sql
UPDATE vendite.ordini_indirizzi
   SET tipo_indirizzo_id = :tipo_fornitura_id
 WHERE id = :id;
-- Se il tipo non è consentito per "ORDINI" → errore dal trigger
```

---

### Ruolo nel sistema

La tabella è **cruciale** per stampa conferme d’ordine, documenti di trasporto derivati e audit: garantisce che l’indirizzo riportato sui documenti provenga da uno **snapshot affidabile**, indipendente da cambiamenti anagrafici successivi.
