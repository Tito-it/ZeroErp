## 📘 Documentazione Concettuale – Funzione `vendite.fn_componi_numero_documento`

> 👀 **Vedi anche**
>
> • [vendite.fn_assegna_numero_documento](/dbzero/vendite/manual/fn_assegna_numero_documento) (l'unica chiamante)
> • [vendite.registri_fatturazione](/dbzero/vendite/manual/registri_fatturazione)
> • Guida: [Numerazione dei documenti e codici automatici](/guide/numerazione-documenti-e-codici)

---

### 🎯 Scopo Principale

(rev 2026-08-31, sera)

Compone la stringa di un numero documento:

```
prefisso  ||  corpo  ||  progressivo con le cifre di riempimento  ||  suffisso
```

```
'DDT'  +  ''            +  0000123    +  ''    →  DDT0000123
'CMM-' +  'ACME-2026-'  +  000000007  +  ''    →  CMM-ACME-2026-000000007
''     +  ''            +  0000001    +  '/A'  →  0000001/A
```

---

### ⭐ È **pura**, e il guadagno è tutto lì

Riceve dei valori e restituisce una stringa. Non legge niente, non scrive niente,
non sa cosa sia un documento.

Prima, per verificare che un numero venisse formattato bene, bisognava
**fabbricare un documento intero** — un documento di trasporto con le sue righe, il
suo indirizzo, la sua causale e la sua transizione di stato. Oggi si scrive una riga
di prova con i valori che si vogliono.

⇒ Il costo di verificare un caso in più è passato da venti righe di preparazione a
**una riga**. È il motivo per cui questa funzione è separata dall'altra, e non un
gusto stilistico: è anche `IMMUTABLE`, quindi si può inlineare e ci si potrebbe
appoggiare un indice.

---

### Il parametro `corpo` — la parte che varia

⚠️ Un parametro che serve a un solo chiamante è di solito un cattivo segno. Qui no,
e la ragione è che **prefisso e suffisso sono condivisi da tutti e quattro**: con
quelli in comune la forma è la stessa per tutti, e il `corpo` non generalizza un
caso particolare — **nomina la parte che varia**.

* vuoto per documenti di trasporto, ordini e resi;
* `<sigla>-<anno>-` per la commessa.

---

### ⚠️ Il separatore non è un parametro, ed è una decisione

Non esiste più un campo «separatore» a sé: se serve, si scrive **dentro il
prefisso** (`CMM-`).

⛔ Con due campi distinti, un prefisso vuoto lasciava il separatore **orfano in
testa** — `-ACME-2026-000000001` — e chi spezzava quel codice sul trattino trovava
un primo pezzo vuoto. Un caso speciale che la commessa aveva e gli altri no, sparito
insieme al campo.

⚠️ Resta invece un separatore **dentro il corpo** della commessa (`sigla-anno-`):
quello è del dominio commessa, non della forma del numero, e vive dove si costruisce
il corpo.

---

### ⚠️ Progressivo assente → nessun numero

Se il progressivo manca, la funzione restituisce **niente**, non un numero
parziale: chi compone senza progressivo sta sbagliando, e mezzo numero sarebbe
peggio di nessun numero.

⭐ Non è `STRICT`: gli altri parametri assenti sono **casi legittimi** — un registro
senza prefisso, un documento senza suffisso — e `STRICT` li trasformerebbe tutti in
un risultato vuoto.

---

{% include-markdown "signature-core.md" %}
