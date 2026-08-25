## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_fatture_guard_data_numerata`

> 👀 **Vedi anche**
>
> [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> [vendite.fn_imposta_data_documento_lotto](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto)
> [vendite.fn_numera_fattura_opz_emessa](/dbzero/vendite/funzioni/fn_numera_fattura_opz_emessa)
> [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)

---

### 🎯 Scopo Principale

**Rende immutabile `vendite.fatture.data` da quando la fattura ha un numero.**

Trigger `BEFORE UPDATE` sulla testata: se il documento ha già un numero fiscale,
la sua data non si tocca più.

---

### ⭐ Nasce da una misura, non dal piano

Il cantiere dava per assodato che `trgfn_fattura_satellite_guard_congelamento`
«congelasse tutto oltre EMESSA». **Non è così**, e lo ha detto la verifica: sulla
testata quel trigger è agganciato a
`BEFORE UPDATE OF emittente_snapshot, cliente_snapshot` — e basta. (Sulle tabelle
satellite `fatture_indirizzi` e `fatture_scadenze` copre tutti gli eventi; sulla
testata no.)

Fino al 2026-08-25 un `UPDATE` della data su una fattura **numerata e
DEFINITIVA** passava senza un errore. E la data è il dato da cui dipendono
**l'anno del sezionale, la chiave del contatore e il piano rate**.

> Il cantiere stava costruendo un cancello sull'ingresso principale lasciando
> aperto il retro.

---

### ⛔ Il discriminante è `OLD.numero`, non lo stato

E non è un dettaglio di implementazione.

`fn_numera_fattura_opz_emessa` **assegna il numero mentre la fattura è in
EMESSA**: il passaggio a DEFINITIVA avviene *dopo*, nella finalizzazione dello
step. Una soglia scritta sugli stati (`DRAFT | EMESSA` scrivibili) lascerebbe
quindi una **finestra reale** in cui il documento ha già un numero fiscale e la
data è ancora modificabile.

La domanda giusta non è *«a che punto è il documento»* ma **«ha già un numero?»**.

---

### ℹ️ Perché un codice errore nuovo

Sulla stessa tabella esiste già `E_COLONNA_NON_MODIFICABILE`, e **non è stato
riusato**. Quel messaggio dice *«Colonna non modificabile: %s»* — dice **cosa**,
non **perché**. E qui il perché è tutto: la data non è bloccata per un capriccio
di schema, è bloccata perché il documento è **già uscito con un numero**.

Il codice nuovo è, per forma, il gemello di `E_FATTURA_NON_ANNULLABILE`.

* **Nel segnaposto va il NUMERO, non l'id**: è quello che compare sul documento e
  che l'operatore ha sotto gli occhi.
* **Nessuna chiave `campo` nel contesto**: su un `CONFLITTO_STATO` non c'è nessun
  campo da accendere nel form — è la *situazione* a non consentire l'operazione,
  non un valore da correggere.

---

### Note operative

* Se la data va cambiata su un lotto, la strada è
  [`fn_imposta_data_documento_lotto`](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto),
  che salta apposta le fatture già numerate invece di andare a sbattere qui.
* Brief: `docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md` §4 DB-14.

---

{% include-markdown "signature-core.md" %}
