## 📘 Documentazione Concettuale – Funzione `vendite.fn_assegna_numero_documento`

> 👀 **Vedi anche**
>
> • [vendite.fn_componi_numero_documento](/dbzero/vendite/manual/fn_componi_numero_documento) (la composizione, pura)
> • [vendite.registri_fatturazione](/dbzero/vendite/manual/registri_fatturazione)
> • [vendite.fn_get_registro_documento](/dbzero/vendite/manual/fn_get_registro_documento)
> • Guida: [Numerazione dei documenti e codici automatici](/guide/numerazione-documenti-e-codici)

---

### 🎯 Scopo Principale

(rev 2026-08-31, sera)

**I sei passi che ogni documento numerato su un registro deve fare, in una sede
sola.** Restituisce registro, anno, progressivo, numero composto e serie risolta.

1. trova il **registro** dell'azienda emittente per quella famiglia di documento;
2. ricava l'**anno** dalla data del documento;
3. risolve la **serie** — quella del documento, poi quella del registro, poi vuota;
4. chiede il **progressivo** al motore dei contatori, sotto lock;
5. legge la **forma** dal registro: prefisso, suffisso, quante cifre;
6. **compone** la stringa.

---

### ⛔ Perché esiste: quattro copie della stessa cosa

Fino al 31 agosto 2026 questi sei passi stavano in **quattro funzioni identiche** —
documenti di trasporto, ordini, resi e commesse — ciascuna per conto proprio.

Il problema di quattro copie non è la lunghezza: è che **si possono correggere in
tre**. Una modifica al modo di comporre il numero andava fatta in quattro posti, e
chi ne dimenticava uno otteneva un documento formattato diversamente dagli altri —
che **nessun controllo respinge**, perché è un numero perfettamente valido, solo
diverso.

---

### ⚠️ Che cosa NON fa, ed è deliberato

**Non decide QUANDO.** Il momento è l'unica cosa che distingue davvero i quattro
documenti — il documento di trasporto numera all'emissione, il reso alla conferma,
ordine e commessa alla creazione — e resta scritto nel trigger di ciascuno.

⭐ Centralizzare anche quello significherebbe mettere in una funzione comune la sola
cosa che comune non è.

---

### ⭐ Il parametro `corpo`, e perché la commessa ci sta dentro

La funzione restituisce **anche il progressivo nudo**, non solo il numero composto,
e accetta un parametro `corpo`: la parte che varia fra le famiglie.

* vuoto per documenti di trasporto, ordini e resi;
* `<sigla>-<anno>-` per la **commessa**, il cui codice porta quei due pezzi dentro
  la stringa — perché è l'unica delle cinque la cui **identità è la stringa nuda**,
  senza colonne separate per anno e registro.

---

### ⚠️ La serie risolta esce, e non è un dettaglio

Chi ha la colonna `serie` deve scriverla, ed è **la stessa** che entra nella chiave
del contatore. Risolverla due volte, con due formule diverse, è esattamente il modo
in cui il contatore e il vincolo di unicità cominciano a guardare due sezionali
diversi senza che nessuno se ne accorga.

---

### ⚠️ Da dove viene la forma, dopo il difetto del `20260831-55`

Prefisso, suffisso e lunghezza vengono **tutti dal registro**, letti in una volta
sola dalla stessa riga.

⛔ Per una giornata la lunghezza è arrivata invece da `config.sistema_codici`, le
cui righe erano appena state cancellate: la lettura non trovava niente, il valore
restava assente e la composizione ripiegava su **sette cifre**.

| | cifre volute | cifre ottenute |
| --- | --- | --- |
| DDT, ordine, reso | 7 | 7 — **giusto per caso** |
| Commessa | 9 | **7** |

⭐ **È il caso da ricordare**: un valore di ripiego che coincide col valore giusto
per tre famiglie su quattro nasconde il difetto, e a rivelarlo è stata l'unica
diversa. La lezione operativa sta nella guida, §9.

---

### Note tecniche

* usa l'**involucro** che risolve il registro, non il lettore: qui si scrive, e un
  emittente senza registro deve **fermare**, non ripiegare;
* è `SECURITY DEFINER` perché legge il registro e chi la chiama è un trigger che
  gira sotto RLS.

---

{% include-markdown "signature-core.md" %}
