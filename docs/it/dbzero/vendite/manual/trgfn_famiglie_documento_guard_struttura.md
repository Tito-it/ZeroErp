## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_famiglie_documento_guard_struttura`

> 👀 **Vedi anche**
>
> **Il predicato NON è qui, sta in:**
>
> • [script.fn_check_famiglia_documento_struttura_modificabile](/dbzero/script/manual/fn_check_famiglia_documento_struttura_modificabile)
>
> **Approfondimenti tabelle:**
>
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)
>
> **Il vicino con cui si contende la parola:**
>
> • [vendite.trgfn_famiglie_documento_guard_riferimenti](/dbzero/vendite/manual/trgfn_famiglie_documento_guard_riferimenti)

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — trigger nato il 2026-09-01)*

**Impedisce di cambiare le colonne che dicono DOVE VIVE il documento** su una
famiglia che ha già dei registri: `schema_tabella`, `nome_tabella`,
`colonna_numero`, `colonna_billing_account`, `colonna_serie`.

Trigger `trg_famiglie_documento_a10_guard_chiave_struttura_upd`, `BEFORE UPDATE
OF` quelle cinque colonne.

---

### 🔴 Il nome del trigger decide chi parla per primo

Si chiama `..._a10_guard_**chiave**_struttura_upd` e non
`..._a10_guard_struttura_upd`. **Non è cosmetica.**

I trigger `BEFORE ROW` scattano in **ordine alfabetico**, e `guard_riferimenti`
verrebbe prima di `guard_struttura`.

⚠️ **Verificato provando**: cambiando `nome_tabella` su una famiglia con
registri, il rifiuto arrivava dal guard dei riferimenti — *«quella tabella non ha
la colonna serie»* — che è vero e non è il punto. Il punto è che quella colonna
**non si cambia affatto**: l'operatore avrebbe corretto il riferimento per andare
a sbattere un attimo dopo contro il muro vero.

⭐ **La regola generale: prima l'immutabilità, poi la validità del valore nuovo.**
Se non si può cambiare, non ha senso dire se il valore nuovo era buono. `chiave`
viene dal codice errore, e `c` sta prima di `r`.

⚠️ Il pgTAP lo presidia con un controllo **sulla frase**, non sul codice di
errore: è l'unico modo perché un rename futuro del trigger diventi rosso.

---

### ⛔ Perché quelle cinque colonne non si toccano

Non descrivono la famiglia, **la fanno funzionare** — e il caso peggiore è
`colonna_serie` portata a vuoto: da quel momento i registri che una serie ce
l'hanno restano con un contenitore del contatore che il documento non sa più
distinguere, e nessun vincolo se ne accorge. Il perché per esteso sta nella
pagina della verifica.

---

### ⚠️ Il campo da accendere è il PRIMO che è cambiato davvero

Non uno fisso: l'operatore ne ha toccato uno, e mandarlo a correggerne un altro è
peggio che non dirglielo. È la stessa scelta già fatta in
`vendite.trgfn_registri_fatturazione_guard_forma_numero`.

---

### ⭐ L'uscita sul no-op, obbligatoria

I due mirror CSV riscrivono queste colonne **a ogni migrazione** con gli stessi
valori, e `UPDATE OF` scatta comunque perché è l'istruzione a nominarle. Senza il
confronto fra vecchio e nuovo, ogni migrazione fallirebbe.

---

### ⛔ `codice_interno` non è nella lista

Lo presidia il **lock automatico**, con il suo messaggio. Metterlo anche qui
darebbe due rifiuti diversi per la stessa colonna, a seconda di quale trigger
scatta per primo — cioè dell'ordine alfabetico, che qui sopra abbiamo appena
finito di governare a mano.

---

### ⚠️ Note operative

* **Solo `UPDATE`, mai `INSERT`**: alla nascita non c'è niente da proteggere, una
  famiglia nuova non ha registri. E un guard `BEFORE ROW` in inserimento
  oscurerebbe i `CHECK` della tabella.
* **`tx_id` NULL e non `NEW.tx_id`**: la fase `_a10_` scatta prima del trigger
  che lo genera.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 11.5.*
