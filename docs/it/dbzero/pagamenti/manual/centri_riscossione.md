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
> `docs/it/dev/work-done/brief-db-posting-e-abbinamento-rata.md`.
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

### 🔴 Due vincoli che erano dichiarati e non esistevano (sanato 2026-08-21)

Fino al 2026-08-21 questa tabella **non poteva contenere più di due righe**, e
nessuno se n'era accorto — perché ne aveva esattamente due.

* `uq_centri_riscossione_compensazione` era un `UNIQUE` **totale su una colonna
  booleana**: una sola riga con `true` e **una sola con `false`**. Nasce così
  perché il `where:` che avrebbe dovuto renderlo parziale era stato scritto su un
  cambio Liquibase che **quell'attributo non ha**, ed è stato ignorato in silenzio;
* il `CHECK` di esclusività fra i due ruoli era dichiarato in un changeSet del
  2026-02-11 e **non è mai stato eseguito**: il blocco SQL era annidato dentro
  l'elenco delle colonne, dove non viene eseguito. La colonna è nata, il vincolo no.

⭐ **Un vincolo saturo e un vincolo rispettato hanno lo stesso aspetto finché non
si prova ad aggiungere.** Oggi i vincoli sono tre e sono veri:

| Vincolo | Dice |
| --- | --- |
| `uq_centri_riscossione_compensazione` *(parziale)* | **un solo** centro di compensazione |
| `uq_centri_riscossione_fondo_fattura` *(parziale)* | **un solo** centro per i fondi fattura |
| `chk_centri_riscossione_ruolo_esclusivo` | un centro è di compensazione **oppure** di fondo fattura, mai tutti e due |

⚠️ Il secondo non era mai stato nemmeno dichiarato: i centri fondo-fattura
potevano essere N, e chi ne sceglieva uno prendeva **il primo per id**. ⭐ Ora quel
`LIMIT 1` legge una riga che il database garantisce unica.

### ℹ️ E i centri si seminano, non si inseriscono a mano

Le due righe interne (`FONDI_FATTURA`, `COMPENSAZIONI`) erano state inserite **a
mano** nel febbraio 2026: su un database ricostruito da zero la tabella era
**vuota**, e non funzionavano né i fondi fattura né le compensazioni. Dal
2026-08-21 la sede è il CSV `80_data/sql/pagamenti/centri_riscossione.csv`, che
porta anche i tre centri reali — `BANCA`, `POSTE`, `CASSA` — senza i quali una
contabile di incasso vero non è creabile.

⛔ Da qui in poi il dato si cambia **dal CSV**: un `UPDATE` diretto creerebbe una
seconda sorgente di verità, e le due divergerebbero fra sviluppo e integrazione.

---

{% include-markdown "signature-core.md" %}
