## 📘 Documentazione Concettuale – Funzione `script.fn_gruppi_trascinati_da_uscita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti)
>
**Approfondimento funzioni:**
>
• [script.vw_lotto_documento_righe](/dbzero/script/views/vw_lotto_documento_righe)
> • [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

Risponde a: **«se tolgo questo documento dal giro, chi viene via insieme a
lui?»**

Ritorna l'elenco degli **altri** documenti del lotto che condividono una bozza
con quello indicato — quelli che, cancellata la bozza, tornerebbero **«da
emettere»**. `[]` quando l'uscita non trascina nessuno.

---

### Perché la domanda ha senso

Una bozza di fattura può contenere righe di **più documenti**: come le attività
si raggruppano in un documento fiscale lo decide il motore della fatturazione, e
niente garantisce una corrispondenza uno-a-uno fra documento fiscale e documento
di origine.

Togliere un documento dal giro **cancella la sua bozza** — e con essa le righe
degli altri che c'erano dentro. Quegli altri non vengono persi: tornano
disponibili e si fatturano al giro successivo. Ma **l'operatore deve saperlo
prima di confermare**, non scoprirlo dopo.

⭐ Nel caso più comune la risposta è `[]`: un documento che fallisce **prima** di
diventare fattura non ha mai avuto una bozza, quindi non trascina nessuno.

---

### Una funzione, tre consumatori

| Chi | Che cosa se ne fa |
| --- | --- |
| la **lista a video** | dice *quanti* sono, prima che si prema il pulsante |
| la **conferma** | li nomina |
| [`vendite.fn_escludi_documento_da_giro`](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro) | sa a chi rimettere l'esito in coda |

⭐ **Scritta tre volte**, il giorno in cui una delle tre cambia l'operatore vede
un numero e ne subisce un altro.

---

### Regole

* Funzione **pura**: non scrive niente.
* Guarda **solo dentro il lotto indicato**: una fattura di un altro lotto che
  contenesse lo stesso documento non viene toccata dall'uscita.
* La catena che lega una riga di fattura al suo documento vive in
  [`script.vw_lotto_documento_righe`](/dbzero/script/views/vw_lotto_documento_righe),
  e **solo lì** — è una catena facile da sbagliare, e la sua trappola è spiegata
  nella doc di quella vista.
* ⛔ **La bozza condivisa non è un motivo di rifiuto.** Rifiutare l'uscita
  lascerebbe bloccati anche i documenti di un'**altra** bozza, che non c'entrano
  niente: sarebbe il problema di partenza, in forma più stretta.

---

### Esempio d'uso

```sql
-- Chi verrebbe via insieme a questo documento
SELECT script.fn_gruppi_trascinati_da_uscita(
    11221, 'ORDINE_VENDITA:01a06ce4-35a6-721a-9cd8-9da48bf77626'
);
-- ["ORDINE_VENDITA:01a07b75-b611-749d-9ac3-8941e6cce0f1"]

-- Quanti sono, per la frase di conferma
SELECT jsonb_array_length(
    script.fn_gruppi_trascinati_da_uscita(11221, 'ORDINE_VENDITA:...')
);
```

> Piano e decisioni: `docs/it/dev/work-in-progress/brief-db-uscita-documento-dal-giro.md`.

---

{% include-markdown "signature-core.md" %}
