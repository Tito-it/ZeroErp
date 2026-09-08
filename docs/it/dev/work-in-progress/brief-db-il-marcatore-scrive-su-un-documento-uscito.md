# Brief DB — il marcatore del pull scrive su un documento uscito dal giro

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-08. **A chi:** team DB.
> **Cantieri che si incontrano:**
> [uscita-documento-dal-giro](../work-done/brief-db-uscita-documento-dal-giro.md)
> e [esito-gruppo-lotto](../work-done/brief-db-esito-gruppo-lotto.md).
>
> **In una riga:** `fn_segna_esito_gruppo_lotto` marca **tutti** i documenti di
> una commessa, compresi quelli `ESCLUSO`. Il trigger dell'uscita rifiuta — e fa
> bene — ma il rifiuto **abbatte il rilancio**. ⇒ Il verbo che esiste per far
> ripartire un lotto lo rende impossibile da rilanciare.

---

## 1. Come è nato

Collaudo a video di Tid, 2026-09-08. Lotto **`LTF-0010263`**: tolto dal giro
`ORDINE_VENDITA:01a06ce4-b46a-…` — **riuscito**, esito `ESCLUSO` con motivo e
timbro — e premuto **«Rilancia step»**.

```
E_PIPELINE · http 400 · request_id 22868c56-a57b-4ebf-9838-c18a2aea1ca9
```

---

## 2. Che cosa abbiamo analizzato

La catena, dai log applicativi:

| # | Chi | Che cosa succede |
| --- | --- | --- |
| 1 | `fn_emit_attivita_fatturabili_da_commessa` | commessa 34137 fallisce — **atteso**, è il guasto del collaudo, e il fan-out lo isola |
| 2 | `_marca_esito_gruppi` (BE) | annota il fallimento: `fn_segna_esito_gruppo_lotto(lotto, 'ERRORE', commessa_id => 34137)` |
| 3 | `fn_segna_esito_gruppo_lotto` | risolve commessa → documenti e fa l'upsert su **tutti**, compreso quello uscito |
| 4 | `trgfn_fatturazione_lotti_esiti_uscita` | rifiuta: `E_LOTTO_DOC_USCITA_IRREVERSIBILE` |
| 5 | — | l'eccezione **esce** dal marcatore e diventa `E_PIPELINE` 400 |

**Tre cose verificate, perché cambiano il perimetro del problema:**

1. ⭐ **Il rifiuto è corretto.** `ESCLUSO` è terminale (D-3). Non chiediamo di
   allentarlo: è il **tentativo** a non doverci essere.
2. ⚠️ **La premessa del codice a catalogo non regge più.**
   `E_LOTTO_DOC_USCITA_IRREVERSIBILE` è `TECNICO` perché *«qui ci arriva solo un
   UPDATE diretto: la madre chiede prima alla sua check»*. Qui a scrivere è il
   percorso normale del backend.
3. ⛔ **Non si aggira ripristinando la ROOT di 34137.** Il trigger guarda la
   **direzione**: se il pull riuscisse, il marcatore scriverebbe `COMPLETED` su
   quel documento e il rifiuto sarebbe identico. Il lotto è fermo nei due versi.

⛔ **Non è un caso di nicchia: è la linea principale.** Si toglie dal giro un
documento *perché* il suo pull fallisce; al rilancio quel pull fallisce ancora,
il marcatore riprova, il giro muore.

⚠️ **E nessun pgTAP poteva vederlo**: i presidi provano le funzioni una per una,
questo nasce dalla **sequenza**.

---

## 3. ⭐ La regola esiste già, in due posti su tre

Il `20260908-07` ha insegnato al **conteggio** a scartare le critiche di un
documento uscito — è la ragione per cui su `LTF-0010263` `evaluate_lotto_status`
dice `critical = 0` mentre la critica è ancora lì. Il **trigger** lo sa. Il
**marcatore** no.

⇒ *Un documento fuori dal giro non si marca, non si conta, non blocca.*

---

## 4. 🔵 Che cosa serve

**Che il marcatore non tenti di scrivere su un documento che ha già lasciato il
giro.**

⚠️ **E non lo filtriamo dal backend**: sarebbe la terza sede di una regola che il
database possiede già in due punti, e la terza è quella che diverge.

### Due cose da decidere nello stesso giro, non dopo

1. 🔵 **Distinguere i due zeri del marcatore.** Con lo scarto, una commessa il
   cui unico documento è uscito produrrà **zero righe marcate** — e il backend lì
   ha un avviso in servizio (`pull_commesse.esito_non_appeso`) che diventerebbe
   rumore su un caso legittimo. Ci serve separare «nessun documento appeso a
   questa commessa» (difetto) da «gli unici documenti sono usciti» (normale). La
   forma è vostra.
2. 🔵 **La segnalazione critica per documento.** Al rilancio il backend ne
   riscrive una per ogni documento della commessa fallita, compreso quello
   uscito. Non blocca — il conteggio la scarta — ma se ne accumula una a ogni
   rilancio su un documento che non è più in gioco. Va scartata anche lì, o è un
   fatto da registrare? È la D-6 vista dal lato di chi scrive.

---

## 5. Dove siamo intanto

`LTF-0010263` **non è rilanciabile**: l'unica via che il modello lascia è
annullare il lotto e rigenerare. ⚠️ Che è anche la misura di quanto pesa — il
verbo «togli dal giro» esiste per non dover annullare il lotto.
