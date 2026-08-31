## 📘 Documentazione Concettuale – Funzione `vendite.fn_push_preventivo_a_ordine`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
>
> Funzioni:
> [vendite.fn_preventivo_ha_residuo_ordine](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_ordine)
> [vendite.fn_preventivo_ha_residuo_commessa](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_commessa)
>
> WIP:
> [Analisi e piano di fix — gestione transazioni backend](/dev/work-done/analisi-fix-transazioni) (Classe A, finding #10)
> [Roll-out multi-dominio GUIDA](/dev/work-in-progress/brief-design-guida-rollout-multidominio) (decisione D-B, `flusso_id`)

### 🎯 Scopo Principale

(latest review 08-07-2026)

La funzione **`vendite.fn_push_preventivo_a_ordine`** copia le righe MERCE di un
preventivo `ACCETTATO` verso un nuovo **ordine `DRAFT`** con
`documento_origine=(PREVENTIVO, id)`, snapshot prezzi e idempotenza di riga.

**Estensione 08-07-2026 (migr. `20260708-01`)** su due assi:

* **Transizione EVASO atomica (finding #10).** La transizione del preventivo
  `ACCETTATO → EVASO` — prima una chiamata *separata* del service
  (`transiziona_a_evaso_se_smistato`, non atomica) — è ora **dentro la funzione**
  (sezione 8): gate bi-ramo (`fn_preventivo_ha_residuo_ordine` +
  `fn_preventivo_ha_residuo_commessa`), atomico con la creazione dell'ordine.
  Niente più «ordine creato + preventivo bloccato in ACCETTATO».
* **`flusso_id` sul link COLLEGATO (D-B).** Nuovo parametro `p_flusso_id`
  (`DEFAULT NULL`, retro-compatibile): valorizza `pratiche_sorgenti.flusso_id`
  sul link `ORDINE` COLLEGATO alla generazione (lo step generatore conosce il
  proprio flusso).

---

### Firma

```sql
vendite.fn_push_preventivo_a_ordine(
    p_preventivo_id        vendite.preventivi.id%TYPE,
    p_righe_ids            bigint[] DEFAULT NULL,
    p_pratica_id           pratiche.pratiche.id%TYPE DEFAULT NULL,
    p_fatturazione_trigger vendite.ordini.fatturazione_trigger%TYPE DEFAULT NULL,
    p_flusso_id            pratiche.pratiche_sorgenti.flusso_id%TYPE DEFAULT NULL
) RETURNS vendite.ordini.id%TYPE
```

> `p_righe_ids` resta `bigint[]` esplicito: PostgreSQL non ammette `colonna%TYPE[]`.

### Parametri di Input

| Parametro | Descrizione |
| --- | --- |
| `p_preventivo_id` | Preventivo `ACCETTATO` sorgente (obbligatorio). |
| `p_righe_ids` | Sottoinsieme di righe da smistare (NULL = tutte le residue). |
| `p_pratica_id` | Se valorizzato, aggancia i link `pratiche_sorgenti` (preventivo `ROOT` + ordine `COLLEGATO`). |
| `p_fatturazione_trigger` | Trigger di fatturazione dell'ordine (default `CONFERMATO`). |
| `p_flusso_id` | **D-B**: flusso dello step generatore, scritto su `flusso_id` del link `COLLEGATO`. Guard `coerenza_flusso` verifica che appartenga alla pratica. |

### Note tecniche

* Firma estesa a **5 parametri** con `DROP FUNCTION` + `CREATE` (aggiungere un
  parametro cambia la firma). `p_flusso_id` ultimo con `DEFAULT NULL` → i
  chiamanti esistenti (3-4 argomenti) restano validi.
* Numero/serie/anno dell'ordine generati dal trigger `trgfn_ordini_gen_numero`;
  audit/tx_id/validità dai trigger esistenti.
* **Follow-up BE**: rimuovere la chiamata separata
  `transiziona_a_evaso_se_smistato` dal percorso ordine-standalone (ora
  ridondante — la funzione transita già; il re-push è bloccato dal guard *stato*
  perché il preventivo diventa EVASO, non più da «nessuna riga»).
