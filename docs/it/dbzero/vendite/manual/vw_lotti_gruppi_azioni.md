## 📘 Documentazione Concettuale – Vista `vendite.vw_lotti_gruppi_azioni`

> 👀 **Vedi anche**
>
> [config.azioni_riga](/dbzero/config/tabelle/azioni_riga) ·
> [script.fn_check_documento_escludibile_da_giro](/dbzero/script/funzioni/fn_check_documento_escludibile_da_giro) ·
> [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro) ·
> [linee guida SQL](/linee-guida-sql) §12.5

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15.10, Q-F5)

**Le azioni di riga dei documenti di un lotto di fatturazione.** Per ogni documento del lotto dice
se si può togliere dal giro e, se no, perché; e quanti altri documenti verrebbero via insieme.

È la **superficie** dell'azione `ESCLUDI_DOCUMENTO_DA_GIRO` nel registro
[`config.azioni_riga`](/dbzero/config/tabelle/azioni_riga). Prima queste colonne le componeva il
repository del backend; ora il backend le legge da qui.

### Le colonne

| Colonna | Cosa dice |
| --- | --- |
| `lotto_id`, `gruppo_key` | il documento nel lotto |
| `uscita_blocco_reason` | il motivo per cui «togli dal giro» è spento; `NULL` = si può togliere |
| `uscita_blocco_reason_key` | la chiave di traduzione dello stesso motivo |
| `n_trascinati` | quanti documenti vengono via insieme; solo dove l'azione è viva |

### Regole

* I documenti del lotto sono il **perimetro dichiarato** unito agli **esiti**: un giro di massa non
  dichiara il perimetro, un giro mirato ha documenti non ancora tentati.
* Il motivo è il **primo** della `fn_check`: è quello con cui la funzione che esegue l'azione
  rifiuta, quindi pulsante ed errore dicono la stessa cosa.
* `security_invoker`: si leggono solo i lotti del proprio perimetro. Si filtra per `lotto_id`.

---

{% include-markdown "signature-core.md" %}
