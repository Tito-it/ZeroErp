## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_categorie_clienti_listini_guard_listino`

> 👀 **Vedi anche**
>
> • [anagrafiche.categorie_clienti_listini](/dbzero/anagrafiche/manual/categorie_clienti_listini) — la matrice categoria → listino
>
> • [script.fn_check_listino_documento](/dbzero/script/funzioni/fn_check_listino_documento) — il controllo, lo stesso di contratti e offerte
>
> • [vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga) — dove lo sbaglio arrivava prima

### 🎯 Scopo Principale

(rev 2026-10-16, brief `brief-db-coerenza-listino-della-riga-di-commessa` §7.4, opzione B di Tid)

Una riga della matrice dice: «i clienti di questa **categoria**, per questa **utility**, di
questa **azienda**, usano questo **listino**». Questo guard rifiuta la riga se il listino è di
un'altra utility o di un'altra azienda.

| Codice | Quando |
| --- | --- |
| `E_CATEGORIA_LISTINO_UTILITY_DIVERSA` | il listino è di un'altra utility |
| `E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO` | il listino è di un'altra azienda, oppure chi scrive non lo può vedere (è fuori dal suo perimetro) |

Entrambi in classe **DATO_ERRATO**, sul campo `listino_id`, con frasi chiuse: non dicono niente
del listino, che l'operatore può non vedere.

---

### Perché qui

Senza questo controllo «clienti di A → listino di B» entrava. Il calcolo del prezzo lo
sceglieva, e lo sbaglio veniva fuori solo al passaggio in commessa, come errore tecnico
(`E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO`), lontano da chi aveva configurato la matrice.
Fermato qui, l'errore arriva a chi può correggerlo, nel momento in cui lo fa.

---

### Come è fatto

* **Il controllo è quello di contratti e offerte**: `script.fn_check_listino_documento`. Vuole
  l'emittente *fiscale*, la matrice porta il *ruolo*: la traduzione è univoca (un ruolo, un
  emittente fiscale).
* **I codici sono della matrice**, perché le frasi dei codici dei documenti dicono «il
  documento». Il guard li sceglie dal motivo della check. Se un giorno la check avesse un
  motivo nuovo, senza un codice qui, il guard si ferma con un errore che lo nomina: un motivo
  nuovo non passa in silenzio e non prende la frase di un altro.
* **Quando scatta**: sempre all'inserimento; in modifica solo se cambiano listino, utility o
  azienda. Le righe già scritte restano come sono finché non si tocca la loro chiave.

---

### 🧪 Il presidio

`db/pgtap/anagrafiche/test-categorie-clienti-listini-guard-listino-v1.sql` (6 casi): i due
trigger, il listino giusto che entra, quello di un'altra utility e quello di un'altra azienda
rifiutati, la modifica verso il listino di un'altra azienda rifiutata, la modifica della sola
variazione che passa.

---
{% include-markdown "signature-core.md" %}
