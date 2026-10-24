## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_listino_aggiungi_articoli`

> 👀 **Vedi anche**
>
> [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — la regola A-5 per cui serve

### 🎯 Scopo Principale

(latest review 2026-10-13, brief-db-articoli-ammessi-per-documento Lotto 3b)

Builder per i **test pgTAP**. Mette degli articoli in una versione di listino: allinea la
tipologia dell'articolo a quella del listino, se è diversa (la riga di listino la pretende), poi
scrive una riga attiva per articolo, con la UoM base e il prezzo dato (default 100).

Serve alle fixture che scrivono un'**OVERRIDE** o un'**ESCLUSIONE**: dal Lotto 3b quelle righe
pretendono l'articolo nel listino del documento (A-5). Prima si scrivevano anche fuori, e la
riga non compariva nel drawer.

⚠️ Va chiamato **prima** di usare l'articolo: su un articolo già usato la tipologia non cambia
(A-10).

Le righe si scrivono anche su una versione ATTIVA; i componenti di un bundle no.

Esempio:
`SELECT dbops.fn_pgtap_listino_aggiungi_articoli(v_versione, ARRAY[v_art1, v_art2]);`

---
{% include-markdown "signature-core.md" %}
