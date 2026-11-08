## 📘 Documentazione Concettuale – Funzione `dbops.trgfn_emittente_modi_solo_migrazione`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.emittente_modi](/dbzero/dbops/tabelle/emittente_modi) — la tabella che protegge
>
> Approfondimento funzioni:
>
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — la domanda «chi scrive è il proprietario?»
> * [ui.trgfn_lista_definizione_guard_multi_emittente](/dbzero/ui/funzioni/trgfn_lista_definizione_guard_multi_emittente) — la stessa regola, su un solo flag

---

### 🎯 Scopo Principale

Fa sì che il registro dei modi dell'emittente lo scriva **solo il migrate**. Aggiungere, cambiare o
togliere una riga, o svuotare la tabella, da un ruolo che non è il proprietario della tabella riceve
`E_EMITTENTE_MODI_NON_SCRIVIBILE`.

---

### Perché

Dal registro il migrate genera il risolutore che dice di chi è ogni riga alle policy e ai guard di
scrittura: il controllo che separa le aziende. Chi scrive una riga del registro sceglie da quale
strada quel controllo leggerà l'emittente. È codice di sicurezza, e arriva solo con una migrazione.

⚠️ È un trigger e non un permesso: il passo dei permessi della migrazione ridà all'applicazione i
privilegi sulle tabelle a ogni corsa, e un permesso tolto tornerebbe.

---

### Che cosa guarda

Solo **chi** scrive, non che cosa: se chi esegue l'istruzione è il proprietario della tabella, o ne
ha i privilegi, passa. Scatta prima di ogni riga inserita, cambiata o cancellata, e prima di uno
svuotamento. Lo svuotamento lo ferma prima ancora la chiave esterna dei bersagli dei processi, finché
qualcuno riferisce un modo.

---

### Test

`dbops/test-emittente-modi-solo-migrazione-v1`, come applicazione: le quattro scritture respinte.

---

{% include-markdown "signature-core.md" %}
