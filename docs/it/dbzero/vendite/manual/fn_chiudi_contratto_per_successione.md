## 📘 Documentazione Concettuale – Funzione `vendite.fn_chiudi_contratto_per_successione(...)`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
>
> Funzioni correlate:
> [vendite.fn_contratto_sovrapposto](/dbzero/vendite/funzioni/fn_contratto_sovrapposto)
> [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto)
>
> Contesto di sviluppo:
> [Brief DB — successione contratti su overlap](/dev/work-done/brief-db-offerta-push-successione-contratto-overlap)

---

### 🎯 Scopo Principale

`vendite.fn_chiudi_contratto_per_successione(...)` è la **seconda metà** del
meccanismo di successione: dopo che [`fn_contratto_sovrapposto`](/dbzero/vendite/funzioni/fn_contratto_sovrapposto)
ha individuato un contratto in conflitto, questa funzione lo **accorcia** per
fare spazio al nuovo, impostando:

```text
valido_al del vecchio = (data di decorrenza del nuovo) − 1 giorno
```

Così le due finestre diventano **contigue, senza buchi né sovrapposizioni** e il
vincolo di esclusione `ex_contratti_no_overlap` viene soddisfatto. Restituisce
la nuova `valido_al` impostata.

> La "successione" è un'operazione **legittima ma esplicita**: questa funzione
> viene invocata solo dopo conferma dell'operatore (parametro
> `p_chiudi_contratto_esistente = true` nel push). Nessun percorso accorcia un
> contratto preesistente di default.

---

### Cosa fa (e cosa NON fa)

- **Accorcia, non annulla**: restringe soltanto `valido_al`. Il contratto
  esistente resta un contratto valido, solo con un periodo più breve.
- **Non cambia lo stato**: un contratto `ATTIVO` accorciato resta `ATTIVO`. La
  transizione di stato a `CESSATO` la esegue **in modo asincrono** il job
  notturno `chiusura_scadenze_daily` (framework
  `dbops.automazione_chiusura_scadenze`, su cui `vendite.contratti` è già
  configurato) quando `valido_al` risulta nel passato. La sincronizzazione
  stato↔data è "cosmetica" e centralizzata, non compito di questa funzione.
- **Non tocca `validita`**: la colonna `validita` è `GENERATED ... STORED`, si
  ricalcola da sola dall'`UPDATE` di `valido_al` nella stessa transazione, quindi
  il vincolo di esclusione è già soddisfatto per l'INSERT successivo.

---

### Guard sulle date (perché esiste)

Se il contratto esistente **inizia dopo** la data che otterrebbe come nuova
`valido_al` (cioè `valido_dal_esistente > nuovo_valido_dal − 1`), l'accorciamento
produrrebbe un intervallo invalido (`valido_al < valido_dal`). La funzione lo
intercetta **prima** e solleva `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA`, con il
numero del contratto nel messaggio.

Questa guard è **necessaria**, non ridondante: su `contratti` non esiste un
trigger parlante sulle date, ma solo il `CHECK chk_contratti_validita`, che
darebbe un errore generico e poco comprensibile. La guard lo anticipa con un
messaggio chiaro.

> **Lock post-attivazione** — il trigger
> `trg_contratti_a10_lock_post_attivazione_upd` scatta solo sull'UPDATE dei 4
> campi di *pricing* (listino, versione, tipo/valore variazione), **non** su
> `valido_al`. Accorciare la validità di un contratto `ATTIVO` è quindi un'azione
> consentita (coperta da test di regressione).

---

### Parametri

| Parametro                  | Tipo     | Note                                                          |
| -------------------------- | -------- | ------------------------------------------------------------- |
| `p_contratto_esistente_id` | `bigint` | Contratto da accorciare. Obbligatorio; bloccato `FOR UPDATE`. |
| `p_nuovo_valido_dal`       | `date`   | Data di decorrenza del nuovo contratto che succede.           |

---

### 📦 Output

| Campo          | Tipo   | Descrizione                                                       |
| -------------- | ------ | ----------------------------------------------------------------- |
| `RETURNS date` | date   | Nuova `valido_al` impostata sul contratto chiuso (`p_nuovo_valido_dal − 1`). |

---

### Codici errore

| Codice                                  | Quando                                                                 |
| --------------------------------------- | ---------------------------------------------------------------------- |
| `E_PARAMETRO_INVALIDO`                  | Parametri `NULL`, oppure contratto inesistente.                        |
| `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` | Il contratto esistente inizia dopo la decorrenza del nuovo: l'accorciamento produrrebbe `valido_al < valido_dal`. Nessuna modifica. |

---

### Esempio d'uso

```sql
-- Il nuovo contratto decorre dal 2026-05-26: chiude il vecchio (id 4821)
-- al 2026-05-25.
SELECT vendite.fn_chiudi_contratto_per_successione(4821, DATE '2026-05-26');
-- 2026-05-25  (nuova valido_al del contratto 4821)
```

---

{% include-markdown "signature-core.md" %}
