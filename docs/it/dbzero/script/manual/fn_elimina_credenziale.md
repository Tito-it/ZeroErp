## 📘 Documentazione Concettuale – Funzione `script.fn_elimina_credenziale()`

> 👀 **Vedi anche**
>
> **La regola che applica:** [fn_check_credenziale_eliminabile](/dbzero/script/funzioni/fn_check_credenziale_eliminabile)
>
> **Dove lascia traccia:** [config.credenziali_eliminate](/dbzero/config/tabelle/credenziali_eliminate)
>
> **Il presidio che la chiede:** [vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare)

---

### 🎯 Scopo Principale
(scritta il 06-10-2026)

**Elimina una credenziale che non ha mai avuto una veste**, per decisione di un
amministratore del software. È il gesto che il presidio delle credenziali da
sanare chiede quando una credenziale non entra da nessuna parte.

---

### Come lavora

1. Chi agisce dev'essere **SUPER_ADMIN**: altrimenti il rifiuto arriva prima di
   guardare la credenziale.
2. **Ferma la credenziale** per il tempo dell'operazione, così un invito che
   arriva nello stesso istante non può darle una veste alle spalle.
3. Chiede alla regola se si può eliminare, e se no **rifiuta col primo motivo**.
4. **Scrive la traccia** (quale credenziale, chi, quando) e poi la elimina. Le
   cose che le appartengono (stato del login, preferenze, secondo fattore, e
   l'etichetta di una credenziale di prova) se ne vanno con lei.

---

### Regole

* Una credenziale con **vesti spente** non si elimina: è una persona disattivata.
* Una credenziale **con una storia** non si elimina: è un'anomalia da segnalare
  allo sviluppo, e la storia non si cancella per farla passare.
* L'applicazione **non può cancellare una credenziale in altro modo**: questa è
  l'unica porta.

---

### Storia

* 2026-10-06 — nasce (`20261006-14`). Brief: brief-db-elimina-credenziale-senza-veste.

{% include-markdown "signature-core.md" %}
