## 📘 Documentazione Concettuale – Funzione `vendite.fn_numero_documento_fattura`

> 👀 **Vedi anche**
>
> Chi la usa:
>
> [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi)
>
> Dove finisce a video:
>
> [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) (era `vw_documento_lineage`, ritirata nel giro B)

---

### 🎯 Scopo Principale

**È la sede unica che dice come si scrive il numero di una fattura.**

Per un DDT, un ordine, un reso o un preventivo la domanda non si pone: la colonna
`numero` **è già** il numero che si legge a video — `DDT0000031`, `ORD0000227`.
Per la fattura no. Lì `numero` è un **contatore** (`bigint`), e l'identità del
documento sta in **tre** colonne — `anno`, `serie`, `numero` — che restano tutte
vuote finché il documento non viene numerato.

Prima di questa funzione nessuno diceva come metterle insieme, e il risultato era
che ogni consumatore lo decideva per conto suo. Nel grafo di genealogia usciva il
contatore nudo:

> `→ Nota di credito 1`

⛔ **Quel `1` non è sbagliato: è ambiguo.** Nello stesso anno possono esistere una
fattura numero 1 e una nota di credito numero 1, e in una lista sono
indistinguibili.

---

### 📥 Input

| Parametro | Tipo | Significato |
|---|---|---|
| `p_numero` | `vendite.fatture.numero%TYPE` (`bigint`) | il contatore del documento; `NULL` finché non è numerato |
| `p_serie` | `vendite.fatture.serie%TYPE` (`varchar`) | la serie, se c'è |

### 📤 Output

Una stringa (`varchar`), oppure `NULL`.

---

### 🧭 La regola, e i suoi tre casi

**La forma decisa è `numero - serie`, senza l'anno.** In prosa: *«fattura n.
1 - VX2»*.

| caso | cosa esce | perché |
|---|---|---|
| numero `103`, serie `VX2` | `103 - VX2` | il caso pieno |
| numero `1`, serie **vuota** | `1` | nessun trattino orfano: una serie che non c'è non lascia traccia |
| **non ancora numerata** | `NULL` | il consumatore usa la scritta che ha già (sul chip del lineage è *«non numerato»*) |

⛔ **L'anno resta fuori di proposito.** La regola dichiarata è *«accanto c'è
sempre la data»*: ripetere l'anno dentro il codice lo direbbe due volte.

⛔ **E si restituisce `NULL`, non la stringa vuota.** Sono due cose diverse per chi
legge: `NULL` dice *«non c'è»*, `''` dice *«c'è, ed è niente»* — e un chip che
riceve `''` disegna una casella vuota invece di scrivere «non numerato».

---

### ⚠️ I due modi silenziosi di sbagliare questa composizione

Sono il motivo per cui la sede dev'essere **una sola**. Non perché le
composizioni fossero tante — in tutto il database ce n'era **un'altra**, quella
del tracciato SDI — ma perché la regola ha due rami che chi la riscrive a mano
non ha ragione di ricordare:

1. **La serie che non c'è.** `numero || ' - ' || serie` con la serie vuota non
   restituisce `1`: restituisce **`NULL`**. In SQL una concatenazione che incontra
   un valore assente annulla tutto il risultato. Il numero **sparisce**, e non c'è
   nessun errore da nessuna parte.
2. **La serie vuota ma presente.** Con una serie valorizzata a stringa vuota il
   risultato è `1 - `, cioè un trattino orfano a video.

⭐ Non sono casi di nicchia: sono i due modi in cui una nota di credito senza
serie smette di avere un numero.

---

### ⚙️ Due scelte tecniche, e perché

**Prende i valori, non l'identificativo della fattura.** Una funzione che
ricevesse l'id dovrebbe andarsi a leggere la riga: dentro una vista che scorre
tutte le fatture sarebbe **una lettura per ogni riga**. Ricevendo i due valori la
funzione è **pura** — non guarda nessuna tabella — e il pianificatore di
PostgreSQL la **assorbe dentro la query**, azzerandone il costo.
⭐ Con un secondo vantaggio che si vede solo scrivendo i test: si prova **senza
costruire nessun documento**.

**Non è `STRICT`**, ed è la scelta che regge metà della regola. `STRICT` è
l'istruzione «se un parametro è assente, restituisci subito niente»: qui il
parametro assente — la serie — è un **caso normale**, e la risposta giusta è il
numero da solo. Messo per abitudine, `STRICT` spegnerebbe il secondo caso della
tabella qui sopra **senza far fallire nessun controllo di forma**: la firma
sarebbe giusta, il resto anche. Per questo il presidio ha un test dedicato che
verifica proprio che la funzione *non* sia `STRICT`.

---

### ⛔ Cosa NON deve diventare

**Non è la stringa per l'Agenzia delle Entrate.** Il tracciato SDI compone
`anno + serie + numero` **senza separatori** (`2026VX2103`), ed è una stringa
destinata a una **macchina**. Unificare le due sembra un risparmio e non lo è:
sono due contratti con due destinatari diversi, e il giorno in cui uno dei due
cambia ci si accorge di averli legati. Resta deliberatamente diversa.

---

### 🛡️ Presidio

`db/pgtap/vendite/test-fn-numero-documento-fattura.sql` — 10 verifiche, tutte
**senza fixture**: i tre casi della regola, i tre modi di non avere una serie,
gli spazi attorno alla serie, l'ordine di precedenza dei rami, e le due
proprietà che non si vedono dal risultato (è `IMMUTABLE`, non è `STRICT`).

---

{% include-markdown "signature-core.md" %}
