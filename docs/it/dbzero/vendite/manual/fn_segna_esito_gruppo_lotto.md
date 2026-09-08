## 📘 Documentazione Concettuale – Funzione `vendite.fn_segna_esito_gruppo_lotto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti)
> • [vendite.fatturazione_lotti_gruppi](/dbzero/vendite/tabelle/fatturazione_lotti_gruppi)
>
**Approfondimento funzioni:**
>
• [script.fn_gruppi_di_commessa_nel_lotto](/dbzero/script/funzioni/fn_gruppi_di_commessa_nel_lotto)
> • [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key)
> • [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

Dire **come è andato un documento dentro un lotto**, scrivendo la sua riga su
`vendite.fatturazione_lotti_esiti`.

La riga si **crea** quando c'è qualcosa da dire: così vale anche per i giri che
non dichiarano nessun perimetro — quelli di massa — che prima restavano muti.

---

### Il chiamante passa ciò che ha in mano

| Ha… | Passa | Che cosa succede |
| --- | --- | --- |
| il **documento** | `p_gruppo_key` | si marca quel documento, se il lotto lo stava lavorando |
| solo la **commessa** (è il caso di chi fallisce al pull) | `p_commessa_id` | si marcano **tutti** i documenti che quella commessa alimenta nel lotto — possono essere più di uno |

---

### ⭐ La risoluzione dalla commessa non è scritta qui

La conversione *«questa commessa quali documenti alimenta, dentro questo
lotto»* vive in
[`script.fn_gruppi_di_commessa_nel_lotto`](/dbzero/script/funzioni/fn_gruppi_di_commessa_nel_lotto),
e questa funzione la **chiama**.

⛔ **Non è un refactoring di comodo.** Quella regola serve anche a **chi scrive
la segnalazione** — il backend, che al pull ha in mano la commessa e non il
documento. Finché viveva solo qui, l'unica via era ricopiarla; e ciò che si
ricopierebbe non è un calcolo ma la **scelta della tabella da cui leggere**, che
è la parte che, spostandosi, produce chiavi mute senza fallire.

*La madre non riscrive il predicato, lo chiama* —
[linee-guida-sql §12.5.2](/linee-guida-sql).

---

### ⚠️ Il perimetro si applica anche qui, e non è un doppione

La funzione estratta filtra sul perimetro perché è **la sua domanda** («nel
lotto»). Questa lo rifiltra perché è **la sua invariante**, e presidia un
ingresso che l'altra non vede: il `p_gruppo_key` passato direttamente dal
chiamante.

⇒ Non è la stessa regola scritta due volte: è una regola applicata su **due
confini**, e quello di qui non è rimuovibile — senza, una chiave arbitraria
scriverebbe un esito su un documento che il lotto non ha mai preso in carico.
Sulla via della commessa il filtro è **idempotente**.

---

### ⛔ Non solleva mai — e il guard sta a monte

La chiama un **gestore d'eccezione**: un errore su di sé coprirebbe quello vero.
Ogni rifiuto esce come `RAISE WARNING` + `RETURN 0`.

⚠️ Ma `script.fn_gruppi_di_commessa_nel_lotto` **solleva** su un id `<= 0`, ed è
giusto che lo faccia: il backend la chiama direttamente, e lì un id invalido è un
chiamante rotto. Le due promesse convivono perché il guard sulla commessa sta
**prima** della chiamata.

⭐ E il messaggio ci ha guadagnato: prima un `p_commessa_id` negativo usciva come
*«nessun documento trovato»*, che è la diagnosi sbagliata — non è che la commessa
non alimenti niente, è che quella commessa non esiste.

---

### Regole

* Un **errore muto** non si scrive: su `ERRORE` serve almeno una fra causa e
  frase (lo pretende anche il vincolo di tabella, e si controlla prima per non
  doverlo far scoprire a lui).
* Un **secondo tentativo sovrascrive**, non duplica: la chiave è
  `(lotto, documento)` e la domanda è *«com'è finita»*, non *«quante volte ci
  abbiamo provato»*. Lo storico dei tentativi vive nel giornale del lotto.
* Il passaggio a `COMPLETED` **azzera** causa, frase e orario: un rosso che non
  scade mai è peggio di nessun rosso.
* ⚠️ **Torna quante righe ha scritto, e lo zero è una risposta**: vuol dire che
  il fallimento non è stato appeso a nessun documento, cioè che il lotto
  racconterà un errore su qualcosa che non mostra. Va guardato.

---

### Esempio d'uso

```sql
-- Il documento c'è: si marca lui
SELECT vendite.fn_segna_esito_gruppo_lotto(
    p_lotto_id         => 11221,
    p_stato            => 'ERRORE',
    p_gruppo_key       => 'ORDINE_VENDITA:01a06ce4-35a6-721a-9cd8-9da48bf77626',
    p_errore_codice    => 'E_PULL_COMMESSA',
    p_errore_messaggio => 'ROOT source mancante');

-- Il documento non c'è: si passa la commessa, e si marcano tutti i suoi
SELECT vendite.fn_segna_esito_gruppo_lotto(
    p_lotto_id         => 11221,
    p_stato            => 'ERRORE',
    p_commessa_id      => 34137,
    p_errore_codice    => 'E_PULL_COMMESSA',
    p_errore_messaggio => 'Errore emissione commessa');
```

> Piano e decisioni: `docs/it/dev/work-in-progress/brief-db-esito-gruppo-lotto.md` §15 ·
> `docs/it/dev/work-in-progress/brief-db-uscita-documento-dal-giro.md` §6.1.

---

{% include-markdown "signature-core.md" %}
