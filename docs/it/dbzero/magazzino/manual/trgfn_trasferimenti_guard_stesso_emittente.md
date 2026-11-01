## 📘 Documentazione Concettuale – Trigger function `magazzino.trgfn_trasferimenti_guard_stesso_emittente`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — dove è montato
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — l'emittente dei due magazzini
>
> Guide:
>
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — classi e campi dei codici

---

### 🎯 Scopo Principale

**Nessuna operazione di magazzino attraversa due emittenti**: rifiuta un trasferimento i cui
due magazzini appartengono a emittenti diversi. Fra due emittenti sarebbe una cessione, con un
documento, non uno spostamento interno.

Un trasferimento ha due magazzini, e il perimetro della sicurezza di riga della tabella poggia
su quello di **origine**: questo guard copre la **destinazione**. È montato prima
dell'inserimento e dell'aggiornamento.

---

### È un dato errato, e il form lo sa

La destinazione la sceglie una persona: classe `DATO_ERRATO`, campo `magazzino_id_to`,
messaggio che nomina i due magazzini. Il frontend accende il campo giusto.

---

### Sotto la sicurezza di riga, un magazzino che non si vede non è proprio

La funzione legge `magazzini` con i diritti di chi scrive: per un operatore, un magazzino
fuori perimetro **non risolve** (mentre la chiave esterna, che la sicurezza di riga non la
vede, passerebbe). Si rifiuta anche allora, con lo stesso codice — dal punto di vista di chi
scrive, un magazzino che non può vedere non è del suo emittente. È fail-closed.

---

### Codici errore

* `E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI` — i due magazzini sono di emittenti diversi, o uno
  dei due non è visibile a chi scrive.

---

### Test

`db/pgtap/rls/test-rls-magazzino-perimetro-v1.sql` (test 9).

---

### Note di migrazione

* 2026-09-15 — nasce con `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7, M-6).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
