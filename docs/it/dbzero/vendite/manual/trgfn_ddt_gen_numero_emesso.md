## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_gen_numero_emesso`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.registri_fatturazione](/dbzero/vendite/manual/registri_fatturazione)
>
> Funzioni:
> [vendite.fn_assegna_numero_documento](/dbzero/vendite/manual/fn_assegna_numero_documento) (i sei passi)
> [vendite.trgfn_v_ddt_protect_num](/dbzero/vendite/funzioni/trgfn_v_ddt_protect_num) (immutabilità)

---

### 🎯 Scopo Principale

(rev 2026-08-31, sera)

Assegna il **`numero` del DDT alla transizione a EMESSO** — non in bozza, per non
lasciare buchi di numerazione da bozze scartate. È agganciata a `vendite.ddt` come
`trg_ddt_z10_gen_numero_emesso_ins_upd` (`BEFORE INSERT OR UPDATE OF stato_doc_ddt_id`).
Fascia `_z10_` dal 2026-10-13 (`20261013-53`): il registro si sceglie con l'emittente e la
utility della bolla, che all'INSERT scrive `trg_ddt_normalize_ins_upd`; prima si chiamava
`trg_ddt_a10_gen_numero_emesso_upd` e girava prima di lui.

---

### Che cosa fa questa funzione, e che cosa NON fa più

⭐ **Qui è rimasto il MOMENTO, e basta.** I sei passi della numerazione — trovare
il registro, ricavare l'anno dalla data, chiedere il progressivo, leggere il
formato, comporre la stringa — stanno in
[`vendite.fn_assegna_numero_documento`](/dbzero/vendite/manual/fn_assegna_numero_documento),
insieme a quelli di ordini, resi e commesse.

Il momento invece **non si centralizza**, ed è deliberato: è l'unica cosa che
distingue davvero i quattro documenti. Il documento di trasporto numera
all'emissione, il reso alla conferma, ordine e commessa alla creazione. Metterlo in
una funzione comune significherebbe mettere in comune la sola cosa che comune non è.

---

### ⚠️ Da dove viene la forma del numero

Dal **registro**: prefisso, suffisso e quante cifre stanno tutti e tre su
`vendite.registri_fatturazione`, e si leggono in una volta sola.

⛔ **Non da `config.sistema_codici`**, che dal 31 agosto 2026 non ha più una riga
`ddt`. Le versioni precedenti di questa scheda dicevano che il formato «resta nel
catalogo dei formati»: era vero fino a metà giornata, ed è la frase che ha coperto
per ore il difetto poi corretto dal changeSet `20260831-55` — la lunghezza letta da
una tabella ormai vuota, e sette cifre di ripiego per tutti.

⭐ I valori con cui un registro **nasce** stanno in
[`vendite.famiglie_documento`](/dbzero/vendite/manual/famiglie_documento).

---

### Le colonne si scrivono insieme

⚠️ `numero`, `anno`, `serie` e `registro_id` sono **una cosa sola** — la chiave del
documento. Scriverne una senza le altre lascerebbe la riga a dichiarare un sezionale
che non è quello su cui ha davvero contato.

L'immutabilità dopo l'assegnazione la garantisce
[`vendite.trgfn_v_ddt_protect_num`](/dbzero/vendite/funzioni/trgfn_v_ddt_protect_num).

---

{% include-markdown "signature-core.md" %}
