## Documentazione Concettuale – Funzione `vendite.fn_get_sorgente_documento_ref(...)`

> **Versione**: 2026-08-20 (richiesta BE punto 2 ·
> `brief-design-note-credito-resi` §40.1.4 · migration `20260820-04`)
>
> **Sostituisce** `vendite.fn_get_sorgente_documento_id`, tolta nel `20260820-06`.

> **Vedi anche**
>
[config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.fn_list_commessa_attivita](/dbzero/vendite/funzioni/fn_list_commessa_attivita)
> [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente)
>
**Guide**: [sorgente polimorfa](/guide/sorgente-polimorfa)

---

### 🎯 Scopo Principale

Dire **qual è il documento di origine** di una riga a sorgente polimorfa, in due
informazioni e **una sola lettura**:

| Colonna | A cosa serve |
| --- | --- |
| `documento_id` | l'id numerico su cui il frontend costruisce l'azione «apri documento sorgente» |
| `documento_numero` | il numero che l'operatore **legge**: `DDT0010839`, `ORD0000227`, `PRV0000081` |

---

### Perché una funzione e non una join

La tabella di destinazione **cambia con la sorgente**
(`config.sorgenti.target_table`, un `regclass`): in una query set-based
servirebbe un `LEFT JOIN` per ogni dominio possibile — quindici, di cui tre
usati — e ognuno diventerebbe una riga da mantenere quando nasce un dominio
nuovo. La funzione legge la destinazione **dal catalogo**.

### Perché una sola funzione e non due

La risoluzione della chiave (regex uuid, lettura di `target_table`,
`key_selector`) è **identica** per l'id e per il numero. Due funzioni gemelle
vorrebbero **due `EXECUTE` per riga di lista** e **due copie della stessa
regola**: la copia sopravvissuta è quella che al primo ritocco diverge.

---

### ⭐ L'etichetta si **dichiara**, non si indovina

La colonna che porta il numero leggibile arriva da
[`config.sorgenti.label_selector`](/dbzero/config/tabelle/sorgenti), gemella di
`key_selector`. Non è uniforme:

| Sorgente | `label_selector` |
| --- | --- |
| `PREVENTIVO`, `CONTRATTO`, `ORDINE_VENDITA`, `DDT_VENDITA`, `RESO_VENDITA`, `FATTURA` | `numero` |
| `OFFERTA_COMMERCIALE`, `COMMESSA` | `codice` |
| `ATTIVITA`, `ATTIVITA_CONSUMI`, le cinque `*_RIGA` | *(nessuna)* |

> ⚠️ Un `COALESCE(numero, codice)` letto via `to_jsonb` funzionerebbe **oggi** e
> diventerebbe una colonna vuota **in silenzio** alla terza convenzione. È lo
> stesso *«non si indovina»* che la funzione applica già alla chiave.

`label_selector` a `NULL` ⇒ `documento_numero` è `NULL` e basta: **non** è un
errore e **non** spegne `documento_id`.

---

### Le tre cose che si comporta bene a sapere

1. ⚠️ **Il ramo uuid è l'unico che il dato percorre.** Misurato il 16-08-2026:
   **88 righe su 88** di `commesse_attivita` hanno un UUID in `sorgente_uid`,
   ordini e DDT compresi — che sono tipi a chiave `id`. La normalizzazione a
   `id::text` vale per `commesse_sorgenti`, **non** per questa colonna. Chi
   tratta «id numerico» come caso principale torna `NULL` su tutto, **senza
   errore**.

2. ⚠️ **Non solleva mai.** Una sorgente irrisolvibile è il caso **normale**: le
   voci manuali, gli **oneri** e le **rettifiche** un documento a monte non ce
   l'hanno per progetto. Qui si risponde a una **lista**, e l'esito giusto è
   l'azione «apri» che sparisce.
   È la differenza con `fn_link_commessa_sorgente`, che **scrive** un legame e
   davanti a una chiave irrisolvibile alza `E_SORG_NORM_NON_RISOLTA`: *fail-closed
   dove si scrive, silenzioso dove si guarda.*

3. ⭐ **Restituisce sempre una riga**, anche tutta a `NULL`. Una `RETURNS TABLE`
   che a volte torna zero righe funziona bene con `LEFT JOIN LATERAL … ON TRUE`
   e **cancella la riga chiamante** il giorno in cui qualcuno scrive
   `CROSS JOIN LATERAL` per distrazione. Una riga sempre presente rende
   quell'errore **impossibile** invece che improbabile.

> ⚠️ **`SECURITY INVOKER`**: le tabelle di destinazione hanno la RLS operatori.
> `NULL` significa «non risolvibile **o** non visibile a chi chiede», **non**
> «non esiste».

> ⚠️ **Se il catalogo mente, cade tutto — di proposito.** Un `label_selector`
> che nomina una colonna inesistente fa scattare `undefined_column`, e la
> funzione risponde `NULL` **anche sull'id**. Un ripiego che salvasse l'id e
> perdesse il solo numero renderebbe il refuso ancora più difficile da vedere:
> una colonna vuota fra molte piene. Così invece sparisce anche l'azione «apri»,
> e qualcuno lo nota. Il cancello vero resta il pgTAP
> (`test-fn-list-commessa-attivita-provenienza-v1`, test 10 e 11).

---

### Esempio d'uso

```sql
-- Come la usa la lista attività di commessa: LATERAL, una chiamata per riga.
SELECT ca.id,
       ref.documento_id     AS sorgente_documento_id,
       ref.documento_numero AS sorgente_documento_numero
  FROM vendite.commesse_attivita ca
  LEFT JOIN LATERAL vendite.fn_get_sorgente_documento_ref(
           ca.sorgente_tipo_id, ca.sorgente_uid) ref ON TRUE
 WHERE ca.commessa_id = 12345;
```

---

{% include-markdown "signature-core.md" %}
