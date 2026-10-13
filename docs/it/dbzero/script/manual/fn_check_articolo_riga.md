## 📘 Documentazione Concettuale – Funzione `script.fn_check_articolo_riga`

> 👀 **Vedi anche**
>
> [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso) — il guard di tabella che la chiama
> [script.trgfn_righe_natura_vendita](/dbzero/script/manual/trgfn_righe_natura_vendita) — la natura della riga, che questa check giudica
> [config.nature_vendita](/dbzero/config/manual/nature_vendita) — le destinazioni

### 🎯 Scopo Principale

(latest review 2026-10-13, brief-db-articoli-ammessi-per-documento A-2; Lotto 3b, `20261013-55`: offerta e contratto)

Dice **perché un articolo non può stare in una riga** di un documento. `[]` vuol dire ammesso;
altrimenti un array **ordinato** di motivi `{codice, reason, reason_key, dettaglio, valori}`.

È la **sede unica** della regola: la chiama il guard di tabella, che solleva il primo motivo, e
la chiamerà il picker degli articoli, che mostra lo stesso motivo prima della scelta. Picker e
guard non possono dissentire, perché leggono la stessa funzione. Il primo motivo è lo stesso
per tutti perché **l'ordine dell'array è il contratto**, ed è scritto qui, non deciso dai nomi
dei trigger.

---

### Le regole di preventivo, ordine e bolla

| # | Motivo | Documenti | Codice |
| --- | --- | --- | --- |
| 1 | l'articolo vive solo dentro un kit | tutti | `E_ARTICOLO_SOLO_COMPONENTE` |
| 2 | la ricorrenza va in offerta | `PREVENTIVO` | `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA` |
| 2 | solo merce (destinazione `ORDINE`) | `ORDINE_VENDITA`, `DDT_VENDITA` | `E_RIGA_NATURA_NON_AMMESSA` |

Prima il solo componente: «usa il kit» viene prima di «va altrove».

La natura giudicata è **quella della riga** (`p_natura_vendita_id`, la natura congelata con cui
la riga è stata venduta), se il chiamante la passa; altrimenti quella dell'articolo, come per
una riga che ancora non esiste.

Sono tutti **motivi di articolo**: dipendono solo dall'articolo e dal documento, non dagli
altri campi della riga. È ciò che permette al picker di usarli prima che la riga esista.

### Le regole di offerta e contratto (Lotto 3b)

La riga è un'**eccezione al listino** del documento, e il tipo d'eccezione (un valore della
riga, `p_tipo_eccezione`, obbligatorio qui) decide le regole.

| # | AGGIUNTA e OVERRIDE (la riga vende) | Codice |
| --- | --- | --- |
| 1 | l'articolo vive solo dentro un kit | `E_ARTICOLO_SOLO_COMPONENTE` |
| 2 | la tipologia dell'articolo non è della utility del documento | `E_RIGA_TIPOLOGIA_FUORI_UTILITY` (composta da `script.fn_check_riga_erogazione`) |
| 3 | l'articolo non ha nessuna erogazione ammessa | `E_ARTICOLO_SENZA_EROGAZIONE` |
| 4 | AGGIUNTA di un articolo già nel listino | `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` |
| 4 | OVERRIDE: documento senza listino / articolo fuori listino (A-5) | `E_RIGA_ECCEZIONE_SENZA_LISTINO` / `_FUORI_LISTINO` |

| # | ESCLUSIONE (la riga toglie un articolo dal listino) | Codice |
| --- | --- | --- |
| 1 | l'articolo è il componente di un bundle: si esclude il bundle | `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA` (composta da `script.fn_check_esclusione_articolo_documento`) |
| 2 | documento senza listino / articolo fuori listino (A-5) | `E_RIGA_ECCEZIONE_SENZA_LISTINO` / `_FUORI_LISTINO` |

* **«Nel listino»** vuol dire una riga della versione operativa **espansa**
  (`vendite.fn_espandi_listino_versione`): le righe standalone **e** i bundle, che stanno nel
  listino coi loro componenti. È la stessa base su cui il drawer applica OVERRIDE ed ESCLUSIONE
  (`vendite.fn_documento_righe_preview`): un'eccezione fuori da lì non comparirebbe.
* L'ESCLUSIONE non giudica solo componente e tipologia: escludere una riga non la vende, e
  togliere una riga sbagliata è un bene.
* La **natura** non è una regola di offerta e contratto: il perimetro lo dicono tipologia ed
  erogazioni.
* ⚠️ **Ponte A-8.** I lettori del listino (`fn_documento_listino_operativo`,
  `fn_check_esclusione_articolo_documento`, `fn_check_riga_erogazione`,
  `fn_get_stato_testata_documento`) parlano ancora `OFFERTA | CONTRATTO`, e il backend chiama il
  primo con quei valori. La traduzione da `OFFERTA_COMMERCIALE` sta in questa funzione, in un
  punto solo, e si ritira quando quei lettori passano a `config.tipi_entita` (giro BE/FE).

---

### Firma

```sql
script.fn_check_articolo_riga(
    p_documento         text,     -- codice di config.tipi_entita
    p_documento_id      bigint,   -- l'id della testata (offerta e contratto: listino e utility)
    p_articolo_id       uuid,
    p_natura_vendita_id bigint DEFAULT NULL,
    p_tipo_eccezione    vendite.tipo_eccezione_contratto DEFAULT NULL) RETURNS jsonb
```

* `p_documento`: `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA`, `OFFERTA_COMMERCIALE` o
  `CONTRATTO`; altro solleva `E_DOC_TIPO_NON_GESTITO`. Listino e distinta entrano col 3c.
* `p_documento_id`: per offerta e contratto il listino e la utility si leggono dalla testata
  salvata (A-1), non dal form.
* `p_tipo_eccezione`: obbligatorio per offerta e contratto (`E_PARAMETRO_INVALIDO`), ignorato
  per gli altri documenti.
* Articolo `NULL` o inesistente: nessun motivo, parla la FK.

---
{% include-markdown "signature-core.md" %}
