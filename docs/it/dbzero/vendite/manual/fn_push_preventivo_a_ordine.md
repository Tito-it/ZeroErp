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
  ⭐ rev 2026-10-12 (`20261012-13`, brief-db-annullo-a-valle-riapre-a-monte
  D-10): la sezione 8 non scrive più la regola, chiama il building block
  [`fn_preventivo_proietta_stato_smistamento`](/dbzero/vendite/funzioni/fn_preventivo_proietta_stato_smistamento),
  la sede unica di `ACCETTATO ↔ EVASO` (la leggono anche l'annullo dell'ordine e
  l'invio in commessa). Stesso esito.
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

### 🔄 rev 2026-09-13 — la data di consegna sopravvive al push

`20260913-20`: la **data richiesta dal cliente** sulla riga di preventivo passa
sulla riga d'ordine. La funzione la legge dalla vista-predicato
`vw_preventivi_righe_smistabili_ordine` (che dal `20260913-16` la espone), non
con una lettura sua delle righe. La **data confermata** resta vuota: è la
promessa nostra, e si decide alla conferma dell'ordine — su un preventivo non
c'è ancora niente da confermare. Tolto dal commento del passo 4 il nome di una
funzione che non esiste più: il numero dell'ordine lo assegna
`trgfn_ordini_gen_numero`, dal motore dei registri. Brief:
`brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezione 2.4.

### 🔄 rev 2026-10-13 — una richiesta già passata arriva vuota

`20261013-67`, collaudo date di consegna. Una consegna non viene prima del
documento ([script.fn_data_consegna_ammessa](/dbzero/script/manual/fn_data_consegna_ammessa)),
e l'ordine nasce con la data di oggi: una richiesta del cliente **anteriore**
alla data dell'ordine arriva `NULL` sulla riga d'ordine. Decisione di Tid fra tre
strade:

| Strada | Perché no / perché sì |
| --- | --- |
| rifiutare il push | ⛔ il preventivo è `ACCETTATO`, fuori bozza: la sua data non si correggerebbe più, e lo smistamento resterebbe fermo |
| portarla alla data dell'ordine | ⛔ nella colonna della richiesta del cliente finirebbe una richiesta che il cliente non ha fatto |
| **azzerarla** | ✅ la richiesta vera resta sulla riga di preventivo (`preventivo_riga_id`); l'ordine nasce `DRAFT` e l'operatore la riscrive |

Senza questa scelta il guard di riga
([script.trgfn_doc_righe_guard_data_consegna](/dbzero/script/manual/trgfn_doc_righe_guard_data_consegna))
rifiuterebbe l'INSERT. Presidio:
`db/pgtap/vendite/test-data-consegna-vs-data-documento-v1.sql`, test 17-19.
