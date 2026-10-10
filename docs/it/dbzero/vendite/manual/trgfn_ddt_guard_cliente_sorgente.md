## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_ddt_guard_cliente_sorgente`

> 👀 **Vedi anche**
>
> [vendite.trgfn_resi_guard_cliente_ddt](/dbzero/vendite/funzioni/trgfn_resi_guard_cliente_ddt) — la stessa regola sul reso
> [vendite.trgfn_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza) — la terza porta: la riga di bolla che evade una riga d'ordine
> [vendite.trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize) — chi eredita il billing account dall'ordine, prima di questo guard

---

### 🎯 Scopo Principale

**Una bolla ha il cliente del documento da cui nasce.**

Ordine, bolla, reso e fattura sono anelli di una catena: il preventivo
diventa ordine, l'ordine diventa bolla, la bolla diventa fattura o reso. Se
due anelli parlano di clienti diversi, la merce di un cliente finisce nella
fattura di un altro. Il cliente, qui, è il **billing account**: la fornitura
precisa del cliente.

Il guard gira quando la bolla nasce e quando cambiano il suo billing account o
la sua sorgente:

1. **bolla da un ordine** (sorgente `ORDINE_VENDITA`): il billing account è
   quello dell'ordine;
2. **bolla da un reso** (sorgente `RESO_VENDITA`, la riconsegna): il billing
   account è quello del reso, anche quando è vuoto;
3. **bolla che evade già righe d'ordine**: il billing account non cambia più,
   nemmeno in bozza, perché quelle righe sono di quel cliente.

Se non torna: `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE` («DDT …: il cliente deve
essere quello di ordine …, il documento da cui nasce»).

---

### 🔒 Una sorgente che non si trova

Il guard legge l'ordine o il reso con i permessi di chi scrive, sotto la RLS.
Dal 10 ottobre 2026 (brief `brief-db-esecutivi-ba-coppia`, decisione di Tid)
una sorgente dichiarata e **non trovata** è un errore:
`E_DOC_SORGENTE_NON_TROVATA` («il documento da cui nasce (ordine) non esiste
o non è visibile»). Un ordine inesistente e uno di un'altra azienda rispondono
allo stesso modo.

Prima il guard diceva «niente da confrontare» e lasciava passare. Una bolla
dell'azienda A poteva così dichiarare come origine l'ordine dell'azienda B,
con un cliente di A: nessun altro controllo lo vedeva, perché il guard
emittente ↔ billing account confronta la bolla col **suo** billing account,
non con la sorgente.

Una sorgente di un altro tipo resta fuori: la regola parla di ordine e reso.

---

### 🧪 Test

`db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql`: test 17 (la bolla eredita
dall'ordine), 18 (bolla dall'ordine di un altro cliente), 20 (il billing
account di una bolla che evade righe d'ordine non cambia), 36 (ordine che non
esiste), 39 (ordine di un'altra azienda: verde come applicazione, rosso da
proprietario del database, dove la RLS non c'è).

### 🔄 rev 2026-10-11 — la regola in una sede sola (brief-db-testata-dopo-emissione §11, R-DB-1)

Da dove viene il cliente della bolla (la sorgente ordine o reso, le righe d'ordine già
evase) lo dice ora `vendite.fn_ddt_vincoli_cliente`. Il guard solleva soltanto, con gli
stessi codici e la stessa frase di prima. La stessa funzione la legge la capability della
bolla per spegnere il cliente nel form: il campo è spento esattamente dove il guard
rifiuterebbe.
