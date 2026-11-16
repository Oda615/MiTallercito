# Changelog


## [Sin publicar]
- **Pedidos: descripción libre por línea.** Cada línea tiene «Producto» (se autocompleta con el catálogo y, al elegir uno, coge su precio y su coste) y debajo una descripción libre de varias líneas para lo que quieras (colores, grabados, entrega…). Sale en el presupuesto y el albarán respetando los saltos de línea, se copia al repetir el pedido y no cambia la descripción del producto en el catálogo.
- Instalador: rótulo «MiTallercito» en lugar del genérico de community-scripts.

## [1.0.0]
Primera versión estable. Reúne todo lo que se preparó como 0.8 y 0.9 (nunca se publicaron) y añade la organización del taller en casa.

### Organización del taller
- **Componentes y ferretería** (Almacén → Componentes): muelles, tornillos, insertos, imanes, cajas, bolsas, pintura… con stock, unidad, coste por unidad sacado del pack, mínimo, ubicación, proveedor y enlace de compra. Entradas con gasto en contabilidad, recuento rápido y «pegar de Amazon» (nombre, precio y unidades del pack). Los que llegan al mínimo se sugieren en la lista de la compra y se avisan en Inicio.
- **Receta de cada artículo**: piezas impresas, componentes por unidad (enlazados al almacén o en texto libre) y pasos de montaje con fotos. El coste del producto incluye los componentes; los pedidos y «Fabricar para stock» los descuentan solos (las ventas de puesto no, porque salen de producto ya hecho).
- **¿Qué me falta para hacer N?**: compara filamento y componentes con lo que tienes, manda lo que falta a la lista de la compra en envases enteros y crea el pedido de fabricación.
- **Ubicaciones con QR**: estanterías, cajoneras, cajas y cajones unos dentro de otros, con etiquetas QR. Al escanearlas ves qué hay dentro (componentes, bobinas y producto terminado) y recuentas en el momento. El buscador dice dónde está cada cosa.
- **Producto terminado y reposición**: cuánto tienes hecho y dónde, mínimo por artículo, y propuesta de qué fabricar para reponer (también en Inicio).
- Almacén se organiza en pestañas: Filamento, Componentes, Terminado, Ubicaciones y Compra.

### Interfaz y día a día
- **Interfaz nueva**: menú lateral agrupado (Vender, Taller, Cuentas, Sistema) con iconos; en el móvil, barra inferior (Inicio, Venta, Pedidos, Almacén, Más) y menú desplegable. Tipografía, espaciado y tablas más limpias; tema claro/oscuro automático.
- **Móvil de verdad**: las tablas se convierten en tarjetas con cada dato etiquetado, botones más grandes y sin desplazamiento horizontal.
- **Formularios propios**: se acabaron las ventanitas del navegador. Pesar bobina, entrada de material, fallos, puestos, mantenimiento… ahora son un único formulario dentro de la app, y los borrados piden confirmación en rojo.
- **Buscador global** (Ctrl+K o «/», o la lupa en el móvil): pedidos, clientes, productos, bobinas, materiales, impresoras y puestos, más acciones rápidas (nuevo pedido, apuntar gasto, lista de la compra…).
- **Lista de la compra** en Almacén: sugerencias de la previsión de filamento, proveedor, precio estimado y total; «Comprado» rellena el alta de bobinas, y «Copiar lista» la agrupa por proveedor.
- **Historial de precios** por material (más barato, media, más caro y mejor precio por proveedor). Las bobinas y entradas guardan el proveedor y, si quieres, actualizan el precio del material.
- **Gastos fijos** en Contabilidad: cuota de autónomo, dominio, alquiler… mensuales, trimestrales, semestrales o anuales. Se apuntan solos el día que toca, sin duplicarse, y se pueden pausar.
- **Alta de bobinas en un solo paso**: en «Añadir bobinas» eliges «＋ Nuevo material…», pones el tipo (PLA, PETG, Resina…) y el nombre se rellena solo («PETG azul»). El material se crea con la bobina, con el precio de lo pagado; ya no hace falta pasar antes por Ajustes. El tono se pone solo según el nombre del color.
- **Pegar de Amazon o de la tienda**: pegas el enlace o el título del producto y rellena tipo, marca, color, peso, cuántas y precio. Si la ficha no se deja leer (captcha), lo saca del propio enlace. En los packs de varios colores, «Añadir una bobina de cada color» las da de alta por separado (creando los materiales que falten) y reparte lo pagado.
- **Instalador del LXC nuevo**, con el motor de community-scripts (Proxmox VE Helper-Scripts): modo por defecto o avanzado (almacenamiento, IP fija, VLAN, IPv6, SSH…), Debian 13 y comando `update` dentro del contenedor. Los archivos ya siguen su formato para proponerla cuando cumpla sus requisitos (ver `docs/community-scripts.md`).
- **Instalador clásico** (`tools/mitallercito-lxc.sh`, adjunto a cada versión): Debian 13 con vuelta a 12 si el Proxmox no la ofrece, VLAN, `--help`, valida IP y recursos, comprueba que la web responde y, si algo falla, borra el contenedor a medio hacer (`MT_KEEP=1` lo conserva). Las órdenes antiguas (`-- update <CTID>`, `--file`) siguen funcionando.
- **Calculadora: tu propio precio**. Si no quieres el precio calculado, pon el tuyo y ves lo que ganas (total y por pieza), el % sobre el coste, IVA, comisión, la diferencia con el calculado y el mínimo para no perder. Al guardar en el catálogo o añadir al pedido se usa tu precio.

### Ventas, catálogo y almacén
- **Variantes de producto**: colores, tamaños… cada una con su precio y su stock (el del producto es la suma). Se eligen al vender en un puesto, al añadir al pedido y al «Fabricar para stock»; la variante puede usar otro material, y se descuenta ese color.
- **Packs y ofertas**: «N por X €», «la N-ésima con descuento» (p. ej. la 2ª a mitad) y «% de descuento», por producto, categoría o todo el catálogo, solo en puestos, solo en pedidos o en ambos. En la venta se aplican solas; en los pedidos, con «Aplicar ofertas».
- **Etiquetas QR de bobinas**: hoja A4 (3×8) o rollos de 62×29, 50×30 y 40×30 mm. Al escanear el QR con el móvil se abre esa bobina para pesarla, darla por gastada o editarla. Al añadir bobinas, ofrece imprimir sus etiquetas.
- **Manyfold**: busca modelos en tu biblioteca y trae sus archivos a pedidos y productos. Lo hace el servidor con OAuth (client credentials, permiso «read»): el navegador nunca ve Manyfold.
- **Previsión de filamento**: lo que piden los pedidos pendientes frente a lo que queda, el gasto diario reciente, cuándo se acaba y cuántas bobinas comprar. Aviso en Inicio y por Telegram.
- La versión publicada incluye también el script del host (`mitallercito-lxc.sh`).
- En el móvil, las tablas anchas se desplazan dentro de su tarjeta en vez de ensanchar la página.
- Dependencias al día: Flask 3.1.3, gunicorn 27, `segno` (QR) y Python 3.15 en Docker.

### Arreglos
- Manyfold: la app se identifica como `MiTallercito/<versión>` en vez de `Python-urllib`, que Cloudflare bloquea con un 403 (error 1010). Si un proxy o Cloudflare bloquea la petición, el error lo dice y propone usar la dirección interna de Manyfold.
- Manyfold por IP: los archivos se descargan siempre del servidor configurado aunque Manyfold dé los enlaces con su dominio público (antes daba «esa dirección no es de tu Manyfold»). Los nombres con puntos («Buffer 1.5») conservan su extensión.

## [0.7.0]
- **Venta en puestos** (pestaña Venta): cobro rápido tocando productos, efectivo/tarjeta/Bizum/transferencia, venta anónima o con cliente. Puestos con caja (cambio inicial, lo esperado y cuadre al cerrar), coste del puesto como gasto, beneficio, y «lo que llevas» frente a lo vendido. Barra de cobro fija en el móvil. «Deshacer» devuelve al stock.
- **Fabricar para stock**: desde la ficha de un producto se crea un pedido «Para stock» que, al pasar a «listo», suma las unidades al stock del producto (y descuenta material y horas como cualquier pedido).
- **Clientes**: fichas creadas solas desde los pedidos (también los antiguos), con historial, gastado, pendiente, «nuevo pedido» y «repetir el último». Autocompletar el cliente en los pedidos.
- **Mantenimiento de impresoras**: tareas por horas de impresión, impresiones o días (lo que llegue antes); perfiles con los intervalos de los fabricantes (Bambu A1 y X1/P1/P2, Prusa MK4 y XL, Creality K1 y Ender-3 V3, Snapmaker U1, Anycubic Kobra S1, Elegoo Centauri Carbon, resina y FDM genérica). Las horas salen de Moonraker (incluido el histórico anterior) o, sin conexión, de los pedidos y fallos; se pueden sumar a mano. Aviso en Inicio y por Telegram.
- **OctoPrint y PrusaLink**: además de Moonraker, estado en vivo de cualquier impresora con OctoPrint o PrusaLink (API key o usuario:contraseña).
- La pestaña «Mantenimiento» de la app pasa a llamarse **Sistema** (actualizaciones y copias).

## [0.6.0]
- **Almacén de bobinas**: cada rollo con material, marca, color (nombre y tono), peso, bobina vacía, ubicación y estado. Paleta con los colores que tienes y lo que queda en cada uno.
- **Pesar bobinas**: lo que queda = peso − bobina vacía. Al gastar o borrar una bobina se pide el peso de la bobina vacía y se aprende para esa marca y material.
- **¿Lo puedo imprimir?**: compara los colores y gramos de un modelo (o del 3MF/G-code importado) con lo que hay en el almacén; la calculadora elige sola la bobina de cada color.
- **Estados de pedido**: presupuesto, recibido, programado, imprimiendo, postprocesado, listo, entregado, cancelado; con historial y tiempo en cada estado.
- **Avisos por Telegram**: pedido atascado más tiempo del debido en un estado (límites configurables), pedido nuevo, entrega hoy/mañana o pasada, stock bajo.
- **Fallos de impresión**: botón «Fallo» con el porcentaje alcanzado; descuenta el material perdido del stock y lo resta del beneficio y del extracto.
- **Conjuntos** en el catálogo: varias piezas, material extra (muelles, tornillos…), instrucciones y «Descargar todo (.zip)». Al añadirlos a un pedido heredan los archivos de sus piezas.
- Los avisos se revisan cada 10 minutos con un temporizador nuevo (`mitallercito-notify.timer`). Ajustes muestra cuándo fue la última revisión. **Si vienes de una versión anterior, actualiza esta vez desde el host de Proxmox** para que se cree el temporizador.

## [0.5.0] – MiTallercito
- Nuevo nombre (antes «Tienda 3D»; las instalaciones anteriores se migran solas).
- Pantalla de Inicio, interfaz en inglés y español, asistente de primer arranque.
- Instalación desde GitHub, actualizaciones firmadas (Ed25519) o desde la rama main.
- Puente para impresoras en otra red, Docker, tests y CI.

## [0.4.0]
- Impresoras Klipper/Moonraker: estado, historial real, enviar G-code. Calculadora con total sin y con IVA.

## [0.3.0]
- Importar G-code/3MF, archivos y ficha por pedido, repetir pedido, stock, roles, mantenimiento.

## [0.2.0]
- Extracto mensual, marca, presupuestos y albaranes en PDF, catálogo para tienda online.

## [0.1.0]
- Calculadora de precios, pedidos y contabilidad.
