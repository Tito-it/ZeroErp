## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_gen_numero_emesso`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
> Funzioni:
> [vendite.trgfn_v_ddt_protect_num](/dbzero/vendite/funzioni/trgfn_v_ddt_protect_num)
> [vendite.fn_numera_fattura_opz_emessa](/dbzero/vendite/funzioni/fn_numera_fattura_opz_emessa) (pattern fatture)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

Assegna il **`numero` del DDT alla transizione a EMESSO** (non in DRAFT), per evitare buchi di
numerazione da bozze scartate. Trigger function agganciata a `vendite.ddt` come
`trg_ddt_a10_gen_numero_emesso_upd` (`BEFORE INSERT OR UPDATE OF stato_doc_ddt_id`).

### Perché fuori dal framework `sistema_codici` (mirror fatture)

Il framework `config.sistema_codici` numera **all'INSERT** (funzione+trigger rigenerati con
template fisso). Le **fatture** risolvono lo stesso problema (numero fiscale a emissione) **stando
fuori dal framework**. Il DDT fa lo stesso:

* la riga `sistema_codici` del DDT ha **`usa_sequenza = false`** → il framework droppa da solo la
  sua funzione+trigger per il DDT e lascia la sequenza;
* questa funzione **bespoke** (nome distinto, non gestito dal framework) assegna il numero solo se
  lo stato è `EMESSO` e il numero è vuoto, leggendo il **formato** (prefisso/separatore/lunghezza)
  dalla riga `sistema_codici` + la sequenza `vendite.ddt_numero_seq`.

Immutabilità post-assegnazione: `vendite.trgfn_v_ddt_protect_num`.
