<p align="center">
  <img src="docs/assets/logo.svg" width="104" alt="MiTallercito">
</p>

<h1 align="center">MiTallercito</h1>

<p align="center">
  <b>Run your little 3D-printing shop from one self-hosted app.</b><br>
  Drop the G-code, get the price. Orders, filament stock, printers, market stalls and bookkeeping in one place.<br>
  Self-hosted on Proxmox (one command) or Docker. In English or Spanish.
</p>

<p align="center">
  <a href="https://github.com/Oda615/MiTallercito/actions/workflows/ci.yml"><img src="https://github.com/Oda615/MiTallercito/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/Oda615/MiTallercito/releases"><img src="https://img.shields.io/github/v/release/Oda615/MiTallercito?include_prereleases&label=release&color=3fae6a" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Oda615/MiTallercito" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/Proxmox-LXC-E57000?logo=proxmox&logoColor=white" alt="Proxmox LXC">
  <img src="https://img.shields.io/badge/Docker-amd64%20%7C%20arm64-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Klipper%20%C2%B7%20OctoPrint%20%C2%B7%20PrusaLink-B12F36" alt="Klipper, OctoPrint, PrusaLink">
</p>

<p align="center">
  <a href="#-install">Install</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-screenshots">Screenshots</a> ·
  <a href="#-updates">Updates</a> ·
  <a href="#-printers-on-another-network-the-bridge">Bridge</a> ·
  <a href="#-español">Español</a>
</p>

<p align="center">
  <img src="docs/assets/demo.gif" width="860" alt="Import a G-code and get the price">
</p>

*"Mi tallercito" is Spanish for "my little workshop". The screenshots show the Spanish UI; the app is fully translated and you pick the language in the first-run wizard.*

---

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 🧮 Price calculator
Material per colour (or the cost your slicer already gives you), electricity, machine amortisation and maintenance, your time, failure risk, margin, marketplace fees, VAT, minimum price and rounding. Total **with and without VAT**, and what you earn. Type **your own price** to see the profit, % on cost and break-even price.

</td>
<td width="50%" valign="top">

### 📂 Slicer import
Drop the `.gcode` or sliced `.3mf` (Orca, Snapmaker Orca, Anycubic Slicer Next, Bambu Studio, PrusaSlicer, Cura): time, grams per colour, cost and print settings fill in by themselves. Parsed in the browser; the file is not uploaded.

</td>
</tr>
<tr>
<td valign="top">

### 📦 Orders
Every line with its **print sheet** (layer height, infill, walls, nozzle, supports, profile) and its STL/3MF/G-code files. One-click "repeat order". PDF quotes and delivery notes with your logo. Statuses from received to delivered, with history.

</td>
<td valign="top">

### 🏠 Home
Upcoming deliveries (and late ones), what is still unpaid, this month vs. last month, printers running, low stock, maintenance due and best sellers.

</td>
</tr>
<tr>
<td valign="top">

### 🏪 Market stalls
Fairs, markets, meetups: tap products, pick cash, card or Bizum and charge. **Anonymous sales**, no details needed. Each stall keeps its cash box (starting change, expected cash, count when you close), its cost, and what you took and should bring back. A sticky checkout bar on mobile. "Make for stock" adds to product stock once printed.

</td>
<td valign="top">

### 👥 Customers
Customer cards created automatically from orders, with history, what they spent and what they owe, plus "new order" and "repeat the last one". Autocomplete in the order form.

</td>
</tr>
<tr>
<td valign="top">

### 🧵 Spool stock room
Every spool with material, brand, colour and weight, added in one step (a new material is created on the fly) or by **pasting the Amazon link or title**. Deducted automatically when printing; weigh it to fine-tune. When it runs out you note the empty weight and it learns **each brand's spool weight**. See your colours at a glance and whether **a multicolour model can be printed** with what you have. A **shopping list** built from the filament forecast, with suppliers and **price history** per material.

</td>
<td valign="top">

### 🔧 Printer maintenance
Tasks by print hours, number of prints or days, whichever comes first, with **manufacturer profiles** (Bambu, Prusa, Creality, Snapmaker, Anycubic, Elegoo, resin, generic FDM). Hours come from Moonraker (including past history) or, without a connection, from orders and failed prints.

</td>
</tr>
<tr>
<td valign="top">

### 🖨️ Klipper, OctoPrint, PrusaLink
Any printer running Moonraker (Klipper), OctoPrint or PrusaLink, each with its own IP: live status, finish time, history with **real time and filament** linked to each order, and send G-code from the order. Printers on another network work through the **bridge** (no VPN).

</td>
<td valign="top">

### 📲 Telegram alerts
A bot that tells you about new orders, deliveries due, low stock, maintenance due and **orders stuck too long in a status** (a limit per status).

</td>
</tr>
<tr>
<td valign="top">

### 🗄️ Home workshop organisation
Components and hardware (springs, screws, inserts, magnets…) with stock and unit cost from the pack. A **recipe** per item: printed pieces, components and assembly steps with photos. **What am I missing to make N?** checks filament and components and sends what is missing to the shopping list. **Locations with QR labels** (shelves, drawers, boxes): scan to see what is inside and recount. Finished goods with a minimum and restock suggestions.

</td>
<td valign="top">

### 💶 Bookkeeping
Income when paid, expenses, who paid what (to split between partners), CSV export. **Fixed expenses** (self-employed fee, domain, rent…) booked automatically each month, quarter or year. **Monthly report** with electricity kWh and €, material, machine and labour hours, VAT and profit. A **Failed** button records the % reached and books the wasted material and cost.

</td>
</tr>
<tr>
<td valign="top">

### 🔐 Built to live on the internet
Users with roles, login rate limiting, secure cookies behind a proxy, a protected first run and **signed updates** (Ed25519) applied by a separate service. The web app never runs as root.

</td>
</tr>
</table>

Also: **product variants** (colours, sizes) with their own price and stock; **bundles and offers** ("3 for €10", "second one half price") applied automatically at the stall; **QR labels** for spools that open the spool on your phone when scanned; a **filament forecast** that tells you what will run out and how much to buy; **Manyfold** integration to pull model files into orders and products; **kits** that group catalog pieces, extra parts (springs, screws…), instructions and all files in one .zip; your branding (name, logo, favicon, colour); a product catalog with photos and prices you can recalculate in one go; and the groundwork for a future online shop (public catalog API, off by default).

## 📸 Screenshots

| Home | Calculator with your own price |
|---|---|
| ![Home](docs/screenshots/dashboard.png) | ![Calculator with your own price](docs/screenshots/calculator.png) |
| **Components and hardware** | **What am I missing to make 10?** |
| ![Components and hardware](docs/screenshots/components.png) | ![What am I missing to make 10?](docs/screenshots/needs.png) |
| **Item recipe** | **Finished goods and restock** |
| ![Item recipe](docs/screenshots/kit.png) | ![Finished goods and restock](docs/screenshots/finished.png) |
| **Shopping list** | **Search (Ctrl+K)** |
| ![Shopping list](docs/screenshots/shopping.png) | ![Search (Ctrl+K)](docs/screenshots/search.png) |
| **Order with print sheet and files** | **Monthly report** |
| ![Order with print sheet and files](docs/screenshots/order.png) | ![Monthly report](docs/screenshots/monthly-report.png) |
| **Market stall sale** | **Customer card** |
| ![Market stall sale](docs/screenshots/stall-sale.png) | ![Customer card](docs/screenshots/customer.png) |
| **Spool stock room and forecast** | **Printer maintenance** |
| ![Spool stock room and forecast](docs/screenshots/stock.png) | ![Printer maintenance](docs/screenshots/maintenance.png) |
| **QR labels for spools** | **Pull files from Manyfold** |
| ![QR labels for spools](docs/screenshots/spool-labels.png) | ![Pull files from Manyfold](docs/screenshots/manyfold.png) |
| **Catalog** | **First run (English)** |
| ![Catalog](docs/screenshots/catalog.png) | ![First run (English)](docs/screenshots/setup-en.png) |

<p align="center"><img src="docs/screenshots/home-mobile.png" width="250" alt="Home on a phone"> <img src="docs/screenshots/stall-mobile.png" width="250" alt="Selling on a phone"> <img src="docs/screenshots/location-mobile.png" width="250" alt="Scanning a drawer's QR"></p>

## 🚀 Install

### Proxmox VE (LXC), recommended
On the Proxmox **host** shell:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/ct/mitallercito.sh)"
```
It uses the [community-scripts](https://community-scripts.org) engine, so it looks and behaves like any Proxmox VE Helper-Script: **Default** (1 CPU, 512 MB, 4 GB, Debian 13, unprivileged) or **Advanced** (ID, storage, static IP, VLAN, IPv6, SSH, resources…). At the end it prints the **first-run link**:

```
http://192.168.1.50:8080/#setup=…
```

To update later, run `update` in the container console.

<details><summary>Offline or unattended install (classic installer)</summary>

`tools/mitallercito-lxc.sh` does not depend on community-scripts. It is attached to every release as `mitallercito-lxc.sh`:

```bash
bash mitallercito-lxc.sh --file mitallercito-0.9.0.mtc          # no internet needed for the app
MT_NONINTERACTIVE=1 CTID=120 IPCFG=192.168.1.50/24,gw=192.168.1.1 VLAN=20 bash mitallercito-lxc.sh
bash mitallercito-lxc.sh --help
```
If anything fails it removes the half-built container (`MT_KEEP=1` keeps it).
</details>

Open it and create your user, printers, materials and prices. Done.

### Docker
```bash
curl -fsSLO https://raw.githubusercontent.com/Oda615/MiTallercito/main/docker-compose.yml
docker compose up -d
docker compose logs mitallercito | grep setup     # first-run link
```

### Putting it on the internet
Point your reverse proxy (Nginx Proxy Manager, Caddy, Traefik…) at `http://IP:8080` with HTTPS. If you also proxy through Cloudflare (orange cloud), set `MT_PROXY_HOPS=2` in `/etc/default/mitallercito` (LXC) or in the `environment` (Docker).

## 🔄 Updates

From the app itself, **System** tab:

| Channel | Installs | Signature |
|---|---|---|
| **Releases** (default) | The latest version from [Releases](https://github.com/Oda615/MiTallercito/releases) | ✅ Ed25519 |
| **main branch** | Whatever is on the repo, without waiting for a release | ❌ (only on installs without a key) |

The database is backed up first and, if the new version fails to start, it rolls back on its own. You can also upload a package by hand, run `update` in the container console, or update from the host:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/tools/mitallercito-lxc.sh)" -- update <CTID>
```

## 🛰️ Printers on another network: the bridge

```mermaid
flowchart LR
  subgraph Shop["Workshop network"]
    P1["🖨️ Klipper"] --- B["Bridge<br/>(Raspberry Pi, NAS…)"]
    P2["🖨️ Klipper"] --- B
  end
  B -- "Outbound HTTPS<br/>(no open ports)" --> T["MiTallercito<br/>(Proxmox / Docker / VPS)"]
```

**Settings → Bridges → Create bridge**, copy the command and run it on any always-on Linux box in that network:
```bash
curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/bridge/install-bridge.sh | sudo bash -s -- --url https://your-shop.example --token mtb_…
```
Then set those printers to *Connection = Bridge* with their local IP. More in [bridge/README.md](bridge/README.md).

## 🛠️ Management (inside the LXC)

```
mitallercito adduser <name> [--admin]   mitallercito passwd <name>   mitallercito users
mitallercito setup-token                mitallercito backup          mitallercito logs
```
Data lives in `/var/lib/mitallercito` (SQLite database, files and daily backups). Include the container in your Proxmox backups.

## 🔒 Security

- **First run** protected by a one-time code: nobody on your network can get there first and make themselves admin.
- **Updates**: the web app only drops the package in a folder. `mitallercito-updater` (root, systemd) checks the signature against the key pinned at install time, accepts only app files (no links or odd paths), backs up the database and rolls back if anything fails. Neither the verifier nor the key can be changed from the web.
- Printer API keys never reach the browser; bridge tokens are stored hashed.
- Found something? See [SECURITY.md](SECURITY.md).

## 🧑‍💻 Development

```bash
pip install -r requirements.txt pytest
MT_DATA_DIR=/tmp/mt python app.py               # http://127.0.0.1:8080
MT_DATA_DIR=/tmp/mt python tools/demo_data.py   # sample data (demo / demo1234)
python -m pytest -q tests
```
How to publish signed releases and contribute: [CONTRIBUTING.md](CONTRIBUTING.md).

## 🗺️ Roadmap

- [ ] Order tracking page for customers
- [ ] Two-factor authentication (TOTP)
- [ ] Online shop front on top of the public API

Ideas? Open an [issue](https://github.com/Oda615/MiTallercito/issues/new/choose).

## 📄 License

[MIT](LICENSE). Use it, change it and set up your own little workshop.

---

<details>
<a id="-español"></a>
<summary><b>🇪🇸 Español</b></summary>

## MiTallercito
**La app para llevar tu tallercito de impresión 3D.** Sueltas el G-code y te dice cuánto cobrar. Pedidos, stock de filamento, impresoras, puestos y cuentas en un solo sitio. Autoalojada en tu Proxmox (un comando) o con Docker. La interfaz está en español y en inglés: se elige en el primer arranque.

### ✨ Qué hace

<table>
<tr>
<td width="50%" valign="top">

#### 🧮 Calculadora de precios
Material (por color, o el coste que ya te da el laminador), luz, amortización y mantenimiento de la máquina, tu tiempo, riesgo de fallo, margen, comisiones de Wallapop/Etsy, IVA, precio mínimo y redondeo. Total **sin IVA y con IVA**, y lo que ganas. Pon **tu propio precio** y ves lo que te queda, el % sobre el coste y el mínimo para no perder.

</td>
<td width="50%" valign="top">

#### 📂 Importar del laminador
Arrastra el `.gcode` o el `.3mf` laminado (Orca, Snapmaker Orca, Anycubic Slicer Next, Bambu Studio, PrusaSlicer, Cura): tiempo, gramos por color, coste y ajustes de impresión se rellenan solos. Se lee en el navegador; el archivo no se sube.

</td>
</tr>
<tr>
<td valign="top">

#### 📦 Pedidos
Cada línea con su **ficha de impresión** (capa, relleno, perímetros, boquilla, soportes, perfil) y sus archivos STL/3MF/G-code. «Repetir pedido» en un clic. Presupuestos y albaranes en PDF con tu logo.

</td>
<td valign="top">

#### 🏠 Inicio
Próximas entregas (y las que se te pasan), lo que falta por cobrar, cómo va el mes frente al anterior, impresoras en marcha, stock bajo y lo más vendido.

</td>
</tr>
<tr>
<td valign="top">

#### 🗄️ Organización del taller
Componentes y ferretería (muelles, tornillos, insertos, imanes…) con stock y coste por unidad sacado del pack. **Receta** de cada artículo: piezas impresas, componentes y pasos de montaje con fotos. **¿Qué me falta para hacer N?** compara filamento y componentes y manda lo que falta a la lista de la compra. **Ubicaciones con QR** (estanterías, cajones, cajas): escaneas y ves qué hay dentro y recuentas. Producto terminado con mínimo y propuesta de reposición.

</td>
<td valign="top">

#### 💶 Cuentas
Ingresos al cobrar, gastos, quién ha pagado qué (para ir a medias entre socios), exportación CSV. **Gastos fijos** (cuota de autónomo, dominio, alquiler…) que se apuntan solos cada mes, trimestre o año. **Extracto mensual** con kWh y € de luz, material, horas de máquina y de mano de obra, IVA y beneficio.

</td>
<td valign="top">

#### 🧵 Almacén de bobinas
Cada bobina con material, marca, color y peso, dada de alta en un solo paso (el material nuevo se crea a la vez) o **pegando el enlace o el título de Amazon**. Se descuenta sola al imprimir; para afinar, la pesas. Al gastarla apuntas lo que pesa vacía y se aprende **la tara de cada marca**. Ves de un vistazo los colores que tienes y si **un modelo multicolor se puede imprimir** con lo que hay. **Lista de la compra** sacada de la previsión, con proveedores e **historial de precios** de cada material.

</td>
</tr>
<tr>
<td valign="top">

#### 🖨️ Impresoras: Klipper, OctoPrint, PrusaLink
Cualquier impresora con Moonraker (Klipper), OctoPrint o PrusaLink, cada una con su IP: estado en vivo, hora a la que termina, historial con **tiempo y filamento reales** asignado a cada pedido, y enviar G-code desde el pedido. Si están en otra red, con el **puente** (sin VPN).

</td>
</tr>
<tr>
<td valign="top">

#### 🔐 Hecho para dejarlo en internet
Usuarios con roles, límite de intentos de login, cookies seguras detrás de proxy, primer arranque protegido y **actualizaciones firmadas** (Ed25519) aplicadas por un servicio aparte. La web nunca corre como root.

</td>
</tr>
<tr>
<td valign="top">

#### 📲 Avisos por Telegram
Estados de pedido (recibido, programado, imprimiendo, postprocesado, listo…) y un bot que avisa de pedidos nuevos, entregas cerca, stock bajo y **pedidos que llevan demasiado en un estado** (límite por estado).

</td>
<td valign="top">

#### 🧩 Conjuntos y fallos
**Conjuntos** de catálogo que agrupan piezas, material extra (muelles, tornillos…), instrucciones y todos los archivos en un .zip. Botón **Fallo**: dices a qué % se paró y se resta el material y el coste perdidos.

</td>
</tr>
<tr>
<td valign="top">

#### 🏪 Venta en puestos
Mercadillos, ferias, quedadas: tocas los productos, eliges efectivo, tarjeta o Bizum y cobras. **Venta anónima** sin pedir datos. Cada puesto lleva su caja (cambio inicial, lo que debería haber, cuadre al cerrar), su coste y lo que te llevaste y tiene que volver. «Fabricar para stock» suma al stock del producto cuando está listo.

</td>
<td valign="top">

#### 👥 Clientes y mantenimiento
**Fichas de cliente** con historial, lo que ha gastado y lo que debe, y «repetir el último». **Mantenimiento** de cada impresora por horas, impresiones o días, con perfiles de los fabricantes (Bambu, Prusa, Creality, Snapmaker, Anycubic, Elegoo, resina): cuenta las horas con Moonraker o con los pedidos y fallos, y avisa por Telegram.

</td>
</tr>
</table>

También: **variantes** de producto (colores, tamaños) con su precio y stock; **packs y ofertas** («3 por 10 €», «la 2ª a mitad») que se aplican solas al cobrar; **etiquetas QR** en las bobinas que al escanearlas abren la bobina en el móvil; **previsión de filamento** que avisa de lo que se va a acabar y cuánto comprar; e integración con **Manyfold** para traer los archivos del modelo a pedidos y productos. Interfaz en **español o inglés** (se elige en el primer arranque), tu marca (nombre, logo, favicon, colores), catálogo de productos con fotos y precios recalculables de golpe, y la base preparada para una futura tienda online (API pública de catálogo, desactivada por defecto).

### 📸 Capturas

| Inicio | Calculadora con tu propio precio |
|---|---|
| ![Inicio](docs/screenshots/dashboard.png) | ![Calculadora con tu propio precio](docs/screenshots/calculator.png) |
| **Componentes y ferretería** | **¿Qué me falta para hacer 10?** |
| ![Componentes y ferretería](docs/screenshots/components.png) | ![¿Qué me falta para hacer 10?](docs/screenshots/needs.png) |
| **Receta de un artículo** | **Producto terminado y reposición** |
| ![Receta de un artículo](docs/screenshots/kit.png) | ![Producto terminado y reposición](docs/screenshots/finished.png) |
| **Lista de la compra** | **Buscador (Ctrl+K)** |
| ![Lista de la compra](docs/screenshots/shopping.png) | ![Buscador (Ctrl+K)](docs/screenshots/search.png) |
| **Pedido con ficha y archivos** | **Extracto mensual** |
| ![Pedido con ficha y archivos](docs/screenshots/order.png) | ![Extracto mensual](docs/screenshots/monthly-report.png) |
| **Venta en un puesto** | **Ficha de cliente** |
| ![Venta en un puesto](docs/screenshots/stall-sale.png) | ![Ficha de cliente](docs/screenshots/customer.png) |
| **Almacén de bobinas y previsión** | **Mantenimiento de impresoras** |
| ![Almacén de bobinas y previsión](docs/screenshots/stock.png) | ![Mantenimiento de impresoras](docs/screenshots/maintenance.png) |
| **Etiquetas QR de bobinas** | **Traer archivos de Manyfold** |
| ![Etiquetas QR de bobinas](docs/screenshots/spool-labels.png) | ![Traer archivos de Manyfold](docs/screenshots/manyfold.png) |
| **Catálogo** | **Primer arranque** |
| ![Catálogo](docs/screenshots/catalog.png) | ![Primer arranque](docs/screenshots/setup.png) |

<p align="center"><img src="docs/screenshots/home-mobile.png" width="250" alt="Inicio en el móvil"> <img src="docs/screenshots/stall-mobile.png" width="250" alt="Cobrando con el móvil"> <img src="docs/screenshots/location-mobile.png" width="250" alt="Escaneando el QR de un cajón"></p>

### 🚀 Instalación

#### Proxmox VE (LXC), lo recomendado
En la consola del **host** Proxmox:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/ct/mitallercito.sh)"
```
Usa el motor de [community-scripts](https://community-scripts.org), así que se ve y funciona como cualquier Helper-Script de Proxmox: modo **por defecto** (1 CPU, 512 MB, 4 GB, Debian 13, sin privilegios) o **avanzado** (ID, almacenamiento, IP fija, VLAN, IPv6, SSH, recursos…). Al final te da el **enlace de primer arranque**:

```
http://192.168.1.50:8080/#setup=…
```

Para actualizar después, escribe `update` en la consola del contenedor.

<details><summary>Instalación sin conexión o desatendida (instalador clásico)</summary>

`tools/mitallercito-lxc.sh` no depende de community-scripts. Va adjunto a cada versión como `mitallercito-lxc.sh`:

```bash
bash mitallercito-lxc.sh --file mitallercito-0.9.0.mtc          # la app no necesita internet
MT_NONINTERACTIVE=1 CTID=120 IPCFG=192.168.1.50/24,gw=192.168.1.1 VLAN=20 bash mitallercito-lxc.sh
bash mitallercito-lxc.sh --help
```
Si algo falla, borra el contenedor a medio hacer (`MT_KEEP=1` lo conserva).
</details>

Ábrelo y crea tu usuario, impresoras, materiales y precios. Listo.

#### Docker
```bash
curl -fsSLO https://raw.githubusercontent.com/Oda615/MiTallercito/main/docker-compose.yml
docker compose up -d
docker compose logs mitallercito | grep setup     # enlace de primer arranque
```

#### Publicarla en internet
Apunta tu proxy inverso (Nginx Proxy Manager, Caddy, Traefik…) a `http://IP:8080` con HTTPS. Si además usas Cloudflare como proxy (nube naranja), pon `MT_PROXY_HOPS=2` en `/etc/default/mitallercito` (LXC) o en el `environment` (Docker).

### 🔄 Actualizaciones

Desde la propia web, pestaña **Sistema**:

| Canal | Qué instala | Firma |
|---|---|---|
| **Versiones publicadas** (por defecto) | La última versión de [Releases](https://github.com/Oda615/MiTallercito/releases) | ✅ Ed25519 |
| **Rama main** | Lo último subido al repo, sin esperar a una versión | ❌ (solo en instalaciones sin clave) |

Antes de instalar se copia la base de datos y, si la versión nueva no arranca, vuelve sola a la anterior. También se puede subir un paquete a mano, escribir `update` en la consola del contenedor o actualizar desde el host:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/tools/mitallercito-lxc.sh)" -- update <CTID>
```

### 🛰️ Impresoras en otra red: el puente

```mermaid
flowchart LR
  subgraph Taller["Red del taller"]
    P1["🖨️ Klipper"] --- B["Puente<br/>(Raspberry Pi, NAS…)"]
    P2["🖨️ Klipper"] --- B
  end
  B -- "HTTPS saliente<br/>(sin abrir puertos)" --> T["MiTallercito<br/>(Proxmox / Docker / VPS)"]
```

**Ajustes → Puentes → Crear puente**, copia el comando y ejecútalo en cualquier Linux siempre encendido de esa red:
```bash
curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/bridge/install-bridge.sh | sudo bash -s -- --url https://tu-taller.ejemplo --token mtb_…
```
Luego, en esas impresoras: *Conexión = Puente* y su IP local. Más en [bridge/README.md](bridge/README.md).

### 🛠️ Gestión (dentro del LXC)

```
mitallercito adduser <nombre> [--admin]   mitallercito passwd <nombre>   mitallercito users
mitallercito setup-token                  mitallercito backup            mitallercito logs
```
Los datos viven en `/var/lib/mitallercito` (base de datos SQLite, archivos y copias diarias). Mete el contenedor en tus backups de Proxmox.

### 🔒 Seguridad

- **Primer arranque** con código de un solo uso: nadie de tu red puede adelantarse y hacerse administrador.
- **Actualizaciones**: la web solo deja el paquete en una carpeta. `mitallercito-updater` (root, systemd) comprueba la firma con la clave fijada al instalar, acepta solo ficheros de la app (sin enlaces ni rutas raras), copia la base de datos y vuelve atrás si algo falla. Ni el verificador ni la clave se pueden cambiar desde la web.
- Las API keys de las impresoras nunca llegan al navegador; los tokens de los puentes se guardan como hash.
- ¿Has encontrado algo? Mira [SECURITY.md](SECURITY.md).

### 🧑‍💻 Desarrollo

```bash
pip install -r requirements.txt pytest
MT_DATA_DIR=/tmp/mt python app.py               # http://127.0.0.1:8080
MT_DATA_DIR=/tmp/mt python tools/demo_data.py   # datos de ejemplo (demo / demo1234)
python -m pytest -q tests
```
Cómo publicar versiones firmadas y cómo colaborar: [CONTRIBUTING.md](CONTRIBUTING.md).

### 🗺️ Hoja de ruta

- [ ] Página de seguimiento del pedido para el cliente
- [ ] Doble factor (TOTP)
- [ ] Escaparate de tienda online sobre la API pública

¿Ideas? Abre un [issue](https://github.com/Oda615/MiTallercito/issues/new/choose).

### 📄 Licencia

[MIT](LICENSE). Úsala, cámbiala y monta tu tallercito.

</details>
