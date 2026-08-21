## 📘 Documentazione Concettuale – Tabella `pagamenti.centri_riscossione`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
> 🔴 **Due vincoli dichiarati nelle migrazioni NON esistono nel database**
> (misurato il 2026-08-21, auto-gen alla mano):
>
> * `uq_centri_riscossione_compensazione` è **totale** su un booleano, non
>   parziale: la tabella **non può contenere più di DUE righe in tutto**. Il
>   `where:` fu scritto su un `addUniqueConstraint`, che quell'attributo non
>   prevede, e venne ignorato in silenzio;
> * `chk_centri_riscossione_ruolo_esclusivo` («o compensazione o fondo fattura»)
>   **non c'è**: il suo blocco `- sql:` è annidato dentro `addColumn.columns:`,
>   e lì dentro non viene eseguito. La colonna è nata, il vincolo no.
>
> ⚠️ Oggi la tabella ha esattamente due righe, quindi il primo vincolo è **saturo
> e indistinguibile da uno rispettato**: aggiungere il centro banca fallisce.
> Rimessi in piedi dal passo **P-1** di
> `docs/it/dev/work-in-progress/brief-db-posting-e-abbinamento-rata.md`.
> ⛔ **Non ancora applicato.**

### 🎯 Scopo Principale
La tabella **`pagamenti.centri_riscossione`** definisce le **origini di incasso**
per i movimenti vendite (banca, posta, cassa, compensazioni, fondo fattura, ecc.).

---

### Campi chiave (semantica)

* `codice`: identificativo leggibile.
* `codice_interno`: codice tecnico/integrazione.
* `is_compensazione`: identifica il centro usato per **compensazioni**.
* `is_fondo_fattura`: identifica il centro usato per movimenti di **fondo fattura**.
* `attivo`: centro attivo.

---

### Regole principali

* `codice` univoco.
* Solo **un centro** può avere `is_compensazione = true`.
* Un centro non può essere contemporaneamente `is_compensazione = true` e `is_fondo_fattura = true`.

---

### ⚠️ I due flag marcano i centri **non di cassa**

Non tutti i movimenti sono denaro arrivato. Un movimento sul centro
`is_fondo_fattura` o `is_compensazione` registra denaro **spostato** da un
documento a un altro, non incassato da un canale.

| Domanda | Che cosa si somma |
| --- | --- |
| «questa fattura è ancora da pagare?» | **tutti** i movimenti — il trasferimento la salda davvero |
| «quanto è **entrato**?» | solo i centri di cassa: questi due vanno **esclusi** |

🔴 La distinzione va messa nella **prima** misura che si scrive, non aggiunta
dopo: un cruscotto di incassato che somma tutto conta come denaro arrivato
qualcosa che è stato solo spostato, e l'errore non si vede — il numero è
plausibile e cresce nel verso giusto. **I due flag esistono anche per questo.**

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.centri_riscossione
WHERE is_compensazione IS TRUE
   OR is_fondo_fattura IS TRUE;
```

---

{% include-markdown "signature-core.md" %}
