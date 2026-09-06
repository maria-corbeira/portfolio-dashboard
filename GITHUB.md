# GitHub, paso a paso

Para ti, Maria. No hace falta saber programar: son cuatro cosas y siempre las mismas.

---

## Qué es cada cosa, en una línea

- **El repositorio** (o "repo") es la carpeta de tu dashboard, con su historial de cambios.
  Existe en dos sitios: en tu Mac y en GitHub. No se sincronizan solos.
- **Un commit** es una foto guardada de la carpeta, con un mensaje que explica qué cambió.
  Yo hago los commits en tu Mac.
- **`git push`** sube esas fotos a GitHub. **Esto solo lo puedes hacer tú** — mi acceso a
  tu Mac no llega al llavero donde está tu contraseña de GitHub.
- **Un Action** es un programa que GitHub ejecuta solo, cada cierto tiempo, en sus
  ordenadores. Tienes dos: uno baja precios cada 15 minutos y otro noticias cada 6 horas.
- **GitHub Pages** convierte tu `index.html` en una página web con dirección propia, que
  es la que le pasarías a tu marido.

---

## 1 · Subir los cambios (lo que tienes pendiente ahora)

Abre la aplicación **Terminal** en tu Mac (Cmd + espacio, escribe "Terminal") y pega:

```
cd ~/Claude/Investing/portfolio-dashboard && git push
```

Pulsa Enter. Si te pide usuario y contraseña, el usuario es `maria-corbeira` y la
contraseña **no es la de tu cuenta**: es un *token*. Si no tienes uno, ve al paso 5.

Cuando termine verás algo como `main -> main`. Ya está.

**Cómo saber qué hay pendiente**, en cualquier momento:

```
cd ~/Claude/Investing/portfolio-dashboard && git status
```

Si dice `Your branch is ahead of 'origin/main' by N commits`, hay N cambios sin subir.

---

## 2 · Ver si los Actions funcionaron

1. Entra en `github.com/maria-corbeira/portfolio-dashboard`
2. Pestaña **Actions**, arriba.
3. Verás la lista de ejecuciones. **Verde** = fue bien. **Rojo** = falló.
4. Pincha en una para ver qué hizo. Si está en rojo, pincha en el paso rojo y cópiame
   el mensaje de error: con eso lo arreglo.

Los Actions se ejecutan solos, pero **la primera vez tarda unos minutos** en arrancar
después del push.

---

## 3 · Lanzar un Action a mano

Cuando yo te pida "ejecuta el probe":

1. **Actions** → en la columna izquierda, elige el que sea (**Probe fuentes**,
   **Actualizar precios** o **Actualizar noticias**).
2. Botón **Run workflow** a la derecha → **Run workflow** otra vez en el desplegable.
3. Espera a que salga en verde y dímelo.

---

## 4 · Publicar la página y compartirla

Solo hay que hacerlo una vez.

1. En el repo, pestaña **Settings**.
2. Menú izquierdo, **Pages**.
3. En *Source* elige **Deploy from a branch**; en *Branch*, `main` y carpeta `/ (root)`.
4. **Save**. A los dos o tres minutos aparece arriba la dirección, del estilo
   `https://maria-corbeira.github.io/portfolio-dashboard/`.

Esa dirección es la que le mandas a tu marido. **Ojo con esto**: el repo es público, así
que cualquiera con el enlace ve tu cartera — participaciones, coste medio y ganancias.
Si prefieres que no, en **Settings → General**, abajo del todo, puedes pasarlo a privado;
Pages seguirá funcionando pero solo para quien invites en **Settings → Collaborators**.

---

## 5 · Si te pide contraseña y no la tienes

GitHub ya no acepta la contraseña normal desde la Terminal. Necesitas un token:

1. En GitHub, arriba a la derecha tu foto → **Settings**.
2. Abajo del todo del menú izquierdo: **Developer settings**.
3. **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**.
4. Ponle un nombre (`portfolio-dashboard`) y marca **DOS** casillas:
   - **`repo`** — para poder subir ficheros
   - **`workflow`** — para poder subir o cambiar los Actions (`.github/workflows/`)

   Si te olvidas de `workflow`, el push falla con
   *"refusing to allow a Personal Access Token to create or update workflow ... without `workflow` scope"*.
   No es un fallo tuyo ni del repo: es que el token no tiene ese permiso.
5. Genera el token.
6. **Cópialo en ese momento**: no se vuelve a mostrar. Guárdalo en tu gestor de contraseñas.
7. Cuando la Terminal te pida la contraseña, pega el token.

Para no tener que pegarlo cada vez, pega esto una sola vez en la Terminal:

```
git config --global credential.helper osxkeychain
```

A partir de ahí lo recuerda.

---

## 6 · Si algo se rompe

**Deshacer lo último que no has subido**, sin perder nada:

```
cd ~/Claude/Investing/portfolio-dashboard && git log --oneline -5
```

Te lista los últimos cinco cambios. Pásame la lista y te digo qué hacer. **No borres la
carpeta ni el repo**: todo el historial está ahí y se puede recuperar casi cualquier cosa.

**Si el push falla por el permiso `workflow`**: tu token no lo tiene. No hace falta
crear uno nuevo — se le puede añadir al que ya tienes: **Settings → Developer settings →
Personal access tokens → Tokens (classic)**, pincha en tu token, marca **`workflow`** y
**Update token**. El valor del token no cambia, así que el que está en tu llavero sigue
valiendo. Vuelve a la Terminal y repite `git push`.

**Si creaste un token nuevo** y el push sigue fallando, el llavero está dando el viejo.
Bórralo escribiendo esto y pulsando Enter dos veces al final:

```
git credential-osxkeychain erase
host=github.com
protocol=https
```

El siguiente `git push` te volverá a pedir usuario y token.

**Si un push falla diciendo algo de `lock`**: es un fichero de bloqueo que dejé yo.
Ejecuta esto y vuelve a intentarlo:

```
cd ~/Claude/Investing/portfolio-dashboard && rm -f .git/*.lock && git push
```

---

## Resumen de lo único que tienes que recordar

| Cuándo | Qué pegas en la Terminal |
|---|---|
| Cuando te diga "hay commits pendientes" | `cd ~/Claude/Investing/portfolio-dashboard && git push` |
| Para ver si hay algo sin subir | `cd ~/Claude/Investing/portfolio-dashboard && git status` |
| Si el push se queja de un lock | `cd ~/Claude/Investing/portfolio-dashboard && rm -f .git/*.lock && git push` |

Todo lo demás se hace pinchando en la web de GitHub.
