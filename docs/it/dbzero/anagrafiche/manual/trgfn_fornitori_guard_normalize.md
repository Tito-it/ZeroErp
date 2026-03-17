## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_fornitori_guard_normalize`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)
>
**Approfondimento funzioni:**
>
[config.sistema_codici](/dbzero/config/manual/sistema_codici)

---

### 🎯 Scopo Principale

(latest review 12-03-2026)
La trigger function **`anagrafiche.trgfn_fornitori_guard_normalize()`**
normalizza i dati minimi del fornitore prima del salvataggio, con focus sul
campo `canale_fe`.

L'obiettivo e' uniformare il valore usato nei flussi di fatturazione elettronica
senza introdurre generazione automatica del `codice`.

---

### Regole applicate

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.fornitori`.
* Se `NEW.canale_fe` e' valorizzato:
  * rimuove tutti gli spazi con `regexp_replace(..., '\\s+', '', 'g')`
  * converte il risultato in maiuscolo con `upper(...)`
* Il blocco di normalizzazione di `NEW.codice` e' presente ma commentato:
  quindi oggi il trigger **non** modifica il codice del fornitore.

---

### Effetto operativo

Dati in ingresso come `ab c 123` vengono salvati come `ABC123`, riducendo le
variazioni formali sul canale FE e semplificando confronti, controlli e
integrazioni a valle.

---

### ⚠️ Nota funzionale

La funzione e' volutamente conservativa: applica solo la normalizzazione del
`canale_fe`, mentre la gestione del `codice` resta separata e non viene forzata
in questo trigger.

---

{% include-markdown "signature-core.md" %}
