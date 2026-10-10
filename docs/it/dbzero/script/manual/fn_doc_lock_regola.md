## 📘 Documentazione Concettuale – Funzione `script.fn_doc_lock_regola()`

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
| righe (`RIGHE`) | documento, colonna verso il padre, stato bozza (`DRAFT` se manca), livello (`TESTATA` se manca), colonne che si cambiano fuori bozza e stati in cui si cambiano, colonne tecniche |
| testata (`TESTATA`) | documento, stato bozza, le colonne nominate nell'ordine del montaggio, ciascuna col suo codice d'errore e gli stati in cui resta aperta fuori bozza. Dal 2026-10-10 gli argomenti sono **terne** *(colonna, codice, stati)*: stati vuoti = bloccata fuori bozza |

Un montaggio sbagliato non solleva qui: la regola porta la frase in `errore`, e la solleva
chi la usa (`E_DOC_RIGHE_LOCK_MONTAGGIO`).

⭐ La forma per stato della testata (decisioni D-8 e D-10: le colonne che restano aperte
dopo l'emissione si fermano quando il documento si chiude) è arrivata **qui** il 2026-10-10,
nella fase 2 del brief: le coppie *(colonna, codice)* sono diventate terne *(colonna, codice,
stati)*, e trigger e lettore l'hanno seguita insieme. Una terna senza colonna o senza codice
è un montaggio sbagliato.
