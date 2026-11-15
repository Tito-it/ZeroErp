## 📘 Documentazione Concettuale – Funzione `script.fn_doc_lock_regola()`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> • [script.fn_doc_lock_montaggi](/dbzero/script/funzioni/fn_doc_lock_montaggi) — il lettore del montaggio, dove sta il quadro intero

---

### 🎯 Scopo Principale

(nata il 2026-10-10, brief `brief-db-testata-dopo-emissione`, fase 1)

**La grammatica** dei due lock «si tocca solo in bozza»: dagli argomenti di un trigger alla
regola che dicono. La chiamano i due lock (da `TG_ARGV`) e il lettore del montaggio (da
`pg_trigger.tgargs`), così nessuno dei due interpreta gli argomenti da sé.

| Lock | Che cosa esce |
| --- | --- |
| righe (`RIGHE`) | documento, colonna verso il padre, stato bozza (dal vocabolario, vedi sotto), livello (`TESTATA` se manca), colonne che si cambiano fuori bozza e stati in cui si cambiano, colonne tecniche |
| testata (`TESTATA`) | documento, stato bozza (dal vocabolario, vedi sotto), le colonne nominate nell'ordine del montaggio, ciascuna col suo codice d'errore e gli stati in cui resta aperta fuori bozza. Dal 2026-10-10 gli argomenti sono **terne** *(colonna, codice, stati)*: stati vuoti = bloccata fuori bozza |

⭐ **La bozza la dice il vocabolario del documento.** `stato_bozza` è il codice dello stato
in cui il documento nasce (colonna `iniziale`): dal tipo documento alla testata
(`config.sorgenti.target_table`), al vocabolario (`script.fn_doc_stato_modello`), allo stato
iniziale (`script.fn_stato_iniziale_id`). L'argomento dello stato bozza resta nella grammatica,
nella sua posizione, e **non si legge**: se il vocabolario sposta lo stato iniziale, il lock lo
segue, e con lui la capability, che legge la stessa regola. Un tipo documento che non porta a
uno stato iniziale è un montaggio sbagliato.

Un montaggio sbagliato non solleva qui: la regola porta la frase in `errore`, e la solleva
chi la usa (`E_DOC_RIGHE_LOCK_MONTAGGIO`).

⭐ La forma per stato della testata (decisioni D-8 e D-10: le colonne che restano aperte
dopo l'emissione si fermano quando il documento si chiude) è arrivata **qui** il 2026-10-10,
nella fase 2 del brief: le coppie *(colonna, codice)* sono diventate terne *(colonna, codice,
stati)*, e trigger e lettore l'hanno seguita insieme. Una terna senza colonna o senza codice
è un montaggio sbagliato.

### 🔄 rev 2026-10-11 — il codice del rifiuto (brief-db-testata-dopo-emissione §11, D-12)

Il building block delle righe legge un **settimo argomento**: il codice d'errore da sollevare.
Senza, resta `E_RIGA_DOC_NON_BOZZA`. Serve ai satelliti del documento (indirizzi e
fornitura), che montano lo stesso lock con `E_DOC_DATI_COLLEGATI_NON_BOZZA`: la frase delle
righe, su un indirizzo, avrebbe detto una cosa falsa. Oltre sette argomenti è un montaggio
sbagliato.

### 🔄 rev 2026-10-18 — la colonna ferma sempre (brief-db-indirizzi-documento-seguono-il-cliente §8.7)

Nella testata il terzo elemento della terna può essere `-`: la colonna è **ferma sempre**, anche
in bozza. Si sceglie quando il documento nasce e non si cambia più. Ogni colonna della regola
porta la chiave `ferma_sempre` (vera solo con `-`; i suoi stati sono vuoti). Un `-` insieme a
degli stati è un montaggio sbagliato.

Prime colonne ferme sempre: utility ed emittente di preventivo, offerta e contratto (in bozza si
cambia il cliente, dentro la stessa utility). Sta qui e non nel registro dei lock di colonna
perché la capability legge il form da questo montaggio: la regola arriva al form senza una
seconda lista.

> 📎 changeSet `20261018-65`. Presidio: `db/pgtap/vendite/test-doc-emittente-utility-fermi-v1.sql`.
