## 📘 Documentazione Concettuale – Funzione `script.fn_check_articolo_riga`

> 👀 **Vedi anche**
>
> [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso) — il guard di tabella che la chiama
> [script.trgfn_righe_natura_vendita](/dbzero/script/manual/trgfn_righe_natura_vendita) — la natura della riga, che questa check giudica
> [config.nature_vendita](/dbzero/config/manual/nature_vendita) — le destinazioni
> [script.fn_articolo_riga_contesto](/dbzero/script/manual/fn_articolo_riga_contesto) e [script.fn_check_articolo_riga_su_contesto](/dbzero/script/manual/fn_check_articolo_riga_su_contesto) — le due metà che compone
> [catalogo.fn_articoli_ammessi](/dbzero/catalogo/manual/fn_articoli_ammessi) — il picker, che chiama le due metà

### 🎯 Scopo Principale

(latest review 2026-10-14, brief-db-articoli-ammessi-per-documento A-2; Lotto 3b, `20261013-55`: offerta e contratto; Lotto 3c, `20261013-59`: versione di listino e distinta; Lotto 4, `20261014-03`: due metà, e la promo; `20261014-06`: il kit senza componenti, D-7)

Dice **perché un articolo non può stare in una riga** di un documento. `[]` vuol dire ammesso;
altrimenti un array **ordinato** di motivi `{codice, reason, reason_key, dettaglio, valori}`.

È la **sede unica** della regola: la chiama il guard di tabella, che solleva il primo motivo, e
il picker degli articoli ([catalogo.fn_articoli_ammessi](/dbzero/catalogo/manual/fn_articoli_ammessi))
mostra lo stesso motivo prima della scelta. Picker e guard non possono dissentire, perché
leggono la stessa regola. Il primo motivo è lo stesso
per tutti perché **l'ordine dell'array è il contratto**, ed è scritto qui, non deciso dai nomi
dei trigger.

---

### Le regole di preventivo, ordine e bolla

| # | Motivo | Documenti | Codice |
| --- | --- | --- | --- |
| 1 | l'articolo vive solo dentro un kit | tutti | `E_ARTICOLO_SOLO_COMPONENTE` |
| 2 | il kit non ha nessun componente attivo (D-7) | tutti | `E_ARTICOLO_KIT_SENZA_COMPONENTI` |
| 3 | la ricorrenza va in offerta | `PREVENTIVO` | `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA` |
| 3 | solo merce (destinazione `ORDINE`) | `ORDINE_VENDITA`, `DDT_VENDITA` | `E_RIGA_NATURA_NON_AMMESSA` |

Prima il solo componente: «usa il kit» viene prima di «va altrove». Il kit vuoto viene subito
dopo: non si vende in nessun documento.

**Il kit senza componenti** (dal 2026-10-14, `20261014-06`): «vuoto» vuol dire nessun legame
attivo nella distinta, a qualunque data. L'inizializzazione dei componenti giudica invece i
componenti validi **alla data del documento** (`E_DOC_COMPOSITO_BOM_VUOTA`): la check rifiuta
solo ciò che l'init rifiuterebbe sempre, e il caso «componenti che ci sono ma non a quella
data» resta all'init.

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
| 2 | il kit non ha nessun componente attivo (D-7) | `E_ARTICOLO_KIT_SENZA_COMPONENTI` |
| 3 | la tipologia dell'articolo non è della utility del documento | `E_RIGA_TIPOLOGIA_FUORI_UTILITY` (composta da `script.fn_check_riga_erogazione`) |
| 4 | l'articolo non ha nessuna erogazione ammessa | `E_ARTICOLO_SENZA_EROGAZIONE` |
| 5 | AGGIUNTA di un articolo già nel listino | `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` |
| 5 | OVERRIDE: documento senza listino / articolo fuori listino (A-5) | `E_RIGA_ECCEZIONE_SENZA_LISTINO` / `_FUORI_LISTINO` |

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
### Le regole di versione di listino e distinta (Lotto 3c)

| # | Versione di listino (`LISTINO_VERSIONE`, la riga di `vendite.listini_righe`) | Codice |
| --- | --- | --- |
| 1 | l'articolo vive solo dentro un kit (D-3) | `E_ARTICOLO_SOLO_COMPONENTE` |
| 2 | composito: nella versione entra coi componenti, non come riga | `E_LISTINO_RIGA_COMPOSITO_VIETATO` |
| 3 | tipologia mancante, o diversa da quella del listino | `E_ARTICOLO_TIPOLOGIA_MANCANTE` / `_INCOMPATIBILE` |

| # | Distinta (`ARTICOLO`, la riga di `catalogo.articoli_componenti`; serve `p_articolo_padre_id`) | Codice |
| --- | --- | --- |
| 1 | il componente è il padre stesso | `E_BOM_COMPONENTE_PADRE` |
| 2 | il componente è composito (D-4) | `E_BOM_COMPONENTE_COMPOSITO` |
| 3 | IVA diversa dal padre | `E_BOM_IVA_DISCORDANTE` |

Nella distinta il «solo componente» è il caso normale, non un motivo. Le regole sul **padre**
(deve essere composito, non può essere solo componente) restano nei loro guard: sono della
testata, non della riga.

### La promo (Lotto 4, D-6)

Una promo si crea solo se il calcolo del prezzo la può applicare.

| # | Promo (`PROMO_ARTICOLO`, la riga di `vendite.promo_articoli`) | Codice |
| --- | --- | --- |
| 1 | l'articolo vive solo dentro un kit: non ha un prezzo suo, e dentro un kit il resolver non applica le promo | `E_PROMO_ARTICOLO_SOLO_COMPONENTE` |

Il **composito** invece è ammesso: il resolver gli dà un prezzo suo quando il contratto ha
un'eccezione su di lui (AGGIUNTA o OVERRIDE), e su quel prezzo la promo si applica.
`p_documento_id` qui non si legge: la promo non ha una testata.

### Due metà: il documento e i motivi (Lotto 4)

Dal 2026-10-14 il corpo è la composizione di due funzioni:

* [script.fn_articolo_riga_contesto](/dbzero/script/manual/fn_articolo_riga_contesto) valida i
  parametri e legge **il lato documento** (listino operativo, versione espansa, tipologia del
  listino, padre della distinta);
* [script.fn_check_articolo_riga_su_contesto](/dbzero/script/manual/fn_check_articolo_riga_su_contesto)
  scrive **i motivi** di un articolo su quel contesto.

Le regole, l'ordine e i codici non sono cambiati. Serve al picker: valuta molti articoli sullo
stesso documento, e il documento lo legge una volta sola invece che per ogni articolo.

### Note

* ⚠️ **Ponte A-8.** I lettori del listino (`fn_documento_listino_operativo`,
  `fn_check_esclusione_articolo_documento`, `fn_check_riga_erogazione`,
  `fn_get_stato_testata_documento`) parlano ancora `OFFERTA | CONTRATTO`, e il backend chiama il
  primo con quei valori. La traduzione da `OFFERTA_COMMERCIALE` sta in un punto solo, il
  contesto ([script.fn_articolo_riga_contesto](/dbzero/script/manual/fn_articolo_riga_contesto)), e si ritira quando quei lettori passano a `config.tipi_entita` (giro BE/FE).

---

### Firma

```sql
script.fn_check_articolo_riga(
    p_documento         text,     -- codice di config.tipi_entita
    p_documento_id      bigint,   -- l'id della testata (offerta e contratto: listino e utility)
    p_articolo_id       uuid,
    p_natura_vendita_id bigint DEFAULT NULL,
    p_tipo_eccezione    vendite.tipo_eccezione_contratto DEFAULT NULL,
    p_articolo_padre_id uuid DEFAULT NULL) RETURNS jsonb
```

* `p_documento`: `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA`, `OFFERTA_COMMERCIALE` o
  `CONTRATTO`, `LISTINO_VERSIONE` (`p_documento_id` = la versione), `ARTICOLO` (la distinta) o
  `PROMO_ARTICOLO`; altro solleva `E_DOC_TIPO_NON_GESTITO`.
* `p_documento_id`: per offerta e contratto il listino e la utility si leggono dalla testata
  salvata (A-1), non dal form.
* `p_tipo_eccezione`: obbligatorio per offerta e contratto (`E_PARAMETRO_INVALIDO`), ignorato
  per gli altri documenti.
* `p_articolo_padre_id`: il padre della distinta, obbligatorio per `ARTICOLO`
  (`E_PARAMETRO_INVALIDO`); la testata della distinta è un articolo, con un id `uuid`.
* Articolo `NULL` o inesistente: nessun motivo, parla la FK.

---
{% include-markdown "signature-core.md" %}
