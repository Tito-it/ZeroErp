## 📘 Documentazione Concettuale – Funzione `vendite.fn_escludi_documento_da_giro`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti) — l'esito del documento, che diventa `ESCLUSO`
> * [vendite.fatturazione_lotti_gruppi](/dbzero/vendite/tabelle/fatturazione_lotti_gruppi) — il perimetro del giro, che non si tocca
> * [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture) — le bozze del lotto
>
> Approfondimento funzioni:
>
> * [script.fn_check_documento_escludibile_da_giro](/dbzero/script/funzioni/fn_check_documento_escludibile_da_giro) — i motivi
> * [script.fn_gruppi_trascinati_da_uscita](/dbzero/script/funzioni/fn_gruppi_trascinati_da_uscita) — i documenti trascinati
> * [vendite.fn_elimina_fattura_da_lotto](/dbzero/vendite/funzioni/fn_elimina_fattura_da_lotto) — il verbo che toglie le bozze
> * [vendite.fn_get_lotto_segnalazioni_summary](/dbzero/vendite/funzioni/fn_get_lotto_segnalazioni_summary) — chi conta per fermare il giro
> * [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il permesso: l'azione `reset_lotto_fattura_draft`
>
> Guide:
>
> * [Fatturazione](/guide/fatturazione) — le vie d'uscita da un lotto, e chi le può prendere

---

### 🎯 Scopo Principale

**Un documento rotto non deve tenere in ostaggio tutto il giro.**

Un giro di fatturazione prende in carico più documenti. Se uno è rotto, il lotto
va in errore e si ferma: gli altri, che hanno già le loro bozze pronte, non
vengono emessi. Prima di questa funzione l'unica azione che il database offriva
su un lotto fermo era **annullarlo** — cioè buttare via il giro intero, bozze
sane comprese.

`vendite.fn_escludi_documento_da_giro` è il verbo che permette all'operatore di
dire: *«questo documento esce da questo giro, per questo motivo»*. Il lotto
riparte con quelli che restano.

---

### Chi la chiama, con quale permesso e su quale lotto

È il verbo dell'endpoint «escludi dal giro». Gira come proprietario (`SECURITY DEFINER`), fuori
dalla row security, quindi permesso e perimetro li controlla lei, all'ingresso:

* **il permesso**, in prima riga: l'azione `reset_lotto_fattura_draft`
  ([`script.fn_guard_azione`](/dbzero/script/funzioni/fn_guard_azione)), la stessa dell'endpoint.
  Senza l'azione: `E_PERMESSO_NEGATO`;
* **il perimetro**, sul lotto, prima dei motivi: un lotto di un'altra azienda risponde
  `E_LOTTO_NON_TROVATO`, come un lotto che non esiste. Le fatture del documento le toglie
  `fn_elimina_fattura_da_lotto`, che rimette il perimetro su ognuna. Chiede la stessa azione, quindi
  il controllo ripetuto non nega niente di nuovo.

**Le porte spente all'ingresso.** Il verbo spegne la GUC del reset del lotto e quella delle righe
contabili prima di cominciare.

---

### Che cosa fa, in ordine

1. **Chiede i motivi**, e non li decide da sé: interroga
   [`script.fn_check_documento_escludibile_da_giro`](/dbzero/script/funzioni/fn_check_documento_escludibile_da_giro)
   e, se c'è anche un solo motivo ostativo, solleva quello **in testa**.
2. **Guarda chi viene via insieme**, *prima* di cancellare qualcosa: una bozza
   può contenere righe di più documenti.
3. **Cancella le bozze** che contengono il documento, componendo
   [`vendite.fn_elimina_fattura_da_lotto`](/dbzero/vendite/funzioni/fn_elimina_fattura_da_lotto)
   — la primitiva che esisteva già, con la sua semantica già decisa.
4. **Marca il documento come uscito**, con il motivo scritto dall'operatore.
5. **Rimette in coda i documenti trascinati**.

---

### Le regole che vale la pena conoscere

#### Il motivo è obbligatorio

Un documento che esce senza motivo è una riga che fra un mese nessuno sa
spiegare. Il motivo lo scrive l'operatore, ed è rifiutato anche se fatto di soli
spazi.

#### Non si torna indietro

`ESCLUSO` è uno stato **terminale**: il documento uscito non rientra in quel
lotto. Se serve fatturare tutto insieme, la strada è **annullare il lotto,
correggere il documento e rigenerare il giro** — una via che esiste già.

#### Escono solo i documenti in errore

Il verbo esiste per sbloccare un giro fermo, non per svuotarlo a mano. Un
documento sano non si toglie: se non deve essere fatturato, non lo si mette nel
perimetro, oppure si annulla e si rigenera.

#### La bozza condivisa viene cancellata lo stesso, e **trascina**

Se la bozza copre anche altri documenti, viene cancellata comunque e quegli
altri tornano **«da emettere»**: si fatturano al giro successivo. La bozza è
pre-fiscale — nessun numero, nessun effetto — quindi non si distrugge niente, si
rimanda.

> ⚠️ **Perché non si rifiuta, in quel caso.** Rifiutare lascerebbe bloccato anche
> chi sta in un'**altra** bozza e non c'entra niente: sarebbe il sequestro di
> partenza, in forma più stretta.

I documenti trascinati tornano allo stato **`PENDING`** — *preso in carico, non
ancora concluso* — e non a `ESCLUSO` (non sono usciti da niente) né restano a
`COMPLETED` (non hanno più una fattura).

#### Il lotto ricorda di averlo preso in carico

Il **perimetro** del giro non viene toccato: se fra un mese qualcuno chiede
perché quel documento non è in quella fattura, la risposta deve stare nel lotto.

#### Nessuna segnalazione viene ritirata

Le criticità restano tutte leggibili. Cambia soltanto **chi conta** per fermare
il giro: la segnalazione di un documento uscito non blocca più, perché il suo
documento non è più in gioco. Il meccanismo è in
[`vendite.fn_get_lotto_segnalazioni_summary`](/dbzero/vendite/funzioni/fn_get_lotto_segnalazioni_summary).

---

### Output

Un `jsonb` con il consuntivo di ciò che è stato fatto — serve a chi chiama per
raccontarlo all'operatore:

| Campo | Significato |
| --- | --- |
| `gruppo_escluso` | il documento uscito |
| `fatture_cancellate` | quante bozze sono state cancellate (0 se non ne aveva) |
| `attivita_riemesse` | quante attività sono tornate disponibili |
| `gruppi_riaperti` | i documenti trascinati, per nome |
| `n_gruppi_riaperti` | quanti sono tornati effettivamente in coda |

---

### Note per chi ci mette le mani

* È una **funzione madre**: una sola `SELECT`, atomica per costruzione. Non va
  spezzata in più chiamate dal livello applicativo — sarebbe uno stato parziale
  in attesa di succedere.
* Gira come proprietario (`SECURITY DEFINER`): il perimetro non lo dà la row security, lo
  controlla il verbo all'ingresso (sezione «Chi la chiama»).
* Il **timbro** dell'uscita (quando, chi) non lo scrive questa funzione: lo
  deriva il trigger
  [`vendite.trgfn_fatturazione_lotti_esiti_uscita`](/dbzero/vendite/funzioni/trgfn_fatturazione_lotti_esiti_uscita).

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — gira come l'applicazione: il verbo è
  `SECURITY DEFINER`, e senza `reset_lotto_fattura_draft` risponde `E_PERMESSO_NEGATO`.
* `db/pgtap/vendite/test-uscita-documento-dal-giro-v1.sql` — l'uscita del documento e i
  trascinati.

---

### Note di migrazione

* 2026-09-08 — nasce (brief-db-uscita-documento-dal-giro).
* 2026-11-25 — `SECURITY DEFINER`: il permesso dell'endpoint in prima riga, il perimetro sul lotto
  all'ingresso (prima lo dava la row security), le porte spente all'ingresso
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7).

---

{% include-markdown "signature-core.md" %}
